import datetime
import json
import logging
from typing import List, Dict, Any, Optional

from app.models.database import (
    get_syllabus_hierarchy,
    get_syllabus_resources,
    save_study_plan,
    save_study_tasks,
    get_active_study_plan,
    get_study_plan_by_id,
    get_plan_tasks,
    update_task_completion,
    update_task_note,
    reschedule_plan_tasks,
)
from app.schemas.study_plan import (
    TaskItemSchema,
    DailyScheduleGroup,
    StudyPlanResponse,
)

logger = logging.getLogger("syllabus_sync.planner")

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class StudyPlannerService:
    """
    Deterministic Study Planning and Adaptive Rescheduling Service.
    Calculates realistic study slots, respects daily availability limits,
    preserves completed task history, and provides honest shortfall calculations.
    """

    @classmethod
    def _parse_date(cls, date_str: str) -> datetime.date:
        return datetime.date.fromisoformat(date_str)

    @classmethod
    def _format_day_name(cls, dt: datetime.date) -> str:
        return WEEKDAY_NAMES[dt.weekday()]

    @classmethod
    def _format_human_date(cls, dt: datetime.date) -> str:
        return dt.strftime("%d %b")

    @classmethod
    async def generate_or_update_plan(
        cls,
        syllabus_id: str,
        exam_date: str,
        daily_target_minutes: int = 120,
        preferred_days: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        preserve_completed: bool = True,
    ) -> StudyPlanResponse:
        """
        Generates a deterministic daily study schedule mapping topics and videos
        into daily slots up to the target exam date.
        """
        hierarchy = get_syllabus_hierarchy(syllabus_id)
        if not hierarchy or not hierarchy.get("modules"):
            raise ValueError(f"Syllabus '{syllabus_id}' has no modules or topics to plan.")

        course_name = hierarchy.get("course_name") or "Course Roadmap"
        preferred_days = preferred_days or WEEKDAY_NAMES
        today = datetime.date.today()
        plan_start = cls._parse_date(start_date) if start_date else today
        plan_exam = cls._parse_date(exam_date)

        if plan_exam <= plan_start:
            raise ValueError(f"Exam date ({exam_date}) must be after the start date ({plan_start.isoformat()}).")

        # Fetch matched videos if available
        resources_data = get_syllabus_resources(syllabus_id)
        topic_to_resource: Dict[str, Any] = {}
        if resources_data and resources_data.get("topic_resources"):
            for tr in resources_data["topic_resources"]:
                if tr.get("resource"):
                    topic_to_resource[tr["topic_id"]] = tr["resource"]

        # Check existing plan
        existing_plan = get_active_study_plan(syllabus_id)
        plan_id = existing_plan["id"] if existing_plan else f"plan_{syllabus_id}"

        # Fetch existing tasks to preserve completions and notes
        existing_tasks = get_plan_tasks(plan_id) if existing_plan else []
        completed_task_map: Dict[str, Dict[str, Any]] = {}
        for t in existing_tasks:
            if t["status"] == "completed" and preserve_completed:
                completed_task_map[t["id"]] = t

        # Build list of planned tasks for all topics in sequential order
        raw_tasks_to_schedule: List[Dict[str, Any]] = []
        modules = hierarchy.get("modules", [])

        for mod_idx, mod in enumerate(modules):
            raw_mod_id = mod.get("id") or f"mod_{mod_idx+1}"
            mod_id = f"{syllabus_id}_{raw_mod_id}" if not raw_mod_id.startswith(syllabus_id) else raw_mod_id
            mod_title = mod.get("title", f"Module {mod_idx+1}")

            for top_idx, topic in enumerate(mod.get("topics", [])):
                raw_top_id = topic.get("id") or f"top_{mod_idx+1}_{top_idx+1}"
                top_id = f"{syllabus_id}_{raw_top_id}" if not raw_top_id.startswith(syllabus_id) else raw_top_id
                top_title = topic.get("title", f"Topic {top_idx+1}")
                difficulty = topic.get("difficulty", "medium")
                est_min = topic.get("estimated_minutes", 60)

                matched_video = topic_to_resource.get(top_id)

                # Task 1: Video lecture
                video_task_id = f"task_{top_id}_video"
                # Video duration from matched metadata, bounded between 15 and 90 min
                if matched_video and matched_video.get("duration_seconds"):
                    v_min = max(15, min(90, matched_video["duration_seconds"] // 60))
                else:
                    v_min = max(20, min(60, est_min // 2))

                raw_tasks_to_schedule.append({
                    "id": video_task_id,
                    "syllabus_id": syllabus_id,
                    "module_id": mod_id,
                    "module_title": mod_title,
                    "topic_id": top_id,
                    "topic_title": top_title,
                    "title": f"Lecture: {top_title}",
                    "task_type": "Video",
                    "duration_minutes": v_min,
                    "video_id": matched_video.get("video_id") if matched_video else None,
                    "video_url": matched_video.get("video_url") if matched_video else None,
                })

                # Task 2: Concept Study & Synthesis
                study_task_id = f"task_{top_id}_study"
                s_min = 25 if difficulty == "easy" else (35 if difficulty == "medium" else 45)
                raw_tasks_to_schedule.append({
                    "id": study_task_id,
                    "syllabus_id": syllabus_id,
                    "module_id": mod_id,
                    "module_title": mod_title,
                    "topic_id": top_id,
                    "topic_title": top_title,
                    "title": f"Study Notes: {top_title}",
                    "task_type": "Study",
                    "duration_minutes": s_min,
                    "video_id": None,
                    "video_url": None,
                })

                # Task 3: Practice Checkpoint
                practice_task_id = f"task_{top_id}_practice"
                p_min = 20 if difficulty == "easy" else (30 if difficulty == "medium" else 45)
                raw_tasks_to_schedule.append({
                    "id": practice_task_id,
                    "syllabus_id": syllabus_id,
                    "module_id": mod_id,
                    "module_title": mod_title,
                    "topic_id": top_id,
                    "topic_title": top_title,
                    "title": f"Practice: {top_title}",
                    "task_type": "Practice",
                    "duration_minutes": p_min,
                    "video_id": None,
                    "video_url": None,
                })

        # Calculate Available Study Days before Exam
        available_calendar_dates: List[datetime.date] = []
        curr_d = plan_start
        while curr_d < plan_exam:
            day_name = cls._format_day_name(curr_d)
            if day_name in preferred_days:
                available_calendar_dates.append(curr_d)
            curr_d += datetime.timedelta(days=1)

        total_workload_minutes = sum(t["duration_minutes"] for t in raw_tasks_to_schedule)
        total_available_minutes = len(available_calendar_dates) * daily_target_minutes

        # Feasibility Analysis
        feasibility_status = "feasible"
        shortfall_minutes = 0
        feasibility_warning = ""

        if total_workload_minutes > total_available_minutes:
            feasibility_status = "impossible"
            shortfall_minutes = total_workload_minutes - total_available_minutes
            shortfall_hours = round(shortfall_minutes / 60, 1)
            workload_hours = round(total_workload_minutes / 60, 1)
            available_hours = round(total_available_minutes / 60, 1)
            feasibility_warning = (
                f"Deadline Shortfall: Course requires {workload_hours}h of study, but only {available_hours}h "
                f"exist across {len(available_calendar_dates)} available study days before {exam_date}. "
                f"Shortfall: {shortfall_hours} hours. Please increase your daily study time or adjust your exam target."
            )
        elif total_workload_minutes > (0.85 * total_available_minutes):
            feasibility_status = "tight"
            workload_hours = round(total_workload_minutes / 60, 1)
            available_hours = round(total_available_minutes / 60, 1)
            cap_pct = round((total_workload_minutes / total_available_minutes) * 100)
            feasibility_warning = (
                f"Tight Schedule: Workload ({workload_hours}h) uses {cap_pct}% of available study capacity ({available_hours}h). "
                f"Stick closely to daily sessions to complete all modules before {exam_date}."
            )

        # Bin-pack tasks into dates
        scheduled_tasks: List[Dict[str, Any]] = []
        day_idx = 0
        current_day_minutes = 0
        current_day_order = 0

        # Separate already completed tasks from pending tasks
        pending_tasks: List[Dict[str, Any]] = []
        for t in raw_tasks_to_schedule:
            if t["id"] in completed_task_map:
                # Keep completed task on its existing scheduled date
                comp = completed_task_map[t["id"]]
                scheduled_tasks.append({
                    **t,
                    "scheduled_date": comp["scheduled_date"],
                    "status": "completed",
                    "completed_at": comp["completed_at"],
                    "notes": comp["notes"],
                    "order_index": comp.get("order_index", 0),
                })
            else:
                pending_tasks.append(t)

        # Distribute pending tasks starting from available_calendar_dates
        if available_calendar_dates:
            for t in pending_tasks:
                if day_idx >= len(available_calendar_dates):
                    # In impossible mode, place remaining tasks on the last available day before exam
                    target_date = available_calendar_dates[-1]
                else:
                    target_date = available_calendar_dates[day_idx]

                scheduled_tasks.append({
                    **t,
                    "scheduled_date": target_date.isoformat(),
                    "status": "pending",
                    "completed_at": None,
                    "notes": None,
                    "order_index": current_day_order,
                })
                current_day_order += 1
                current_day_minutes += t["duration_minutes"]

                if current_day_minutes >= daily_target_minutes:
                    day_idx += 1
                    current_day_minutes = 0
                    current_day_order = 0
        else:
            # Emergency fallback: assign all to plan_start
            for t in pending_tasks:
                scheduled_tasks.append({
                    **t,
                    "scheduled_date": plan_start.isoformat(),
                    "status": "pending",
                    "completed_at": None,
                    "notes": None,
                    "order_index": 0,
                })

        # Save Plan to SQLite
        plan_dict = {
            "id": plan_id,
            "syllabus_id": syllabus_id,
            "title": f"Study Roadmap: {course_name}",
            "exam_date": exam_date,
            "daily_target_minutes": daily_target_minutes,
            "preferred_days": preferred_days,
            "start_date": plan_start.isoformat(),
            "status": "active",
            "feasibility_status": feasibility_status,
            "shortfall_minutes": shortfall_minutes,
            "feasibility_warning": feasibility_warning,
            "total_planned_minutes": total_workload_minutes,
            "completed_minutes": sum(t["duration_minutes"] for t in scheduled_tasks if t["status"] == "completed"),
        }
        save_study_plan(plan_dict)

        # Save Tasks to SQLite
        save_study_tasks(plan_id, scheduled_tasks, preserve_completed=preserve_completed)

        return await cls.get_plan_details(plan_id)

    @classmethod
    async def get_plan_details(cls, plan_id: str) -> StudyPlanResponse:
        """Retrieves a full study plan with daily task groupings and metrics."""
        plan = get_study_plan_by_id(plan_id)
        if not plan:
            # Try finding active plan by syllabus_id
            plan = get_active_study_plan(plan_id)
            if not plan:
                raise ValueError(f"Study plan '{plan_id}' not found.")

        real_plan_id = plan["id"]
        syllabus_id = plan["syllabus_id"]
        hierarchy = get_syllabus_hierarchy(syllabus_id)
        course_name = hierarchy.get("course_name") if hierarchy else "Course"

        raw_tasks = get_plan_tasks(real_plan_id)
        today_iso = datetime.date.today().isoformat()

        # Group tasks by scheduled_date
        date_groups: Dict[str, List[TaskItemSchema]] = {}
        for r in raw_tasks:
            d_str = r["scheduled_date"]
            task_schema = TaskItemSchema(
                id=r["id"],
                plan_id=r["plan_id"],
                syllabus_id=r["syllabus_id"],
                module_id=r["module_id"],
                module_title=r.get("module_title"),
                topic_id=r["topic_id"],
                topic_title=r.get("topic_title"),
                scheduled_date=r["scheduled_date"],
                title=r["title"],
                task_type=r["task_type"],
                duration_minutes=r["duration_minutes"],
                video_id=r.get("video_id"),
                video_url=r.get("video_url"),
                status=r["status"],
                completed_at=r.get("completed_at"),
                notes=r.get("notes"),
                order_index=r.get("order_index", 0),
            )
            date_groups.setdefault(d_str, []).append(task_schema)

        daily_schedules: List[DailyScheduleGroup] = []
        for d_str in sorted(date_groups.keys()):
            d_obj = cls._parse_date(d_str)
            group_tasks = date_groups[d_str]
            total_m = sum(t.duration_minutes for t in group_tasks)
            comp_m = sum(t.duration_minutes for t in group_tasks if t.status == "completed")

            daily_schedules.append(DailyScheduleGroup(
                date=d_str,
                day_name=cls._format_day_name(d_obj),
                formatted_date=cls._format_human_date(d_obj),
                total_minutes=total_m,
                completed_minutes=comp_m,
                is_today=(d_str == today_iso),
                tasks=group_tasks,
            ))

        total_tasks_count = len(raw_tasks)
        completed_tasks_count = sum(1 for t in raw_tasks if t["status"] == "completed")
        total_min = plan.get("total_planned_minutes", 0)
        comp_min = plan.get("completed_minutes", 0)
        prog_pct = round((comp_min / total_min * 100), 1) if total_min > 0 else 0.0

        shortfall_min = plan.get("shortfall_minutes", 0)
        shortfall_hrs = round(shortfall_min / 60, 1)

        pref_days = json.loads(plan.get("preferred_days_json") or '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]')

        return StudyPlanResponse(
            id=real_plan_id,
            syllabus_id=syllabus_id,
            course_name=course_name,
            title=plan["title"],
            exam_date=plan["exam_date"],
            daily_target_minutes=plan["daily_target_minutes"],
            preferred_days=pref_days,
            feasibility_status=plan.get("feasibility_status", "feasible"),
            shortfall_minutes=shortfall_min,
            shortfall_hours=shortfall_hrs,
            feasibility_warning=plan.get("feasibility_warning") or "",
            total_planned_minutes=total_min,
            completed_minutes=comp_min,
            progress_percentage=prog_pct,
            total_tasks_count=total_tasks_count,
            completed_tasks_count=completed_tasks_count,
            daily_schedules=daily_schedules,
            created_at=plan.get("created_at") or today_iso,
            updated_at=plan.get("updated_at") or today_iso,
            message=f"Plan contains {total_tasks_count} tasks across {len(daily_schedules)} study days ({prog_pct}% complete).",
        )

    @classmethod
    async def reschedule_missed_tasks(
        cls,
        plan_id: str,
        missed_date: Optional[str] = None,
        from_date: Optional[str] = None,
    ) -> StudyPlanResponse:
        """
        Adaptive Recovery: Identifies unfinished tasks from missed days and redistributes
        them across future study slots, updating feasibility and shortfall warnings.
        """
        plan = get_study_plan_by_id(plan_id)
        if not plan:
            plan = get_active_study_plan(plan_id)
            if not plan:
                raise ValueError(f"Study plan '{plan_id}' not found.")

        real_plan_id = plan["id"]
        today = datetime.date.today()
        ref_from_date = cls._parse_date(from_date) if from_date else today
        plan_exam = cls._parse_date(plan["exam_date"])
        daily_target = plan["daily_target_minutes"]
        pref_days = json.loads(plan.get("preferred_days_json") or '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]')

        all_tasks = get_plan_tasks(real_plan_id)

        # Identify overdue or missed unfinished tasks
        unfinished_tasks_to_reschedule: List[Dict[str, Any]] = []
        future_pending_tasks: List[Dict[str, Any]] = []

        for t in all_tasks:
            if t["status"] == "completed":
                continue

            t_date = cls._parse_date(t["scheduled_date"])
            if missed_date and t["scheduled_date"] == missed_date:
                unfinished_tasks_to_reschedule.append(t)
            elif not missed_date and t_date < ref_from_date:
                unfinished_tasks_to_reschedule.append(t)
            else:
                future_pending_tasks.append(t)

        if not unfinished_tasks_to_reschedule:
            # No missed tasks to recover
            return await cls.get_plan_details(real_plan_id)

        # Re-pack: missed tasks go first to maintain prerequisite order, followed by future tasks
        all_pending_tasks = unfinished_tasks_to_reschedule + future_pending_tasks

        # Available calendar dates from ref_from_date to exam_date
        future_available_dates: List[datetime.date] = []
        curr_d = ref_from_date
        while curr_d < plan_exam:
            day_name = cls._format_day_name(curr_d)
            if day_name in pref_days:
                future_available_dates.append(curr_d)
            curr_d += datetime.timedelta(days=1)

        total_pending_minutes = sum(t["duration_minutes"] for t in all_pending_tasks)
        total_available_minutes = len(future_available_dates) * daily_target

        feasibility_status = "feasible"
        shortfall_minutes = 0
        feasibility_warning = ""

        if total_pending_minutes > total_available_minutes:
            feasibility_status = "impossible"
            shortfall_minutes = total_pending_minutes - total_available_minutes
            shortfall_hours = round(shortfall_minutes / 60, 1)
            feasibility_warning = (
                f"Rescheduling Shortfall: After recovering missed study sessions, remaining workload "
                f"exceeds available time before {plan['exam_date']} by {shortfall_hours} hours. "
                f"Increase daily study hours to catch up."
            )
        elif total_pending_minutes > (0.85 * total_available_minutes):
            feasibility_status = "tight"
            feasibility_warning = "Tight Schedule: Recovered tasks consume almost all remaining study capacity."

        rescheduled_mappings: List[Dict[str, Any]] = []
        day_idx = 0
        current_day_minutes = 0
        current_day_order = 0

        if future_available_dates:
            for t in all_pending_tasks:
                if day_idx >= len(future_available_dates):
                    target_date = future_available_dates[-1]
                else:
                    target_date = future_available_dates[day_idx]

                rescheduled_mappings.append({
                    "id": t["id"],
                    "scheduled_date": target_date.isoformat(),
                    "order_index": current_day_order,
                })
                current_day_order += 1
                current_day_minutes += t["duration_minutes"]

                if current_day_minutes >= daily_target:
                    day_idx += 1
                    current_day_minutes = 0
                    current_day_order = 0
        else:
            for t in all_pending_tasks:
                rescheduled_mappings.append({
                    "id": t["id"],
                    "scheduled_date": ref_from_date.isoformat(),
                    "order_index": 0,
                })

        reschedule_plan_tasks(
            plan_id=real_plan_id,
            rescheduled_tasks=rescheduled_mappings,
            new_feasibility={
                "feasibility_status": feasibility_status,
                "shortfall_minutes": shortfall_minutes,
                "feasibility_warning": feasibility_warning,
            }
        )

        return await cls.get_plan_details(real_plan_id)

    @classmethod
    async def toggle_task_completion(cls, task_id: str, completed: bool) -> TaskItemSchema:
        """Marks a task complete/incomplete and recalculates metrics."""
        updated = update_task_completion(task_id, completed)
        if not updated:
            raise ValueError(f"Task '{task_id}' not found.")

        return TaskItemSchema(
            id=updated["id"],
            plan_id=updated["plan_id"],
            syllabus_id=updated["syllabus_id"],
            module_id=updated["module_id"],
            module_title=updated.get("module_title"),
            topic_id=updated["topic_id"],
            topic_title=updated.get("topic_title"),
            scheduled_date=updated["scheduled_date"],
            title=updated["title"],
            task_type=updated["task_type"],
            duration_minutes=updated["duration_minutes"],
            video_id=updated.get("video_id"),
            video_url=updated.get("video_url"),
            status=updated["status"],
            completed_at=updated.get("completed_at"),
            notes=updated.get("notes"),
            order_index=updated.get("order_index", 0),
        )

    @classmethod
    async def save_task_notes(cls, task_id: str, notes: str) -> TaskItemSchema:
        """Saves student notes on a specific task."""
        updated = update_task_note(task_id, notes)
        if not updated:
            raise ValueError(f"Task '{task_id}' not found.")

        return TaskItemSchema(
            id=updated["id"],
            plan_id=updated["plan_id"],
            syllabus_id=updated["syllabus_id"],
            module_id=updated["module_id"],
            module_title=updated.get("module_title"),
            topic_id=updated["topic_id"],
            topic_title=updated.get("topic_title"),
            scheduled_date=updated["scheduled_date"],
            title=updated["title"],
            task_type=updated["task_type"],
            duration_minutes=updated["duration_minutes"],
            video_id=updated.get("video_id"),
            video_url=updated.get("video_url"),
            status=updated["status"],
            completed_at=updated.get("completed_at"),
            notes=updated.get("notes"),
            order_index=updated.get("order_index", 0),
        )

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TaskItemSchema(BaseModel):
    id: str = Field(description="Stable unique ID for the task")
    plan_id: str = Field(description="Parent plan ID")
    syllabus_id: str = Field(description="Associated syllabus ID")
    module_id: str = Field(description="Parent module ID")
    module_title: Optional[str] = Field(default=None, description="Module title")
    topic_id: str = Field(description="Associated topic ID")
    topic_title: Optional[str] = Field(default=None, description="Topic title")
    scheduled_date: str = Field(description="Scheduled date (YYYY-MM-DD)")
    title: str = Field(description="Task title")
    task_type: Literal["Video", "Practice", "Study"] = Field(description="Type of task")
    duration_minutes: int = Field(description="Planned duration in minutes")
    video_id: Optional[str] = Field(default=None, description="YouTube video ID if type is Video")
    video_url: Optional[str] = Field(default=None, description="YouTube URL if type is Video")
    status: Literal["pending", "completed"] = Field(default="pending", description="Task completion status")
    completed_at: Optional[str] = Field(default=None, description="ISO timestamp when marked complete")
    notes: Optional[str] = Field(default=None, description="Student study notes for this task")
    order_index: int = Field(default=0, description="Order index within the day")


class DailyScheduleGroup(BaseModel):
    date: str = Field(description="Date string (YYYY-MM-DD)")
    day_name: str = Field(description="Short weekday name (e.g. Mon, Tue)")
    formatted_date: str = Field(description="Human formatted date (e.g. 21 Apr)")
    total_minutes: int = Field(default=0, description="Total planned study minutes for this day")
    completed_minutes: int = Field(default=0, description="Completed minutes for this day")
    is_today: bool = Field(default=False, description="Whether this day is today")
    tasks: List[TaskItemSchema] = Field(default_factory=list, description="Tasks scheduled for this date")


class StudyPlanCreateRequest(BaseModel):
    exam_date: str = Field(description="Target exam date (YYYY-MM-DD)")
    daily_target_minutes: int = Field(default=120, description="Daily available study time in minutes")
    preferred_days: List[str] = Field(
        default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        description="Preferred days of week for study sessions"
    )
    start_date: Optional[str] = Field(default=None, description="Plan start date (defaults to today)")
    preserve_completed: bool = Field(default=True, description="Preserve completed tasks when regenerating")


class StudyPlanResponse(BaseModel):
    id: str = Field(description="Unique identifier of the study plan")
    syllabus_id: str = Field(description="Associated syllabus ID")
    course_name: Optional[str] = Field(default=None, description="Course name")
    title: str = Field(description="Study plan title")
    exam_date: str = Field(description="Target exam deadline")
    daily_target_minutes: int = Field(description="Configured daily study minutes limit")
    preferred_days: List[str] = Field(default_factory=list)
    feasibility_status: Literal["feasible", "tight", "impossible"] = Field(
        description="Whether the workload realistically fits before the exam"
    )
    shortfall_minutes: int = Field(default=0, description="Workload minutes shortfall if impossible")
    shortfall_hours: float = Field(default=0.0, description="Workload hours shortfall if impossible")
    feasibility_warning: str = Field(default="", description="Human-readable warning regarding feasibility")
    total_planned_minutes: int = Field(default=0)
    completed_minutes: int = Field(default=0)
    progress_percentage: float = Field(default=0.0)
    total_tasks_count: int = Field(default=0)
    completed_tasks_count: int = Field(default=0)
    daily_schedules: List[DailyScheduleGroup] = Field(default_factory=list)
    created_at: str
    updated_at: str
    message: str


class TaskStatusUpdateRequest(BaseModel):
    completed: bool = Field(description="New completion state")


class TaskNoteUpdateRequest(BaseModel):
    notes: str = Field(description="Student notes for this task")


class RescheduleRequest(BaseModel):
    missed_date: Optional[str] = Field(default=None, description="Specific missed date to redistribute")
    from_date: Optional[str] = Field(default=None, description="Start date for redistribution (defaults to today)")


class UserSettingsSchema(BaseModel):
    preferred_language: str = Field(default="English")
    lesson_style: str = Field(default="In-depth")
    daily_study_availability: str = Field(default="2-4 hours")
    daily_target_minutes: int = Field(default=120)
    exam_date: str = Field(default="2026-05-15")
    study_days: List[str] = Field(default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    theme: Literal["dark", "light"] = Field(default="dark")
    study_reminders: bool = Field(default=True)
    deadline_alerts: bool = Field(default=True)
    auto_save_progress: bool = Field(default=True)

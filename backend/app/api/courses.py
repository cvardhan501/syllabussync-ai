import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.core.auth import get_current_user_id, verify_ownership

from app.schemas.course import (
    CourseCreateRequest,
    CourseUpdateRequest,
    CourseResponse,
    CourseListResponse,
    SemesterOverviewResponse,
    SyllabusSetupRequest,
    ReplaceSyllabusRequest,
)
from app.schemas.syllabus import SyllabusAnalysisResponse
from app.models.database import (
    create_course,
    get_courses,
    get_course,
    update_course,
    archive_course,
    delete_course,
    get_semester_overview,
    replace_course_syllabus,
    get_syllabus_record,
    save_syllabus_hierarchy,
    update_syllabus_exam_date,
)
from app.agents.syllabus_analyzer import SyllabusAnalyzerAgent
from app.services.syllabus_validator import SyllabusValidatorService
from app.services.study_planner import StudyPlannerService

logger = logging.getLogger("syllabus_sync.api.courses")

router = APIRouter(prefix="/courses", tags=["Courses & Academic Planning"])


@router.get(
    "",
    response_model=CourseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all courses and their academic progress"
)
async def list_courses(
    include_archived: bool = Query(False, description="Include archived courses"),
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    courses_data = get_courses(include_archived=include_archived, owner_user_id=current_user_id)
    return CourseListResponse(
        status="success",
        total_count=len(courses_data),
        courses=[CourseResponse(**c) for c in courses_data],
    )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course with custom preferences and assessments"
)
async def create_new_course(
    payload: CourseCreateRequest,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    if payload.syllabus_id:
        s_record = get_syllabus_record(payload.syllabus_id)
        if not s_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Syllabus with ID '{payload.syllabus_id}' was not found."
            )
        verify_ownership(s_record.get("owner_user_id"), current_user_id, resource_type="syllabus")

    course_data = payload.model_dump()
    # Unconditionally enforce verified user ID; never trust client-supplied owner_user_id
    if current_user_id:
        course_data["owner_user_id"] = current_user_id
    else:
        course_data["owner_user_id"] = "default_user"
    created = create_course(course_data, owner_user_id=current_user_id)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create course."
        )
    return CourseResponse(**created)


@router.get(
    "/semester-overview",
    response_model=SemesterOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Semester-level academic metrics, upcoming assessments timeline, and course breakdowns"
)
async def get_semester_academic_overview(
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    overview = get_semester_overview(owner_user_id=current_user_id)
    return SemesterOverviewResponse(
        status="success",
        total_courses=overview["total_courses"],
        total_topics=overview["total_topics"],
        total_tasks=overview["total_tasks"],
        completed_tasks=overview["completed_tasks"],
        overall_percentage=overview["overall_percentage"],
        overdue_tasks_count=overview["overdue_tasks_count"],
        upcoming_assessments=overview["upcoming_assessments"],
        courses=[CourseResponse(**c) for c in overview["courses"]],
    )


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get course by ID or linked syllabus ID"
)
async def get_course_details(
    course_id: str,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    verify_ownership(course.get("owner_user_id"), current_user_id, resource_type="course")
    return CourseResponse(**course)


@router.put(
    "/{course_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update course metadata, preferences, or assessments"
)
async def update_course_details(
    course_id: str,
    payload: CourseUpdateRequest,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    verify_ownership(course.get("owner_user_id"), current_user_id, resource_type="course")

    updates = payload.model_dump(exclude_unset=True)
    # Strip any client-supplied owner_user_id to prevent ownership transfer or spoofing
    updates.pop("owner_user_id", None)
    if "assessments" in updates and updates["assessments"] is not None:
        updates["assessments"] = [a for a in updates["assessments"]]

    updated = update_course(course_id, updates, owner_user_id=current_user_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    return CourseResponse(**updated)


@router.post(
    "/{course_id}/archive",
    status_code=status.HTTP_200_OK,
    summary="Archive or unarchive a course"
)
async def toggle_archive_course(
    course_id: str,
    is_archived: bool = Query(True),
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    verify_ownership(course.get("owner_user_id"), current_user_id, resource_type="course")

    success = archive_course(course_id, is_archived=is_archived, owner_user_id=current_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    action = "archived" if is_archived else "unarchived"
    return {"status": "success", "message": f"Course {action} successfully."}


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a course and all associated syllabus data, tasks, and plans"
)
async def remove_course(
    course_id: str,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    verify_ownership(course.get("owner_user_id"), current_user_id, resource_type="course")

    success = delete_course(course_id, owner_user_id=current_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    return {"status": "success", "message": "Course deleted successfully."}


@router.post(
    "/{course_id}/replace-syllabus",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace course syllabus document with preserved completion history"
)
async def replace_syllabus(
    course_id: str,
    payload: ReplaceSyllabusRequest,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    verify_ownership(course.get("owner_user_id"), current_user_id, resource_type="course")

    new_s_record = get_syllabus_record(payload.new_syllabus_id)
    if not new_s_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replacement syllabus '{payload.new_syllabus_id}' was not found."
        )
    verify_ownership(new_s_record.get("owner_user_id"), current_user_id, resource_type="syllabus")

    updated = replace_course_syllabus(
        course_id=course_id,
        new_syllabus_id=payload.new_syllabus_id,
        preserve_matching_completions=payload.preserve_matching_completions,
        owner_user_id=current_user_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID '{course_id}' was not found."
        )
    return CourseResponse(**updated)


@router.post(
    "/setup-and-analyze",
    status_code=status.HTTP_200_OK,
    summary="Submit syllabus setup wizard preferences and trigger AI analysis & study roadmap"
)
async def setup_and_analyze_syllabus(
    payload: SyllabusSetupRequest,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Submits student preferences gathered in the Pre-analysis Syllabus Setup Wizard:
    1. Validates syllabus record existence and raw text.
    2. Runs AI syllabus analysis (or fallback) using Strands SDK.
    3. Persists structured hierarchy in SQLite.
    4. Creates the new Course record with student preferences and assessment pattern.
    5. Generates the course study plan using the configured availability and target exam date.
    """
    s_record = get_syllabus_record(payload.syllabus_id)
    if not s_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Syllabus with ID '{payload.syllabus_id}' was not found. Please upload first."
        )

    # Enforce ownership if syllabus is owned by another user
    verify_ownership(s_record.get("owner_user_id"), current_user_id, resource_type="syllabus")
    resolved_owner = current_user_id or (str(s_record["owner_user_id"]) if s_record.get("owner_user_id") else None)

    raw_text = s_record["raw_text"]
    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The syllabus document contains no readable text."
        )

    logger.info(
        f"Starting setup-and-analyze for syllabus '{payload.syllabus_id}', course '{payload.course_name}' "
        f"(owner: {resolved_owner})"
    )

    try:
        # 1. Run AI analysis
        hierarchy, is_fallback, analysis_engine = await SyllabusAnalyzerAgent.analyze_syllabus(raw_text)

        # Override course name and code from student wizard input
        if payload.course_name:
            hierarchy.course_name = payload.course_name
        if payload.course_code:
            hierarchy.course_code = payload.course_code

        # 2. Persist syllabus hierarchy
        save_syllabus_hierarchy(
            syllabus_id=payload.syllabus_id,
            hierarchy_dict=hierarchy.model_dump(),
            is_fallback=is_fallback,
            analysis_engine=analysis_engine,
        )

        # 3. Calculate daily target minutes from availability string
        availability_map = {
            "30-60 minutes": 45,
            "1-2 hours": 90,
            "2-4 hours": 180,
            "4+ hours": 240,
        }
        daily_target_mins = availability_map.get(payload.daily_study_availability, 120)

        # 4. Create or update course
        course_dict = {
            "id": f"course_{payload.syllabus_id}",
            "syllabus_id": payload.syllabus_id,
            "owner_user_id": resolved_owner,
            "course_name": payload.course_name,
            "course_code": payload.course_code,
            "language": payload.language,
            "lesson_style": payload.lesson_style,
            "daily_study_availability": payload.daily_study_availability,
            "daily_target_minutes": daily_target_mins,
            "assessment_system_type": payload.assessment_system_type,
            "assessment_scope": payload.assessment_scope,
            "color_theme": "blue",
            "assessments": [a.model_dump() for a in payload.assessments],
        }
        course = create_course(course_dict, owner_user_id=resolved_owner)

        # 5. Determine target exam date for initial plan
        # Use earliest upcoming assessment date or end-sem date if available
        target_exam_date = None
        sorted_assessments = sorted(payload.assessments, key=lambda a: a.exam_date)
        for a in sorted_assessments:
            if a.assessment_type == "end_sem" or a.scope in ("end_sem", "both"):
                target_exam_date = a.exam_date
                break
        if not target_exam_date and sorted_assessments:
            target_exam_date = sorted_assessments[-1].exam_date

        if target_exam_date:
            update_syllabus_exam_date(payload.syllabus_id, target_exam_date)

        # 6. Generate initial study plan if exam date is set
        plan_data = None
        if target_exam_date:
            try:
                plan_data = await StudyPlannerService.generate_or_update_plan(
                    syllabus_id=payload.syllabus_id,
                    exam_date=target_exam_date,
                    daily_target_minutes=daily_target_mins,
                    owner_user_id=resolved_owner,
                )
            except Exception as e:
                logger.warning(f"Could not auto-generate plan during setup: {e}")

        # Build validation report
        val_report = SyllabusValidatorService.validate_hierarchy(
            hierarchy.model_dump(),
            is_fallback=is_fallback,
        )

        ass_info = hierarchy.assessment_info
        if isinstance(ass_info, list):
            ass_info = "\n".join(str(x) for x in ass_info) if ass_info else None

        analysis_res = SyllabusAnalysisResponse(
            status="success",
            syllabus_id=payload.syllabus_id,
            owner_user_id=resolved_owner,
            filename=s_record["filename"],
            file_type=s_record["file_type"],
            char_count=s_record["char_count"],
            word_count=s_record["word_count"],
            course_name=payload.course_name,
            course_code=payload.course_code,
            term=hierarchy.term,
            credits=hierarchy.credits,
            course_objectives=hierarchy.course_objectives,
            course_outcomes=hierarchy.course_outcomes,
            prerequisites=hierarchy.prerequisites,
            textbooks=hierarchy.textbooks,
            assessment_info=ass_info,
            modules=hierarchy.modules,
            ambiguous_sections=hierarchy.ambiguous_sections,
            total_topics_count=sum(len(m.topics) for m in hierarchy.modules),
            total_estimated_minutes=sum(sum(t.estimated_minutes for t in m.topics) for m in hierarchy.modules),
            validation_report=val_report,
            is_fallback=is_fallback,
            analysis_engine=analysis_engine,
            ai_status=hierarchy.ai_status,
            ai_status_message=hierarchy.ai_status_message,
            message=f"Syllabus analyzed and course '{payload.course_name}' created successfully.",
        )

        logger.info(
            f"Successfully processed setup-and-analyze for course '{payload.course_name}' "
            f"(course_id: {course.get('id') if isinstance(course, dict) else getattr(course, 'id', 'unknown')})"
        )

        return {
            "status": "success",
            "course": course,
            "analysis": analysis_res.model_dump(),
            "study_plan": plan_data.model_dump() if plan_data else None,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Syllabus setup and analysis failed for '{payload.syllabus_id}': {exc}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Syllabus setup and analysis failed: {str(exc)}"
        )


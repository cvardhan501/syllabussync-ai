import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from app.schemas.study_plan import (
    StudyPlanCreateRequest,
    StudyPlanResponse,
    TaskItemSchema,
    TaskStatusUpdateRequest,
    TaskNoteUpdateRequest,
    RescheduleRequest,
    UserSettingsSchema,
)
from app.services.study_planner import StudyPlannerService
from app.models.database import get_user_settings, save_user_settings

logger = logging.getLogger("syllabus_sync.api.planner")

router = APIRouter(tags=["Study Planner"])


@router.post(
    "/study-plan/{syllabus_id}",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or regenerate a personalized daily study plan"
)
async def create_study_plan(
    syllabus_id: str,
    payload: StudyPlanCreateRequest,
):
    """
    Generates a deterministic daily study timetable matching topics, video lectures,
    notes, and practice checkpoints into available days before the target exam date.
    Preserves completed tasks when regenerating.
    """
    try:
        return await StudyPlannerService.generate_or_update_plan(
            syllabus_id=syllabus_id,
            exam_date=payload.exam_date,
            daily_target_minutes=payload.daily_target_minutes,
            preferred_days=payload.preferred_days,
            start_date=payload.start_date,
            preserve_completed=payload.preserve_completed,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/study-plan/{syllabus_id}",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve active study plan and daily tasks for a syllabus"
)
async def get_study_plan(syllabus_id: str):
    """Retrieves the active study plan and its grouped daily schedule."""
    try:
        return await StudyPlannerService.get_plan_details(syllabus_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/study-plan/{plan_id}/tasks/{task_id}/status",
    response_model=TaskItemSchema,
    status_code=status.HTTP_200_OK,
    summary="Mark a study task complete or incomplete"
)
async def update_task_status(
    plan_id: str,
    task_id: str,
    payload: TaskStatusUpdateRequest,
):
    """Toggles task completion status and recalculates plan metrics."""
    try:
        return await StudyPlannerService.toggle_task_completion(task_id, payload.completed)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/study-plan/{plan_id}/tasks/{task_id}/notes",
    response_model=TaskItemSchema,
    status_code=status.HTTP_200_OK,
    summary="Save study notes for a specific task"
)
async def save_task_notes(
    plan_id: str,
    task_id: str,
    payload: TaskNoteUpdateRequest,
):
    """Saves student notes on a specific task."""
    try:
        return await StudyPlannerService.save_task_notes(task_id, payload.notes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/study-plan/{plan_id}/reschedule",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Adaptive recovery: Reschedule unfinished tasks after a missed day"
)
async def reschedule_missed_tasks(
    plan_id: str,
    payload: Optional[RescheduleRequest] = None,
):
    """
    Identifies unfinished tasks from missed days and redistributes them into future
    available slots, respecting daily availability limits and updating shortfall calculations.
    """
    req = payload or RescheduleRequest()
    try:
        return await StudyPlannerService.reschedule_missed_tasks(
            plan_id=plan_id,
            missed_date=req.missed_date,
            from_date=req.from_date,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==============================================================================
# Settings Endpoints
# ==============================================================================

@router.get(
    "/settings",
    response_model=UserSettingsSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve saved student learning preferences"
)
async def get_settings():
    """Retrieves persisted student learning and app settings."""
    return get_user_settings()


@router.put(
    "/settings",
    response_model=UserSettingsSchema,
    status_code=status.HTTP_200_OK,
    summary="Update and persist student learning preferences"
)
async def update_settings(payload: UserSettingsSchema):
    """Saves student preferences in SQLite."""
    saved = save_user_settings(payload.model_dump())
    return saved

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.schemas.resource import (
    ResourceDiscoveryRequest,
    ResourceDiscoveryResponse,
    AlternativeResourcesResponse,
    ReplaceChannelRequest,
    TopicResourceMapping,
    ThirdChannelApprovalRequest,
)
from app.services.resource_matcher import ResourceMatcherService
from app.services.youtube_client import (
    YouTubeAuthException,
    YouTubeQuotaExceededException,
    YouTubeConnectionException,
)

logger = logging.getLogger("syllabus_sync.api.resources")

router = APIRouter(prefix="/syllabus", tags=["YouTube Resources"])


@router.post(
    "/{syllabus_id}/discover-resources",
    response_model=ResourceDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover and match genuine YouTube educational resources for syllabus topics"
)
async def discover_resources(
    syllabus_id: str,
    payload: Optional[ResourceDiscoveryRequest] = None,
):
    """
    Discovers educational YouTube videos for each syllabus topic using the official
    YouTube Data API v3 and channel selection strategy (1-channel vs 2-channel vs 3rd approval).
    """
    req = payload or ResourceDiscoveryRequest()
    try:
        return await ResourceMatcherService.discover_resources_for_syllabus(
            syllabus_id=syllabus_id,
            preferred_language=req.preferred_language,
            force_refresh=req.force_refresh,
            allow_third_channel=req.allow_third_channel,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except YouTubeAuthException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"YouTube Authentication Error: {str(e)}",
        )
    except YouTubeQuotaExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"YouTube Quota Exceeded: {str(e)}",
        )
    except YouTubeConnectionException as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"YouTube Connection Timeout: {str(e)}",
        )


@router.get(
    "/{syllabus_id}/resources",
    response_model=ResourceDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve saved YouTube resources and coverage audit for a syllabus"
)
async def get_resources(syllabus_id: str):
    """Retrieves previously discovered resources and coverage statistics for a syllabus."""
    try:
        return await ResourceMatcherService.discover_resources_for_syllabus(
            syllabus_id=syllabus_id,
            force_refresh=False,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{syllabus_id}/topics/{topic_id}/alternatives",
    response_model=AlternativeResourcesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get alternative channels and videos for a specific topic"
)
async def get_topic_alternatives(
    syllabus_id: str,
    topic_id: str,
    language: str = Query("English", description="Preferred video language"),
):
    """
    Retrieves real alternative educational videos for a topic,
    strictly excluding channels already rejected by the student.
    """
    try:
        return await ResourceMatcherService.get_alternatives_for_topic(
            syllabus_id=syllabus_id,
            topic_id=topic_id,
            preferred_language=language,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/{syllabus_id}/topics/{topic_id}/replace-channel",
    response_model=TopicResourceMapping,
    status_code=status.HTTP_200_OK,
    summary="Replace current channel with an alternative for this topic"
)
async def replace_topic_channel(
    syllabus_id: str,
    topic_id: str,
    payload: ReplaceChannelRequest,
):
    """
    Excludes the disliked channel from this topic, sets the newly chosen video,
    and updates only this topic resource without resetting progress or other topics.
    """
    try:
        return await ResourceMatcherService.replace_topic_channel(
            syllabus_id=syllabus_id,
            topic_id=topic_id,
            rejected_channel=payload.rejected_channel,
            selected_video_id=payload.selected_video_id,
            reason=payload.reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/{syllabus_id}/approve-third-channel",
    response_model=ResourceDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve introducing a 3rd channel when 2 channels are insufficient"
)
async def approve_third_channel(
    syllabus_id: str,
    payload: Optional[ThirdChannelApprovalRequest] = None,
):
    """
    Records student approval for introducing a 3rd channel and updates the resource plan.
    """
    approve = payload.approve if payload else True
    try:
        return await ResourceMatcherService.discover_resources_for_syllabus(
            syllabus_id=syllabus_id,
            allow_third_channel=approve,
            force_refresh=True,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


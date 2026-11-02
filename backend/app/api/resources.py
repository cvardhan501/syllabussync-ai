import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.core.auth import get_current_user_id, verify_ownership
from app.models.database import get_syllabus_owner_id
from app.schemas.resource import (
    ResourceDiscoveryRequest,
    ResourceDiscoveryResponse,
    AlternativeResourcesResponse,
    ReplaceChannelRequest,
    TopicResourceMapping,
    ThirdChannelApprovalRequest,
    ChannelDiscoveryRequest,
    ChannelDiscoveryResponse,
    PreviewStrategyRequest,
    PreviewStrategyResponse,
    ConfirmChannelStrategyRequest,
)
from app.services.resource_matcher import ResourceMatcherService
from app.services.youtube_client import (
    YouTubeApiException,
    YouTubeAuthException,
    YouTubeQuotaExceededException,
    YouTubeConnectionException,
)

logger = logging.getLogger("syllabus_sync.api.resources")

router = APIRouter(prefix="/syllabus", tags=["YouTube Resources"])


@router.post(
    "/{syllabus_id}/channel-discovery",
    response_model=ChannelDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover candidate accredited YouTube educational channels for course subjects"
)
async def discover_channels(
    syllabus_id: str,
    payload: Optional[ChannelDiscoveryRequest] = None,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Discovers candidate educational channels teaching course topics across prioritized languages,
    auditing coverage count, example videos, and syllabus fit before strategy selection.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

    req = payload or ChannelDiscoveryRequest()
    try:
        return await ResourceMatcherService.discover_channels_for_syllabus(
            syllabus_id=syllabus_id,
            languages=req.languages,
            force_refresh=req.force_refresh,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except YouTubeQuotaExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"YouTube Quota Exceeded: {str(e)}",
        )
    except YouTubeAuthException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube Authentication Error: {str(e)}",
        )
    except YouTubeConnectionException as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"YouTube Connection Timeout: {str(e)}",
        )
    except YouTubeApiException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube API Error: {str(e)}",
        )


@router.post(
    "/{syllabus_id}/preview-strategy",
    response_model=PreviewStrategyResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview topic-to-channel distribution table and metrics for chosen strategy"
)
async def preview_strategy(
    syllabus_id: str,
    payload: PreviewStrategyRequest,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Generates preview table showing syllabus topics, assigned channels, matched videos,
    and verified vs missing coverage for the student's chosen strategy before confirmation.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

    try:
        return await ResourceMatcherService.generate_strategy_preview(
            syllabus_id=syllabus_id,
            strategy=payload.strategy,
            languages=payload.languages,
            selected_channel_names=payload.selected_channel_names,
            custom_assignments=payload.custom_assignments,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except YouTubeQuotaExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"YouTube Quota Exceeded: {str(e)}",
        )
    except YouTubeAuthException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube Authentication Error: {str(e)}",
        )
    except YouTubeConnectionException as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"YouTube Connection Timeout: {str(e)}",
        )
    except YouTubeApiException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube API Error: {str(e)}",
        )


@router.post(
    "/{syllabus_id}/confirm-strategy",
    response_model=ResourceDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm strategy and generate final persistent Video Library"
)
async def confirm_strategy(
    syllabus_id: str,
    payload: ConfirmChannelStrategyRequest,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Records student confirmation of their preferred channel strategy and generates the final
    persistent Video Library in SQLite with verified matches and honest coverage metrics.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

    try:
        return await ResourceMatcherService.confirm_channel_strategy(
            syllabus_id=syllabus_id,
            strategy=payload.strategy,
            languages=payload.languages,
            selected_channel_names=payload.selected_channel_names,
            custom_assignments=payload.custom_assignments,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except YouTubeQuotaExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"YouTube Quota Exceeded: {str(e)}",
        )
    except YouTubeAuthException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube Authentication Error: {str(e)}",
        )
    except YouTubeConnectionException as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"YouTube Connection Timeout: {str(e)}",
        )
    except YouTubeApiException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube API Error: {str(e)}",
        )


@router.post(
    "/{syllabus_id}/discover-resources",
    response_model=ResourceDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover and match genuine YouTube educational resources for syllabus topics"
)
async def discover_resources(
    syllabus_id: str,
    payload: Optional[ResourceDiscoveryRequest] = None,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Discovers educational YouTube videos for each syllabus topic using the official
    YouTube Data API v3 and channel selection strategy.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

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
    except YouTubeApiException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube API Error: {str(e)}",
        )


@router.get(
    "/{syllabus_id}/resources",
    response_model=ResourceDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve saved YouTube resources and coverage audit for a syllabus"
)
async def get_resources(
    syllabus_id: str,
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """Retrieves previously discovered resources and coverage statistics for a syllabus."""
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

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
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Retrieves real alternative educational videos for a topic,
    strictly excluding channels already rejected by the student.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

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
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Excludes the disliked channel from this topic, sets the newly chosen video,
    and updates only this topic resource without resetting progress or other topics.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

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
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Records student approval for introducing a 3rd channel and immediately updates the resource plan
    using fast cached topic candidates without redundant external network discovery.
    """
    s_owner = get_syllabus_owner_id(syllabus_id)
    verify_ownership(s_owner, current_user_id, resource_type="syllabus")

    approve = payload.approve if payload else True
    try:
        from app.models.database import get_syllabus_resources
        existing = get_syllabus_resources(syllabus_id)
        current_strategy = (existing.get("channel_strategy") if existing else None) or "two_channels"
        current_langs = (existing.get("languages") if existing else None) or ["English"]

        return await ResourceMatcherService.confirm_channel_strategy(
            syllabus_id=syllabus_id,
            strategy=current_strategy,
            languages=current_langs,
            allow_third_channel=approve,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

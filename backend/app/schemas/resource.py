from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, model_validator


class VideoResource(BaseModel):
    id: str = Field(description="Unique identifier (YouTube video ID)")
    video_id: str = Field(description="YouTube video ID")
    title: str = Field(description="Official YouTube video title")
    description: Optional[str] = Field(default="", description="Video description snippet")
    channel_title: str = Field(description="YouTube channel name")
    channel_id: Optional[str] = Field(default=None, description="YouTube channel ID")
    thumbnail_url: str = Field(description="High or medium quality thumbnail URL")
    duration_seconds: int = Field(default=0, description="Video duration in seconds")
    duration_formatted: str = Field(default="0:00", description="Human-readable duration (MM:SS or HH:MM:SS)")
    language: Optional[str] = Field(default="English", description="Identified or requested language (or 'Unknown')")
    published_at: Optional[str] = Field(default=None, description="ISO publication date string")
    view_count: int = Field(default=0, description="Approximate view count")
    relevance_score: float = Field(default=0.0, description="Relevance score (0.0 to 1.0)")
    relevance_explanation: str = Field(default="", description="Topic-specific explanation of why this video matches the topic")
    is_uncertain: bool = Field(default=False, description="True if match has low confidence or lacks direct topic evidence")
    provenance: Literal["live", "cache", "fallback"] = Field(default="live", description="Provenance of video resource: live YouTube API, cache, or dev fallback")
    video_url: str = Field(description="Direct YouTube URL (https://www.youtube.com/watch?v=...)")
    availability_status: Literal["available", "unavailable", "missing"] = Field(
        default="available",
        description="Whether the video is currently playable/embeddable on YouTube"
    )


class TopicResourceMapping(BaseModel):
    topic_id: str = Field(description="Unique ID of syllabus topic")
    topic_title: str = Field(description="Title of topic")
    module_id: str = Field(description="Unique ID of parent module")
    module_title: str = Field(description="Title of parent module")
    resource: Optional[VideoResource] = Field(default=None, description="Matched primary YouTube video")
    provenance: Optional[Literal["live", "cache", "fallback"]] = Field(default=None, description="Provenance of assigned resource")
    match_status: Literal["verified", "probable", "unverified", "no_resource", "relevant", "candidate_only", "needs_review"] = Field(
        default="no_resource",
        description="Coverage classification: verified (strong evidence), probable (likely/broader context), unverified (insufficient info), no_resource (missing/none found)"
    )
    match_confidence: Literal["high", "medium", "low", "uncertain"] = Field(
        default="uncertain",
        description="Confidence level of topic match"
    )
    availability_status: Literal["available", "unavailable", "missing"] = Field(
        default="available",
        description="Whether the assigned video is currently playable/embeddable"
    )
    relevance_notes: Optional[str] = Field(default=None, description="Specific alignment notes or missing prerequisites")
    rejected_channels: List[str] = Field(default_factory=list, description="Channels disliked/rejected by student for this topic")
    assigned_channel: Optional[str] = Field(default=None, description="Active channel assigned to this topic")
    is_shared_video: bool = Field(default=False, description="Whether this video is legitimately shared across multiple topics")
    shared_with_topics: List[str] = Field(default_factory=list, description="Titles of other syllabus topics covered by this video")


class ChannelCoverageSummary(BaseModel):
    channel_title: str = Field(description="Name of YouTube channel")
    channel_id: Optional[str] = Field(default=None, description="YouTube channel ID")
    channel_url: Optional[str] = Field(default=None, description="Direct URL to YouTube channel")
    topics_covered: int = Field(default=0, description="Count of topics covered by this channel")
    topic_ids: List[str] = Field(default_factory=list, description="IDs of covered topics")
    is_primary: bool = Field(default=False, description="Whether this is the primary channel covering syllabus")
    percentage_of_course: float = Field(default=0.0, description="Share of syllabus topics covered (0.0 - 100.0%)")

    @model_validator(mode="before")
    @classmethod
    def _ensure_topics_covered(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "topics_covered" not in data or data["topics_covered"] is None:
                data["topics_covered"] = len(data.get("topic_ids", []))
        return data


class CoverageMetrics(BaseModel):
    total_topics: int = Field(default=0, description="Total syllabus theory topics")
    topics_with_candidates: int = Field(default=0, description="Topics with at least one candidate resource found")
    topics_with_relevant: int = Field(default=0, description="Topics with verified relevant resources (backward compatibility)")
    topics_with_verified: int = Field(default=0, description="Topics with strong, verified topic-specific matches")
    topics_with_probable: int = Field(default=0, description="Topics with probable/contextual matches")
    topics_with_no_resource: int = Field(default=0, description="Topics with no suitable educational resource found")
    topics_needing_review: int = Field(default=0, description="Topics needing student review / probable matches")
    coverage_percentage: float = Field(default=0.0, description="Percentage of topics with verified resources")
    verified_coverage_percentage: float = Field(default=0.0, description="Percentage with strictly verified topic matches")
    probable_coverage_percentage: float = Field(default=0.0, description="Percentage with probable matches")


class ExampleVideo(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    duration_formatted: str
    video_url: str


class DiscoveredChannelItem(BaseModel):
    channel_title: str
    channel_id: Optional[str] = None
    channel_url: str
    language: str
    relevant_video_count: int
    topics_covered: List[str] = Field(default_factory=list)
    topic_ids_covered: List[str] = Field(default_factory=list)
    topics_not_covered: List[str] = Field(default_factory=list)
    example_videos: List[ExampleVideo] = Field(default_factory=list)
    fit_score: float = Field(default=0.0, description="0.0 - 1.0 fit score indicating alignment with syllabus")
    availability_status: str = Field(default="available")
    match_notes: str = Field(default="")


class ChannelDiscoveryRequest(BaseModel):
    languages: List[str] = Field(default_factory=lambda: ["English"], description="Ordered list of preferred languages by priority")
    force_refresh: bool = Field(default=False, description="Bypass cache and rediscover fresh candidate channels")


class ChannelDiscoveryResponse(BaseModel):
    status: str = Field(default="success")
    syllabus_id: str
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    total_topics: int = 0
    languages: List[str] = Field(default_factory=lambda: ["English"])
    discovered_channels: List[DiscoveredChannelItem] = Field(default_factory=list)
    message: str = "Discovered educational channels"


class ChannelDistributionPreviewItem(BaseModel):
    topic_id: str
    topic_title: str
    module_title: str
    selected_channel: str
    candidate_video_title: Optional[str] = None
    candidate_video_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_formatted: Optional[str] = None
    match_status: str = "verified" # verified, probable, unverified, no_resource
    relevance_explanation: str = ""
    available_channels: List[str] = Field(default_factory=list)


class PreviewStrategyRequest(BaseModel):
    strategy: Literal["one_channel", "two_channels", "different_per_topic", "custom"]
    languages: List[str] = Field(default_factory=lambda: ["English"])
    selected_channel_names: Optional[List[str]] = None
    custom_assignments: Optional[Dict[str, str]] = None # topic_id -> channel_title


class PreviewStrategyResponse(BaseModel):
    status: str = Field(default="success")
    syllabus_id: str
    strategy: str
    strategy_title: str
    strategy_explanation: str
    selected_channels: List[ChannelCoverageSummary] = Field(default_factory=list)
    preview_items: List[ChannelDistributionPreviewItem] = Field(default_factory=list)
    coverage: CoverageMetrics
    missing_topics: List[str] = Field(default_factory=list)
    requires_third_channel_approval: bool = False
    third_channel_candidates: List[str] = Field(default_factory=list)


class ConfirmChannelStrategyRequest(BaseModel):
    strategy: Literal["one_channel", "two_channels", "different_per_topic", "custom"]
    languages: List[str] = Field(default_factory=lambda: ["English"])
    selected_channel_names: Optional[List[str]] = None
    custom_assignments: Optional[Dict[str, str]] = None # topic_id -> channel_title


class ResourceDiscoveryRequest(BaseModel):
    preferred_language: str = Field(default="English", description="Target video language")
    force_refresh: bool = Field(default=False, description="Bypass SQLite cache and make live queries")
    allow_third_channel: bool = Field(default=False, description="Student consent to add a 3rd channel if 2 channels are insufficient")


class ResourceDiscoveryResponse(BaseModel):
    status: str = Field(default="success")
    syllabus_id: str = Field(description="Target syllabus ID")
    course_name: Optional[str] = Field(default=None)
    course_code: Optional[str] = Field(default=None)
    coverage: CoverageMetrics = Field(description="Detailed topic coverage audit")
    selected_channels: List[ChannelCoverageSummary] = Field(
        default_factory=list,
        description="Selected channels and workload distribution"
    )
    requires_third_channel_approval: bool = Field(
        default=False,
        description="True if 2 channels are insufficient and student approval is required for a 3rd channel"
    )
    third_channel_candidates: List[str] = Field(
        default_factory=list,
        description="Recommended 3rd channels awaiting student approval"
    )
    strategy_explanation: str = Field(description="Explanation of the channel selection strategy applied")
    topic_resources: List[TopicResourceMapping] = Field(
        default_factory=list,
        description="List of all syllabus topics and their assigned YouTube resources"
    )
    is_fallback: bool = Field(
        default=False,
        description="True if generated by local deterministic fallback because no YouTube API key is configured"
    )
    discovery_engine: str = Field(default="YouTube Data API v3")
    message: str = Field(default="Resource discovery completed successfully.", description="Summary message")
    is_confirmed: bool = Field(default=True, description="Whether this channel distribution has been confirmed by student")
    channel_strategy: str = Field(default="two_channels", description="Selected channel strategy")


class AlternativeResourceItem(BaseModel):
    video: VideoResource
    recommendation_reason: str = Field(description="Reason why this alternative is recommended")
    is_current: bool = Field(default=False, description="Whether this is the currently assigned video")


class AlternativeResourcesResponse(BaseModel):
    topic_id: str
    topic_title: str
    current_channel: Optional[str] = None
    rejected_channels: List[str] = Field(default_factory=list)
    alternatives: List[AlternativeResourceItem] = Field(default_factory=list)
    message: str


class ReplaceChannelRequest(BaseModel):
    rejected_channel: str = Field(description="Channel to dislike and reject")
    selected_video_id: str = Field(description="YouTube ID of chosen replacement video")
    reason: Optional[str] = Field(default=None, description="Optional student reason for rejection")


class ThirdChannelApprovalRequest(BaseModel):
    approve: bool = Field(default=True, description="Whether student approves introducing a 3rd channel")

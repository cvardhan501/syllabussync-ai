from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class VideoResource(BaseModel):
    id: str = Field(description="Unique identifier (YouTube video ID)")
    video_id: str = Field(description="YouTube video ID")
    title: str = Field(description="Official YouTube video title")
    channel_title: str = Field(description="YouTube channel name")
    channel_id: Optional[str] = Field(default=None, description="YouTube channel ID")
    thumbnail_url: str = Field(description="High or medium quality thumbnail URL")
    duration_seconds: int = Field(default=0, description="Video duration in seconds")
    duration_formatted: str = Field(default="0:00", description="Human-readable duration (MM:SS or HH:MM:SS)")
    language: Optional[str] = Field(default="English", description="Identified or requested language")
    published_at: Optional[str] = Field(default=None, description="ISO publication date string")
    view_count: int = Field(default=0, description="Approximate view count")
    relevance_score: float = Field(default=0.0, description="Relevance score (0.0 to 1.0)")
    relevance_explanation: str = Field(default="", description="Brief explanation of why this video matches the topic")
    is_uncertain: bool = Field(default=False, description="True if match has low confidence or lacks direct topic evidence")
    video_url: str = Field(description="Direct YouTube URL (https://www.youtube.com/watch?v=...)")


class TopicResourceMapping(BaseModel):
    topic_id: str = Field(description="Unique ID of syllabus topic")
    topic_title: str = Field(description="Title of topic")
    module_id: str = Field(description="Unique ID of parent module")
    module_title: str = Field(description="Title of parent module")
    resource: Optional[VideoResource] = Field(default=None, description="Matched primary YouTube video")
    match_status: Literal["relevant", "candidate_only", "no_resource", "needs_review"] = Field(
        default="no_resource",
        description="Coverage classification: relevant (high match), candidate_only (weak match), no_resource (none found), needs_review (uncertain)"
    )
    match_confidence: Literal["high", "medium", "low", "uncertain"] = Field(
        default="uncertain",
        description="Confidence level of topic match"
    )
    relevance_notes: Optional[str] = Field(default=None, description="Specific alignment notes or missing prerequisites")
    rejected_channels: List[str] = Field(default_factory=list, description="Channels disliked/rejected by student for this topic")


class ChannelCoverageSummary(BaseModel):
    channel_title: str = Field(description="Name of YouTube channel")
    topics_covered: int = Field(description="Count of topics covered by this channel")
    topic_ids: List[str] = Field(default_factory=list, description="IDs of covered topics")
    is_primary: bool = Field(default=False, description="Whether this is the primary channel covering syllabus")
    percentage_of_course: float = Field(default=0.0, description="Share of syllabus topics covered (0.0 - 100.0%)")


class CoverageMetrics(BaseModel):
    total_topics: int = Field(default=0, description="Total syllabus topics")
    topics_with_candidates: int = Field(default=0, description="Topics with at least one candidate resource found")
    topics_with_relevant: int = Field(default=0, description="Topics with a sufficiently relevant resource confirmed")
    topics_with_no_resource: int = Field(default=0, description="Topics with no suitable educational resource found")
    topics_needing_review: int = Field(default=0, description="Topics with uncertain or ambiguous matches needing student verification")
    coverage_percentage: float = Field(default=0.0, description="Percentage of topics with verified relevant resources")


class ResourceDiscoveryRequest(BaseModel):
    preferred_language: str = Field(default="English", description="Target video language")
    force_refresh: bool = Field(default=False, description="Bypass SQLite cache and make live queries")
    allow_third_channel: bool = Field(default=False, description="Student consent to add a 3rd channel if 2 channels are insufficient")


class ResourceDiscoveryResponse(BaseModel):
    status: str = Field(default="success")
    syllabus_id: str = Field(description="Target syllabus ID")
    course_name: Optional[str] = Field(default=None)
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
    message: str = Field(description="Summary message")


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


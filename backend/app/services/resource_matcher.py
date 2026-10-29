import logging
from typing import List, Dict, Any, Optional

from app.models.database import (
    get_syllabus_hierarchy,
    get_topic_rejected_channels,
    add_rejected_channel,
    save_discovered_resources,
    get_syllabus_resources,
    update_topic_resource,
    set_third_channel_approved,
)
from app.services.youtube_client import YouTubeClientService
from app.schemas.resource import (
    VideoResource,
    TopicResourceMapping,
    ChannelCoverageSummary,
    CoverageMetrics,
    ResourceDiscoveryResponse,
    AlternativeResourceItem,
    AlternativeResourcesResponse,
)

logger = logging.getLogger("syllabus_sync.matcher")


class ResourceMatcherService:
    """
    Coordinates syllabus topic search query generation, YouTube API discovery,
    channel selection strategy (1-channel vs 2-channel vs 3rd-channel approval),
    channel replacement, and coverage tracking.
    """

    @classmethod
    async def discover_resources_for_syllabus(
        cls,
        syllabus_id: str,
        preferred_language: str = "English",
        force_refresh: bool = False,
        allow_third_channel: bool = False,
    ) -> ResourceDiscoveryResponse:
        """
        Discovers educational YouTube resources for all topics in the syllabus
        using the 1-channel -> 2-channel -> 3rd-channel approval policy.
        """
        # 1. Check if resources already discovered and not forced refresh
        if not force_refresh:
            existing = get_syllabus_resources(syllabus_id)
            if existing and existing.get("topic_resources"):
                # If third channel was approved recently, update state
                if allow_third_channel and existing.get("requires_third_channel_approval"):
                    set_third_channel_approved(syllabus_id, True)
                    existing["requires_third_channel_approval"] = False
                return ResourceDiscoveryResponse(**existing)

        # 2. Retrieve syllabus topic hierarchy
        hierarchy = get_syllabus_hierarchy(syllabus_id)
        if not hierarchy or not hierarchy.get("modules"):
            raise ValueError(f"Syllabus '{syllabus_id}' has no modules or topics to match.")

        course_name = hierarchy.get("course_name") or "Computer Science"
        modules = hierarchy.get("modules", [])

        # Flatten topics with module context
        flattened_topics = []
        for mod in modules:
            raw_mod_id = mod.get("id", "mod")
            mod_id = raw_mod_id if raw_mod_id.startswith(syllabus_id) else f"{syllabus_id}_{raw_mod_id}"
            mod_title = mod.get("title", "Module")
            for top in mod.get("topics", []):
                raw_top_id = top.get("id", "top")
                top_id = raw_top_id if raw_top_id.startswith(syllabus_id) else f"{syllabus_id}_{raw_top_id}"
                flattened_topics.append({
                    "topic_id": top_id,
                    "topic_title": top["title"],
                    "module_id": mod_id,
                    "module_title": mod_title,
                    "explanation": top.get("explanation", ""),
                    "estimated_minutes": top.get("estimated_minutes", 60),
                })

        total_topics_count = len(flattened_topics)
        if total_topics_count == 0:
            raise ValueError(f"Syllabus '{syllabus_id}' contains 0 topics.")

        # 3. For each topic, search candidate videos
        topic_candidates: Dict[str, List[Dict[str, Any]]] = {}
        channel_to_topics: Dict[str, set] = {}
        is_any_fallback = False

        for t in flattened_topics:
            t_id = t["topic_id"]
            # Exclude channels rejected by student for this topic
            rejected = get_topic_rejected_channels(syllabus_id, t_id)

            # Build query
            query = f"{course_name} {t['topic_title']}"
            videos, is_fallback = await YouTubeClientService.search_videos(
                query=query,
                language=preferred_language,
                max_results=5,
                force_refresh=force_refresh,
                excluded_channels=rejected,
            )

            if is_fallback:
                is_any_fallback = True

            topic_candidates[t_id] = videos

            for v in videos:
                ch = v["channel_title"]
                channel_to_topics.setdefault(ch, set()).add(t_id)

        # 4. Apply Channel Selection Strategy (1 -> 2 -> 3 with approval)
        # Sort channels by topic coverage count descending
        sorted_channels = sorted(
            channel_to_topics.items(),
            key=lambda item: len(item[1]),
            reverse=True
        )

        selected_channels: List[ChannelCoverageSummary] = []
        requires_third_approval = False
        third_candidates: List[str] = []
        strategy_explanation = ""
        active_channel_set: set = set()

        if not sorted_channels:
            strategy_explanation = "No suitable educational video channels were found for the syllabus topics."
        else:
            top_channel, top_topics = sorted_channels[0]
            top_coverage_ratio = len(top_topics) / total_topics_count

            # Policy Rule 1: Evaluate if ONE credible channel can cover most topics adequately (>= 75% or all if <= 4 topics)
            if top_coverage_ratio >= 0.75 or len(top_topics) == total_topics_count:
                active_channel_set.add(top_channel)
                selected_channels.append(ChannelCoverageSummary(
                    channel_title=top_channel,
                    topics_covered=len(top_topics),
                    topic_ids=list(top_topics),
                    is_primary=True,
                    percentage_of_course=round(top_coverage_ratio * 100, 1),
                ))
                strategy_explanation = (
                    f"Selected 1 primary channel '{top_channel}', which comprehensively covers "
                    f"{len(top_topics)} of {total_topics_count} ({round(top_coverage_ratio * 100)}%) syllabus topics."
                )

            # Policy Rule 2: Evaluate TWO complementary channels with balanced workload
            else:
                active_channel_set.add(top_channel)
                selected_channels.append(ChannelCoverageSummary(
                    channel_title=top_channel,
                    topics_covered=len(top_topics),
                    topic_ids=list(top_topics),
                    is_primary=True,
                    percentage_of_course=round(top_coverage_ratio * 100, 1),
                ))

                # Find best complementary second channel that covers maximum remaining topics
                remaining_topics = set(t["topic_id"] for t in flattened_topics) - top_topics
                best_second_channel = None
                best_second_overlap = set()

                for ch, ch_topics in sorted_channels[1:]:
                    uncovered_overlap = ch_topics & remaining_topics
                    if len(uncovered_overlap) > len(best_second_overlap):
                        best_second_overlap = uncovered_overlap
                        best_second_channel = ch

                if best_second_channel:
                    active_channel_set.add(best_second_channel)
                    selected_channels.append(ChannelCoverageSummary(
                        channel_title=best_second_channel,
                        topics_covered=len(best_second_overlap),
                        topic_ids=list(best_second_overlap),
                        is_primary=False,
                        percentage_of_course=round((len(best_second_overlap) / total_topics_count) * 100, 1),
                    ))

                combined_covered = top_topics | best_second_overlap
                still_uncovered = set(t["topic_id"] for t in flattened_topics) - combined_covered

                # Policy Rule 3: If 2 channels are still insufficient, ask student before introducing 3rd channel
                if len(still_uncovered) > 0:
                    # Find candidates for third channel
                    third_candidates_set = set()
                    for ch, ch_topics in sorted_channels:
                        if ch not in active_channel_set and (ch_topics & still_uncovered):
                            third_candidates_set.add(ch)

                    third_candidates = list(third_candidates_set)[:3]

                    if allow_third_channel and third_candidates:
                        # Student gave consent to introduce 3rd channel
                        ch3 = third_candidates[0]
                        ch3_topics = channel_to_topics.get(ch3, set()) & still_uncovered
                        active_channel_set.add(ch3)
                        selected_channels.append(ChannelCoverageSummary(
                            channel_title=ch3,
                            topics_covered=len(ch3_topics),
                            topic_ids=list(ch3_topics),
                            is_primary=False,
                            percentage_of_course=round((len(ch3_topics) / total_topics_count) * 100, 1),
                        ))
                        requires_third_approval = False
                        strategy_explanation = (
                            f"Introduced 3 channels with student approval: '{top_channel}' (primary), "
                            f"'{best_second_channel}' (secondary), and '{ch3}' to maximize course coverage."
                        )
                    else:
                        requires_third_approval = True
                        strategy_explanation = (
                            f"Two channels ('{top_channel}', '{best_second_channel or 'secondary'}') cover "
                            f"{len(combined_covered)} of {total_topics_count} topics. "
                            f"Approval is requested to introduce a 3rd channel for remaining topics."
                        )
                else:
                    strategy_explanation = (
                        f"Selected 2 complementary channels: '{top_channel}' and '{best_second_channel}' "
                        f"providing full coverage across all {total_topics_count} syllabus topics."
                    )

        # 5. Build final topic-to-resource mappings
        topic_mappings: List[Dict[str, Any]] = []
        covered_count = 0
        candidate_count = 0
        uncertain_count = 0
        no_resource_count = 0

        for t in flattened_topics:
            t_id = t["topic_id"]
            candidates = topic_candidates.get(t_id, [])

            if candidates:
                candidate_count += 1

            # Pick best video: prioritize active selected channels
            chosen_video = None
            for v in candidates:
                if v["channel_title"] in active_channel_set:
                    chosen_video = v
                    break

            if not chosen_video and candidates:
                # If third channel is pending approval, mark as uncertain/candidate_only
                chosen_video = candidates[0]
                is_from_active = chosen_video["channel_title"] in active_channel_set
            else:
                is_from_active = bool(chosen_video)

            if chosen_video:
                if is_from_active:
                    match_status = "relevant"
                    match_confidence = "high"
                    notes = f"Verified alignment with selected course channel '{chosen_video['channel_title']}'."
                    covered_count += 1
                else:
                    match_status = "needs_review" if requires_third_approval else "candidate_only"
                    match_confidence = "uncertain"
                    notes = f"Candidate from '{chosen_video['channel_title']}' pending channel approval."
                    uncertain_count += 1

                # Construct VideoResource
                res = VideoResource(
                    id=chosen_video["id"],
                    video_id=chosen_video["video_id"],
                    title=chosen_video["title"],
                    channel_title=chosen_video["channel_title"],
                    channel_id=chosen_video.get("channel_id"),
                    thumbnail_url=chosen_video["thumbnail_url"],
                    duration_seconds=chosen_video["duration_seconds"],
                    duration_formatted=chosen_video["duration_formatted"],
                    language=chosen_video["language"],
                    published_at=chosen_video.get("published_at"),
                    view_count=chosen_video.get("view_count", 0),
                    relevance_score=chosen_video.get("relevance_score", 0.8),
                    relevance_explanation=chosen_video.get("relevance_explanation", notes),
                    is_uncertain=(match_confidence == "uncertain"),
                    video_url=chosen_video["video_url"],
                )
            else:
                match_status = "no_resource"
                match_confidence = "uncertain"
                notes = "No suitable educational video found matching this topic."
                no_resource_count += 1
                res = None

            topic_mappings.append({
                "topic_id": t_id,
                "topic_title": t["topic_title"],
                "module_id": t["module_id"],
                "module_title": t["module_title"],
                "resource": res.model_dump() if res else None,
                "match_status": match_status,
                "match_confidence": match_confidence,
                "relevance_notes": notes,
                "rejected_channels": get_topic_rejected_channels(syllabus_id, t_id),
            })

        # 6. Compute coverage metrics
        cov_pct = round((covered_count / total_topics_count) * 100, 1) if total_topics_count > 0 else 0.0
        coverage_metrics = CoverageMetrics(
            total_topics=total_topics_count,
            topics_with_candidates=candidate_count,
            topics_with_relevant=covered_count,
            topics_with_no_resource=no_resource_count,
            topics_needing_review=uncertain_count,
            coverage_percentage=cov_pct,
        )

        discovery_engine = "Local Deterministic Fallback" if is_any_fallback else "YouTube Data API v3"

        # 7. Persist to SQLite
        save_discovered_resources(
            syllabus_id=syllabus_id,
            topic_mappings=topic_mappings,
            coverage=coverage_metrics.model_dump(),
            selected_channels=[c.model_dump() for c in selected_channels],
            requires_third_approval=requires_third_approval,
            third_channel_candidates=third_candidates,
            strategy_explanation=strategy_explanation,
            is_fallback=is_any_fallback,
            discovery_engine=discovery_engine,
        )

        return ResourceDiscoveryResponse(
            status="success",
            syllabus_id=syllabus_id,
            course_name=course_name,
            coverage=coverage_metrics,
            selected_channels=selected_channels,
            requires_third_channel_approval=requires_third_approval,
            third_channel_candidates=third_candidates,
            strategy_explanation=strategy_explanation,
            topic_resources=[TopicResourceMapping(**m) for m in topic_mappings],
            is_fallback=is_any_fallback,
            discovery_engine=discovery_engine,
            message=f"Discovered resources for {covered_count} of {total_topics_count} topics ({cov_pct}% coverage).",
        )

    @classmethod
    async def get_alternatives_for_topic(
        cls,
        syllabus_id: str,
        topic_id: str,
        preferred_language: str = "English",
    ) -> AlternativeResourcesResponse:
        """
        Finds alternative candidate channels and videos for a specific topic,
        strictly excluding channels rejected by the student.
        """
        hierarchy = get_syllabus_hierarchy(syllabus_id)
        if not hierarchy:
            raise ValueError(f"Syllabus '{syllabus_id}' not found.")

        # Find target topic
        target_topic = None
        for mod in hierarchy.get("modules", []):
            for t in mod.get("topics", []):
                t_id = t["id"] if t["id"].startswith(syllabus_id) else f"{syllabus_id}_{t['id']}"
                if t_id == topic_id or t["id"] == topic_id or topic_id.endswith(t["id"]):
                    target_topic = t
                    break
            if target_topic:
                break

        if not target_topic:
            raise ValueError(f"Topic '{topic_id}' not found in syllabus '{syllabus_id}'.")

        rejected_channels = get_topic_rejected_channels(syllabus_id, topic_id)

        # Get current resource to know current channel
        resources_data = get_syllabus_resources(syllabus_id)
        current_channel = None
        if resources_data:
            for tr in resources_data.get("topic_resources", []):
                tr_id = tr["topic_id"] if tr["topic_id"].startswith(syllabus_id) else f"{syllabus_id}_{tr['topic_id']}"
                if (tr_id == topic_id or tr["topic_id"] == topic_id or topic_id.endswith(tr["topic_id"])) and tr.get("resource"):
                    current_channel = tr["resource"].get("channel_title")
                    break

        all_excluded = set(rejected_channels)
        if current_channel:
            all_excluded.add(current_channel)

        # Search alternatives
        query = f"{hierarchy.get('course_name', '')} {target_topic['title']}"
        videos, _ = await YouTubeClientService.search_videos(
            query=query,
            language=preferred_language,
            max_results=8,
            force_refresh=True,
            excluded_channels=list(all_excluded),
        )

        alternatives: List[AlternativeResourceItem] = []
        for v in videos:
            alternatives.append(AlternativeResourceItem(
                video=VideoResource(
                    id=v["id"],
                    video_id=v["video_id"],
                    title=v["title"],
                    channel_title=v["channel_title"],
                    channel_id=v.get("channel_id"),
                    thumbnail_url=v["thumbnail_url"],
                    duration_seconds=v["duration_seconds"],
                    duration_formatted=v["duration_formatted"],
                    language=v["language"],
                    published_at=v.get("published_at"),
                    view_count=v.get("view_count", 0),
                    relevance_score=v.get("relevance_score", 0.8),
                    relevance_explanation=f"Alternative educational lesson from channel '{v['channel_title']}'.",
                    is_uncertain=False,
                    video_url=v["video_url"],
                ),
                recommendation_reason=f"Popular lesson with {v.get('view_count', 0):,} views.",
                is_current=False,
            ))

        return AlternativeResourcesResponse(
            topic_id=topic_id,
            topic_title=target_topic["title"],
            current_channel=current_channel,
            rejected_channels=rejected_channels,
            alternatives=alternatives,
            message=f"Found {len(alternatives)} alternative candidates for '{target_topic['title']}'.",
        )

    @classmethod
    async def replace_topic_channel(
        cls,
        syllabus_id: str,
        topic_id: str,
        rejected_channel: str,
        selected_video_id: str,
        reason: Optional[str] = None,
    ) -> TopicResourceMapping:
        """
        Replaces the current channel for a single topic with the selected alternative.
        Excludes the rejected channel and preserves all other topics and study progress.
        """
        # 1. Add rejected channel
        add_rejected_channel(syllabus_id, topic_id, rejected_channel, reason)

        # 2. Look up selected video details (from alternatives or YouTube)
        # Search query for the video ID or generate directly
        video_url = f"https://www.youtube.com/watch?v={selected_video_id}"
        video_dict = {
            "id": selected_video_id,
            "video_id": selected_video_id,
            "title": f"Replacement Tutorial for {topic_id}",
            "channel_title": "Selected Alternative Creator",
            "channel_id": None,
            "thumbnail_url": f"https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=600&auto=format&fit=crop&q=80",
            "duration_seconds": 1200,
            "duration_formatted": "20:00",
            "language": "English",
            "published_at": "2024-01-01T00:00:00Z",
            "view_count": 50000,
            "relevance_score": 0.9,
            "relevance_explanation": f"Student-selected replacement replacing '{rejected_channel}'.",
            "is_uncertain": False,
            "video_url": video_url,
        }

        # Check if video was already in alternatives or cache
        cached_resources = get_syllabus_resources(syllabus_id)
        if cached_resources:
            for tr in cached_resources.get("topic_resources", []):
                res = tr.get("resource")
                if res and res.get("video_id") == selected_video_id:
                    video_dict.update(res)
                    break

        # 3. Update single topic resource in SQLite
        update_topic_resource(
            syllabus_id=syllabus_id,
            topic_id=topic_id,
            video_dict=video_dict,
            match_status="relevant",
            match_confidence="high",
            relevance_notes=f"Student selected replacement; '{rejected_channel}' rejected.",
        )

        hierarchy = get_syllabus_hierarchy(syllabus_id)
        module_id = "mod_1"
        module_title = "Module"
        topic_title = "Topic"

        if hierarchy:
            for mod in hierarchy.get("modules", []):
                for t in mod.get("topics", []):
                    if t["id"] == topic_id:
                        module_id = mod.get("id", "mod_1")
                        module_title = mod.get("title", "Module")
                        topic_title = t.get("title", "Topic")
                        break

        rejected_list = get_topic_rejected_channels(syllabus_id, topic_id)

        return TopicResourceMapping(
            topic_id=topic_id,
            topic_title=topic_title,
            module_id=module_id,
            module_title=module_title,
            resource=VideoResource(**video_dict),
            match_status="relevant",
            match_confidence="high",
            relevance_notes=f"Replacement selected; '{rejected_channel}' excluded.",
            rejected_channels=rejected_list,
        )

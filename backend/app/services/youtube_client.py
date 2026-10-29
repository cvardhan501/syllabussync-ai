import re
import hashlib
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings
from app.models.database import get_cached_search, save_cached_search

logger = logging.getLogger("syllabus_sync.youtube")

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"

LANGUAGE_CODE_MAP = {
    "english": "en",
    "hindi": "hi",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "tamil": "ta",
    "telugu": "te",
}


class YouTubeApiException(Exception):
    """Base exception for YouTube Data API operations."""
    pass


class YouTubeAuthException(YouTubeApiException):
    """Raised when YouTube API key is missing or invalid."""
    pass


class YouTubeQuotaExceededException(YouTubeApiException):
    """Raised when YouTube API daily quota limit is reached."""
    pass


class YouTubeConnectionException(YouTubeApiException):
    """Raised on network failures or timeouts."""
    pass


def parse_iso8601_duration(iso_duration: str) -> tuple[int, str]:
    """
    Parses an ISO 8601 duration string (e.g., 'PT1H15M30S', 'PT12M45S', 'PT45S')
    into total seconds and human-readable string (e.g. '1:15:30' or '12:45').
    """
    if not iso_duration or not isinstance(iso_duration, str):
        return 0, "0:00"

    pattern = re.compile(
        r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
    )
    match = pattern.match(iso_duration)
    if not match:
        return 0, "0:00"

    parts = match.groupdict()
    days = int(parts.get("days") or 0)
    hours = int(parts.get("hours") or 0) + days * 24
    minutes = int(parts.get("minutes") or 0)
    seconds = int(parts.get("seconds") or 0)

    total_seconds = hours * 3600 + minutes * 60 + seconds

    if hours > 0:
        formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        formatted = f"{minutes}:{seconds:02d}"

    return total_seconds, formatted


class YouTubeClientService:
    """
    Client for YouTube Data API v3 with quota protection, SQLite query caching,
    timeout resilience, deduplication, and local development fallback.
    """

    @classmethod
    def _compute_query_hash(cls, query: str, language: str, max_results: int) -> str:
        raw = f"{query.strip().lower()}|{language.strip().lower()}|{max_results}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    async def search_videos(
        cls,
        query: str,
        language: str = "English",
        max_results: Optional[int] = None,
        force_refresh: bool = False,
        excluded_channels: Optional[List[str]] = None,
    ) -> tuple[List[Dict[str, Any]], bool]:
        """
        Searches for educational videos matching the query.
        Returns (list_of_video_dicts, is_fallback).
        """
        max_results = max_results or settings.youtube_max_search_results
        lang_code = LANGUAGE_CODE_MAP.get(language.lower(), "en")
        query_hash = cls._compute_query_hash(query, lang_code, max_results)
        excluded_set = {ch.strip().lower() for ch in (excluded_channels or [])}

        # 1. Check SQLite Cache if not forcing refresh
        if not force_refresh:
            cached_data = get_cached_search(query_hash)
            if cached_data and isinstance(cached_data, list):
                # Filter out excluded channels from cached results
                filtered = [
                    v for v in cached_data 
                    if v.get("channel_title", "").strip().lower() not in excluded_set
                ]
                if filtered:
                    return filtered, False

        # 2. Check credentials
        has_credentials = settings.has_youtube_credentials()

        if not has_credentials:
            if settings.allow_dev_fallback_youtube:
                logger.info(f"YOUTUBE_API_KEY not configured; using deterministic local fallback for '{query}'.")
                fallback_videos = cls._generate_fallback_videos(query, language, excluded_set)
                return fallback_videos, True
            else:
                raise YouTubeAuthException(
                    "YouTube API key is not configured. Set YOUTUBE_API_KEY in the backend environment."
                )

        api_key = settings.youtube_api_key

        # 3. Call official YouTube Data API v3
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Step A: Search videos
                search_params = {
                    "part": "snippet",
                    "type": "video",
                    "q": f"{query} tutorial lecture educational",
                    "maxResults": min(max_results * 2, 15),  # fetch buffer for deduplication & filtering
                    "relevanceLanguage": lang_code,
                    "videoEmbeddable": "true",
                    "safeSearch": "strict",
                    "key": api_key,
                }

                search_resp = await client.get(f"{YOUTUBE_BASE_URL}/search", params=search_params)

                if search_resp.status_code == 403:
                    error_json = search_resp.json().get("error", {})
                    errors = error_json.get("errors", [])
                    reasons = [e.get("reason") for e in errors]
                    if "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons:
                        logger.warning("YouTube API daily quota exceeded. Falling back if permitted.")
                        if settings.allow_dev_fallback_youtube:
                            return cls._generate_fallback_videos(query, language, excluded_set), True
                        raise YouTubeQuotaExceededException(
                            "YouTube Data API daily quota limit exceeded. Please check your Google Cloud Console quota."
                        )
                    elif "keyInvalid" in reasons or "API_KEY_INVALID" in reasons:
                        raise YouTubeAuthException("Configured YOUTUBE_API_KEY is invalid or unauthorized.")
                    else:
                        raise YouTubeApiException(f"YouTube API permission error: {error_json.get('message', 'Forbidden')}")

                elif search_resp.status_code == 400:
                    raise YouTubeAuthException("YouTube API request was rejected (invalid API key or parameter).")

                search_resp.raise_for_status()
                search_data = search_resp.json()
                items = search_data.get("items", [])

                if not items:
                    return [], False

                video_ids = [
                    item["id"]["videoId"]
                    for item in items
                    if item.get("id", {}).get("videoId")
                ]

                # Step B: Fetch detailed video metadata (durations, statistics)
                details_params = {
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(video_ids),
                    "key": api_key,
                }

                details_resp = await client.get(f"{YOUTUBE_BASE_URL}/videos", params=details_params)
                details_resp.raise_for_status()
                details_data = details_resp.json()
                video_items = details_data.get("items", [])

                results = []
                seen_video_ids = set()

                for v in video_items:
                    v_id = v["id"]
                    if v_id in seen_video_ids:
                        continue
                    seen_video_ids.add(v_id)

                    snippet = v.get("snippet", {})
                    content_details = v.get("contentDetails", {})
                    stats = v.get("statistics", {})

                    channel_title = snippet.get("channelTitle", "YouTube Educator")
                    if channel_title.strip().lower() in excluded_set:
                        continue

                    # Parse duration
                    raw_duration = content_details.get("duration", "PT0S")
                    duration_sec, duration_fmt = parse_iso8601_duration(raw_duration)

                    # Thumbnails
                    thumbs = snippet.get("thumbnails", {})
                    thumb_url = (
                        thumbs.get("high", {}).get("url")
                        or thumbs.get("medium", {}).get("url")
                        or thumbs.get("default", {}).get("url")
                        or f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                    )

                    view_count = int(stats.get("viewCount", 0))

                    results.append({
                        "id": v_id,
                        "video_id": v_id,
                        "title": snippet.get("title", "Educational Video"),
                        "channel_title": channel_title,
                        "channel_id": snippet.get("channelId"),
                        "thumbnail_url": thumb_url,
                        "duration_seconds": duration_sec,
                        "duration_formatted": duration_fmt,
                        "language": language,
                        "published_at": snippet.get("publishedAt"),
                        "view_count": view_count,
                        "relevance_score": 0.85,
                        "relevance_explanation": f"Official educational video from {channel_title}.",
                        "is_uncertain": False,
                        "video_url": f"https://www.youtube.com/watch?v={v_id}",
                    })

                    if len(results) >= max_results:
                        break

                # Save to cache
                save_cached_search(query_hash, query, lang_code, results)
                return results, False

            except httpx.TimeoutException:
                logger.error("Timeout connecting to YouTube Data API v3.")
                if settings.allow_dev_fallback_youtube:
                    return cls._generate_fallback_videos(query, language, excluded_set), True
                raise YouTubeConnectionException("YouTube Data API request timed out. Please check your internet connection.")
            except httpx.RequestError as exc:
                logger.error(f"Network error during YouTube Data API request: {str(exc)}")
                if settings.allow_dev_fallback_youtube:
                    return cls._generate_fallback_videos(query, language, excluded_set), True
                raise YouTubeConnectionException(f"Network error contacting YouTube: {str(exc)}")

    @classmethod
    def _generate_fallback_videos(
        cls,
        query: str,
        language: str,
        excluded_channels: set,
    ) -> List[Dict[str, Any]]:
        """
        Generates realistic educational videos using known educational creators
        when YOUTUBE_API_KEY is not configured or in development mode.
        """
        # Pool of standard channels
        channel_pool = [
            ("freeCodeCamp.org", "UC8butISFwT-Wl7EV0hUK0BQ", "English"),
            ("CS50", "UCcabW7890RKJzL968QWEykA", "English"),
            ("MIT OpenCourseWare", "UCEBb1b_L6zDS3xTUrIALZOw", "English"),
            ("Traversy Media", "UC29ju8bIPH5as8OGnSuP50Q", "English"),
            ("CodeWithHarry", "UCeVMnSShP_Iviwkknt83cww", "Hindi"),
            ("Apna College", "UCBwmMxybNva6P_5VmxjzwqA", "Hindi"),
            ("Khan Academy", "UC4a-Gbdw7vOaccHmFo40b9g", "English"),
            ("Abdul Bari", "UCZCFT11CWBi3MHNlGf019nw", "English"),
            ("Corey Schafer", "UCCezIgC97PvUuR4_gbFUs5g", "English"),
        ]

        # Prioritize channel matching target language
        target_lang_lower = language.lower()
        matching_channels = [
            ch for ch in channel_pool 
            if ch[2].lower() == target_lang_lower and ch[0].strip().lower() not in excluded_channels
        ]
        if not matching_channels:
            matching_channels = [
                ch for ch in channel_pool 
                if ch[0].strip().lower() not in excluded_channels
            ]

        results = []
        for i, (ch_name, ch_id, ch_lang) in enumerate(matching_channels[:3]):
            # Deterministic video ID based on query and channel
            v_hash = hashlib.md5(f"{query}_{ch_name}".encode("utf-8")).hexdigest()[:11]
            duration_minutes = 15 + ((i * 17) % 45)
            duration_sec = duration_minutes * 60 + ((i * 23) % 60)
            fmt_sec = f"{duration_minutes}:{((i * 23) % 60):02d}"

            results.append({
                "id": v_hash,
                "video_id": v_hash,
                "title": f"{query} Full Course & Comprehensive Lecture - {ch_name}",
                "channel_title": ch_name,
                "channel_id": ch_id,
                "thumbnail_url": f"https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=600&auto=format&fit=crop&q=80",
                "duration_seconds": duration_sec,
                "duration_formatted": fmt_sec,
                "language": ch_lang,
                "published_at": "2024-01-15T12:00:00Z",
                "view_count": 125000 + i * 45000,
                "relevance_score": 0.88 - (i * 0.05),
                "relevance_explanation": f"Matched educational topic from verified channel {ch_name}.",
                "is_uncertain": False,
                "video_url": f"https://www.youtube.com/watch?v={v_hash}",
            })

        return results


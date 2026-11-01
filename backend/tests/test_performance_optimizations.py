import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import httpx

from app.services.youtube_client import YouTubeClientService
from app.services.resource_matcher import ResourceMatcherService, _RELEVANCE_CACHE, _PREVIEW_CACHE
from app.models.database import (
    get_cached_search,
    save_cached_search,
    _IN_MEMORY_SEARCH_CACHE,
    get_all_rejected_channels_for_syllabus,
    add_rejected_channel,
)
from app.api.health import get_health, _LAST_HEALTH_CHECK_TIME, _CACHED_DB_OK


@pytest.mark.anyio
async def test_http_client_singleton_and_reuse():
    """Verify YouTubeClientService reuses the persistent keep-alive httpx.AsyncClient."""
    client1 = await YouTubeClientService.get_http_client()
    client2 = await YouTubeClientService.get_http_client()
    assert client1 is client2
    assert not client1.is_closed


@pytest.mark.anyio
async def test_search_videos_batch_bounded_concurrency():
    """Verify search_videos_batch enforces the concurrency semaphore limit."""
    active_concurrent = 0
    max_observed_concurrent = 0
    lock = asyncio.Lock()

    async def mock_search_impl(query, **kwargs):
        nonlocal active_concurrent, max_observed_concurrent
        async with lock:
            active_concurrent += 1
            if active_concurrent > max_observed_concurrent:
                max_observed_concurrent = active_concurrent
        await asyncio.sleep(0.02)
        async with lock:
            active_concurrent -= 1
        return ([{"video_id": f"v_{query}", "channel_title": "Test Channel"}], False)

    requests = [{"query": f"Topic {i}", "language": "English"} for i in range(12)]
    with patch.object(YouTubeClientService, "search_videos", side_effect=mock_search_impl):
        results = await YouTubeClientService.search_videos_batch(requests, concurrency_limit=4)
        assert len(results) == 12
        assert max_observed_concurrent <= 4


def test_in_memory_search_cache_hit():
    """Verify get_cached_search serves in-memory cached results instantaneously without database hits."""
    test_hash = f"test_perf_hash_{time.time()}"
    sample_data = [{"video_id": "vid_perf_1", "title": "Performance Lecture"}]

    save_cached_search(test_hash, "perf query", "en", sample_data)

    # In-memory cache must now contain this query_hash
    assert test_hash in _IN_MEMORY_SEARCH_CACHE

    # Ensure get_cached_search returns data even if database connection raises an error
    with patch("app.models.database.get_db_connection", side_effect=RuntimeError("DB should not be reached")):
        cached = get_cached_search(test_hash)
        assert cached is not None
        assert cached[0]["video_id"] == "vid_perf_1"


def test_evaluate_video_relevance_memoization():
    """Verify evaluate_video_relevance memoizes score and status for repeated candidate assessments."""
    _RELEVANCE_CACHE.clear()
    video = {
        "id": "vid_memo_1",
        "video_id": "vid_memo_1",
        "title": "CPU Scheduling Algorithms FCFS and SJF Tutorial",
        "description": "Comprehensive explanation of CPU scheduling and process dispatch",
        "channel_title": "Gate Smashers",
        "duration_seconds": 1800,
        "duration_formatted": "30:00",
    }
    top_title = "CPU Scheduling Algorithms FCFS SJF"
    course_name = "Operating Systems"

    score1, status1, expl1 = ResourceMatcherService.evaluate_video_relevance(top_title, video, course_name)
    assert status1 == "verified"
    assert (top_title.lower(), "vid_memo_1", course_name.lower()) in _RELEVANCE_CACHE

    # Subsequent call with mutated video text but same ID must hit cache
    mutated_video = dict(video)
    mutated_video["title"] = "Different unmatching title"
    score2, status2, expl2 = ResourceMatcherService.evaluate_video_relevance(top_title, mutated_video, course_name)
    assert score2 == score1
    assert status2 == status1
    assert expl2 == expl1


def test_get_all_rejected_channels_for_syllabus():
    """Verify get_all_rejected_channels_for_syllabus loads all rejected channels in a single batch query."""
    s_id = f"syl_perf_test_{int(time.time())}"
    add_rejected_channel(s_id, "topic_1", "Channel Alpha", "Disliked accent")
    add_rejected_channel(s_id, "topic_2", "Channel Beta", "Too long")

    all_rejected = get_all_rejected_channels_for_syllabus(s_id)
    assert "Channel Alpha" in all_rejected.get("topic_1", [])
    assert "Channel Beta" in all_rejected.get("topic_2", [])


@pytest.mark.anyio
async def test_health_check_caching():
    """Verify get_health caches database status within TTL window to prevent connection storms."""
    # First call pings DB
    resp1 = await get_health()
    assert resp1.status == "healthy"

    # Subsequent call within 15 seconds returns cached status without invoking DB
    with patch("app.models.database.get_db_connection", side_effect=RuntimeError("DB should not be contacted")):
        resp2 = await get_health()
        assert resp2.database_connected == resp1.database_connected


def test_long_multiclause_topic_query_bounded():
    """Verify multi-clause topic titles are cleanly truncated to primary concepts and bounded within length limit."""
    long_topic = (
        "Overview of system design; Estimating performance; Making a reuse plan; "
        "An exception-handling policy; Making a policy for concurrency; Global software control; "
        "Setting boundary conditions; Implementing concurrency control; System design milestones."
    )
    course_name = "Object Oriented Analysis and Design (CSE3016)"
    query = ResourceMatcherService.generate_topic_search_query(course_name, long_topic)

    assert "Object Oriented Analysis and Design" in query
    assert len(query) < 140
    # Primary concepts preserved
    assert "Overview of system design" in query or "Estimating performance" in query
    # Trailing 7th/8th clauses stripped to prevent HTTP 400
    assert "System design milestones" not in query


def test_sanitize_log_text_redacts_keys():
    """Verify API keys and credentials are never leaked in logs or error traces."""
    sample_url = "https://www.googleapis.com/youtube/v3/search?part=snippet&q=math&key=AIzaSySecretKey12345&maxResults=5"
    sanitized = YouTubeClientService._sanitize_log_text(sample_url)
    assert "AIzaSySecretKey12345" not in sanitized
    assert "key=[REDACTED]" in sanitized


@pytest.mark.anyio
async def test_youtube_expired_api_key_raises_auth_exception():
    """Verify HTTP 400 with 'API key expired' or 'API_KEY_INVALID' raises YouTubeAuthException in production mode."""
    from app.services.youtube_client import YouTubeAuthException
    from app.core.config import settings

    mock_resp = httpx.Response(
        status_code=400,
        json={
            "error": {
                "code": 400,
                "message": "API key expired. Please renew the API key.",
                "status": "INVALID_ARGUMENT",
                "details": [{"reason": "API_KEY_INVALID"}]
            }
        },
        request=httpx.Request("GET", "https://www.googleapis.com/youtube/v3/search")
    )

    with patch.object(settings, "allow_dev_fallback_youtube", False):
        with patch.object(settings, "youtube_api_key", "AIzaSyTestExpiredKey"):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            with patch.object(YouTubeClientService, "get_http_client", return_value=mock_client):
                with pytest.raises(YouTubeAuthException) as exc_info:
                    await YouTubeClientService.search_videos("Algorithm Design", force_refresh=True)
                assert "expired or invalid" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_channel_discovery_fault_tolerant_to_single_topic_failure():
    """Verify discover_channels_for_syllabus succeeds when a single topic fails but others succeed."""
    sample_hierarchy = {
        "course_name": "Software Engineering",
        "course_code": "SE101",
        "modules": [
            {
                "id": "m1",
                "title": "Module 1",
                "topics": [
                    {"id": "t1", "title": "Topic One Clean"},
                    {"id": "t2", "title": "Topic Two Error Prone"},
                    {"id": "t3", "title": "Topic Three Clean"},
                ]
            }
        ]
    }

    async def mock_search(query, **kwargs):
        if "Topic Two" in query:
            raise httpx.RequestError("Temporary network glitch on topic 2")
        return [
            {
                "video_id": f"vid_{query[:10]}",
                "title": f"Video for {query[:20]}",
                "channel_title": "EduChannel Alpha",
                "channel_id": "ch_alpha",
                "thumbnail_url": "https://img.youtube.com/thumb.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": "English",
                "relevance_score": 0.85,
                "relevance_explanation": "Good match",
                "availability_status": "available",
            }
        ], False

    with patch("app.services.resource_matcher.get_syllabus_hierarchy", return_value=sample_hierarchy):
        with patch.object(YouTubeClientService, "search_videos", side_effect=mock_search):
            res = await ResourceMatcherService.discover_channels_for_syllabus("syl_resilience_test")
            assert res.status == "success"
            assert len(res.discovered_channels) >= 1
            assert res.discovered_channels[0].channel_title == "EduChannel Alpha"


def test_channel_discovery_endpoint_catches_auth_exception():
    """Verify POST /api/syllabus/{syllabus_id}/channel-discovery returns HTTP 502 Bad Gateway on YouTubeAuthException."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.youtube_client import YouTubeAuthException

    client = TestClient(app)

    with patch("app.api.resources.get_syllabus_owner_id", return_value=None):
        with patch.object(
            ResourceMatcherService,
            "discover_channels_for_syllabus",
            side_effect=YouTubeAuthException("YouTube Data API key is expired or invalid.")
        ):
            resp = client.post("/api/syllabus/test_syl_123/channel-discovery", json={"languages": ["English"]})
            assert resp.status_code == 502
            assert "YouTube Authentication Error" in resp.json()["detail"]
            assert "expired or invalid" in resp.json()["detail"]



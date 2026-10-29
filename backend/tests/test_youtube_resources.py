import io
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import docx
import httpx
import pytest

from app.main import app
from app.core.config import Settings, settings
from app.services.youtube_client import parse_iso8601_duration, YouTubeClientService
from app.models.database import (
    get_syllabus_resources,
    get_topic_rejected_channels,
)

client = TestClient(app)


def create_sample_syllabus(title: str = "Computer Science 101") -> str:
    """Helper to upload and analyze a syllabus, returning syllabus_id."""
    doc = docx.Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph("Module 1: Foundations of Programming")
    doc.add_paragraph("Introduction to Python and Syntax")
    doc.add_paragraph("Control Flow and Loops")
    doc.add_paragraph("Module 2: Advanced Data Structures")
    doc.add_paragraph("Linked Lists and Stacks")
    doc.add_paragraph("Binary Search Trees")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/syllabus/analyze",
        files={"file": ("test_course.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 200
    return res.json()["syllabus_id"]


def test_parse_iso8601_duration():
    """Verify ISO 8601 duration parser handles hours, minutes, seconds, and edge cases."""
    assert parse_iso8601_duration("PT15M33S") == (933, "15:33")
    assert parse_iso8601_duration("PT1H23M45S") == (5025, "1:23:45")
    assert parse_iso8601_duration("PT45S") == (45, "0:45")
    assert parse_iso8601_duration("PT1H") == (3600, "1:00:00")
    assert parse_iso8601_duration("P0D") == (0, "0:00")
    assert parse_iso8601_duration("") == (0, "0:00")
    assert parse_iso8601_duration("invalid") == (0, "0:00")


@pytest.mark.anyio
async def test_youtube_api_mocked_http_success():
    """Verify official YouTube Data API response parsing and duration conversion with mocked HTTP."""
    search_mock_response = {
        "items": [
            {"id": {"videoId": "vid_abc123"}},
            {"id": {"videoId": "vid_xyz789"}},
        ]
    }

    videos_mock_response = {
        "items": [
            {
                "id": "vid_abc123",
                "snippet": {
                    "title": "Python for Beginners - Full Course",
                    "channelTitle": "freeCodeCamp.org",
                    "channelId": "UC8butISFwT-Wl7EV0hUK0BQ",
                    "thumbnails": {"high": {"url": "https://img.youtube.com/vi/vid_abc123/hqdefault.jpg"}},
                    "publishedAt": "2023-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT4H20M15S"},
                "statistics": {"viewCount": "2500000"},
            },
            {
                "id": "vid_xyz789",
                "snippet": {
                    "title": "Data Structures in 10 Minutes",
                    "channelTitle": "CS50",
                    "channelId": "UCcabW7890RKJzL968QWEykA",
                    "thumbnails": {"high": {"url": "https://img.youtube.com/vi/vid_xyz789/hqdefault.jpg"}},
                    "publishedAt": "2023-02-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M00S"},
                "statistics": {"viewCount": "1200000"},
            },
        ]
    }

    async def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "/search" in url:
            resp.json.return_value = search_mock_response
        elif "/videos" in url:
            resp.json.return_value = videos_mock_response
        resp.raise_for_status = MagicMock()
        return resp

    with patch.object(Settings, "has_youtube_credentials", return_value=True):
        with patch.object(settings, "youtube_api_key", "test_mock_key"):
            with patch("httpx.AsyncClient.get", side_effect=mock_get):
                videos, is_fallback = await YouTubeClientService.search_videos(
                    query="Python Basics",
                    language="English",
                    force_refresh=True,
                )

                assert is_fallback is False
                assert len(videos) == 2
                assert videos[0]["video_id"] == "vid_abc123"
                assert videos[0]["channel_title"] == "freeCodeCamp.org"
                assert videos[0]["duration_formatted"] == "4:20:15"
                assert videos[0]["duration_seconds"] == 15615
                assert videos[0]["view_count"] == 2500000
                assert videos[1]["video_id"] == "vid_xyz789"
                assert videos[1]["duration_formatted"] == "10:00"


def test_missing_api_key_and_fallback_disabled_returns_503():
    """Verify endpoint returns 503 when YouTube API key is missing and fallback is explicitly disabled."""
    s_id = create_sample_syllabus("OS and Networking")

    with patch.object(Settings, "has_youtube_credentials", return_value=False):
        with patch.object(settings, "allow_dev_fallback_youtube", False):
            response = client.post(
                f"/api/syllabus/{s_id}/discover-resources",
                json={"preferred_language": "English", "force_refresh": True}
            )
            assert response.status_code == 503
            assert "YouTube Authentication Error" in response.json()["detail"]


@pytest.mark.anyio
async def test_quota_exceeded_handling():
    """Verify quota exceeded response (403 quotaExceeded) is properly handled."""
    async def mock_quota_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 403
        resp.json.return_value = {
            "error": {
                "errors": [{"reason": "quotaExceeded", "message": "Daily Limit Exceeded"}],
                "message": "Daily Limit Exceeded"
            }
        }
        return resp

    with patch.object(Settings, "has_youtube_credentials", return_value=True):
        with patch.object(settings, "youtube_api_key", "test_mock_key"):
            with patch.object(settings, "allow_dev_fallback_youtube", False):
                with patch("httpx.AsyncClient.get", side_effect=mock_quota_get):
                    with pytest.raises(Exception) as excinfo:
                        await YouTubeClientService.search_videos("Sorting", force_refresh=True)
                    assert "quota" in str(excinfo.value).lower()


@pytest.mark.anyio
async def test_deduplication_of_videos():
    """Verify duplicate video IDs in search/video responses are cleanly deduplicated."""
    videos_mock_with_duplicates = {
        "items": [
            {
                "id": "vid_dup1",
                "snippet": {"title": "Title 1", "channelTitle": "Ch 1", "thumbnails": {}},
                "contentDetails": {"duration": "PT10M"},
                "statistics": {"viewCount": "100"},
            },
            {
                "id": "vid_dup1",  # duplicate ID
                "snippet": {"title": "Title 1 Duplicate", "channelTitle": "Ch 1", "thumbnails": {}},
                "contentDetails": {"duration": "PT10M"},
                "statistics": {"viewCount": "100"},
            },
        ]
    }

    async def mock_dup_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "/search" in url:
            resp.json.return_value = {"items": [{"id": {"videoId": "vid_dup1"}}, {"id": {"videoId": "vid_dup1"}}]}
        else:
            resp.json.return_value = videos_mock_with_duplicates
        resp.raise_for_status = MagicMock()
        return resp

    with patch.object(Settings, "has_youtube_credentials", return_value=True):
        with patch.object(settings, "youtube_api_key", "test_mock_key"):
            with patch("httpx.AsyncClient.get", side_effect=mock_dup_get):
                videos, _ = await YouTubeClientService.search_videos("Deduplication Test", force_refresh=True)
                assert len(videos) == 1
                assert videos[0]["video_id"] == "vid_dup1"


def test_one_channel_adequate_coverage_policy():
    """Verify that when 1 credible channel adequately covers syllabus topics, it is selected as primary."""
    s_id = create_sample_syllabus("Discrete Mathematics")

    # Mock search to return 'freeCodeCamp.org' for all topics
    def mock_search_one_channel(query, language, **kwargs):
        return [
            {
                "id": f"vid_{abs(hash(query)) % 10000}",
                "video_id": f"vid_{abs(hash(query)) % 10000}",
                "title": f"Discrete Math - {query}",
                "channel_title": "freeCodeCamp.org",
                "channel_id": "UC8butISFwT-Wl7EV0hUK0BQ",
                "thumbnail_url": "https://img.youtube.com/vi/test/hqdefault.jpg",
                "duration_seconds": 1800,
                "duration_formatted": "30:00",
                "language": language,
                "published_at": "2023-01-01T00:00:00Z",
                "view_count": 500000,
                "relevance_score": 0.92,
                "relevance_explanation": "Comprehensive lecture series.",
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=test",
            }
        ], False

    with patch("app.services.youtube_client.YouTubeClientService.search_videos", side_effect=mock_search_one_channel):
        response = client.post(
            f"/api/syllabus/{s_id}/discover-resources",
            json={"preferred_language": "English", "force_refresh": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["selected_channels"]) == 1
        assert data["selected_channels"][0]["channel_title"] == "freeCodeCamp.org"
        assert data["selected_channels"][0]["is_primary"] is True
        assert data["requires_third_channel_approval"] is False
        assert data["coverage"]["coverage_percentage"] > 0


def test_two_channel_balance_policy():
    """Verify two complementary channels are selected when 1 channel covers part of syllabus."""
    s_id = create_sample_syllabus("Full Stack Web Development")

    call_count = 0

    def mock_search_two_channels(query, language, **kwargs):
        nonlocal call_count
        call_count += 1
        ch = "Traversy Media" if call_count % 2 == 1 else "Corey Schafer"
        return [
            {
                "id": f"vid_{call_count}",
                "video_id": f"vid_{call_count}",
                "title": f"Lesson - {query}",
                "channel_title": ch,
                "channel_id": "UC29ju8bIPH5as8OGnSuP50Q",
                "thumbnail_url": "https://img.youtube.com/vi/test/hqdefault.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": language,
                "published_at": "2023-01-01T00:00:00Z",
                "view_count": 300000,
                "relevance_score": 0.88,
                "relevance_explanation": f"Matched from {ch}.",
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=test",
            }
        ], False

    with patch("app.services.youtube_client.YouTubeClientService.search_videos", side_effect=mock_search_two_channels):
        response = client.post(
            f"/api/syllabus/{s_id}/discover-resources",
            json={"preferred_language": "English", "force_refresh": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["selected_channels"]) == 2
        ch_names = [c["channel_title"] for c in data["selected_channels"]]
        assert "Traversy Media" in ch_names
        assert "Corey Schafer" in ch_names
        assert data["requires_third_channel_approval"] is False


def test_third_channel_approval_flow():
    """Verify that if 2 channels leave topics uncovered, approval is required before introducing a 3rd."""
    s_id = create_sample_syllabus("Compiler Design")

    call_count = 0

    def mock_search_three_channels(query, language, **kwargs):
        nonlocal call_count
        call_count += 1
        channels = ["Channel Alpha", "Channel Beta", "Channel Gamma", "Channel Delta"]
        ch = channels[(call_count - 1) % len(channels)]

        return [
            {
                "id": f"vid_{call_count}",
                "video_id": f"vid_{call_count}",
                "title": f"Lecture - {query}",
                "channel_title": ch,
                "channel_id": "UC123",
                "thumbnail_url": "https://img.youtube.com/vi/test/hqdefault.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": language,
                "published_at": "2023-01-01T00:00:00Z",
                "view_count": 10000,
                "relevance_score": 0.85,
                "relevance_explanation": f"From {ch}.",
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=test",
            }
        ], False

    with patch("app.services.youtube_client.YouTubeClientService.search_videos", side_effect=mock_search_three_channels):
        # Initial request without third channel consent
        res = client.post(
            f"/api/syllabus/{s_id}/discover-resources",
            json={"preferred_language": "English", "allow_third_channel": False, "force_refresh": True}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["requires_third_channel_approval"] is True
        assert len(data["third_channel_candidates"]) >= 1

        # Student approves third channel via POST /api/syllabus/{id}/approve-third-channel
        appr_res = client.post(
            f"/api/syllabus/{s_id}/approve-third-channel",
            json={"approve": True}
        )
        assert appr_res.status_code == 200
        appr_data = appr_res.json()
        assert appr_data["requires_third_channel_approval"] is False
        assert len(appr_data["selected_channels"]) == 3


def test_disliked_channel_replacement_and_persistence():
    """Verify alternative channel discovery, rejection exclusion, and single-topic replacement."""
    s_id = create_sample_syllabus("Database Systems")

    # 1. Discover initial resources using dev fallback
    disc_res = client.post(f"/api/syllabus/{s_id}/discover-resources")
    assert disc_res.status_code == 200
    disc_data = disc_res.json()
    first_mapping = disc_data["topic_resources"][0]
    target_topic_id = first_mapping["topic_id"]
    initial_channel = first_mapping["resource"]["channel_title"]

    # 2. Query alternatives for this topic
    alt_res = client.get(f"/api/syllabus/{s_id}/topics/{target_topic_id}/alternatives")
    assert alt_res.status_code == 200
    alt_data = alt_res.json()
    assert alt_data["topic_id"] == target_topic_id
    assert len(alt_data["alternatives"]) >= 1

    # Ensure none of the alternatives use the current channel
    for alt in alt_data["alternatives"]:
        assert alt["video"]["channel_title"] != initial_channel

    chosen_replacement = alt_data["alternatives"][0]["video"]
    replacement_video_id = chosen_replacement["video_id"]
    replacement_channel = chosen_replacement["channel_title"]

    # 3. Replace the channel
    rep_res = client.post(
        f"/api/syllabus/{s_id}/topics/{target_topic_id}/replace-channel",
        json={
            "rejected_channel": initial_channel,
            "selected_video_id": replacement_video_id,
            "reason": "Instructor speaks too rapidly."
        }
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["topic_id"] == target_topic_id
    assert rep_data["resource"]["video_id"] == replacement_video_id
    assert initial_channel in rep_data["rejected_channels"]

    # 4. Verify rejection is persisted in SQLite
    rejected_in_db = get_topic_rejected_channels(s_id, target_topic_id)
    assert initial_channel in rejected_in_db

    # 5. Verify other topics were NOT affected
    all_res = client.get(f"/api/syllabus/{s_id}/resources")
    assert all_res.status_code == 200
    all_data = all_res.json()
    assert len(all_data["topic_resources"]) == len(disc_data["topic_resources"])
    updated_first = all_data["topic_resources"][0]
    assert updated_first["resource"]["video_id"] == replacement_video_id


def test_sqlite_persistence_and_retrieval():
    """Verify discovered resources, coverage audit, and channels persist across requests."""
    s_id = create_sample_syllabus("Artificial Intelligence")

    # Discover
    disc_res = client.post(f"/api/syllabus/{s_id}/discover-resources")
    assert disc_res.status_code == 200
    disc_data = disc_res.json()

    # Retrieve without rediscovering
    get_res = client.get(f"/api/syllabus/{s_id}/resources")
    assert get_res.status_code == 200
    get_data = get_res.json()

    assert get_data["syllabus_id"] == s_id
    assert get_data["coverage"]["total_topics"] == disc_data["coverage"]["total_topics"]
    assert len(get_data["topic_resources"]) == len(disc_data["topic_resources"])
    assert len(get_data["selected_channels"]) == len(disc_data["selected_channels"])

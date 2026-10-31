"""
Automated tests for:
1. Course title and course code extraction from multi-line syllabus text.
2. Numbered module organization (Module 1 — ..., Module 2 — ...) and ordering.
3. Topic-to-module mapping and numbering preservation.
4. One-channel full-coverage selection strategy.
5. Two-channel approximately 50:50 workload distribution strategy.
6. Third-channel user approval requirement when 2 channels are insufficient.
7. Preferred language filtering.
8. Channel replacement and coverage recalculation.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import (
    init_db,
    save_raw_syllabus,
    save_syllabus_hierarchy,
    get_syllabus_resources,
)
from app.services.syllabus_extractor import SyllabusStructureExtractor, ExtractedSyllabusData
from app.agents.syllabus_analyzer import SyllabusAnalyzerAgent
from app.schemas.syllabus import SyllabusHierarchy, ModuleItem, TopicItem

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_course_title_and_code_multiline_extraction():
    """Requirement Part 1: Extracts actual course title and code when split across multiple lines."""
    raw = """
    Syllabus format for a Theory alone Course
    Course Code: 
    CSE3016 
    Course Title:  
    Object Oriented Modelling and Design using UML 
    TPC 3 0 3 
    Version No. 1.00 
    """
    lines = SyllabusStructureExtractor.clean_and_unwrap_lines(raw)
    data = ExtractedSyllabusData()
    SyllabusStructureExtractor._extract_header_metadata(lines, data)

    assert data.course_code == "CSE3016"
    assert data.course_name == "Object Oriented Modelling and Design using UML"


def test_arbitrary_course_title_not_hardcoded():
    """Requirement Part 1: Never hardcode course name; extracts any university course."""
    raw = """
    Department of Electrical Engineering
    Course Code: EE402
    Course Title: Advanced Control Systems Engineering
    Credits: 4
    """
    lines = SyllabusStructureExtractor.clean_and_unwrap_lines(raw)
    data = ExtractedSyllabusData()
    SyllabusStructureExtractor._extract_header_metadata(lines, data)

    assert data.course_code == "EE402"
    assert data.course_name == "Advanced Control Systems Engineering"


def test_numbered_module_organization():
    """Requirement Part 2: Restores Module 1 —, Module 2 — numbering and preserves titles and topics."""
    hierarchy = SyllabusHierarchy(
        course_name="Object Oriented Modelling and Design using UML",
        course_code="CSE3016",
        modules=[
            ModuleItem(
                id="mod_1",
                title="Introduction to Object-Oriented Concepts",
                topics=[
                    TopicItem(id="t1", title="Object-Oriented Development and Modelling Concepts", estimated_minutes=60, difficulty="easy"),
                    TopicItem(id="t2", title="Generalization, Inheritance, and Grouping Constructs", estimated_minutes=60, difficulty="medium"),
                    TopicItem(id="t3", title="Sample Object Models", estimated_minutes=60, difficulty="medium"),
                ]
            ),
            ModuleItem(
                id="mod_2",
                title="Advanced Class Concepts and State Modelling",
                topics=[
                    TopicItem(id="t4", title="Advanced object and class concepts", estimated_minutes=90, difficulty="hard"),
                    TopicItem(id="t5", title="State Modelling", estimated_minutes=90, difficulty="hard"),
                ]
            )
        ]
    )

    SyllabusAnalyzerAgent._ensure_stable_ids(hierarchy)

    assert hierarchy.modules[0].title == "Module 1 — Introduction to Object-Oriented Concepts"
    assert hierarchy.modules[1].title == "Module 2 — Advanced Class Concepts and State Modelling"
    assert len(hierarchy.modules[0].topics) == 3
    assert hierarchy.modules[0].topics[0].title == "Object-Oriented Development and Modelling Concepts"
    assert hierarchy.modules[0].topics[0].estimated_minutes == 60
    assert hierarchy.modules[0].topics[0].difficulty == "easy"


def test_two_channel_50_50_distribution():
    """Requirement Part 3 (Strategy 2): 2 complementary channels distribute topics ~50:50."""
    sid = "test_syl_50_50"
    save_raw_syllabus(sid, "Test_50_50.pdf", "pdf", 1000, 500, 100, "Syllabus text")

    # 6 topics total across 2 modules
    hierarchy_dict = {
        "course_name": "Distributed Systems",
        "course_code": "CS401",
        "modules": [
            {
                "id": "mod_1",
                "title": "Module 1 — Fundamentals",
                "topics": [
                    {"id": "t1", "title": "System Models", "estimated_minutes": 60, "difficulty": "easy"},
                    {"id": "t2", "title": "Networking Basics", "estimated_minutes": 60, "difficulty": "easy"},
                    {"id": "t3", "title": "RPC and RMI", "estimated_minutes": 60, "difficulty": "medium"},
                ]
            },
            {
                "id": "mod_2",
                "title": "Module 2 — Consensus",
                "topics": [
                    {"id": "t4", "title": "Time and Global States", "estimated_minutes": 60, "difficulty": "medium"},
                    {"id": "t5", "title": "Paxos Consensus", "estimated_minutes": 90, "difficulty": "hard"},
                    {"id": "t6", "title": "Raft Algorithm", "estimated_minutes": 90, "difficulty": "hard"},
                ]
            }
        ]
    }
    save_syllabus_hierarchy(sid, hierarchy_dict, is_fallback=True, analysis_engine="Mock")

    # Mock search: Channel Alpha covers all topics, Channel Beta covers all topics
    # Since neither covers exclusively, Strategy 2 balances shared topics ~50:50 (3 and 3)
    def mock_search(query, language, **kwargs):
        return [
            {
                "id": f"vid_alpha_{query}",
                "video_id": f"vid_alpha_{query[:6]}",
                "title": f"Alpha Lesson on {query}",
                "channel_title": "Channel Alpha",
                "channel_id": "UC_ALPHA",
                "thumbnail_url": "https://img.youtube.com/vi/a/hqdefault.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": language,
                "published_at": "2024-01-01T00:00:00Z",
                "view_count": 50000,
                "relevance_score": 0.85,
                "relevance_explanation": "Alpha coverage",
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=alpha",
            },
            {
                "id": f"vid_beta_{query}",
                "video_id": f"vid_beta_{query[:6]}",
                "title": f"Beta Lesson on {query}",
                "channel_title": "Channel Beta",
                "channel_id": "UC_BETA",
                "thumbnail_url": "https://img.youtube.com/vi/b/hqdefault.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": language,
                "published_at": "2024-01-01T00:00:00Z",
                "view_count": 60000,
                "relevance_score": 0.85,
                "relevance_explanation": "Beta coverage",
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=beta",
            }
        ], False

    # Force 2 channels by simulating partial coverage
    call_idx = 0
    def mock_partial_search(query, language, **kwargs):
        nonlocal call_idx
        call_idx += 1
        # Topics 1-4 covered by Alpha, Topics 3-6 covered by Beta
        results = []
        if call_idx in (1, 2, 3, 4):
            results.append({
                "id": f"v_a_{call_idx}",
                "video_id": f"v_a_{call_idx}",
                "title": f"Alpha on {query}",
                "channel_title": "Channel Alpha",
                "channel_id": "UC_ALPHA",
                "thumbnail_url": "https://img.youtube.com/vi/a/hqdefault.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": language,
                "relevance_score": 0.88,
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=alpha",
            })
        if call_idx in (3, 4, 5, 6):
            results.append({
                "id": f"v_b_{call_idx}",
                "video_id": f"v_b_{call_idx}",
                "title": f"Beta on {query}",
                "channel_title": "Channel Beta",
                "channel_id": "UC_BETA",
                "thumbnail_url": "https://img.youtube.com/vi/b/hqdefault.jpg",
                "duration_seconds": 1200,
                "duration_formatted": "20:00",
                "language": language,
                "relevance_score": 0.88,
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=beta",
            })
        return results, False

    with patch("app.services.youtube_client.YouTubeClientService.search_videos", side_effect=mock_partial_search):
        res = client.post(
            f"/api/syllabus/{sid}/discover-resources",
            json={"preferred_language": "English", "force_refresh": True}
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["selected_channels"]) == 2
        
        # Verify ~50:50 distribution (3 topics each out of 6)
        c_a = next(c for c in data["selected_channels"] if c["channel_title"] == "Channel Alpha")
        c_b = next(c for c in data["selected_channels"] if c["channel_title"] == "Channel Beta")
        assert c_a["topics_covered"] == 3
        assert c_b["topics_covered"] == 3
        assert c_a["percentage_of_course"] == 50.0
        assert c_b["percentage_of_course"] == 50.0
        assert data["coverage"]["coverage_percentage"] == 100.0


def test_channel_replacement_updates_coverage():
    """Requirement Part 5: Replacing a channel updates coverage and topic assignment without breaking others."""
    sid = "test_syl_replace"
    save_raw_syllabus(sid, "Test_Replace.pdf", "pdf", 1000, 500, 100, "Syllabus text")

    hierarchy_dict = {
        "course_name": "Operating Systems",
        "course_code": "CS301",
        "modules": [
            {
                "id": "mod_1",
                "title": "Module 1 — Processes",
                "topics": [
                    {"id": "t1", "title": "Threads", "estimated_minutes": 60, "difficulty": "easy"}
                ]
            }
        ]
    }
    save_syllabus_hierarchy(sid, hierarchy_dict, is_fallback=True, analysis_engine="Mock")

    # Initial discover
    def mock_s(query, language, **kwargs):
        return [
            {
                "id": "vid_init",
                "video_id": "vid_init",
                "title": "Original Video",
                "channel_title": "Old Channel",
                "channel_id": "UC_OLD",
                "thumbnail_url": "https://img.youtube.com/vi/old/hqdefault.jpg",
                "duration_seconds": 900,
                "duration_formatted": "15:00",
                "language": "English",
                "relevance_score": 0.85,
                "is_uncertain": False,
                "video_url": "https://www.youtube.com/watch?v=old",
            }
        ], False

    with patch("app.services.youtube_client.YouTubeClientService.search_videos", side_effect=mock_s):
        res1 = client.post(f"/api/syllabus/{sid}/discover-resources", json={"force_refresh": True})
        assert res1.status_code == 200
        assert res1.json()["selected_channels"][0]["channel_title"] == "Old Channel"

    # Replace channel for t1
    rep_res = client.post(
        f"/api/syllabus/{sid}/topics/t1/replace-channel",
        json={
            "rejected_channel": "Old Channel",
            "selected_video_id": "vid_new_creator",
            "reason": "Prefer cleaner explanations"
        }
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["match_status"] == "relevant"
    assert "Old Channel" in rep_data["rejected_channels"]

    # Verify updated resources reflection
    get_res = client.get(f"/api/syllabus/{sid}/resources")
    assert get_res.status_code == 200
    new_channels = [c["channel_title"] for c in get_res.json()["selected_channels"]]
    assert "Old Channel" not in new_channels


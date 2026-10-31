"""
Phase 5 Comprehensive Automated Tests
======================================
Tests:
- Syllabus metadata (codes, credits, objectives, outcomes, textbooks) does NOT become topics
- Un-wrapping broken lines and structured module extraction
- Validation engine detects suspicious counts, fragments, duplicates, metadata leakage
- Prerequisite topological ordering in study plans
- Provenance tracking (live vs cache vs fallback) and honest coverage calculation
- Safe diagnostics endpoint and secret redaction
"""

import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.syllabus_extractor import SyllabusStructureExtractor
from app.services.syllabus_validator import SyllabusValidatorService
from app.models.database import init_db

client = TestClient(app)


def setup_module():
    init_db()


def test_os_syllabus_metadata_not_topics():
    """Verify that an Operating Systems university syllabus does NOT get turned into 205 topics and 200+ hours."""
    raw_syllabus = """
    DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING
    CS 305: OPERATING SYSTEMS (Regulation 2021)
    Credits: 3 0 0 3                                                Semester: V

    COURSE OBJECTIVES:
    • To understand the basic concepts and functions of operating systems.
    • To understand Processes and Threads.
    • To analyze Scheduling algorithms.
    • To understand the concept of Deadlocks.
    • To analyze various memory management schemes.
    • To be familiar with I/O management and File systems.

    COURSE OUTCOMES:
    CO1: Understand the structure and functions of OS
    CO2: Implement process scheduling and synchronization algorithms
    CO3: Analyze deadlocks and develop deadlock handling mechanisms
    CO4: Compare and contrast memory allocation techniques
    CO5: Explain file system concepts and disk scheduling algorithms

    UNIT I: OPERATING SYSTEM OVERVIEW & PROCESS MANAGEMENT            (9 Hours)
    Operating System Structure – Operating System Operations – Process Concept: Process state, Process Control Block, Process scheduling, Operations on processes – Inter-process Communication; CPU Scheduling: Basic concepts, Scheduling criteria, Scheduling algorithms; Multiple-processor scheduling.

    UNIT II: PROCESS SYNCHRONIZATION & DEADLOCKS                      (9 Hours)
    Process Synchronization: Critical-Section Problem, Peterson’s Solution, Synchronization Hardware, Semaphores, Classic Problems of Synchronization, Monitors. Deadlocks: System Model, Deadlock Characterization, Methods for Handling Deadlocks, Deadlock Prevention, Deadlock Avoidance, Deadlock Detection, Recovery from Deadlock.

    UNIT III: STORAGE MANAGEMENT                                      (9 Hours)
    Main Memory: Contiguous Memory Allocation, Paging, Structure of the Page Table, Segmentation. Virtual Memory: Demand Paging, Copy-on-Write, Page Replacement, Allocation of Frames, Thrashing, Memory-Mapped Files.

    UNIT IV: FILE SYSTEM & I/O SYSTEMS                                (9 Hours)
    Mass-Storage Structure: Overview, Disk Structure, Disk Attachment, Disk Scheduling, Swap-Space Management. File System Interface: File Concept, Access Methods, Directory Structure, File System Mounting. File System Implementation: File-System Structure, Allocation Methods, Free-Space Management.

    UNIT V: CASE STUDIES                                              (9 Hours)
    The Linux System: Design Principles, Kernel Modules, Process Management, Scheduling, Memory Management, File Systems, Interprocess Communication. Windows 10: Design Principles, System Components, File System.
    TOTAL: 45 Hours

    TEXT BOOKS:
    1. Abraham Silberschatz, Peter Baer Galvin and Greg Gagne, "Operating System Concepts", 10th Edition, John Wiley and Sons Inc., 2018.
    2. William Stallings, "Operating Systems: Internals and Design Principles", 9th Edition, Pearson Education, 2018.

    REFERENCES:
    1. Andrew S. Tanenbaum, "Modern Operating Systems", 4th Edition, Pearson, 2015.
    2. D. M. Dhamdhere, "Operating Systems - A Concept-Based Approach", 3rd Edition, McGraw Hill Education, 2017.
    """

    data = SyllabusStructureExtractor.extract_structure(raw_syllabus)

    # 1. Identity
    assert "OPERATING SYSTEMS" in data.course_name.upper()
    assert data.course_code == "CS 305"
    assert data.credits is not None and "3" in data.credits

    # 2. Separated metadata counts
    assert len(data.objectives) >= 5, "Objectives were not separated"
    assert len(data.outcomes) >= 5, "Outcomes were not separated"
    assert len(data.textbooks) >= 2, "Textbooks were not separated"

    # 3. Clean module structure
    assert len(data.modules) == 5, f"Expected 5 units, found {len(data.modules)}"

    all_topics = [t for m in data.modules for t in m["topics"]]
    total_topic_count = len(all_topics)
    total_minutes = sum(t["estimated_minutes"] for t in all_topics)

    # Must NOT be 205 topics or 200+ hours!
    assert total_topic_count <= 25, f"Topic count {total_topic_count} is too high (expected <= 25 discrete concepts)"
    assert total_minutes <= 1800, f"Total minutes {total_minutes} exceeds reasonable course duration"

    # 4. Ensure no metadata leaked into topics
    for t in all_topics:
        title = t["title"].lower()
        assert "regulation 2021" not in title
        assert "credits" not in title
        assert "course objectives" not in title
        assert "course outcomes" not in title
        assert "silberschatz" not in title
        assert "pearson" not in title
        assert "total: 45 hours" not in title
        assert "co1" not in title
        assert not title.endswith(("and", "or", "to", "for", "in", "by"))


def test_validation_engine_detects_all_defect_types():
    """Verify that SyllabusValidatorService flags empty modules, metadata leakage, fragments, and duplicates."""
    malformed_hierarchy = {
        "course_name": "Test Course",
        "modules": [
            {
                "id": "mod_1",
                "title": "Module 1: Foundations",
                "topics": [
                    {
                        "id": "top_1_1",
                        "title": "Valid Initial Concept",
                        "estimated_minutes": 45,
                        "difficulty": "medium",
                    },
                    {
                        "id": "top_1_2",
                        "title": "Credits: 3-0-0-3 Semester V",  # Metadata leakage
                        "estimated_minutes": 45,
                        "difficulty": "medium",
                    },
                    {
                        "id": "top_1_3",
                        "title": "Introduction to the concept of and",  # Sentence fragment
                        "estimated_minutes": 5,  # Unreasonable duration (< 10m)
                        "difficulty": "easy",
                    },
                    {
                        "id": "top_1_4",
                        "title": "Valid Initial Concept",  # Duplicate topic
                        "estimated_minutes": 45,
                        "difficulty": "medium",
                    },
                ]
            },
            {
                "id": "mod_2",
                "title": "Module 2: Advanced Topics",
                "topics": []  # Empty module
            }
        ]
    }

    report = SyllabusValidatorService.validate_hierarchy(malformed_hierarchy)

    assert report.is_valid is True
    assert report.needs_confirmation is True, "Malformed structure must require explicit student confirmation"
    assert report.quality_score < 75, f"Quality score {report.quality_score} should be < 75"

    codes = [w.code for w in report.warnings]
    assert "METADATA_LEAKAGE" in codes, "Did not detect metadata leakage"
    assert "SENTENCE_FRAGMENT" in codes, "Did not detect sentence fragment"
    assert "DUPLICATE_TOPIC" in codes, "Did not detect duplicate topic"
    assert "EMPTY_MODULE" in codes, "Did not detect empty module"
    assert "UNREASONABLE_DURATION" in codes, "Did not detect unreasonable duration"

    # Verify actionable suggested actions
    actions = [w.suggested_action for w in report.warnings]
    assert "remove" in actions
    assert "merge" in actions
    assert "add_topic" in actions


def test_prerequisite_topological_ordering_in_study_plan():
    """Verify that topics with explicit prerequisites are scheduled strictly after their prerequisites."""
    # 1. Upload & save a custom hierarchy with prerequisites
    # Topic 1: Foundations (Prereq: None)
    # Topic 2: Advanced Trees (Prereq: Topic 1)
    # Topic 3: Balanced AVL Trees (Prereq: Topic 2)
    # Even if they are listed in reverse order, topological sort must schedule Topic 1 -> 2 -> 3!
    hierarchy_payload = {
        "course_name": "Data Structures",
        "modules": [
            {
                "id": "mod_1",
                "title": "Module 1: Trees",
                "order_index": 0,
                "topics": [
                    {
                        "id": "top_c",
                        "title": "Balanced AVL Trees",
                        "explanation": "Self-balancing binary search trees.",
                        "estimated_minutes": 60,
                        "difficulty": "hard",
                        "prerequisites": ["top_b"],  # Depends on top_b
                        "subtopics": [],
                        "order_index": 0,
                    },
                    {
                        "id": "top_b",
                        "title": "Binary Search Trees",
                        "explanation": "BST insertion and deletion.",
                        "estimated_minutes": 45,
                        "difficulty": "medium",
                        "prerequisites": ["top_a"],  # Depends on top_a
                        "subtopics": [],
                        "order_index": 1,
                    },
                    {
                        "id": "top_a",
                        "title": "Tree Fundamentals",
                        "explanation": "Nodes, edges, and tree traversals.",
                        "estimated_minutes": 30,
                        "difficulty": "easy",
                        "prerequisites": [],
                        "subtopics": [],
                        "order_index": 2,
                    },
                ]
            }
        ]
    }

    # Upload a blank document to get an ID
    res = client.post(
        "/api/syllabus/upload",
        files={"file": ("trees.pdf", b"%PDF-1.4 sample content with enough text length for parsing digital syllabus", "application/pdf")}
    )
    # If 400 because not a full PDF, create docx
    if res.status_code != 200:
        import io, docx
        doc = docx.Document()
        doc.add_heading("Trees Course", 0)
        doc.add_paragraph("Tree traversals, binary search trees, and AVL trees.")
        buf = io.BytesIO()
        doc.save(buf)
        res = client.post(
            "/api/syllabus/upload",
            files={"file": ("trees.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )

    s_id = res.json()["syllabus_id"]

    # Save edited topics
    update_res = client.put(f"/api/syllabus/{s_id}/topics", json=hierarchy_payload)
    assert update_res.status_code == 200

    # Generate study plan
    from datetime import date, timedelta
    exam = (date.today() + timedelta(days=20)).isoformat()
    plan_res = client.post(f"/api/study-plan/{s_id}", json={
        "exam_date": exam,
        "daily_target_minutes": 60,
        "preferred_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    })
    assert plan_res.status_code == 200
    plan = plan_res.json()

    all_tasks = [t for g in plan["daily_schedules"] for t in g["tasks"]]

    # Find the first task date & order for each topic
    top_a_order = next(i for i, t in enumerate(all_tasks) if "top_a" in t["topic_id"])
    top_b_order = next(i for i, t in enumerate(all_tasks) if "top_b" in t["topic_id"])
    top_c_order = next(i for i, t in enumerate(all_tasks) if "top_c" in t["topic_id"])

    # Assert strict prerequisite ordering: Tree Fundamentals < Binary Search Trees < Balanced AVL Trees
    assert top_a_order < top_b_order, f"top_a (Fundamentals) was scheduled at {top_a_order}, after top_b at {top_b_order}"
    assert top_b_order < top_c_order, f"top_b (BST) was scheduled at {top_b_order}, after top_c at {top_c_order}"


def test_diagnostics_safe_zero_secret_leakage():
    """Verify that GET /api/diagnostics returns sanitized operational data without disclosing secrets."""
    res = client.get("/api/diagnostics")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert "backend" in data
    assert "database" in data
    assert "strands" in data
    assert "youtube" in data

    # Verify database tables
    assert data["database"]["status"] == "connected"
    assert data["database"]["tables_count"] >= 5

    # Verify zero secrets in JSON serialization
    json_str = json.dumps(data)
    assert "AIzaSy" not in json_str, "YouTube API key leaked in diagnostics response!"
    assert "AWS_SECRET_ACCESS_KEY" not in json_str
    assert "aws_secret" not in json_str.lower()
    assert "bearer" not in json_str.lower()

    # YouTube status check
    yt = data["youtube"]
    assert "key_configured" in yt
    assert "key_summary" in yt
    assert yt["key_summary"].startswith("Configured") or yt["key_summary"].startswith("Not Set")


def test_diagnostics_test_youtube_mocked():
    """Verify POST /api/diagnostics/test-youtube safely executes without throwing unhandled exceptions."""
    # Test mocked 200 OK
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"id": {"videoId": "test_123"}}]}

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        res = client.post("/api/diagnostics/test-youtube")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "youtube"
        assert data["tested"] is True
        assert data["status"] == "success"
        assert "latency_ms" in data
        assert "YouTube Data API v3 connection successful" in data["message"]

    # Test mocked 403 quota exceeded
    mock_quota_resp = MagicMock()
    mock_quota_resp.status_code = 403
    mock_quota_resp.json.return_value = {
        "error": {"errors": [{"reason": "quotaExceeded"}]}
    }

    with patch("httpx.AsyncClient.get", return_value=mock_quota_resp):
        res = client.post("/api/diagnostics/test-youtube")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "quota_exceeded"
        assert "quota exceeded" in data["message"].lower()


def test_youtube_provenance_explicit_labeling():
    """Verify that resource mappings carry explicit provenance ('live', 'cache', or 'fallback')."""
    from app.schemas.resource import VideoResource, TopicResourceMapping

    video_live = VideoResource(
        id="vid_1",
        video_id="vid_1",
        title="Live YouTube Video",
        channel_title="freeCodeCamp.org",
        thumbnail_url="https://img.youtube.com/vi/vid_1/hqdefault.jpg",
        duration_seconds=1200,
        duration_formatted="20:00",
        video_url="https://www.youtube.com/watch?v=vid_1",
        provenance="live",
    )
    assert video_live.provenance == "live"

    video_fb = VideoResource(
        id="vid_2",
        video_id="vid_2",
        title="Fallback Video",
        channel_title="Local Educator",
        thumbnail_url="https://img.youtube.com/vi/vid_2/hqdefault.jpg",
        duration_seconds=900,
        duration_formatted="15:00",
        video_url="https://www.youtube.com/watch?v=vid_2",
        provenance="fallback",
    )
    assert video_fb.provenance == "fallback"

    mapping = TopicResourceMapping(
        topic_id="top_1",
        topic_title="Operating Systems",
        module_id="mod_1",
        module_title="Module 1",
        resource=video_live,
        provenance="live",
        match_status="relevant",
        match_confidence="high",
    )
    assert mapping.provenance == "live"
    assert mapping.resource.provenance == "live"


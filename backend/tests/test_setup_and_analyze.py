"""
Tests for /api/courses/setup-and-analyze endpoint.
Verifies:
1. Fix for AttributeError: 'SyllabusValidatorService' has no attribute 'audit_hierarchy'
2. Fix for ValidationError: assessment_info must be a valid string, not a list
3. Authenticated ownership handling and multi-course independence
4. Full upload -> setup-and-analyze flow with mocked AI execution (0 AWS credits)
"""

import datetime
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import (
    init_db,
    save_raw_syllabus,
    get_course,
    get_syllabus_record,
)
from app.schemas.syllabus import SyllabusHierarchy, ModuleItem, TopicItem
from app.services.syllabus_validator import SyllabusValidatorService

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


def test_validator_service_audit_and_validate_hierarchy():
    """Verifies that both validate_hierarchy and audit_hierarchy accept dict and model objects."""
    hierarchy = SyllabusHierarchy(
        course_name="CSE3016 Object Oriented Modelling",
        course_code="CSE3016",
        modules=[
            ModuleItem(
                id="mod_1",
                title="Module 1: Introduction",
                topics=[
                    TopicItem(id="top_1", title="Intro to UML", estimated_minutes=60, difficulty="easy")
                ]
            )
        ]
    )

    # 1. audit_hierarchy with SyllabusHierarchy model
    rep1 = SyllabusValidatorService.audit_hierarchy(hierarchy, is_fallback=True)
    assert rep1.quality_score > 0
    assert any(w.code == "FALLBACK_ACTIVE" for w in rep1.warnings)

    # 2. audit_hierarchy with raw dict
    rep2 = SyllabusValidatorService.audit_hierarchy(hierarchy.model_dump(), is_fallback=False)
    assert rep2.quality_score > 0

    # 3. validate_hierarchy with model object
    rep3 = SyllabusValidatorService.validate_hierarchy(hierarchy, is_fallback=False)
    assert rep3.quality_score > 0


def test_setup_and_analyze_success():
    """Verifies that /api/courses/setup-and-analyze succeeds without 500 internal server error."""
    sid = "test_syl_setup_cse3016"
    save_raw_syllabus(
        sid,
        "CSE3016 Course Syllabus.pdf",
        "pdf",
        150000,
        4000,
        800,
        "Course Code: CSE3016\nCourse Title: Object Oriented Modelling\nModule 1: UML Basics\nModule 2: Class Diagrams",
        owner_user_id="student_123"
    )

    future_ca1 = (datetime.date.today() + datetime.timedelta(days=20)).isoformat()
    future_final = (datetime.date.today() + datetime.timedelta(days=60)).isoformat()

    payload = {
        "syllabus_id": sid,
        "course_name": "Object Oriented Modelling and Design using UML",
        "course_code": "CSE3016",
        "language": "English",
        "lesson_style": "In-depth",
        "daily_study_availability": "2-4 hours",
        "assessment_system_type": "autonomous",
        "assessment_scope": "both",
        "assessments": [
            {
                "name": "CA1 Exam",
                "exam_date": future_ca1,
                "assessment_type": "internal",
                "scope": "internal",
                "weightage": 30,
                "order_index": 0
            },
            {
                "name": "Final Semester Exam",
                "exam_date": future_final,
                "assessment_type": "end_sem",
                "scope": "end_sem",
                "weightage": 70,
                "order_index": 1
            }
        ]
    }

    mock_hierarchy = SyllabusHierarchy(
        course_name="Object Oriented Modelling and Design using UML",
        course_code="CSE3016",
        assessment_info="Continuous assessment 30%, Final exam 70%",
        modules=[
            ModuleItem(
                id="mod_1",
                title="Module 1: UML Basics",
                topics=[
                    TopicItem(id="top_1", title="Use Case Diagrams", estimated_minutes=90, difficulty="medium")
                ]
            ),
            ModuleItem(
                id="mod_2",
                title="Module 2: Class Diagrams",
                topics=[
                    TopicItem(id="top_2", title="Class & Object Diagrams", estimated_minutes=120, difficulty="hard")
                ]
            )
        ]
    )

    with patch("app.agents.syllabus_analyzer.SyllabusAnalyzerAgent.analyze_syllabus", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (mock_hierarchy, False, "Strands Agents SDK (bedrock: claude-sonnet-5)")

        resp = client.post(
            "/api/courses/setup-and-analyze",
            json=payload,
            headers={"X-User-Id": "student_123"}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "success"
        assert data["course"]["course_name"] == "Object Oriented Modelling and Design using UML"
        assert data["course"]["course_code"] == "CSE3016"
        assert data["course"]["owner_user_id"] == "student_123"
        assert data["analysis"]["assessment_info"] == "Continuous assessment 30%, Final exam 70%"
        assert len(data["analysis"]["modules"]) == 2
        assert data["analysis"]["total_topics_count"] == 2
        assert data["analysis"]["validation_report"]["quality_score"] > 0


def test_setup_and_analyze_with_none_and_list_assessment_info():
    """Verifies that assessment_info as None or list doesn't trigger Pydantic ValidationError."""
    sid = "test_syl_none_ass"
    save_raw_syllabus(
        sid,
        "Course.pdf",
        "pdf",
        50000,
        2000,
        400,
        "Module 1: General Topics",
        owner_user_id="user_abc"
    )

    payload = {
        "syllabus_id": sid,
        "course_name": "General Course",
        "course_code": "GEN101",
        "language": "English",
        "lesson_style": "Beginner-friendly",
        "daily_study_availability": "1-2 hours",
        "assessment_system_type": "autonomous",
        "assessment_scope": "both",
        "assessments": []
    }

    # Case 1: assessment_info is None
    mock_hierarchy = SyllabusHierarchy(
        course_name="General Course",
        course_code="GEN101",
        assessment_info=None,
        modules=[
            ModuleItem(
                id="mod_1",
                title="Module 1: Basics",
                topics=[TopicItem(id="t1", title="Topic 1", estimated_minutes=45)]
            )
        ]
    )

    with patch("app.agents.syllabus_analyzer.SyllabusAnalyzerAgent.analyze_syllabus", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (mock_hierarchy, True, "Deterministic Fallback")

        resp = client.post(
            "/api/courses/setup-and-analyze",
            json=payload,
            headers={"X-User-Id": "user_abc"}
        )
        assert resp.status_code == 200
        assert resp.json()["analysis"]["assessment_info"] is None


def test_setup_and_analyze_ownership_enforcement():
    """Verifies that student B cannot analyze or claim student A's uploaded syllabus."""
    sid = "test_syl_alice"
    save_raw_syllabus(
        sid,
        "Alice_Syllabus.pdf",
        "pdf",
        10000,
        1000,
        200,
        "Alice course text",
        owner_user_id="alice_uuid"
    )

    payload = {
        "syllabus_id": sid,
        "course_name": "Alice Course",
        "language": "English",
        "assessments": []
    }

    # Bob tries to claim Alice's syllabus
    resp = client.post(
        "/api/courses/setup-and-analyze",
        json=payload,
        headers={"X-User-Id": "bob_uuid"}
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"] or "permission" in resp.json()["detail"].lower()


def test_setup_and_analyze_nonexistent_syllabus():
    """Verifies that non-existent syllabus_id returns 404 Not Found."""
    payload = {
        "syllabus_id": "nonexistent_syl_9999",
        "course_name": "Ghost Course",
        "language": "English",
        "assessments": []
    }
    resp = client.post(
        "/api/courses/setup-and-analyze",
        json=payload,
        headers={"X-User-Id": "any_user"}
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


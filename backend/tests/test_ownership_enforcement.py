"""
Multi-user tenant isolation and ownership security enforcement tests.
Validates that User A and User B cannot access, mutate, or hijack each other's
courses, syllabi, study plans, study tasks, assessments, or resources.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import (
    get_db_connection,
    create_course,
    get_course,
    get_courses,
    update_course,
    archive_course,
    delete_course,
    save_raw_syllabus,
    get_syllabus_record,
    get_syllabus_hierarchy,
    save_study_plan,
    save_study_tasks,
    get_study_plan_by_id,
    get_plan_tasks,
    update_task_completion,
    update_task_note,
    reschedule_plan_tasks,
    save_course_assessments,
    get_course_assessments,
    replace_course_syllabus,
    get_task_owner_id,
    get_syllabus_resources,
)
from app.core.auth import verify_ownership
from fastapi import HTTPException

client = TestClient(app)

USER_A = "usr_alice_101"
USER_B = "usr_bob_202"


@pytest.fixture(autouse=True)
def clean_test_entities():
    """Ensures test records are removed after each test run."""
    yield
    # Cleanup courses created during test
    for uid in [USER_A, USER_B]:
        courses = get_courses(owner_user_id=uid, include_archived=True)
        for c in courses:
            delete_course(c["id"], owner_user_id=uid)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM syllabi WHERE owner_user_id IN (?, ?)", (USER_A, USER_B))
        conn.commit()


class TestMultiTenantCourseIsolation:
    """Verifies that courses owned by User A are inaccessible and immutable to User B."""

    def test_user_b_cannot_view_user_a_course(self):
        c_a = create_course({
            "course_name": "Distributed Systems",
            "course_code": "CS401",
        }, owner_user_id=USER_A)

        # User A can access
        assert get_course(c_a["id"], owner_user_id=USER_A) is not None

        # User B cannot access User A's course
        assert get_course(c_a["id"], owner_user_id=USER_B) is None

    def test_user_b_cannot_list_user_a_courses(self):
        c_a = create_course({"course_name": "Alice Private Course"}, owner_user_id=USER_A)
        c_b = create_course({"course_name": "Bob Private Course"}, owner_user_id=USER_B)

        alice_courses = get_courses(owner_user_id=USER_A)
        bob_courses = get_courses(owner_user_id=USER_B)

        alice_ids = [c["id"] for c in alice_courses]
        bob_ids = [c["id"] for c in bob_courses]

        assert c_a["id"] in alice_ids
        assert c_b["id"] not in alice_ids
        assert c_b["id"] in bob_ids
        assert c_a["id"] not in bob_ids

    def test_user_b_cannot_update_user_a_course(self):
        c_a = create_course({"course_name": "Original Name"}, owner_user_id=USER_A)

        # User B attempts to change course name
        update_course(c_a["id"], {"course_name": "Hacked Name"}, owner_user_id=USER_B)

        # Name must remain unchanged
        refetched = get_course(c_a["id"], owner_user_id=USER_A)
        assert refetched["course_name"] == "Original Name"

    def test_user_b_cannot_archive_or_delete_user_a_course(self):
        c_a = create_course({"course_name": "Security Target"}, owner_user_id=USER_A)

        # User B attempts to archive
        success_arch = archive_course(c_a["id"], is_archived=True, owner_user_id=USER_B)
        assert success_arch is False

        # Course remains active for User A
        refetched = get_course(c_a["id"], owner_user_id=USER_A)
        assert refetched["is_archived"] is False

        # User B attempts to delete
        success_del = delete_course(c_a["id"], owner_user_id=USER_B)
        assert success_del is False

        # Course still exists for User A
        assert get_course(c_a["id"], owner_user_id=USER_A) is not None


class TestSyllabusAndHierarchyIsolation:
    """Verifies that syllabus documents and analysis hierarchies cannot be read across tenants."""

    def test_user_b_cannot_read_user_a_syllabus_record(self):
        s_id = "syl_alice_secret_doc"
        save_raw_syllabus(
            syllabus_id=s_id,
            filename="alice_confidential.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            char_count=500,
            word_count=100,
            raw_text="Confidential syllabus content",
            owner_user_id=USER_A,
        )

        # User A can read
        rec_a = get_syllabus_record(s_id, owner_user_id=USER_A)
        assert rec_a is not None
        assert rec_a["filename"] == "alice_confidential.pdf"

        # User B cannot read
        rec_b = get_syllabus_record(s_id, owner_user_id=USER_B)
        assert rec_b is None

    def test_user_b_cannot_read_user_a_syllabus_resources(self):
        s_id = "syl_alice_resources"
        save_raw_syllabus(
            syllabus_id=s_id,
            filename="resources.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            char_count=100,
            word_count=20,
            raw_text="Topics text",
            owner_user_id=USER_A,
        )

        res_b = get_syllabus_resources(s_id, owner_user_id=USER_B)
        assert res_b is None


class TestStudyPlanAndTaskIsolation:
    """Verifies that daily tasks, completion toggles, and study plans are protected."""

    def test_user_b_cannot_view_or_modify_user_a_study_plan(self):
        plan_id = "plan_alice_101"
        syl_id = "syl_alice_101"
        save_study_plan({
            "id": plan_id,
            "syllabus_id": syl_id,
            "title": "Alice Study Timetable",
            "exam_date": "2026-06-01",
            "daily_target_minutes": 90,
        }, owner_user_id=USER_A)

        task_id = "task_alice_01"
        save_study_tasks(plan_id, [{
            "id": task_id,
            "syllabus_id": syl_id,
            "module_id": "mod_1",
            "topic_id": "top_1",
            "scheduled_date": "2026-05-20",
            "title": "Study Cryptography",
            "task_type": "video",
            "duration_minutes": 45,
            "status": "pending",
        }])

        # Verify task owner lookup
        assert get_task_owner_id(task_id) == USER_A

        # User B cannot read plan or tasks
        assert get_study_plan_by_id(plan_id, owner_user_id=USER_B) is None
        assert get_plan_tasks(plan_id, owner_user_id=USER_B) == []

        # User B attempts to mark Alice's task complete
        t_res = update_task_completion(task_id, completed=True, owner_user_id=USER_B)
        assert t_res is None

        # User B attempts to modify Alice's task note
        n_res = update_task_note(task_id, notes="Malicious note", owner_user_id=USER_B)
        assert n_res is None

        # User A verifies task remains untouched
        tasks = get_plan_tasks(plan_id, owner_user_id=USER_A)
        assert len(tasks) == 1
        assert tasks[0]["status"] == "pending"
        assert tasks[0]["notes"] is None


class TestRelationalAndSpoofingProtection:
    """Verifies prevention of ownership spoofing and cross-tenant parent-child hijacking."""

    def test_verify_ownership_raises_403_or_404_for_other_user(self):
        # Access denied without leaking or permitting modification
        with pytest.raises(HTTPException) as exc_info:
            verify_ownership(resource_owner_id=USER_A, current_user_id=USER_B, resource_type="course")
        assert exc_info.value.status_code in (403, 404)

    def test_verify_ownership_succeeds_for_matching_user(self):
        # Does not raise
        verify_ownership(resource_owner_id=USER_A, current_user_id=USER_A, resource_type="course")

    def test_child_assessments_protected_by_parent_course(self):
        c_a = create_course({"course_name": "Course With Exam"}, owner_user_id=USER_A)
        save_course_assessments(c_a["id"], [
            {"name": "Midterm Exam", "exam_date": "2026-05-10", "weightage": 30.0}
        ])

        # User A retrieves assessment
        asm_a = get_course_assessments(c_a["id"], owner_user_id=USER_A)
        assert len(asm_a) == 1
        assert asm_a[0]["name"] == "Midterm Exam"

        # User B cannot retrieve assessment
        asm_b = get_course_assessments(c_a["id"], owner_user_id=USER_B)
        assert len(asm_b) == 0

    def test_cross_tenant_syllabus_replacement_blocked(self):
        # Alice creates a course
        c_alice = create_course({"course_name": "Alice Course"}, owner_user_id=USER_A)

        # Bob creates a private syllabus
        s_bob = "syl_bob_private"
        save_raw_syllabus(
            syllabus_id=s_bob,
            filename="bob_secret.pdf",
            file_type="pdf",
            file_size_bytes=500,
            char_count=50,
            word_count=10,
            raw_text="Bob syllabus text",
            owner_user_id=USER_B,
        )

        # Alice attempts to attach Bob's private syllabus to Alice's course
        res = replace_course_syllabus(
            course_id=c_alice["id"],
            new_syllabus_id=s_bob,
            owner_user_id=USER_A,
        )
        assert res is None


class TestCourseCreationSyllabusAssociation:
    """Verifies that POST /api/courses enforces syllabus ownership and blocks cross-tenant linkage."""

    def test_user_a_cannot_create_course_with_user_b_syllabus(self):
        # User B creates a private syllabus
        s_bob = "syl_bob_association_test"
        save_raw_syllabus(
            syllabus_id=s_bob,
            filename="bob_syllabus.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            char_count=100,
            word_count=20,
            raw_text="Confidential Syllabus for User B",
            owner_user_id=USER_B,
        )

        # User A attempts to create a course linking User B's syllabus -> must be rejected with 403
        res = client.post(
            "/api/courses",
            headers={"X-User-Id": USER_A},
            json={
                "course_name": "Infiltrator Course",
                "course_code": "SEC401",
                "syllabus_id": s_bob,
            },
        )
        assert res.status_code == 403
        assert "Access denied" in res.json()["detail"]

    def test_user_can_create_course_with_own_syllabus(self):
        # User A creates their own syllabus
        s_alice = "syl_alice_own_test"
        save_raw_syllabus(
            syllabus_id=s_alice,
            filename="alice_syllabus.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            char_count=100,
            word_count=20,
            raw_text="Alice's Verified Syllabus",
            owner_user_id=USER_A,
        )

        # User A creates course linking their own syllabus -> succeeds
        res = client.post(
            "/api/courses",
            headers={"X-User-Id": USER_A},
            json={
                "course_name": "Alice Legitimate Course",
                "course_code": "CS101",
                "syllabus_id": s_alice,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["owner_user_id"] == USER_A
        assert data["syllabus_id"] == s_alice

    def test_create_course_with_nonexistent_syllabus_returns_404(self):
        res = client.post(
            "/api/courses",
            headers={"X-User-Id": USER_A},
            json={
                "course_name": "Ghost Syllabus Course",
                "syllabus_id": "nonexistent_syl_99999",
            },
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_create_course_without_syllabus_id_succeeds(self):
        res = client.post(
            "/api/courses",
            headers={"X-User-Id": USER_A},
            json={
                "course_name": "No Syllabus Course",
                "course_code": "GEN100",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["owner_user_id"] == USER_A
        assert data["syllabus_id"] is None


class TestSyllabusUploadAndAccessOwnership:
    """Verifies syllabus upload ownership assignment, type normalization, and cross-user isolation."""

    def test_authenticated_user_uploads_and_accesses_own_syllabus(self):
        import io
        import uuid
        user_uuid = str(uuid.uuid4())
        dummy_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

        # 1. Upload syllabus with authenticated user
        with patch("app.services.syllabus_parser.SyllabusParserService._extract_pdf_text") as mock_extract:
            mock_extract.return_value = ("Module 1: Intro\nTopic 1.1: Basics", 1, "pages", "Notes")
            res = client.post(
                "/api/syllabus/upload",
                headers={"X-User-Id": user_uuid},
                files={"file": ("test_course_syllabus.pdf", dummy_pdf, "application/pdf")},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        syllabus_id = data["syllabus_id"]
        assert syllabus_id is not None
        assert data["owner_user_id"] == user_uuid

        # 2. Verify record in database has correct owner_user_id
        s_record = get_syllabus_record(syllabus_id)
        assert s_record is not None
        assert s_record["owner_user_id"] == user_uuid

        # 3. Access own syllabus via verify_ownership (simulating PostgreSQL uuid.UUID object vs str)
        uuid_obj = uuid.UUID(user_uuid)
        # Should not raise 403
        verify_ownership(resource_owner_id=uuid_obj, current_user_id=user_uuid, resource_type="syllabus")
        verify_ownership(resource_owner_id=user_uuid, current_user_id=user_uuid, resource_type="syllabus")

    def test_other_user_denied_access_to_uploaded_syllabus(self):
        s_id = f"syl_priv_{USER_A}_01"
        save_raw_syllabus(
            syllabus_id=s_id,
            filename="private_notes.pdf",
            file_type="pdf",
            file_size_bytes=2048,
            char_count=500,
            word_count=80,
            raw_text="Confidential Syllabus Details",
            owner_user_id=USER_A,
        )

        # User B attempts to access User A's syllabus
        res = client.get(
            f"/api/syllabus/{s_id}",
            headers={"X-User-Id": USER_B},
        )
        assert res.status_code == 403
        assert "Access denied: You do not have permission to access or modify this syllabus" in res.json()["detail"]

        # User B attempts to setup-and-analyze User A's syllabus
        res_setup = client.post(
            "/api/courses/setup-and-analyze",
            headers={"X-User-Id": USER_B},
            json={
                "syllabus_id": s_id,
                "course_name": "Bob Hijack Attempt",
                "course_code": "SEC999",
                "language": "English",
                "lesson_style": "In-depth",
                "daily_study_availability": "2-4 hours",
                "assessment_system_type": "autonomous",
                "assessment_scope": "both",
                "assessments": [],
            },
        )
        assert res_setup.status_code == 403
        assert "Access denied: You do not have permission to access or modify this syllabus" in res_setup.json()["detail"]

    def test_production_missing_or_invalid_jwt_rejected_on_upload(self, monkeypatch):
        import app.core.config
        monkeypatch.setattr(app.core.config.settings, "app_env", "production")

        dummy_pdf = b"%PDF-1.4 mock content"

        # 1. No Authorization header -> 401
        res_no_auth = client.post(
            "/api/syllabus/upload",
            files={"file": ("test.pdf", dummy_pdf, "application/pdf")},
        )
        assert res_no_auth.status_code == 401
        assert "Authentication required" in res_no_auth.json()["detail"]

        # 2. Spoofing with X-User-Id in production -> 401
        res_spoof = client.post(
            "/api/syllabus/upload",
            headers={"X-User-Id": USER_A},
            files={"file": ("test.pdf", dummy_pdf, "application/pdf")},
        )
        assert res_spoof.status_code == 401

        # 3. Invalid Bearer token in production -> 401
        res_bad_token = client.post(
            "/api/syllabus/upload",
            headers={"Authorization": "Bearer totally-invalid-token"},
            files={"file": ("test.pdf", dummy_pdf, "application/pdf")},
        )
        assert res_bad_token.status_code == 401

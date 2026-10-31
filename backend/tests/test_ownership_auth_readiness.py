import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import (
    get_db_path,
    create_course,
    save_raw_syllabus,
    save_syllabus_hierarchy,
    save_study_plan,
    save_study_tasks,
    delete_course,
)

client = TestClient(app)


def test_database_migration_columns_and_indexes():
    """Verifies owner_user_id columns and performance indexes exist across tables."""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check columns
        courses_cols = {col[1] for col in cursor.execute("PRAGMA table_info(courses)").fetchall()}
        assert "owner_user_id" in courses_cols, "courses must have owner_user_id column"

        syllabi_cols = {col[1] for col in cursor.execute("PRAGMA table_info(syllabi)").fetchall()}
        assert "owner_user_id" in syllabi_cols, "syllabi must have owner_user_id column"

        plans_cols = {col[1] for col in cursor.execute("PRAGMA table_info(study_plans)").fetchall()}
        assert "owner_user_id" in plans_cols, "study_plans must have owner_user_id column"

        settings_cols = {col[1] for col in cursor.execute("PRAGMA table_info(user_settings)").fetchall()}
        assert "owner_user_id" in settings_cols, "user_settings must have owner_user_id column"

        # Check indexes
        index_names = {idx[1] for idx in cursor.execute("SELECT * FROM sqlite_master WHERE type = 'index'").fetchall()}
        assert "idx_courses_owner" in index_names, "idx_courses_owner must exist"
        assert "idx_syllabi_owner" in index_names, "idx_syllabi_owner must exist"
        assert "idx_study_plans_owner" in index_names, "idx_study_plans_owner must exist"
        assert "idx_user_settings_owner" in index_names, "idx_user_settings_owner must exist"


def test_legacy_unowned_data_accessible_in_dev_mode():
    """Verifies that legacy unowned courses created without authentication remain fully accessible."""
    legacy_id = "course_legacy_dev_test"
    create_course({
        "id": legacy_id,
        "course_name": "Legacy Operating Systems",
        "course_code": "CS201",
        "owner_user_id": None,
    })

    # Unauthenticated GET request (no headers) should succeed
    res = client.get(f"/api/courses/{legacy_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == legacy_id
    assert data["course_name"] == "Legacy Operating Systems"
    assert data["owner_user_id"] is None

    # Cleanup
    delete_course(legacy_id)


def test_multi_tenant_course_creation_and_listing_isolation():
    """
    Verifies that Alice and Bob create courses under their respective user IDs,
    and their course listings are completely isolated.
    """
    alice_headers = {"X-User-Id": "usr_alice_1111"}
    bob_headers = {"X-User-Id": "usr_bob_2222"}

    # Alice creates a course
    alice_res = client.post(
        "/api/courses",
        headers=alice_headers,
        json={
            "course_name": "Alice Neural Networks",
            "course_code": "CS501",
            "language": "English",
            "daily_study_availability": "2-4 hours",
        }
    )
    assert alice_res.status_code == 201
    alice_course = alice_res.json()
    alice_id = alice_course["id"]
    assert alice_course["owner_user_id"] == "usr_alice_1111"

    # Bob creates a course
    bob_res = client.post(
        "/api/courses",
        headers=bob_headers,
        json={
            "course_name": "Bob Quantum Computing",
            "course_code": "PH601",
            "language": "English",
            "daily_study_availability": "1-2 hours",
        }
    )
    assert bob_res.status_code == 201
    bob_course = bob_res.json()
    bob_id = bob_course["id"]
    assert bob_course["owner_user_id"] == "usr_bob_2222"

    # Alice lists courses -> sees only Alice's course
    alice_list = client.get("/api/courses", headers=alice_headers)
    assert alice_list.status_code == 200
    alice_course_ids = [c["id"] for c in alice_list.json()["courses"]]
    assert alice_id in alice_course_ids
    assert bob_id not in alice_course_ids

    # Bob lists courses -> sees only Bob's course
    bob_list = client.get("/api/courses", headers=bob_headers)
    assert bob_list.status_code == 200
    bob_course_ids = [c["id"] for c in bob_list.json()["courses"]]
    assert bob_id in bob_course_ids
    assert alice_id not in bob_course_ids

    # Cleanup
    delete_course(alice_id)
    delete_course(bob_id)


def test_cross_user_course_access_rejected_with_403():
    """
    Verifies that Bob cannot read, modify, archive, or delete Alice's course.
    Knowing the course ID does NOT grant permission (403 Forbidden).
    """
    alice_headers = {"X-User-Id": "usr_alice_secure"}
    bob_headers = {"X-User-Id": "usr_bob_intruder"}

    # Create Alice's course
    create_res = client.post(
        "/api/courses",
        headers=alice_headers,
        json={
            "course_name": "Alice Distributed Systems",
            "course_code": "CS401",
        }
    )
    assert create_res.status_code == 201
    alice_course_id = create_res.json()["id"]

    # 1. Bob tries to GET Alice's course -> 403 Forbidden
    res_get = client.get(f"/api/courses/{alice_course_id}", headers=bob_headers)
    assert res_get.status_code == 403
    assert "Access denied" in res_get.json()["detail"]

    # 2. Bob tries to PUT Alice's course -> 403 Forbidden
    res_put = client.put(
        f"/api/courses/{alice_course_id}",
        headers=bob_headers,
        json={"course_name": "Hacked Course Name"}
    )
    assert res_put.status_code == 403

    # 3. Bob tries to ARCHIVE Alice's course -> 403 Forbidden
    res_arch = client.post(
        f"/api/courses/{alice_course_id}/archive?is_archived=true",
        headers=bob_headers,
    )
    assert res_arch.status_code == 403

    # 4. Bob tries to DELETE Alice's course -> 403 Forbidden
    res_del = client.delete(f"/api/courses/{alice_course_id}", headers=bob_headers)
    assert res_del.status_code == 403

    # Alice herself CAN view and delete her course
    res_alice_get = client.get(f"/api/courses/{alice_course_id}", headers=alice_headers)
    assert res_alice_get.status_code == 200

    res_alice_del = client.delete(f"/api/courses/{alice_course_id}", headers=alice_headers)
    assert res_alice_del.status_code == 200


def test_cross_user_syllabus_and_study_plan_rejected_with_403():
    """
    Verifies that Bob cannot access or modify Alice's syllabus, topics, or study tasks.
    """
    alice_headers = {"X-User-Id": "usr_alice_academic"}
    bob_headers = {"X-User-Id": "usr_bob_academic"}

    s_id = "syl_alice_private"
    save_raw_syllabus(
        syllabus_id=s_id,
        filename="Alice_Compilers.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        char_count=500,
        word_count=100,
        raw_text="Module 1 Lexical Analysis",
        owner_user_id="usr_alice_academic",
    )

    save_syllabus_hierarchy(
        syllabus_id=s_id,
        hierarchy_dict={
            "course_name": "Compiler Design",
            "course_code": "CS305",
            "modules": [
                {
                    "id": "mod_1",
                    "title": "Lexical Analysis",
                    "topics": [
                        {"id": "top_1", "title": "Regular Expressions", "estimated_minutes": 60, "difficulty": "medium"}
                    ]
                }
            ],
            "ambiguous_sections": [],
        },
        is_fallback=True,
        analysis_engine="Test",
    )

    plan_id = "plan_alice_private"
    save_study_plan(
        {
            "id": plan_id,
            "syllabus_id": s_id,
            "title": "Alice Study Plan",
            "exam_date": "2026-06-15",
            "daily_target_minutes": 120,
            "owner_user_id": "usr_alice_academic",
        },
        owner_user_id="usr_alice_academic"
    )

    save_study_tasks(
        plan_id=plan_id,
        tasks=[{
            "id": "task_alice_1",
            "syllabus_id": s_id,
            "module_id": f"{s_id}_mod_1",
            "topic_id": f"{s_id}_top_1",
            "scheduled_date": "2026-05-01",
            "title": "Study Lexical Analysis",
            "task_type": "Study",
            "duration_minutes": 60,
            "status": "pending",
        }]
    )

    # 1. Bob tries to GET Alice's syllabus -> 403 Forbidden
    res_syl = client.get(f"/api/syllabus/{s_id}", headers=bob_headers)
    assert res_syl.status_code == 403

    # 2. Bob tries to update Alice's syllabus topics -> 403 Forbidden
    res_top = client.put(
        f"/api/syllabus/{s_id}/topics",
        headers=bob_headers,
        json={"modules": [{"id": "mod_1", "title": "Tampered Title", "topics": [], "order_index": 0}]}
    )
    assert res_top.status_code == 403

    # 3. Bob tries to GET Alice's study plan -> 403 Forbidden
    res_plan = client.get(f"/api/study-plan/{s_id}", headers=bob_headers)
    assert res_plan.status_code == 403

    # 4. Bob tries to mark Alice's task complete -> 403 Forbidden
    res_task = client.put(
        f"/api/study-plan/{plan_id}/tasks/task_alice_1/status",
        headers=bob_headers,
        json={"completed": True}
    )
    assert res_task.status_code == 403

    # Alice herself CAN access her syllabus and plan
    res_alice_syl = client.get(f"/api/syllabus/{s_id}", headers=alice_headers)
    assert res_alice_syl.status_code == 200

    res_alice_plan = client.get(f"/api/study-plan/{s_id}", headers=alice_headers)
    assert res_alice_plan.status_code == 200


def test_semester_overview_scoped_to_current_user():
    """Verifies that semester overview metrics aggregate only courses belonging to the requester."""
    u1_headers = {"X-User-Id": "usr_carol_333"}
    u2_headers = {"X-User-Id": "usr_david_444"}

    # Carol creates 2 courses
    c1 = client.post("/api/courses", headers=u1_headers, json={"course_name": "Carol Math", "course_code": "M1"}).json()
    c2 = client.post("/api/courses", headers=u1_headers, json={"course_name": "Carol Physics", "course_code": "P1"}).json()

    # David creates 1 course
    d1 = client.post("/api/courses", headers=u2_headers, json={"course_name": "David Biology", "course_code": "B1"}).json()

    # Carol gets semester overview -> shows 2 courses
    carol_ov = client.get("/api/courses/semester-overview", headers=u1_headers).json()
    assert carol_ov["total_courses"] == 2
    carol_names = [c["course_name"] for c in carol_ov["courses"]]
    assert "Carol Math" in carol_names
    assert "Carol Physics" in carol_names
    assert "David Biology" not in carol_names

    # David gets semester overview -> shows 1 course
    david_ov = client.get("/api/courses/semester-overview", headers=u2_headers).json()
    assert david_ov["total_courses"] == 1
    assert david_ov["courses"][0]["course_name"] == "David Biology"

    # Cleanup
    delete_course(c1["id"])
    delete_course(c2["id"])
    delete_course(d1["id"])


def test_user_settings_per_user_isolation():
    """Verifies that user settings can be saved and retrieved per-user without interfering."""
    headers_u1 = {"X-User-Id": "usr_eve"}
    headers_u2 = {"X-User-Id": "usr_frank"}

    # Eve saves Spanish and Fast-paced
    client.put(
        "/api/settings",
        headers=headers_u1,
        json={
            "preferred_language": "Spanish",
            "lesson_style": "Fast-paced",
            "daily_study_availability": "4+ hours",
            "daily_target_minutes": 240,
        }
    )

    # Frank retrieves settings -> should NOT have Eve's Spanish/Fast-paced settings
    frank_settings = client.get("/api/settings", headers=headers_u2).json()
    assert frank_settings["preferred_language"] == "English"
    assert frank_settings["lesson_style"] == "In-depth"

    # Eve retrieves settings -> gets her saved settings
    eve_settings = client.get("/api/settings", headers=headers_u1).json()
    assert eve_settings["preferred_language"] == "Spanish"
    assert eve_settings["lesson_style"] == "Fast-paced"


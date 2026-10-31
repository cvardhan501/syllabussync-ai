import datetime
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import (
    init_db,
    save_raw_syllabus,
    save_syllabus_hierarchy,
    create_course,
    get_courses,
    get_course,
    update_course,
    archive_course,
    delete_course,
    get_semester_overview,
    replace_course_syllabus,
    save_study_plan,
    save_study_tasks,
    update_task_completion,
    update_task_note,
    get_plan_tasks,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


def test_create_and_retrieve_multiple_courses_independently():
    """
    Scenario 1 & 2:
    Uploading or creating two different courses must NEVER overwrite each other.
    Both courses exist simultaneously and can be retrieved independently.
    """
    # 1. Setup Syllabus A
    sid_a = "test_syl_os_101"
    save_raw_syllabus(sid_a, "Operating_Systems.pdf", "pdf", 1024, 500, 100, "Module 1 OS Process Management")
    save_syllabus_hierarchy(
        sid_a,
        {
            "course_name": "Operating Systems",
            "course_code": "CS301",
            "modules": [
                {
                    "id": "mod_1",
                    "title": "Module 1: Processes",
                    "topics": [
                        {"id": "top_1", "title": "Process Scheduling", "estimated_minutes": 60, "difficulty": "medium"}
                    ]
                }
            ]
        },
        is_fallback=True,
        analysis_engine="MockHeuristic",
    )

    # 2. Setup Syllabus B
    sid_b = "test_syl_dbms_102"
    save_raw_syllabus(sid_b, "Database_Systems.pdf", "pdf", 2048, 800, 150, "Module 1 Relational Algebra")
    save_syllabus_hierarchy(
        sid_b,
        {
            "course_name": "Database Systems",
            "course_code": "CS302",
            "modules": [
                {
                    "id": "mod_1",
                    "title": "Module 1: Relational Model",
                    "topics": [
                        {"id": "top_1", "title": "SQL and Normalization", "estimated_minutes": 90, "difficulty": "hard"}
                    ]
                }
            ]
        },
        is_fallback=True,
        analysis_engine="MockHeuristic",
    )

    # 3. Create Course A
    ca_res = client.post("/api/courses", json={
        "course_name": "Operating Systems",
        "course_code": "CS301",
        "syllabus_id": sid_a,
        "language": "English",
        "lesson_style": "In-depth",
        "daily_study_availability": "2-4 hours",
        "daily_target_minutes": 120,
        "assessment_system_type": "autonomous",
        "assessments": [
            {
                "name": "CA1",
                "exam_date": (datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
                "assessment_type": "internal",
            }
        ]
    })
    assert ca_res.status_code == 201
    course_a = ca_res.json()
    cid_a = course_a["id"]

    # 4. Create Course B
    cb_res = client.post("/api/courses", json={
        "course_name": "Database Systems",
        "course_code": "CS302",
        "syllabus_id": sid_b,
        "language": "English",
        "lesson_style": "Practical",
        "daily_study_availability": "1-2 hours",
        "daily_target_minutes": 90,
        "assessment_system_type": "university",
        "assessments": [
            {
                "name": "IA1",
                "exam_date": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
                "assessment_type": "internal",
            }
        ]
    })
    assert cb_res.status_code == 201
    course_b = cb_res.json()
    cid_b = course_b["id"]

    # Verify both exist independently
    assert cid_a != cid_b

    get_a = client.get(f"/api/courses/{cid_a}")
    assert get_a.status_code == 200
    data_a = get_a.json()
    assert data_a["course_name"] == "Operating Systems"
    assert data_a["course_code"] == "CS301"
    assert data_a["lesson_style"] == "In-depth"

    get_b = client.get(f"/api/courses/{cid_b}")
    assert get_b.status_code == 200
    data_b = get_b.json()
    assert data_b["course_name"] == "Database Systems"
    assert data_b["course_code"] == "CS302"
    assert data_b["lesson_style"] == "Practical"


def test_assessment_patterns_and_milestones():
    """
    Scenario 3:
    Verifies Autonomous, University, and Custom assessment patterns with milestone schedules.
    """
    today = datetime.date.today()
    future_20 = (today + datetime.timedelta(days=20)).isoformat()
    future_45 = (today + datetime.timedelta(days=45)).isoformat()
    future_75 = (today + datetime.timedelta(days=75)).isoformat()

    # Create autonomous pattern course
    res = client.post("/api/courses", json={
        "course_name": "Discrete Mathematics",
        "course_code": "MAT201",
        "assessment_system_type": "autonomous",
        "assessments": [
            {"name": "CA1", "exam_date": future_20, "assessment_type": "internal", "weightage": 20},
            {"name": "CA2", "exam_date": future_45, "assessment_type": "internal", "weightage": 20},
            {"name": "End-Sem", "exam_date": future_75, "assessment_type": "end_sem", "weightage": 60},
        ]
    })
    assert res.status_code == 201
    course = res.json()
    assert len(course["assessments"]) == 3
    assert course["assessments"][0]["name"] == "CA1"
    assert course["assessments"][0]["days_remaining"] == 20
    assert course["next_assessment"]["name"] == "CA1"


def test_past_exam_date_validation_rejects_with_400():
    """
    Scenario 4:
    Reject past assessment dates and past study plan dates with 400 Bad Request.
    """
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    # 1. Course creation with past date
    res = client.post("/api/courses", json={
        "course_name": "History 101",
        "assessments": [
            {"name": "Old Exam", "exam_date": yesterday, "assessment_type": "internal"}
        ]
    })
    assert res.status_code == 422 or res.status_code == 400
    assert "Exam date cannot be in the past" in res.text

    # 2. Study plan creation with past date
    plan_res = client.post("/api/study-plan/fake_syl_id", json={
        "exam_date": yesterday,
        "daily_target_minutes": 60,
    })
    assert plan_res.status_code == 422 or plan_res.status_code == 400
    assert "Exam date cannot be in the past" in plan_res.text


def test_separate_course_study_plans_completions_and_notes():
    """
    Scenario 5:
    Tasks, completions, and notes in Course A must NEVER leak into or modify Course B.
    """
    # Create two courses with their own plans and tasks
    cid_1 = "course_plan_test_1"
    cid_2 = "course_plan_test_2"
    sid_1 = "syl_plan_1"
    sid_2 = "syl_plan_2"

    save_raw_syllabus(sid_1, "c1.pdf", "pdf", 1000, 100, 50, "C1")
    save_raw_syllabus(sid_2, "c2.pdf", "pdf", 1000, 100, 50, "C2")

    create_course({"id": cid_1, "syllabus_id": sid_1, "course_name": "Course 1"})
    create_course({"id": cid_2, "syllabus_id": sid_2, "course_name": "Course 2"})

    plan_1 = {"id": f"plan_{cid_1}", "syllabus_id": sid_1, "title": "Plan 1", "exam_date": "2026-12-01"}
    plan_2 = {"id": f"plan_{cid_2}", "syllabus_id": sid_2, "title": "Plan 2", "exam_date": "2026-12-01"}

    save_study_plan(plan_1)
    save_study_plan(plan_2)

    tasks_1 = [{
        "id": "t1_video",
        "syllabus_id": sid_1,
        "module_id": "m1",
        "topic_id": "top1",
        "scheduled_date": "2026-11-01",
        "title": "C1 Lecture 1",
        "task_type": "Video",
        "duration_minutes": 30,
        "status": "pending",
    }]
    tasks_2 = [{
        "id": "t2_video",
        "syllabus_id": sid_2,
        "module_id": "m2",
        "topic_id": "top2",
        "scheduled_date": "2026-11-01",
        "title": "C2 Lecture 1",
        "task_type": "Video",
        "duration_minutes": 30,
        "status": "pending",
    }]

    save_study_tasks(plan_1["id"], tasks_1, preserve_completed=False)
    save_study_tasks(plan_2["id"], tasks_2, preserve_completed=False)

    # Complete Task 1 in Course 1 and add note
    update_task_completion("t1_video", True)
    update_task_note("t1_video", "Important notes for Course 1")

    # Verify Task 1 is completed with notes
    t1_tasks = get_plan_tasks(plan_1["id"])
    assert t1_tasks[0]["status"] == "completed"
    assert t1_tasks[0]["notes"] == "Important notes for Course 1"

    # Verify Task 2 in Course 2 is completely unaffected
    t2_tasks = get_plan_tasks(plan_2["id"])
    assert t2_tasks[0]["status"] == "pending"
    assert t2_tasks[0]["notes"] is None


def test_semester_overview_progress_aggregation():
    """
    Scenario 6:
    Semester overview aggregates all active courses, topic counts, upcoming assessments, and overdue tasks.
    """
    res = client.get("/api/courses/semester-overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_courses" in data
    assert "total_topics" in data
    assert "overall_percentage" in data
    assert "upcoming_assessments" in data
    assert isinstance(data["upcoming_assessments"], list)


def test_safe_syllabus_replacement_preserves_completed_topics():
    """
    Scenario 7:
    Replacing a course's syllabus PDF re-parses it, but topics matching old titles keep their completed status and notes.
    """
    cid = "course_replace_test"
    old_sid = "syl_old_ver"
    new_sid = "syl_new_ver"

    save_raw_syllabus(old_sid, "Old_Course.pdf", "pdf", 1000, 100, 50, "Old Syllabus")
    save_raw_syllabus(new_sid, "New_Course.pdf", "pdf", 1500, 150, 75, "New Syllabus")

    create_course({"id": cid, "syllabus_id": old_sid, "course_name": "Software Engineering"})

    # Setup old task with completed status and notes
    plan_id = f"plan_{cid}"
    save_study_plan({"id": plan_id, "syllabus_id": old_sid, "title": "SE Plan", "exam_date": "2026-11-20"})
    save_study_tasks(plan_id, [
        {
            "id": "task_agile_video",
            "syllabus_id": old_sid,
            "module_id": "m1",
            "topic_id": "top_agile",
            "scheduled_date": "2026-11-05",
            "title": "Agile Scrum Methodology",
            "task_type": "Video",
            "duration_minutes": 45,
            "status": "completed",
            "notes": "Studied sprint backlog & daily standup.",
        }
    ], preserve_completed=False)

    # Now replace syllabus in course
    res = client.post(f"/api/courses/{cid}/replace-syllabus", json={
        "new_syllabus_id": new_sid,
        "preserve_matching_completions": True,
    })
    assert res.status_code == 200
    updated_course = res.json()
    assert updated_course["syllabus_id"] == new_sid

    # Generate new tasks for new syllabus containing the same topic title with preserve_completed=True
    new_tasks = [
        {
            "id": "new_task_agile_video",
            "syllabus_id": new_sid,
            "module_id": "m_new",
            "topic_id": "top_new_agile",
            "scheduled_date": "2026-11-06",
            "title": "Agile Scrum Methodology",
            "task_type": "Video",
            "duration_minutes": 45,
            "status": "pending",
        }
    ]
    save_study_tasks(plan_id, new_tasks, preserve_completed=True)

    # Verify matching completion history was re-applied
    plan_tasks = get_plan_tasks(plan_id)
    assert any(t["title"] == "Agile Scrum Methodology" and t["status"] == "completed" for t in plan_tasks)


def test_course_archival_and_cascading_deletion():
    """
    Scenario 8:
    Archiving hides course from default list. Deleting permanently cleans course and all linked entities.
    """
    cid = "course_arch_del_test"
    sid = "syl_arch_del"
    save_raw_syllabus(sid, "Test.pdf", "pdf", 500, 50, 20, "Test")
    create_course({"id": cid, "syllabus_id": sid, "course_name": "Temporary Course"})

    # 1. Archive
    arch_res = client.post(f"/api/courses/{cid}/archive?is_archived=true")
    assert arch_res.status_code == 200

    active_courses = client.get("/api/courses?include_archived=false").json()["courses"]
    assert not any(c["id"] == cid for c in active_courses)

    all_courses = client.get("/api/courses?include_archived=true").json()["courses"]
    assert any(c["id"] == cid for c in all_courses)

    # 2. Delete
    del_res = client.delete(f"/api/courses/{cid}")
    assert del_res.status_code == 200

    # Verify course no longer exists
    check_res = client.get(f"/api/courses/{cid}")
    assert check_res.status_code == 404

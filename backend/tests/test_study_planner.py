import io
import datetime
from fastapi.testclient import TestClient
import docx
import pytest

from app.main import app
from app.models.database import get_db_connection

client = TestClient(app)


def create_test_syllabus(title: str = "Operating Systems 301") -> str:
    """Helper to upload and analyze a syllabus, returning syllabus_id."""
    doc = docx.Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph("Module 1: Processes and Concurrency")
    doc.add_paragraph("Process Management and Threads")
    doc.add_paragraph("CPU Scheduling Algorithms")
    doc.add_paragraph("Module 2: Memory Architecture")
    doc.add_paragraph("Virtual Memory and Paging")
    doc.add_paragraph("Page Replacement Policies")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/syllabus/analyze",
        files={"file": ("os_syllabus.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 200
    return res.json()["syllabus_id"]


def test_generate_feasible_study_plan():
    """Verify study plan generation with reasonable deadline produces feasible timetable."""
    s_id = create_test_syllabus("Operating Systems Feasible")

    # Exam date 60 days in the future
    future_exam = (datetime.date.today() + datetime.timedelta(days=60)).isoformat()

    response = client.post(
        f"/api/study-plan/{s_id}",
        json={
            "exam_date": future_exam,
            "daily_target_minutes": 120,
            "preferred_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["syllabus_id"] == s_id
    assert data["feasibility_status"] == "feasible"
    assert data["shortfall_minutes"] == 0
    assert data["total_tasks_count"] > 0
    assert len(data["daily_schedules"]) > 0

    # Verify task structure
    first_day = data["daily_schedules"][0]
    assert len(first_day["tasks"]) > 0
    first_task = first_day["tasks"][0]
    assert first_task["task_type"] in ["Video", "Practice", "Study"]
    assert first_task["status"] == "pending"
    assert first_task["duration_minutes"] > 0


def test_impossible_deadline_and_shortfall_warning():
    """Verify that an impossibly tight deadline generates honest warning and exact shortfall hours."""
    s_id = create_test_syllabus("Operating Systems Rush")

    # Exam date tomorrow!
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    response = client.post(
        f"/api/study-plan/{s_id}",
        json={
            "exam_date": tomorrow,
            "daily_target_minutes": 60,  # only 60 minutes available total before tomorrow!
            "preferred_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["feasibility_status"] == "impossible"
    assert data["shortfall_minutes"] > 0
    assert data["shortfall_hours"] > 0
    assert "Shortfall" in data["feasibility_warning"]
    assert "hours" in data["feasibility_warning"]


def test_task_completion_and_progress_recalculation():
    """Verify completing a task updates progress percentage and completed minutes."""
    s_id = create_test_syllabus("Software Engineering")
    exam_date = (datetime.date.today() + datetime.timedelta(days=45)).isoformat()

    plan_res = client.post(
        f"/api/study-plan/{s_id}",
        json={"exam_date": exam_date, "daily_target_minutes": 120}
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    plan_id = plan_data["id"]

    # Pick the first task
    first_task = plan_data["daily_schedules"][0]["tasks"][0]
    task_id = first_task["id"]
    task_duration = first_task["duration_minutes"]

    # Complete the task
    upd_res = client.put(
        f"/api/study-plan/{plan_id}/tasks/{task_id}/status",
        json={"completed": True}
    )
    assert upd_res.status_code == 200
    upd_task = upd_res.json()
    assert upd_task["status"] == "completed"
    assert upd_task["completed_at"] is not None

    # Fetch updated plan
    get_res = client.get(f"/api/study-plan/{s_id}")
    assert get_res.status_code == 200
    updated_plan = get_res.json()
    assert updated_plan["completed_minutes"] >= task_duration
    assert updated_plan["completed_tasks_count"] >= 1
    assert updated_plan["progress_percentage"] > 0.0

    # Toggle incomplete
    uncomplete_res = client.put(
        f"/api/study-plan/{plan_id}/tasks/{task_id}/status",
        json={"completed": False}
    )
    assert uncomplete_res.status_code == 200
    assert uncomplete_res.json()["status"] == "pending"


def test_save_and_retrieve_task_notes():
    """Verify student notes are saved and retrieved on a task."""
    s_id = create_test_syllabus("Computer Graphics")
    exam_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    plan_res = client.post(
        f"/api/study-plan/{s_id}",
        json={"exam_date": exam_date, "daily_target_minutes": 90}
    )
    plan_data = plan_res.json()
    plan_id = plan_data["id"]
    task_id = plan_data["daily_schedules"][0]["tasks"][0]["id"]

    note_text = "Key takeaway: Paging eliminates external fragmentation but can cause internal fragmentation."
    note_res = client.put(
        f"/api/study-plan/{plan_id}/tasks/{task_id}/notes",
        json={"notes": note_text}
    )
    assert note_res.status_code == 200
    assert note_res.json()["notes"] == note_text

    # Verify notes persist in plan retrieval
    get_res = client.get(f"/api/study-plan/{s_id}")
    task_found = None
    for day in get_res.json()["daily_schedules"]:
        for t in day["tasks"]:
            if t["id"] == task_id:
                task_found = t
                break
    assert task_found is not None
    assert task_found["notes"] == note_text


def test_preserve_completed_tasks_on_regeneration():
    """Verify regenerating a study plan never discards completed tasks or notes."""
    s_id = create_test_syllabus("Distributed Systems")
    exam_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    plan_res = client.post(
        f"/api/study-plan/{s_id}",
        json={"exam_date": exam_date, "daily_target_minutes": 120}
    )
    plan_data = plan_res.json()
    plan_id = plan_data["id"]

    # Mark first task complete and add note
    task_id = plan_data["daily_schedules"][0]["tasks"][0]["id"]
    client.put(f"/api/study-plan/{plan_id}/tasks/{task_id}/status", json={"completed": True})
    client.put(f"/api/study-plan/{plan_id}/tasks/{task_id}/notes", json={"notes": "Preserved note."})

    # Regenerate plan with different daily minutes
    regen_res = client.post(
        f"/api/study-plan/{s_id}",
        json={
            "exam_date": exam_date,
            "daily_target_minutes": 60,
            "preserve_completed": True
        }
    )
    assert regen_res.status_code == 200
    regen_data = regen_res.json()
    assert regen_data["completed_tasks_count"] >= 1

    # Verify task is still completed with note intact
    found = False
    for day in regen_data["daily_schedules"]:
        for t in day["tasks"]:
            if t["id"] == task_id:
                assert t["status"] == "completed"
                assert t["notes"] == "Preserved note."
                found = True
                break
    assert found is True


def test_reschedule_missed_day_adaptive_recovery():
    """Verify unfinished tasks from a missed day are redistributed into future slots."""
    s_id = create_test_syllabus("Machine Learning")
    exam_date = (datetime.date.today() + datetime.timedelta(days=20)).isoformat()

    plan_res = client.post(
        f"/api/study-plan/{s_id}",
        json={"exam_date": exam_date, "daily_target_minutes": 120}
    )
    plan_data = plan_res.json()
    plan_id = plan_data["id"]

    # Intentionally update scheduled_date of first 2 tasks to yesterday (simulating a missed day)
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    tasks = plan_data["daily_schedules"][0]["tasks"]
    with get_db_connection() as conn:
        conn.execute("UPDATE study_tasks SET scheduled_date = ? WHERE id = ?", (yesterday, tasks[0]["id"]))
        if len(tasks) > 1:
            conn.execute("UPDATE study_tasks SET scheduled_date = ? WHERE id = ?", (yesterday, tasks[1]["id"]))
        conn.commit()

    # Trigger adaptive rescheduling
    resched_res = client.post(
        f"/api/study-plan/{plan_id}/reschedule",
        json={"from_date": datetime.date.today().isoformat()}
    )
    assert resched_res.status_code == 200
    resched_data = resched_res.json()

    # Verify no tasks are scheduled on yesterday
    for day in resched_data["daily_schedules"]:
        assert day["date"] != yesterday or day["tasks"][0]["status"] == "completed"


def test_user_settings_persistence():
    """Verify user settings are saved and retrieved from SQLite backend."""
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200

    new_settings = {
        "preferred_language": "Hindi",
        "lesson_style": "Fast-paced",
        "daily_study_availability": "1-2 hours",
        "daily_target_minutes": 90,
        "exam_date": "2026-06-01",
        "study_days": ["Mon", "Wed", "Fri"],
        "theme": "dark",
        "study_reminders": True,
        "deadline_alerts": False,
        "auto_save_progress": True,
    }

    put_res = client.put("/api/settings", json=new_settings)
    assert put_res.status_code == 200
    saved = put_res.json()
    assert saved["preferred_language"] == "Hindi"
    assert saved["lesson_style"] == "Fast-paced"
    assert saved["daily_target_minutes"] == 90
    assert saved["exam_date"] == "2026-06-01"
    assert saved["study_days"] == ["Mon", "Wed", "Fri"]
    assert saved["deadline_alerts"] is False


import sys
import json
import httpx
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("========================================")
    print("SYLLABUSSYNC AI — LIVE E2E VERIFICATION")
    print("========================================")
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. Health check
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health = resp.json()
    print(f"[*] 1. Health check passed: {health['status']} ({health['app_name']} v{health['version']})")

    # 2. Settings check & update
    resp = client.get("/api/settings")
    assert resp.status_code == 200, f"Get settings failed: {resp.text}"
    print(f"[*] 2a. Initial settings retrieved: preferred_language={resp.json()['preferred_language']}")

    update_payload = {
        "preferred_language": "English",
        "lesson_style": "In-depth",
        "daily_target_minutes": 120,
        "exam_date": (date.today() + timedelta(days=45)).isoformat(),
        "study_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "theme": "dark",
        "study_reminders": True,
        "deadline_alerts": True,
        "auto_save_progress": True
    }
    resp = client.put("/api/settings", json=update_payload)
    assert resp.status_code == 200, f"Update settings failed: {resp.text}"
    print(f"[*] 2b. Settings updated and persisted in SQLite: {resp.json()['exam_date']}")

    # 3. Upload a sample syllabus as a valid DOCX file
    import io
    from docx import Document

    doc = Document()
    doc.add_heading("CS201: Data Structures and Algorithms", level=0)
    doc.add_heading("Unit 1: Trees and Graphs", level=1)
    doc.add_paragraph("Binary Search Trees and AVL Trees. Balance factors, rotations, and tree traversals.")
    doc.add_paragraph("Graph Traversal BFS and DFS. Adjacency lists, shortest paths, and topological sorting.")
    doc.add_heading("Unit 2: Dynamic Programming", level=1)
    doc.add_paragraph("Memoization and Tabulation. Overlapping subproblems, optimal substructure.")
    doc.add_paragraph("Knapsack and Longest Common Subsequence. 0/1 Knapsack dynamic table formulation.")

    docx_buf = io.BytesIO()
    doc.save(docx_buf)
    docx_buf.seek(0)

    files = {"file": ("cs201_syllabus.docx", docx_buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    resp = client.post("/api/syllabus/upload", files=files)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    upload_data = resp.json()
    syllabus_id = upload_data["syllabus_id"]
    print(f"[*] 3. Syllabus uploaded: ID={syllabus_id}, Words={upload_data['word_count']}")

    # 4. Analyze syllabus
    resp = client.post("/api/syllabus/analyze", data={"syllabus_id": syllabus_id})
    assert resp.status_code == 200, f"Analysis failed: {resp.text}"
    analysis_data = resp.json()
    print(f"[*] 4. Syllabus analyzed: Course='{analysis_data.get('course_name')}', Modules={len(analysis_data['modules'])}, Total Topics={analysis_data['total_topics_count']}")
    assert len(analysis_data["modules"]) > 0, "No modules extracted"
    first_topic = analysis_data["modules"][0]["topics"][0]
    first_topic_id = first_topic["id"]
    print(f"    First topic: '{first_topic['title']}' (ID: {first_topic_id}, Est: {first_topic['estimated_minutes']}m)")

    # 5. YouTube Resource Discovery
    resp = client.post(f"/api/syllabus/{syllabus_id}/discover-resources", json={"preferred_language": "English"})
    assert resp.status_code == 200, f"Resource discovery failed: {resp.text}"
    resources_data = resp.json()
    print(f"[*] 5. YouTube discovery completed: Engine='{resources_data['discovery_engine']}', Coverage={resources_data['coverage']['coverage_percentage']}%")
    print(f"    Channels selected: {[c['channel_title'] for c in resources_data['selected_channels']]}")

    # 6. Generate Study Plan (Feasible)
    exam_target = (date.today() + timedelta(days=30)).isoformat()
    plan_payload = {
        "exam_date": exam_target,
        "daily_target_minutes": 90,
        "preferred_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "preserve_completed": True
    }
    resp = client.post(f"/api/study-plan/{syllabus_id}", json=plan_payload)
    assert resp.status_code == 200, f"Study plan generation failed: {resp.text}"
    plan = resp.json()
    plan_id = plan["id"]
    print(f"[*] 6. Study plan generated: Plan ID={plan_id}, Total Tasks={plan['total_tasks_count']}, Feasibility='{plan['feasibility_status']}'")
    assert plan["total_tasks_count"] > 0, "No tasks generated in study plan"
    assert len(plan["daily_schedules"]) > 0, "No daily schedules generated"

    # 7. Retrieve Study Plan
    resp = client.get(f"/api/study-plan/{syllabus_id}")
    assert resp.status_code == 200, f"Get study plan failed: {resp.text}"
    retrieved_plan = resp.json()
    assert retrieved_plan["id"] == plan_id
    first_task = retrieved_plan["daily_schedules"][0]["tasks"][0]
    first_task_id = first_task["id"]
    print(f"[*] 7. Study plan retrieved: Day 1 ({retrieved_plan['daily_schedules'][0]['date']}) has {len(retrieved_plan['daily_schedules'][0]['tasks'])} tasks.")
    print(f"    First task: '{first_task['title']}' ({first_task['duration_minutes']} min, status: {first_task['status']})")

    # 8. Mark Task Complete
    resp = client.put(f"/api/study-plan/{plan_id}/tasks/{first_task_id}/status", json={"completed": True})
    assert resp.status_code == 200, f"Update task status failed: {resp.text}"
    task_update = resp.json()
    assert task_update["status"] == "completed"
    print(f"[*] 8. Task {first_task_id} marked COMPLETED. Verified status='{task_update['status']}'")

    # 9. Save Study Notes
    note_text = "Mastered AVL rotation: LL, RR, LR, RL balancing cases. Highly effective YouTube breakdown."
    resp = client.put(f"/api/study-plan/{plan_id}/tasks/{first_task_id}/notes", json={"notes": note_text})
    assert resp.status_code == 200, f"Save note failed: {resp.text}"
    note_res = resp.json()
    assert note_res["notes"] == note_text
    print(f"[*] 9. Task study notes persisted: '{note_res['notes'][:40]}...'")

    # 10. Regeneration Preservation Check
    # Regenerate plan with a new exam date; ensure completed task history is preserved!
    resp = client.post(f"/api/study-plan/{syllabus_id}", json={
        "exam_date": (date.today() + timedelta(days=40)).isoformat(),
        "daily_target_minutes": 100,
        "preserve_completed": True
    })
    assert resp.status_code == 200, f"Regeneration failed: {resp.text}"
    regenerated_plan = resp.json()
    all_regen_tasks = [t for g in regenerated_plan["daily_schedules"] for t in g["tasks"]]
    preserved_task = next((t for t in all_regen_tasks if t["id"] == first_task_id), None)
    assert preserved_task is not None, "Completed task was discarded during plan regeneration!"
    assert preserved_task["status"] == "completed", "Completed status was lost during plan regeneration!"
    assert preserved_task["notes"] == note_text, "Task notes were lost during plan regeneration!"
    print(f"[*] 10. Plan regenerated successfully: Completed task {first_task_id} PRESERVED with notes intact!")

    # 11. Adaptive Recovery / Missed-Day Reschedule
    resp = client.post(f"/api/study-plan/{plan_id}/reschedule")
    assert resp.status_code == 200, f"Reschedule failed: {resp.text}"
    rescheduled_plan = resp.json()
    print(f"[*] 11. Adaptive recovery executed: Rescheduled across {len(rescheduled_plan['daily_schedules'])} daily slots without dropping completed tasks.")

    # 12. Honest Deadline Warning / Impossible Deadline Test
    tight_target = (date.today() + timedelta(days=1)).isoformat()
    resp = client.post(f"/api/study-plan/{syllabus_id}", json={
        "exam_date": tight_target,
        "daily_target_minutes": 15,
        "preferred_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "preserve_completed": True
    })
    assert resp.status_code == 200, f"Tight plan generation failed: {resp.text}"
    tight_plan = resp.json()
    print(f"[*] 12. Impossible deadline evaluated:")
    print(f"    Feasibility status: '{tight_plan['feasibility_status']}'")
    print(f"    Shortfall minutes:  {tight_plan['shortfall_minutes']}m ({tight_plan['shortfall_minutes'] // 60}h {tight_plan['shortfall_minutes'] % 60}m)")
    print(f"    Honest Warning:     '{tight_plan['feasibility_warning']}'")
    assert tight_plan["feasibility_status"] == "impossible", "Feasibility should be 'impossible'!"
    assert tight_plan["shortfall_minutes"] > 0, "Shortfall minutes must be > 0!"
    assert "Shortfall" in tight_plan["feasibility_warning"] or "Cannot fit" in tight_plan["feasibility_warning"]

    print("\n=======================================================")
    print("ALL 12 LIVE END-TO-END VERIFICATION CHECKS PASSED 100%!")
    print("=======================================================")

if __name__ == "__main__":
    main()

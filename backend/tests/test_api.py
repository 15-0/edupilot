from datetime import date, timedelta

from tests.conftest import register


def test_full_student_flow(client):
    admin_h, admin = register(client, "Admin", "admin@uni.edu")
    assert admin["role"] == "admin"  # first account becomes admin

    h, me = register(client, "Asha", "asha@uni.edu")
    assert me["role"] == "student"

    # auth
    assert client.post("/api/auth/register", json={"name": "x", "email": "ASHA@uni.edu", "password": "password123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "asha@uni.edu", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "asha@uni.edu", "password": "password123"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/admin/users", headers=h).status_code == 403
    assert len(client.get("/api/admin/users", headers=admin_h).json()) == 2

    # courses
    bio = client.post("/api/courses", headers=h, json={"course_name": "Biology", "course_code": "BSC 401"}).json()
    env = client.post("/api/courses", headers=h, json={"course_name": "Environmental Science", "course_code": "MC-401"}).json()
    assert bio["enrolled"] and bio["can_manage"]
    assert len(client.get("/api/courses", headers=h).json()) == 2

    # assignments
    today = date.today()
    a = client.post("/api/assignments", headers=h, json={
        "course_id": bio["course_id"], "title": "Lab report", "due_date": str(today + timedelta(days=2)), "priority": "high"
    })
    assert a.status_code == 201, a.text
    client.post("/api/assignments", headers=h, json={
        "course_id": env["course_id"], "title": "Essay", "due_date": str(today - timedelta(days=1))
    })
    assert client.patch(f"/api/assignments/{a.json()['assignment_id']}", headers=h, json={"status": "in_progress"}).json()["status"] == "in_progress"
    assert any(x["is_overdue"] for x in client.get("/api/assignments", headers=h).json())

    # grades (validation + auto prediction)
    bad = client.post("/api/grades", headers=h, json={"course_id": bio["course_id"], "assessment_type": "quiz", "title": "Q", "score": 120, "max_score": 100})
    assert bad.status_code == 422
    for i, s in enumerate([82, 74, 58, 61]):
        r = client.post("/api/grades", headers=h, json={
            "course_id": bio["course_id"], "assessment_type": "quiz", "title": f"Quiz {i + 1}: Cell biology {i}",
            "score": s, "graded_on": str(today - timedelta(days=20 - i * 5)),
        })
        assert r.status_code == 201, r.text
    client.post("/api/grades", headers=h, json={"course_id": env["course_id"], "assessment_type": "midterm", "title": "Midterm", "score": 45, "max_score": 50})
    preds = client.get("/api/ai/predictions", headers=h).json()
    assert len(preds) == 2
    for p in preds:
        assert 0 <= p["lower_bound"] <= p["predicted_score"] <= p["upper_bound"] <= 100

    # attendance upsert + unique day
    for status in ("present", "absent"):
        r = client.post("/api/attendance", headers=h, json={"course_id": bio["course_id"], "attendance_date": str(today), "status": status})
        assert r.status_code == 201
    assert len(client.get("/api/attendance", headers=h, params={"course_id": bio["course_id"]}).json()) == 1
    assert client.get("/api/attendance/summary", headers=h).json()[0]["absent"] == 1

    # study sessions
    for d in range(3):
        assert client.post("/api/study-sessions", headers=h, json={"course_id": bio["course_id"], "duration_minutes": 50,
                           "topic": "Mitosis", "session_date": str(today - timedelta(days=d))}).status_code == 201

    dash = client.get("/api/dashboard", headers=h).json()
    assert dash["stats"]["study_streak"] == 3
    assert dash["stats"]["course_count"] == 2
    assert dash["stats"]["overdue_assignments"] == 1

    # AI: predictions, weak subjects, study plan
    assert len(client.post("/api/ai/predict", headers=h).json()) == 2
    assert client.get("/api/ai/model-info", headers=h).json()["mae"] > 0
    recs = client.post("/api/ai/weak-subjects", headers=h).json()
    assert all(r["topics"] for r in recs)
    plan = client.post("/api/ai/study-plan", headers=h, json={"hours_per_day": 2}).json()
    assert len(plan) == 7 and all(p["tasks"] for p in plan)
    assert any(t["type"] == "assignment" for p in plan for t in p["tasks"])
    task = plan[0]["tasks"][0]
    toggled = client.patch(f"/api/ai/study-plan/{plan[0]['plan_id']}/tasks/{task['id']}", headers=h, json={"done": True}).json()
    assert toggled["tasks"][0]["done"] is True
    # regenerating replaces (unique per day)
    assert len(client.post("/api/ai/study-plan", headers=h, json={}).json()) == 7

    cal = client.get("/api/calendar", headers=h, params={"start": str(today - timedelta(days=7)), "end": str(today + timedelta(days=7))}).json()
    assert {"assignment", "session", "plan"} <= {e["type"] for e in cal}

    # documents + RAG chat (extractive mode without an API key)
    notes = (b"Photosynthesis converts light energy into chemical energy stored in glucose. "
             b"It happens in the chloroplasts of plant cells.\n\n"
             b"Mitosis is cell division producing two identical daughter cells. Its phases are prophase, "
             b"metaphase, anaphase and telophase.")
    up = client.post("/api/documents", headers=h, files={"file": ("bio-notes.txt", notes, "text/plain")},
                     data={"course_id": str(bio["course_id"])})
    assert up.status_code == 201, up.text
    assert up.json()["chunk_count"] >= 1
    assert client.post("/api/documents", headers=h, files={"file": ("x.exe", b"abc", "application/octet-stream")}).status_code == 400
    ans = client.post("/api/documents/chat", headers=h, json={"question": "What are the phases of mitosis?"}).json()
    assert ans["mode"] == "extractive" and ans["sources"][0]["filename"] == "bio-notes.txt"

    # isolation: another student can't see or edit my data
    h2, _ = register(client, "Ben", "ben@uni.edu")
    assert client.get("/api/grades", headers=h2).json() == []
    assert client.get("/api/documents", headers=h2).json() == []
    assert client.delete(f"/api/assignments/{a.json()['assignment_id']}", headers=h2).status_code == 404
    assert client.post("/api/grades", headers=h2, json={"course_id": bio["course_id"], "assessment_type": "quiz", "title": "x", "score": 1}).status_code == 403
    assert client.delete(f"/api/courses/{bio['course_id']}", headers=h2).status_code == 403

    # documents cleanup
    assert client.delete(f"/api/documents/{up.json()['document_id']}", headers=h).status_code == 204


def test_instructor_can_grade_enrolled_students(client):
    ih, _ = register(client, "Dr Rao", "rao@uni.edu", role="instructor")
    sh, student = register(client, "Chen", "chen@uni.edu")
    course = client.post("/api/courses", headers=ih, json={"course_name": "Chemistry"}).json()
    assert course["instructor_id"] is not None

    payload = {"course_id": course["course_id"], "student_id": student["user_id"], "assessment_type": "lab", "title": "Lab 1", "score": 70}
    assert client.post("/api/grades", headers=ih, json=payload).status_code == 400  # not enrolled yet
    assert client.post(f"/api/courses/{course['course_id']}/enroll", headers=sh).json()["enrolled"]
    assert client.post("/api/grades", headers=ih, json=payload).status_code == 201
    roster = client.get(f"/api/courses/{course['course_id']}/students", headers=ih).json()
    assert [s["email"] for s in roster] == ["chen@uni.edu"]
    assert client.get(f"/api/courses/{course['course_id']}/students", headers=sh).status_code == 403
    seen = client.get("/api/grades", headers=ih, params={"course_id": course["course_id"], "student_id": student["user_id"]}).json()
    assert len(seen) == 1
    assert len(client.get("/api/grades", headers=sh).json()) == 1

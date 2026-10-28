"""Fill a running API with demo data.

Run (backend must be running):  python -m scripts.seed_demo [http://localhost:8000]
Demo login: demo@edupilot.dev / demo12345
"""
import random
import sys
from datetime import date, timedelta

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api"
EMAIL, PASSWORD = "demo@edupilot.dev", "demo12345"


def main() -> None:
    c = httpx.Client(base_url=BASE, timeout=60)
    r = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        r = c.post("/auth/register", json={"name": "Demo Student", "email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    if c.get("/courses").json():
        print("Demo data already present - log in with", EMAIL, PASSWORD)
        return

    rng = random.Random(4)
    today = date.today()
    courses = [
        ("Biology", "BSC 401", 78, ["Cell structure", "Mitosis & meiosis", "Genetics", "Photosynthesis", "Enzymes"]),
        ("Environmental Science", "MC-401", 62, ["Ecosystems", "Carbon cycle", "Pollution", "Biodiversity", "Climate models"]),
        ("Calculus II", "MATH 202", 85, ["Integration by parts", "Series", "Polar curves", "Taylor series"]),
    ]
    for name, code, level, topics in courses:
        cid = c.post("/courses", json={"course_name": name, "course_code": code, "semester": "Fall 2026"}).json()["course_id"]
        for i, topic in enumerate(topics):
            score = max(20, min(100, rng.gauss(level, 9) - (i * 2 if level < 70 else 0)))
            c.post("/grades", json={"course_id": cid, "assessment_type": "quiz" if i % 3 else "assignment",
                                    "title": f"Quiz {i + 1}: {topic}", "score": round(score),
                                    "graded_on": str(today - timedelta(days=40 - i * 8))}).raise_for_status()
        for d in range(1, 30, 2):
            status = rng.choices(["present", "late", "absent"], [0.8 if level > 70 else 0.6, 0.1, 0.1 if level > 70 else 0.3])[0]
            c.post("/attendance", json={"course_id": cid, "attendance_date": str(today - timedelta(days=d)), "status": status})
        for d in range(0, 21, rng.choice([1, 2, 3])):
            c.post("/study-sessions", json={"course_id": cid, "duration_minutes": rng.choice([30, 45, 60, 90]),
                                            "topic": rng.choice(topics), "session_date": str(today - timedelta(days=d))})
        c.post("/assignments", json={"course_id": cid, "title": f"{name} problem set", "due_date": str(today + timedelta(days=rng.randint(1, 6))), "priority": "high"})
        c.post("/assignments", json={"course_id": cid, "title": f"{name} reading summary", "due_date": str(today - timedelta(days=5)), "status": "completed"})

    c.post("/ai/predict").raise_for_status()
    c.post("/ai/weak-subjects").raise_for_status()
    c.post("/ai/study-plan", json={"hours_per_day": 2}).raise_for_status()
    notes = (
        "Mitosis is the process of cell division that produces two genetically identical daughter cells. "
        "It has four phases: prophase (chromosomes condense), metaphase (chromosomes line up at the equator), "
        "anaphase (sister chromatids separate) and telophase (nuclear envelopes reform).\n\n"
        "Photosynthesis occurs in chloroplasts. Light-dependent reactions in the thylakoid membranes produce ATP "
        "and NADPH; the Calvin cycle in the stroma uses them to fix carbon dioxide into glucose."
    )
    c.post("/documents", files={"file": ("biology-lecture-notes.txt", notes.encode(), "text/plain")}).raise_for_status()
    print("Demo data created. Log in with", EMAIL, PASSWORD)


if __name__ == "__main__":
    main()

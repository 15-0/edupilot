from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import enrolled_course_ids
from app.models import AIPrediction, Assignment, Attendance, Course, Grade, StudyPlan, StudySession, User
from app.security import get_current_user

router = APIRouter(tags=["dashboard"])


def _study_streak(days: set[date]) -> int:
    today = date.today()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    course_ids = enrolled_course_ids(db, user.user_id)
    courses = db.scalars(select(Course).where(Course.course_id.in_(course_ids)).order_by(Course.course_name)).all()
    names = {c.course_id: c.course_name for c in courses}

    grades = db.scalars(select(Grade).where(Grade.user_id == user.user_id).order_by(Grade.graded_on, Grade.grade_id)).all()
    attendance = db.scalars(select(Attendance).where(Attendance.user_id == user.user_id)).all()
    sessions = db.scalars(select(StudySession).where(StudySession.user_id == user.user_id)).all()
    assignments = db.scalars(select(Assignment).where(Assignment.user_id == user.user_id)).all()

    # Latest prediction per course
    latest_pred: dict[int, AIPrediction] = {}
    for p in db.scalars(
        select(AIPrediction).where(AIPrediction.user_id == user.user_id).order_by(AIPrediction.created_at, AIPrediction.prediction_id)
    ):
        latest_pred[p.course_id] = p

    def pct(g: Grade) -> float:
        return g.score / g.max_score * 100

    total_w = sum(g.weight for g in grades)
    overall_avg = round(sum(pct(g) * g.weight for g in grades) / total_w, 1) if total_w else None

    counted = [a for a in attendance if a.status != "excused"]
    att_rate = (
        round(sum(1 if a.status == "present" else 0.75 if a.status == "late" else 0 for a in counted) / len(counted) * 100, 1)
        if counted else None
    )

    week_start = today - timedelta(days=today.weekday())
    minutes_this_week = sum(s.duration_minutes for s in sessions if s.session_date >= week_start)
    total_minutes = sum(s.duration_minutes for s in sessions)

    # Weekly study hours for the last 8 weeks
    weekly = []
    for i in range(7, -1, -1):
        ws = week_start - timedelta(weeks=i)
        we = ws + timedelta(days=6)
        mins = sum(s.duration_minutes for s in sessions if ws <= s.session_date <= we)
        weekly.append({"week": ws.strftime("%d %b"), "hours": round(mins / 60, 1)})

    per_course = []
    for c in courses:
        cg = [g for g in grades if g.course_id == c.course_id]
        w = sum(g.weight for g in cg)
        ca = [a for a in attendance if a.course_id == c.course_id and a.status != "excused"]
        pred = latest_pred.get(c.course_id)
        per_course.append({
            "course_id": c.course_id,
            "course_name": c.course_name,
            "course_code": c.course_code,
            "color": c.color,
            "average": round(sum(pct(g) * g.weight for g in cg) / w, 1) if w else None,
            "grade_count": len(cg),
            "attendance_rate": round(sum(1 if a.status == "present" else 0.75 if a.status == "late" else 0 for a in ca) / len(ca) * 100, 1) if ca else None,
            "study_hours": round(sum(s.duration_minutes for s in sessions if s.course_id == c.course_id) / 60, 1),
            "predicted_score": pred.predicted_score if pred else None,
            "risk_level": pred.risk_level if pred else None,
            "pending_assignments": sum(1 for a in assignments if a.course_id == c.course_id and a.status != "completed"),
        })

    upcoming = sorted(
        (a for a in assignments if a.status != "completed" and a.due_date >= today - timedelta(days=7)),
        key=lambda a: a.due_date,
    )[:6]

    grade_trend = [
        {"date": g.graded_on.isoformat(), "title": g.title, "course": names.get(g.course_id, ""), "percentage": round(pct(g), 1)}
        for g in grades[-20:]
    ]

    today_plan = db.scalar(select(StudyPlan).where(StudyPlan.user_id == user.user_id, StudyPlan.planned_date == today))

    return {
        "user": {"name": user.name, "role": user.role},
        "stats": {
            "course_count": len(courses),
            "overall_average": overall_avg,
            "attendance_rate": att_rate,
            "study_hours_this_week": round(minutes_this_week / 60, 1),
            "total_study_hours": round(total_minutes / 60, 1),
            "study_streak": _study_streak({s.session_date for s in sessions}),
            "pending_assignments": sum(1 for a in assignments if a.status != "completed"),
            "overdue_assignments": sum(1 for a in assignments if a.status != "completed" and a.due_date < today),
        },
        "courses": per_course,
        "upcoming_assignments": [
            {
                "assignment_id": a.assignment_id,
                "title": a.title,
                "course_name": names.get(a.course_id),
                "due_date": a.due_date.isoformat(),
                "status": a.status,
                "priority": a.priority,
                "is_overdue": a.due_date < today,
            }
            for a in upcoming
        ],
        "weekly_study_hours": weekly,
        "grade_trend": grade_trend,
        "today_plan": {"plan_id": today_plan.plan_id, "tasks": today_plan.tasks} if today_plan else None,
    }


@router.get("/calendar")
def calendar(start: date, end: date, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if end < start:
        raise HTTPException(status_code=400, detail="end must be on or after start")
    if (end - start).days > 120:
        raise HTTPException(status_code=400, detail="Date range is limited to 120 days")
    names = dict(db.execute(select(Course.course_id, Course.course_name)).all())
    events = []
    for a in db.scalars(select(Assignment).where(
        Assignment.user_id == user.user_id, Assignment.due_date >= start, Assignment.due_date <= end
    )):
        events.append({
            "id": f"a-{a.assignment_id}", "type": "assignment", "date": a.due_date.isoformat(),
            "title": a.title, "course_name": names.get(a.course_id), "status": a.status, "priority": a.priority,
        })
    for s in db.scalars(select(StudySession).where(
        StudySession.user_id == user.user_id, StudySession.session_date >= start, StudySession.session_date <= end
    )):
        events.append({
            "id": f"s-{s.session_id}", "type": "session", "date": s.session_date.isoformat(),
            "title": s.topic or "Study session", "course_name": names.get(s.course_id), "minutes": s.duration_minutes,
        })
    for p in db.scalars(select(StudyPlan).where(
        StudyPlan.user_id == user.user_id, StudyPlan.planned_date >= start, StudyPlan.planned_date <= end
    )):
        for t in p.tasks:
            events.append({
                "id": f"p-{p.plan_id}-{t.get('id')}", "type": "plan", "date": p.planned_date.isoformat(),
                "title": t.get("title"), "course_name": t.get("course_name"), "minutes": t.get("minutes"),
                "done": t.get("done", False), "plan_id": p.plan_id, "task_id": t.get("id"),
            })
    return sorted(events, key=lambda e: e["date"])

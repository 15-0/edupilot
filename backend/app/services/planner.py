"""Weak-subject analysis and personalised weekly study plans."""
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.deps import enrolled_course_ids
from app.models import AIRecommendation, Assignment, Course, Grade, StudyPlan
from app.services import llm, predictor

GENERIC_ACTIVITIES = [
    "Review lecture notes and summarise key ideas",
    "Practice problems / past-paper questions",
    "Self-quiz with flashcards (active recall)",
    "Re-explain the hardest concept in your own words",
]


def _course_analysis(db: Session, user_id: int, course: Course) -> dict:
    features = predictor.compute_features(db, user_id, course.course_id)
    estimate = predictor.predict(features)
    grades = db.scalars(select(Grade).where(Grade.user_id == user_id, Grade.course_id == course.course_id)).all()
    weak_items = sorted(
        ((g.title, g.score / g.max_score * 100) for g in grades if g.score / g.max_score < 0.7),
        key=lambda x: x[1],
    )
    reasons = []
    if features["has_grades"] and features["avg_score"] < 70:
        reasons.append(f"average of {features['avg_score']:.0f}%")
    if estimate["predicted_score"] < 70:
        reasons.append(f"estimated final around {estimate['predicted_score']:.0f}%")
    if features["score_trend"] <= -3:
        reasons.append("scores trending downward")
    if features["has_attendance"] and features["attendance_rate"] < 0.75:
        reasons.append(f"attendance at {features['attendance_rate'] * 100:.0f}%")
    return {
        "course": course,
        "features": features,
        "estimate": estimate,
        "weak_topics": [t for t, _ in weak_items][:5],
        "reasons": reasons,
        "is_weak": bool(reasons),
    }


def _llm_topics(course: Course, weak_titles: list[str], avg: float) -> list[str] | None:
    prompt = (
        f"Course: {course.course_name}" + (f" ({course.course_code})" if course.course_code else "") + "\n"
        f"Student's current average: {avg:.0f}%\n"
        f"Low-scoring assessments: {', '.join(weak_titles) or 'none recorded'}\n\n"
        "List 3 to 5 specific revision topics this student should focus on next. "
        "Return only the topics, one per line, no numbering or extra text."
    )
    text = llm.complete("You are an academic advisor who gives concise, specific revision advice.", prompt, max_tokens=1500)
    if not text:
        return None
    topics = [line.strip(" -*•\t0123456789.)") for line in text.splitlines()]
    topics = [t for t in topics if 2 < len(t) < 120]
    return topics[:5] or None


def analyse_weak_subjects(db: Session, user_id: int, use_llm: bool = True) -> list[AIRecommendation]:
    courses = db.scalars(select(Course).where(Course.course_id.in_(enrolled_course_ids(db, user_id)))).all()
    db.execute(delete(AIRecommendation).where(AIRecommendation.user_id == user_id))
    recs = []
    for course in courses:
        a = _course_analysis(db, user_id, course)
        if not a["is_weak"]:
            continue
        topics, source = None, "rules"
        if use_llm:
            topics = _llm_topics(course, a["weak_topics"], a["features"]["avg_score"])
            source = "llm" if topics else "rules"
        if not topics:
            topics = [f"Revisit: {t}" for t in a["weak_topics"]] or [
                f"Core concepts of {course.course_name}",
                "Work through end-of-chapter problems",
                "Summarise each lecture on one page",
            ]
        score = a["estimate"]["predicted_score"]
        rec = AIRecommendation(
            user_id=user_id,
            course_id=course.course_id,
            reason="Flagged because of " + ", ".join(a["reasons"]) + ".",
            topics=topics,
            priority="high" if score < 60 else "medium" if score < 70 else "low",
            source=source,
        )
        db.add(rec)
        recs.append(rec)
    db.commit()
    for r in recs:
        db.refresh(r)
    return recs


def generate_week_plan(db: Session, user_id: int, start: date, hours_per_day: float = 2.0,
                       rest_day: int | None = 6) -> list[StudyPlan]:
    courses = db.scalars(select(Course).where(Course.course_id.in_(enrolled_course_ids(db, user_id)))).all()
    if not courses:
        raise ValueError("Enrol in at least one course before generating a study plan")

    end = start + timedelta(days=6)
    assignments = db.scalars(
        select(Assignment).where(
            Assignment.user_id == user_id,
            Assignment.status != "completed",
            Assignment.due_date >= start,
            Assignment.due_date <= end + timedelta(days=7),
        ).order_by(Assignment.due_date)
    ).all()

    analysis = {c.course_id: _course_analysis(db, user_id, c) for c in courses}
    priority: dict[int, float] = {}
    for cid, a in analysis.items():
        p = 1.0 + max(0.0, 100 - a["estimate"]["predicted_score"]) / 20
        p += {"high": 1.5, "medium": 0.75, "low": 0.0}[a["estimate"]["risk_level"]]
        for asg in assignments:
            if asg.course_id == cid:
                days_left = (asg.due_date - start).days
                p += 2.5 if days_left <= 3 else 1.2 if days_left <= 7 else 0.4
        priority[cid] = p

    credit = {cid: 0.0 for cid in priority}
    topic_cursor = {cid: 0 for cid in priority}
    plans = []
    db.execute(delete(StudyPlan).where(
        StudyPlan.user_id == user_id, StudyPlan.planned_date >= start, StudyPlan.planned_date <= end
    ))

    for offset in range(7):
        day = start + timedelta(days=offset)
        budget = int(hours_per_day * 60 * (0.5 if rest_day is not None and day.weekday() == rest_day else 1))
        tasks: list[dict] = []

        # 1) Deadline work: assignments due within the next 2 days
        for asg in assignments:
            if 0 <= (asg.due_date - day).days <= 2 and budget >= 25:
                mins = min(50, budget)
                tasks.append({
                    "type": "assignment",
                    "course_id": asg.course_id,
                    "course_name": analysis[asg.course_id]["course"].course_name,
                    "title": f"Work on \"{asg.title}\" (due {asg.due_date.strftime('%a %d %b')})",
                    "minutes": mins,
                })
                budget -= mins

        # 2) Revision blocks via weighted round-robin over course priorities
        blocks = 2 if budget >= 50 else 1 if budget >= 20 else 0
        for cid in credit:
            credit[cid] += priority[cid]
        for b in range(blocks):
            cid = max(credit, key=credit.get)
            credit[cid] -= sum(priority.values()) / max(blocks, 1)
            a = analysis[cid]
            weak = a["weak_topics"]
            idx = topic_cursor[cid]
            topic_cursor[cid] += 1
            title = f"Revise: {weak[idx % len(weak)]}" if weak and idx % 2 == 0 else GENERIC_ACTIVITIES[idx % len(GENERIC_ACTIVITIES)]
            mins = budget if b == blocks - 1 else max(20, round(budget / blocks / 5) * 5)
            tasks.append({
                "type": "revision",
                "course_id": cid,
                "course_name": a["course"].course_name,
                "title": title,
                "minutes": int(mins),
            })
            budget -= int(mins)

        for i, t in enumerate(tasks):
            t["id"] = f"{day.isoformat()}-{i}"
            t["done"] = False
        plan = StudyPlan(
            user_id=user_id,
            planned_date=day,
            title=f"Study plan - {day.strftime('%A %d %b')}",
            tasks=tasks,
            course_id=tasks[0]["course_id"] if len({t["course_id"] for t in tasks}) == 1 else None,
        )
        db.add(plan)
        plans.append(plan)

    db.commit()
    for p in plans:
        db.refresh(p)
    return plans

"""Performance prediction: feature extraction from the DB + model inference.

Predictions are *estimates* with an uncertainty range, never a guarantee.
"""
import logging
import threading
from datetime import date, timedelta

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import train
from app.models import AIPrediction, Assignment, Attendance, Grade, StudySession

log = logging.getLogger(__name__)
_bundle: dict | None = None
_lock = threading.Lock()


def ensure_model() -> dict:
    global _bundle
    with _lock:
        if _bundle is None:
            if not train.MODEL_PATH.exists():
                log.info("No trained model found - training baseline model")
                train.train_and_save(verbose=False)
            try:
                _bundle = joblib.load(train.MODEL_PATH)
            except Exception:  # corrupted / incompatible artifact -> retrain
                log.exception("Could not load model; retraining")
                train.train_and_save(verbose=False)
                _bundle = joblib.load(train.MODEL_PATH)
    return _bundle


def model_info() -> dict:
    return ensure_model()["metrics"]


def compute_features(db: Session, user_id: int, course_id: int) -> dict:
    today = date.today()
    grades = db.scalars(
        select(Grade).where(Grade.user_id == user_id, Grade.course_id == course_id).order_by(Grade.graded_on, Grade.grade_id)
    ).all()
    pcts = [g.score / g.max_score * 100 for g in grades]
    weights = [g.weight for g in grades]
    has_grades = bool(grades)
    avg = float(np.average(pcts, weights=weights)) if has_grades else 70.0
    trend = float(np.polyfit(np.arange(len(pcts)), pcts, 1)[0]) if len(pcts) >= 3 else 0.0

    att = db.scalars(
        select(Attendance.status).where(Attendance.user_id == user_id, Attendance.course_id == course_id)
    ).all()
    counted = [s for s in att if s != "excused"]
    attendance_rate = (
        sum(1 if s == "present" else 0.75 if s == "late" else 0 for s in counted) / len(counted) if counted else 0.85
    )

    since = today - timedelta(days=28)
    minutes = sum(db.scalars(
        select(StudySession.duration_minutes).where(
            StudySession.user_id == user_id, StudySession.course_id == course_id, StudySession.session_date >= since
        )
    ).all())
    study_hours = minutes / 60 / 4

    assignments = db.scalars(
        select(Assignment).where(Assignment.user_id == user_id, Assignment.course_id == course_id)
    ).all()
    due = [a for a in assignments if a.due_date <= today] or assignments
    completion = sum(a.status == "completed" for a in due) / len(due) if due else 0.8

    return {
        "avg_score": round(avg, 2),
        "attendance_rate": round(attendance_rate, 3),
        "study_hours_per_week": round(study_hours, 2),
        "completion_rate": round(completion, 3),
        "score_trend": round(float(np.clip(trend, -10, 10)), 3),
        "num_assessments": len(grades),
        "has_grades": has_grades,
        "has_attendance": bool(counted),
    }


def explain(features: dict) -> list[str]:
    drivers = []
    if not features.get("has_grades"):
        drivers.append("No grades recorded yet - estimate is based on defaults and is very uncertain.")
    if features["attendance_rate"] < 0.75:
        drivers.append(f"Attendance is low ({features['attendance_rate'] * 100:.0f}%).")
    if features["study_hours_per_week"] < 3:
        drivers.append(f"Only {features['study_hours_per_week']:.1f} study hours/week logged for this course.")
    if features["completion_rate"] < 0.7:
        drivers.append(f"Assignment completion is {features['completion_rate'] * 100:.0f}%.")
    if features["score_trend"] <= -2:
        drivers.append("Recent scores are trending downward.")
    elif features["score_trend"] >= 2:
        drivers.append("Recent scores are trending upward.")
    if features.get("has_grades") and features["avg_score"] < 60:
        drivers.append(f"Current average is {features['avg_score']:.0f}%.")
    return drivers


def predict(features: dict) -> dict:
    bundle = ensure_model()
    X = pd.DataFrame([[features[f] for f in bundle["features"]]], columns=bundle["features"])
    score = float(np.clip(bundle["model"].predict(X)[0], 0, 100))
    mae = bundle["metrics"]["mae"]
    width = 1.5 * mae
    if features["num_assessments"] < 3:
        width *= 1.6
    if not features.get("has_grades"):
        width += 8
    lower, upper = max(0.0, score - width), min(100.0, score + width)
    risk = "high" if score < 60 else "medium" if score < 72 else "low"
    return {
        "predicted_score": round(score, 1),
        "lower_bound": round(lower, 1),
        "upper_bound": round(upper, 1),
        "risk_level": risk,
        "model_version": bundle["metrics"]["model_version"],
    }


def predict_and_store(db: Session, user_id: int, course_id: int) -> AIPrediction:
    features = compute_features(db, user_id, course_id)
    result = predict(features)
    row = AIPrediction(user_id=user_id, course_id=course_id, features=features, **result)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

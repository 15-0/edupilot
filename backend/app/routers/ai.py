from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.database import get_db
from app.deps import enrolled_course_ids, require_enrolled_course
from app.models import AIPrediction, AIRecommendation, Course, StudyPlan, User
from app.schemas import PredictionOut, RecommendationOut, StudyPlanOut, StudyPlanRequest, TaskToggle
from app.security import get_current_user
from app.services import planner, predictor

router = APIRouter(prefix="/ai", tags=["ai"])


def _names(db: Session) -> dict[int, str]:
    return dict(db.execute(select(Course.course_id, Course.course_name)).all())


def _prediction_out(p: AIPrediction, names: dict[int, str]) -> PredictionOut:
    out = PredictionOut.model_validate(p)
    out.course_name = names.get(p.course_id)
    out.drivers = predictor.explain(p.features)
    return out


@router.get("/status")
def ai_status():
    return {"llm_enabled": settings.llm_enabled, "model": settings.claude_model if settings.llm_enabled else None,
            "embedding_provider": settings.embedding_provider}


@router.get("/model-info")
def model_info(_: User = Depends(get_current_user)):
    return predictor.model_info()


@router.post("/predict", response_model=list[PredictionOut])
def predict(course_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recompute performance estimates (one course, or every enrolled course)."""
    if course_id is not None:
        require_enrolled_course(db, user, course_id)
        ids = [course_id]
    else:
        ids = enrolled_course_ids(db, user.user_id)
    names = _names(db)
    return [_prediction_out(predictor.predict_and_store(db, user.user_id, cid), names) for cid in ids]


@router.get("/predictions", response_model=list[PredictionOut])
def latest_predictions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    latest: dict[int, AIPrediction] = {}
    for p in db.scalars(
        select(AIPrediction).where(AIPrediction.user_id == user.user_id).order_by(AIPrediction.created_at, AIPrediction.prediction_id)
    ):
        latest[p.course_id] = p
    names = _names(db)
    return [_prediction_out(p, names) for p in latest.values()]


@router.get("/predictions/history", response_model=list[PredictionOut])
def prediction_history(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(AIPrediction)
        .where(AIPrediction.user_id == user.user_id, AIPrediction.course_id == course_id)
        .order_by(AIPrediction.created_at, AIPrediction.prediction_id)
    ).all()
    names = _names(db)
    return [_prediction_out(p, names) for p in rows[-30:]]


@router.post("/weak-subjects", response_model=list[RecommendationOut])
def weak_subjects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recs = planner.analyse_weak_subjects(db, user.user_id)
    names = _names(db)
    out = []
    for r in recs:
        o = RecommendationOut.model_validate(r)
        o.course_name = names.get(r.course_id)
        out.append(o)
    return out


@router.get("/recommendations", response_model=list[RecommendationOut])
def recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    names = _names(db)
    out = []
    for r in db.scalars(select(AIRecommendation).where(AIRecommendation.user_id == user.user_id)):
        o = RecommendationOut.model_validate(r)
        o.course_name = names.get(r.course_id)
        out.append(o)
    return out


@router.post("/study-plan", response_model=list[StudyPlanOut])
def create_study_plan(data: StudyPlanRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start = data.start_date or date.today()
    try:
        return planner.generate_week_plan(db, user.user_id, start, data.hours_per_day, data.rest_day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/study-plan", response_model=list[StudyPlanOut])
def get_study_plan(start: date | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start = start or date.today() - timedelta(days=date.today().weekday())
    return db.scalars(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.user_id, StudyPlan.planned_date >= start,
               StudyPlan.planned_date <= start + timedelta(days=13))
        .order_by(StudyPlan.planned_date)
    ).all()


@router.patch("/study-plan/{plan_id}/tasks/{task_id}", response_model=StudyPlanOut)
def toggle_task(plan_id: int, task_id: str, data: TaskToggle,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Study plan not found")
    tasks = [dict(t) for t in plan.tasks]
    for t in tasks:
        if t.get("id") == task_id:
            t["done"] = data.done
            break
    else:
        raise HTTPException(status_code=404, detail="Task not found")
    plan.tasks = tasks
    flag_modified(plan, "tasks")
    db.commit()
    db.refresh(plan)
    return plan

"""CRUD for assignments, grades, attendance and study sessions."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    can_view_student_record,
    get_course_or_404,
    require_enrolled_course,
    resolve_target_student,
)
from app.models import Assignment, Attendance, Course, Grade, StudySession, User
from app.schemas import (
    AssignmentIn,
    AssignmentOut,
    AssignmentUpdate,
    AttendanceIn,
    AttendanceOut,
    AttendanceSummary,
    GradeIn,
    GradeOut,
    GradeUpdate,
    StudySessionIn,
    StudySessionOut,
)
from app.security import get_current_user
from app.services import predictor

router = APIRouter(tags=["academics"])


def _course_names(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(db.execute(select(Course.course_id, Course.course_name).where(Course.course_id.in_(ids))).all())


def _student_scope(db: Session, user: User, course_id: int | None, student_id: int | None) -> int:
    """Whose records to list: self by default, or a student in a course the caller manages."""
    if student_id is None or student_id == user.user_id:
        return user.user_id
    if course_id is None:
        raise HTTPException(status_code=400, detail="course_id is required when viewing another student's records")
    get_course_or_404(db, course_id)
    if not can_view_student_record(db, user, student_id, course_id):
        raise HTTPException(status_code=403, detail="Not allowed to view this student's records")
    return student_id


# ------------------------------------------------------------------ Assignments
def _assignment_out(a: Assignment, names: dict[int, str]) -> AssignmentOut:
    out = AssignmentOut.model_validate(a)
    out.course_name = names.get(a.course_id)
    out.is_overdue = a.status != "completed" and a.due_date < date.today()
    return out


def _own_assignment(db: Session, user: User, assignment_id: int) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None or a.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(
    course_id: int | None = None,
    status: str | None = Query(default=None, pattern="^(pending|in_progress|completed)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(Assignment).where(Assignment.user_id == user.user_id)
    if course_id is not None:
        q = q.where(Assignment.course_id == course_id)
    if status:
        q = q.where(Assignment.status == status)
    items = db.scalars(q.order_by(Assignment.due_date, Assignment.assignment_id)).all()
    names = _course_names(db, {a.course_id for a in items})
    return [_assignment_out(a, names) for a in items]


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(data: AssignmentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_enrolled_course(db, user, data.course_id)
    a = Assignment(**data.model_dump(), user_id=user.user_id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _assignment_out(a, _course_names(db, {a.course_id}))


@router.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: int, data: AssignmentUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    a = _own_assignment(db, user, assignment_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None and key in ("title", "due_date", "status", "priority"):
            continue
        setattr(a, key, value)
    db.commit()
    db.refresh(a)
    return _assignment_out(a, _course_names(db, {a.course_id}))


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own_assignment(db, user, assignment_id))
    db.commit()


# ------------------------------------------------------------------ Grades
def _grade_out(g: Grade, names: dict[int, str]) -> GradeOut:
    out = GradeOut.model_validate(g)
    out.course_name = names.get(g.course_id)
    out.percentage = round(g.score / g.max_score * 100, 2)
    return out


def _editable_grade(db: Session, user: User, grade_id: int) -> Grade:
    g = db.get(Grade, grade_id)
    if g is None or not can_view_student_record(db, user, g.user_id, g.course_id):
        raise HTTPException(status_code=404, detail="Grade not found")
    return g


@router.get("/grades", response_model=list[GradeOut])
def list_grades(
    course_id: int | None = None,
    student_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = _student_scope(db, user, course_id, student_id)
    q = select(Grade).where(Grade.user_id == owner)
    if course_id is not None:
        q = q.where(Grade.course_id == course_id)
    items = db.scalars(q.order_by(Grade.graded_on, Grade.grade_id)).all()
    names = _course_names(db, {g.course_id for g in items})
    return [_grade_out(g, names) for g in items]


@router.post("/grades", response_model=GradeOut, status_code=201)
def create_grade(data: GradeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owner = resolve_target_student(db, user, data.course_id, data.student_id)
    payload = data.model_dump(exclude={"student_id"})
    payload["graded_on"] = payload["graded_on"] or date.today()
    g = Grade(**payload, user_id=owner)
    db.add(g)
    db.commit()
    db.refresh(g)
    # New academic data -> refresh the performance estimate for this course
    predictor.predict_and_store(db, owner, g.course_id)
    return _grade_out(g, _course_names(db, {g.course_id}))


@router.patch("/grades/{grade_id}", response_model=GradeOut)
def update_grade(grade_id: int, data: GradeUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g = _editable_grade(db, user, grade_id)
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    score = changes.get("score", g.score)
    max_score = changes.get("max_score", g.max_score)
    if score > max_score:
        raise HTTPException(status_code=422, detail="score cannot be greater than max_score")
    for key, value in changes.items():
        setattr(g, key, value)
    db.commit()
    db.refresh(g)
    predictor.predict_and_store(db, g.user_id, g.course_id)
    return _grade_out(g, _course_names(db, {g.course_id}))


@router.delete("/grades/{grade_id}", status_code=204)
def delete_grade(grade_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g = _editable_grade(db, user, grade_id)
    db.delete(g)
    db.commit()


# ------------------------------------------------------------------ Attendance
@router.get("/attendance", response_model=list[AttendanceOut])
def list_attendance(
    course_id: int | None = None,
    student_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = _student_scope(db, user, course_id, student_id)
    q = select(Attendance).where(Attendance.user_id == owner)
    if course_id is not None:
        q = q.where(Attendance.course_id == course_id)
    items = db.scalars(q.order_by(Attendance.attendance_date.desc())).all()
    names = _course_names(db, {a.course_id for a in items})
    out = []
    for a in items:
        o = AttendanceOut.model_validate(a)
        o.course_name = names.get(a.course_id)
        out.append(o)
    return out


@router.post("/attendance", response_model=AttendanceOut, status_code=201)
def mark_attendance(data: AttendanceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create or update the attendance record for that student/course/day."""
    owner = resolve_target_student(db, user, data.course_id, data.student_id)
    rec = db.scalar(
        select(Attendance).where(
            Attendance.user_id == owner,
            Attendance.course_id == data.course_id,
            Attendance.attendance_date == data.attendance_date,
        )
    )
    if rec is None:
        rec = Attendance(
            user_id=owner, course_id=data.course_id, attendance_date=data.attendance_date, status=data.status
        )
        db.add(rec)
    else:
        rec.status = data.status
    db.commit()
    db.refresh(rec)
    out = AttendanceOut.model_validate(rec)
    out.course_name = _course_names(db, {rec.course_id}).get(rec.course_id)
    return out


@router.delete("/attendance/{attendance_id}", status_code=204)
def delete_attendance(attendance_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = db.get(Attendance, attendance_id)
    if rec is None or not can_view_student_record(db, user, rec.user_id, rec.course_id):
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.delete(rec)
    db.commit()


@router.get("/attendance/summary", response_model=list[AttendanceSummary])
def attendance_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Attendance.course_id, Attendance.status).where(Attendance.user_id == user.user_id)
    ).all()
    names = _course_names(db, {r.course_id for r in rows})
    agg: dict[int, dict[str, int]] = {}
    for r in rows:
        agg.setdefault(r.course_id, {"present": 0, "absent": 0, "late": 0, "excused": 0})[r.status] += 1
    result = []
    for cid, c in agg.items():
        counted = c["present"] + c["absent"] + c["late"]
        rate = round((c["present"] + 0.75 * c["late"]) / counted * 100, 1) if counted else None
        result.append(AttendanceSummary(course_id=cid, course_name=names.get(cid, "?"), rate=rate, **c))
    return sorted(result, key=lambda s: s.course_name)


# ------------------------------------------------------------------ Study sessions
@router.get("/study-sessions", response_model=list[StudySessionOut])
def list_sessions(
    course_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(StudySession).where(StudySession.user_id == user.user_id)
    if course_id is not None:
        q = q.where(StudySession.course_id == course_id)
    if start:
        q = q.where(StudySession.session_date >= start)
    if end:
        q = q.where(StudySession.session_date <= end)
    items = db.scalars(q.order_by(StudySession.session_date.desc(), StudySession.session_id.desc())).all()
    names = _course_names(db, {s.course_id for s in items if s.course_id})
    out = []
    for s in items:
        o = StudySessionOut.model_validate(s)
        o.course_name = names.get(s.course_id) if s.course_id else None
        out.append(o)
    return out


@router.post("/study-sessions", response_model=StudySessionOut, status_code=201)
def log_session(data: StudySessionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.course_id is not None:
        require_enrolled_course(db, user, data.course_id)
    s = StudySession(**data.model_dump(exclude={"session_date"}), user_id=user.user_id,
                     session_date=data.session_date or date.today())
    db.add(s)
    db.commit()
    db.refresh(s)
    o = StudySessionOut.model_validate(s)
    o.course_name = _course_names(db, {s.course_id}).get(s.course_id) if s.course_id else None
    return o


@router.delete("/study-sessions/{session_id}", status_code=204)
def delete_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(StudySession, session_id)
    if s is None or s.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Study session not found")
    db.delete(s)
    db.commit()

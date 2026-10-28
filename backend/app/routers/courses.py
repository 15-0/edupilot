from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import can_manage_course, get_course_or_404, is_enrolled
from app.models import Course, Enrollment, User
from app.schemas import CourseIn, CourseOut, CourseUpdate, UserOut
from app.security import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])


def _to_out(db: Session, course: Course, user: User) -> CourseOut:
    out = CourseOut.model_validate(course)
    out.instructor_name = course.instructor.name if course.instructor else None
    out.enrolled = is_enrolled(db, user.user_id, course.course_id)
    out.can_manage = can_manage_course(user, course)
    out.student_count = db.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.course_id == course.course_id)
    ) or 0
    return out


@router.get("", response_model=list[CourseOut])
def my_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Courses the user is enrolled in or teaches."""
    enrolled = select(Enrollment.course_id).where(Enrollment.user_id == user.user_id)
    courses = db.scalars(
        select(Course)
        .where((Course.course_id.in_(enrolled)) | (Course.instructor_id == user.user_id))
        .order_by(Course.course_name)
    ).all()
    return [_to_out(db, c, user) for c in courses]


@router.get("/catalog", response_model=list[CourseOut])
def catalog(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    courses = db.scalars(select(Course).order_by(Course.course_name)).all()
    return [_to_out(db, c, user) for c in courses]


@router.post("", response_model=CourseOut, status_code=201)
def create_course(data: CourseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = Course(
        **data.model_dump(),
        created_by=user.user_id,
        instructor_id=user.user_id if user.role in ("instructor", "admin") else None,
    )
    db.add(course)
    db.flush()
    if user.role != "instructor":  # students (and admins tracking their own studies) take the course they create
        db.add(Enrollment(user_id=user.user_id, course_id=course.course_id, enrollment_date=date.today()))
    db.commit()
    db.refresh(course)
    return _to_out(db, course, user)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _to_out(db, get_course_or_404(db, course_id), user)


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int, data: CourseUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    course = get_course_or_404(db, course_id)
    if not can_manage_course(user, course):
        raise HTTPException(status_code=403, detail="Only the course owner can edit it")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(course, key, value)
    db.commit()
    db.refresh(course)
    return _to_out(db, course, user)


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = get_course_or_404(db, course_id)
    if not can_manage_course(user, course):
        raise HTTPException(status_code=403, detail="Only the course owner can delete it")
    db.delete(course)
    db.commit()


@router.post("/{course_id}/enroll", response_model=CourseOut)
def enroll(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = get_course_or_404(db, course_id)
    if not is_enrolled(db, user.user_id, course_id):
        db.add(Enrollment(user_id=user.user_id, course_id=course_id, enrollment_date=date.today()))
        db.commit()
    return _to_out(db, course, user)


@router.delete("/{course_id}/enroll", status_code=204)
def unenroll(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enrollment = db.get(Enrollment, (user.user_id, course_id))
    if enrollment is None:
        raise HTTPException(status_code=404, detail="You are not enrolled in this course")
    db.delete(enrollment)
    db.commit()


@router.get("/{course_id}/students", response_model=list[UserOut])
def course_students(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = get_course_or_404(db, course_id)
    if not can_manage_course(user, course):
        raise HTTPException(status_code=403, detail="Only the course instructor can view the roster")
    return db.scalars(
        select(User).join(Enrollment, Enrollment.user_id == User.user_id).where(Enrollment.course_id == course_id)
    ).all()

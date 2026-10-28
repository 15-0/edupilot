"""Shared access-control helpers for routers."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, User


def get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def is_enrolled(db: Session, user_id: int, course_id: int) -> bool:
    return db.get(Enrollment, (user_id, course_id)) is not None


def can_manage_course(user: User, course: Course) -> bool:
    return user.role == "admin" or course.instructor_id == user.user_id or course.created_by == user.user_id


def require_enrolled_course(db: Session, user: User, course_id: int) -> Course:
    course = get_course_or_404(db, course_id)
    if not is_enrolled(db, user.user_id, course_id) and not can_manage_course(user, course):
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")
    return course


def resolve_target_student(db: Session, user: User, course_id: int, student_id: int | None) -> int:
    """Return whose record is being written.

    Students write their own records. Instructors/admins may write records for students
    enrolled in a course they manage.
    """
    course = get_course_or_404(db, course_id)
    if student_id is None or student_id == user.user_id:
        if not is_enrolled(db, user.user_id, course_id):
            raise HTTPException(status_code=403, detail="You are not enrolled in this course")
        return user.user_id
    if user.role not in ("instructor", "admin") or not can_manage_course(user, course):
        raise HTTPException(status_code=403, detail="Only the course instructor can record data for other students")
    if not is_enrolled(db, student_id, course_id):
        raise HTTPException(status_code=400, detail="That student is not enrolled in this course")
    return student_id


def can_view_student_record(db: Session, user: User, owner_id: int, course_id: int) -> bool:
    if user.user_id == owner_id or user.role == "admin":
        return True
    course = db.get(Course, course_id)
    return course is not None and user.role == "instructor" and can_manage_course(user, course)


def enrolled_course_ids(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(Enrollment.course_id).where(Enrollment.user_id == user_id)))

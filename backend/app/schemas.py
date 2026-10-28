from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Role = Literal["student", "instructor", "admin"]
AssignmentStatus = Literal["pending", "in_progress", "completed"]
Priority = Literal["low", "medium", "high"]
AssessmentType = Literal["quiz", "assignment", "midterm", "final", "project", "lab", "other"]
AttendanceStatus = Literal["present", "absent", "late", "excused"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["student", "instructor"] = "student"

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORM):
    user_id: int
    name: str
    email: str
    role: Role
    created_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class RoleUpdate(BaseModel):
    role: Role


# ---------- Courses ----------
class CourseIn(BaseModel):
    course_name: str = Field(min_length=1, max_length=150)
    course_code: str | None = Field(default=None, max_length=30)
    semester: str | None = Field(default=None, max_length=40)
    credits: int = Field(default=3, ge=1, le=30)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)


class CourseUpdate(BaseModel):
    course_name: str | None = Field(default=None, min_length=1, max_length=150)
    course_code: str | None = Field(default=None, max_length=30)
    semester: str | None = Field(default=None, max_length=40)
    credits: int | None = Field(default=None, ge=1, le=30)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)


class CourseOut(ORM):
    course_id: int
    course_name: str
    course_code: str | None
    semester: str | None
    credits: int
    description: str | None
    color: str | None
    instructor_id: int | None
    created_by: int | None
    instructor_name: str | None = None
    enrolled: bool = False
    can_manage: bool = False
    student_count: int = 0


# ---------- Assignments ----------
class AssignmentIn(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date
    status: AssignmentStatus = "pending"
    priority: Priority = "medium"


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: AssignmentStatus | None = None
    priority: Priority | None = None


class AssignmentOut(ORM):
    assignment_id: int
    course_id: int
    course_name: str | None = None
    title: str
    description: str | None
    due_date: date
    status: AssignmentStatus
    priority: Priority
    is_overdue: bool = False


# ---------- Grades ----------
class GradeIn(BaseModel):
    course_id: int
    student_id: int | None = None  # instructors may grade an enrolled student
    assessment_type: AssessmentType
    title: str = Field(min_length=1, max_length=200)
    score: float = Field(ge=0)
    max_score: float = Field(default=100, gt=0)
    weight: float = Field(default=1, gt=0, le=100)
    graded_on: date | None = None

    @model_validator(mode="after")
    def score_within_max(self):
        if self.score > self.max_score:
            raise ValueError("score cannot be greater than max_score")
        return self


class GradeUpdate(BaseModel):
    assessment_type: AssessmentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0, le=100)
    graded_on: date | None = None


class GradeOut(ORM):
    grade_id: int
    user_id: int
    course_id: int
    course_name: str | None = None
    assessment_type: AssessmentType
    title: str
    score: float
    max_score: float
    weight: float
    percentage: float = 0
    graded_on: date


# ---------- Attendance ----------
class AttendanceIn(BaseModel):
    course_id: int
    student_id: int | None = None
    attendance_date: date
    status: AttendanceStatus


class AttendanceOut(ORM):
    attendance_id: int
    user_id: int
    course_id: int
    course_name: str | None = None
    attendance_date: date
    status: AttendanceStatus


class AttendanceSummary(BaseModel):
    course_id: int
    course_name: str
    present: int
    absent: int
    late: int
    excused: int
    rate: float | None


# ---------- Study sessions ----------
class StudySessionIn(BaseModel):
    course_id: int | None = None
    duration_minutes: int = Field(gt=0, le=1440)
    topic: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    session_date: date | None = None


class StudySessionOut(ORM):
    session_id: int
    course_id: int | None
    course_name: str | None = None
    duration_minutes: int
    topic: str | None
    notes: str | None
    session_date: date


# ---------- AI ----------
class PredictionOut(ORM):
    prediction_id: int
    course_id: int
    course_name: str | None = None
    predicted_score: float
    lower_bound: float
    upper_bound: float
    risk_level: Priority
    features: dict
    model_version: str
    created_at: datetime | None = None
    drivers: list[str] = []


class StudyPlanRequest(BaseModel):
    start_date: date | None = None
    hours_per_day: float = Field(default=2.0, gt=0, le=12)
    rest_day: int | None = Field(default=6, ge=0, le=6, description="0=Mon ... 6=Sun; lighter day")


class StudyPlanOut(ORM):
    plan_id: int
    planned_date: date
    title: str
    tasks: list[dict]


class TaskToggle(BaseModel):
    done: bool


class RecommendationOut(ORM):
    recommendation_id: int
    course_id: int
    course_name: str | None = None
    reason: str
    topics: list[str]
    priority: Priority
    source: str
    created_at: datetime | None = None


# ---------- Documents ----------
class DocumentOut(ORM):
    document_id: int
    course_id: int | None
    filename: str
    file_size: int
    page_count: int
    chunk_count: int
    upload_date: datetime | None = None


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[int] | None = None
    course_id: int | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class ChatSource(BaseModel):
    ref: int
    document_id: int
    filename: str
    page_number: int | None
    snippet: str
    score: float


class ChatOut(BaseModel):
    answer: str
    mode: Literal["llm", "extractive", "empty"]
    sources: list[ChatSource]

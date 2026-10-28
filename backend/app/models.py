from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")

if settings.is_postgres:
    from pgvector.sqlalchemy import Vector

    EmbeddingType = Vector(settings.embedding_dim)
else:  # SQLite fallback for local runs/tests: store the vector as a JSON array
    EmbeddingType = JSON()


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student','instructor','admin')", name="ck_users_role"),)

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student", server_default="student")
    created_at: Mapped[datetime] = _created_at()


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (CheckConstraint("credits > 0 AND credits <= 30", name="ck_courses_credits"),)

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_name: Mapped[str] = mapped_column(String(150), nullable=False)
    course_code: Mapped[str | None] = mapped_column(String(30))
    semester: Mapped[str | None] = mapped_column(String(40))
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(20))
    instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created_at()

    instructor: Mapped["User | None"] = relationship(foreign_keys=[instructor_id])


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (Index("ix_enrollments_course", "course_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), primary_key=True)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("status IN ('pending','in_progress','completed')", name="ck_assignments_status"),
        CheckConstraint("priority IN ('low','medium','high')", name="ck_assignments_priority"),
        Index("ix_assignments_user_due", "user_id", "due_date"),
    )

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium", server_default="medium")
    created_at: Mapped[datetime] = _created_at()

    course: Mapped[Course] = relationship()


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (
        CheckConstraint(
            "assessment_type IN ('quiz','assignment','midterm','final','project','lab','other')",
            name="ck_grades_type",
        ),
        CheckConstraint("max_score > 0", name="ck_grades_max_positive"),
        CheckConstraint("score >= 0 AND score <= max_score", name="ck_grades_score_range"),
        CheckConstraint("weight > 0", name="ck_grades_weight_positive"),
        Index("ix_grades_user_course", "user_id", "course_id"),
    )

    grade_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100, server_default="100")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1, server_default="1")
    graded_on: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    created_at: Mapped[datetime] = _created_at()

    course: Mapped[Course] = relationship()


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        CheckConstraint("status IN ('present','absent','late','excused')", name="ck_attendance_status"),
        UniqueConstraint("user_id", "course_id", "attendance_date", name="uq_attendance_day"),
    )

    attendance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0 AND duration_minutes <= 1440", name="ck_sessions_duration"),
        Index("ix_sessions_user_date", "user_id", "session_date"),
    )

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.course_id", ondelete="SET NULL"))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class AIPrediction(Base):
    __tablename__ = "ai_predictions"
    __table_args__ = (
        CheckConstraint("predicted_score >= 0 AND predicted_score <= 100", name="ck_predictions_range"),
        CheckConstraint("risk_level IN ('low','medium','high')", name="ck_predictions_risk"),
        Index("ix_predictions_user_course_time", "user_id", "course_id", "created_at"),
    )

    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    predicted_score: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    features: Mapped[dict] = mapped_column(JSONType, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    __table_args__ = (
        CheckConstraint("priority IN ('low','medium','high')", name="ck_recommendations_priority"),
        Index("ix_recommendations_user", "user_id"),
    )

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    topics: Mapped[list] = mapped_column(JSONType, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="rules", server_default="rules")
    created_at: Mapped[datetime] = _created_at()


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (UniqueConstraint("user_id", "planned_date", name="uq_study_plan_day"),)

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.course_id", ondelete="SET NULL"))
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tasks: Mapped[list] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_user", "user_id"),)

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.course_id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    upload_date: Mapped[datetime] = _created_at()

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


_chunk_args: tuple = (UniqueConstraint("document_id", "chunk_index", name="uq_chunk_position"),)
if settings.is_postgres:
    _chunk_args += (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = _chunk_args

    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(EmbeddingType, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")

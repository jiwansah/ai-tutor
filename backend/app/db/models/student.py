import uuid
from sqlalchemy import String, Float, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampMixin

class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    preferred_style: Mapped[str] = mapped_column(String(30), default="step_by_step")
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_time_minutes: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="student_profile")
    mastery = relationship("ConceptMastery", back_populates="student", cascade="all, delete-orphan")

class ConceptMastery(Base, TimestampMixin):
    __tablename__ = "concept_mastery"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_profiles.id"), index=True)
    concept_key: Mapped[str] = mapped_column(String(120), index=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed: Mapped[str | None] = mapped_column(String(50))
    next_review: Mapped[str | None] = mapped_column(String(50))
    misconceptions: Mapped[dict] = mapped_column(JSON, default=dict)

    student = relationship("StudentProfile", back_populates="mastery")
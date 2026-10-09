import uuid
from sqlalchemy import String, ForeignKey, JSON, Integer, Float, Date, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampMixin


class AnalyticsEvent(Base, TimestampMixin):
    """
    Privacy-safe event stream.
    - No free-form text
    - No PII
    - Only IDs, enums, timestamps, and safe numeric measures
    """
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who (IDs only — never joined back to PII)
    student_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    school_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    class_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # What
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    # e.g. question_asked, answer_verified, mode_used, diagnostic_triggered,
    #      prerequisite_flagged, session_started, session_ended

    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    concept_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    # Safe measures (never raw text)
    mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    was_verified: Mapped[bool | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


class DailyRollup(Base, TimestampMixin):
    """Pre-aggregated daily metrics per school for fast dashboards."""
    __tablename__ = "analytics_daily_rollups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day: Mapped[str] = mapped_column(String(10), index=True)      # "2026-10-07"
    school_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    class_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Aggregated numbers
    active_students: Mapped[int] = mapped_column(Integer, default=0)
    sessions_started: Mapped[int] = mapped_column(Integer, default=0)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    answers_correct: Mapped[int] = mapped_column(Integer, default=0)
    answers_verified: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Distribution (counts per mode)
    mode_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    top_concepts: Mapped[list] = mapped_column(JSON, default=list)   # [{concept, count}]
    weak_concepts: Mapped[list] = mapped_column(JSON, default=list)  # [{concept, avg_mastery}]


Index("ix_analytics_events_type_day", AnalyticsEvent.event_type, AnalyticsEvent.created_at)

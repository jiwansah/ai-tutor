import uuid
from sqlalchemy import String, ForeignKey, Integer, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base, TimestampMixin


class IngestJob(Base, TimestampMixin):
    """
    One PDF upload. Tracks parsing progress and holds the parsed
    structure (chapters/sections/chunks) until the teacher approves it.
    """
    __tablename__ = "ingest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"), index=True)

    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))    # where PDF is stored on disk
    file_size_kb: Mapped[int] = mapped_column(Integer, default=0)

    # pending | parsing | preview_ready | approved | failed
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)   # 0-100
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    page_count: Mapped[int] = mapped_column(Integer, default=0)

    # Parsed structure — editable by the teacher before approval.
    # Shape: {"chapters": [{"number": 4, "title": "...", "sections": [...]}]}
    parsed_data: Mapped[dict] = mapped_column(JSON, default=dict)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

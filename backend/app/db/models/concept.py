import uuid
from sqlalchemy import String, ForeignKey, Text, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampMixin


class Concept(Base, TimestampMixin):
    """A single learning objective (may span sections)."""
    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id"), nullable=True, index=True
    )
    learning_objectives: Mapped[list] = mapped_column(JSON, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class ConceptPrerequisite(Base, TimestampMixin):
    """Edge in the concept graph: concept_id requires prerequisite_id."""
    __tablename__ = "concept_prerequisites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id"), index=True)
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id"), index=True)
    strength: Mapped[str] = mapped_column(String(20), default="required")  # required | helpful

    __table_args__ = (
        UniqueConstraint("concept_id", "prerequisite_id", name="uq_concept_prereq"),
    )


class ConceptMisconception(Base, TimestampMixin):
    """Common wrong mental models for a concept."""
    __tablename__ = "concept_misconceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id"), index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remedy: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

import uuid
from sqlalchemy import String, ForeignKey, Text, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base, TimestampMixin


class Concept(Base, TimestampMixin):
    """
    A learning objective.

    Scope:
      - class_id + subject_id set  → class-specific concept (e.g., photosynthesis in Class 7 Science)
      - subject_id only            → subject-wide concept (e.g., reading comprehension in English)
      - both NULL                  → global concept (e.g., inverse operations, critical thinking)
    """
    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scope — both nullable for cross-grade concepts
    class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("classes.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # Optional: which section shows this concept by default
    primary_section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )

    learning_objectives: Mapped[list] = mapped_column(JSON, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class ConceptPrerequisite(Base, TimestampMixin):
    __tablename__ = "concept_prerequisites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    strength: Mapped[str] = mapped_column(String(20), default="required")

    __table_args__ = (
        UniqueConstraint("concept_id", "prerequisite_id", name="uq_concept_prereq"),
    )


class ConceptMisconception(Base, TimestampMixin):
    __tablename__ = "concept_misconceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remedy: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

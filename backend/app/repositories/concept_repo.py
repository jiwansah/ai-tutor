from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.concept import Concept, ConceptPrerequisite, ConceptMisconception


class ConceptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_key(self, key: str) -> Concept | None:
        return (await self.db.execute(
            select(Concept).where(Concept.key == key)
        )).scalar_one_or_none()

    async def get_by_id(self, concept_id) -> Concept | None:
        return (await self.db.execute(
            select(Concept).where(Concept.id == concept_id)
        )).scalar_one_or_none()

    async def get_for_section(self, section_id) -> Concept | None:
        return (await self.db.execute(
            select(Concept).where(Concept.primary_section_id == section_id)
        )).scalar_one_or_none()

    async def list_for_scope(
        self,
        class_id: str | None = None,
        subject_id: str | None = None,
        include_global: bool = True,
    ) -> list[Concept]:
        """
        List concepts for a class/subject scope.
        By default also includes global concepts (both NULL).
        """
        stmt = select(Concept).order_by(Concept.order_index, Concept.name)

        if class_id or subject_id:
            conditions = []
            if class_id:
                conditions.append(Concept.class_id == class_id)
            if subject_id:
                conditions.append(Concept.subject_id == subject_id)
            if include_global:
                conditions.append(
                    (Concept.class_id.is_(None)) & (Concept.subject_id.is_(None))
                )
            stmt = stmt.where(or_(*conditions))

        return list((await self.db.execute(stmt)).scalars().all())

    async def get_prerequisites(self, concept_id) -> list[Concept]:
        stmt = (
            select(Concept)
            .join(ConceptPrerequisite, ConceptPrerequisite.prerequisite_id == Concept.id)
            .where(ConceptPrerequisite.concept_id == concept_id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_misconceptions(self, concept_id) -> list[ConceptMisconception]:
        stmt = (
            select(ConceptMisconception)
            .where(ConceptMisconception.concept_id == concept_id)
            .order_by(ConceptMisconception.order_index)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_all(self) -> list[Concept]:
        stmt = select(Concept).order_by(Concept.order_index, Concept.name)
        return list((await self.db.execute(stmt)).scalars().all())

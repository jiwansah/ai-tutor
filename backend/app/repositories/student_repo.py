from sqlalchemy import select
from app.db.models.student import ConceptMastery, StudentProfile
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[StudentProfile]):
    model = StudentProfile

    async def get_mastery(self, student_id, concept_key: str) -> ConceptMastery | None:
        return (await self.db.execute(
            select(ConceptMastery).where(
                ConceptMastery.student_id == student_id,
                ConceptMastery.concept_key == concept_key,
            )
        )).scalar_one_or_none()

    async def upsert_mastery(
        self,
        student_id,
        concept_key: str,
        mastery: float,
        is_correct: bool,
    ) -> ConceptMastery:
        row = await self.get_mastery(student_id, concept_key)
        if row:
            row.mastery = mastery
            row.attempts += 1
            row.correct += int(is_correct)
        else:
            row = ConceptMastery(
                student_id=student_id,
                concept_key=concept_key,
                mastery=mastery,
                attempts=1,
                correct=int(is_correct),
            )
            self.db.add(row)
        await self.db.flush()
        return row

    async def weak_areas(self, student_id, threshold: float = 0.6, limit: int = 20):
        return list((await self.db.execute(
            select(ConceptMastery)
            .where(ConceptMastery.student_id == student_id, ConceptMastery.mastery < threshold)
            .order_by(ConceptMastery.mastery.asc())
            .limit(limit)
        )).scalars().all())
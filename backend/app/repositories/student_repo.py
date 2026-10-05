from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.student import ConceptMastery, StudentProfile


class StudentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile_by_user(self, user_id) -> StudentProfile | None:
        return (await self.db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )).scalar_one_or_none()

    async def get_mastery(self, student_id, concept_key):
        return (await self.db.execute(
            select(ConceptMastery).where(
                ConceptMastery.student_id == student_id,
                ConceptMastery.concept_key == concept_key,
            )
        )).scalar_one_or_none()

    async def upsert_mastery(self, student_id, concept_key, mastery, is_correct):
        row = await self.get_mastery(student_id, concept_key)
        if row:
            row.mastery = mastery
            row.attempts += 1
            row.correct += int(is_correct)
        else:
            row = ConceptMastery(student_id=student_id, concept_key=concept_key,
                                 mastery=mastery, attempts=1, correct=int(is_correct))
            self.db.add(row)
        await self.db.flush()
        return row

    async def weak_areas(self, student_id, threshold=0.6, limit=20):
        return list((await self.db.execute(
            select(ConceptMastery)
            .where(ConceptMastery.student_id == student_id, ConceptMastery.mastery < threshold)
            .order_by(ConceptMastery.mastery.asc())
            .limit(limit)
        )).scalars().all())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.orchestrator import TutorContext
from app.db.models.student import ConceptMastery


async def diagnose(db: AsyncSession, ctx: TutorContext, question: str) -> dict:
    """
    Identify concept from question + fetch current mastery.
    In production: use LLM classifier against concept graph.
    Here: infer concept_key from section_id.
    """
    concept_key = ctx.concept_key or (f"section:{ctx.section_id}" if ctx.section_id else None)

    mastery = 0.0
    if concept_key:
        stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == ctx.student_id,
            ConceptMastery.concept_key == concept_key,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            mastery = row.mastery

    return {
        "concept_key": concept_key,
        "mastery": mastery,
        "readiness": "low" if mastery < 0.4 else "medium" if mastery < 0.7 else "high",
    }
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import current_user
from app.db.models.user import User
from app.db.models.student import ConceptMastery
from app.db.models.session import Attempt

router = APIRouter()


@router.get("/me/progress")
async def my_progress(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ConceptMastery).where(
        ConceptMastery.student_id == user.student_profile.id
    ).order_by(ConceptMastery.mastery.asc()).limit(20)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "student_id": str(user.id),
        "weak_areas": [
            {"concept": r.concept_key, "mastery": r.mastery, "attempts": r.attempts}
            for r in rows if r.mastery < 0.6
        ],
        "all": [
            {"concept": r.concept_key, "mastery": r.mastery, "attempts": r.attempts}
            for r in rows
        ],
    }
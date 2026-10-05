from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.v1.tutor import current_user
from app.db.models.user import User
from app.repositories.student_repo import StudentRepository

router = APIRouter()


@router.get("/me/progress")
async def my_progress(user: User = Depends(current_user),
                      db: AsyncSession = Depends(get_db)):
    profile = await StudentRepository(db).get_profile_by_user(user.id)
    if not profile:
        return {"weak_areas": [], "all": []}
    rows = await StudentRepository(db).weak_areas(profile.id, threshold=1.0, limit=50)
    return {
        "student_id": str(user.id),
        "weak_areas": [{"concept": r.concept_key, "mastery": r.mastery, "attempts": r.attempts}
                       for r in rows if r.mastery < 0.6],
        "all": [{"concept": r.concept_key, "mastery": r.mastery, "attempts": r.attempts} for r in rows],
    }

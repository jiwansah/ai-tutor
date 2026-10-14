from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.tutor import current_user
from app.db.models.user import User
from app.db.models.curriculum import Chapter
from app.repositories.student_repo import StudentRepository

router = APIRouter()


@router.get("/me/progress")
async def my_progress(user: User = Depends(current_user),
                      db: AsyncSession = Depends(get_db)):
    profile = await StudentRepository(db).get_profile_by_user(user.id)
    if not profile:
        return {"weak_areas": [], "all": []}

    rows = await StudentRepository(db).weak_areas(profile.id, threshold=1.0, limit=50)

    # Collect all chapter UUIDs so we can resolve them in one query
    chapter_ids = []
    for r in rows:
        if r.concept_key and r.concept_key.startswith("chapter:"):
            cid = r.concept_key.split(":", 1)[1]
            chapter_ids.append(cid)

    chapter_titles: dict[str, str] = {}
    if chapter_ids:
        chapters = (await db.execute(
            select(Chapter.id, Chapter.title).where(Chapter.id.in_(chapter_ids))
        )).all()
        chapter_titles = {str(cid): title for cid, title in chapters}

    def friendly(key: str) -> str:
        if key.startswith("chapter:"):
            cid = key.split(":", 1)[1]
            return chapter_titles.get(cid, key)
        if key.startswith("subject:"):
            return key.split(":", 1)[1]
        return key

    all_items = [
        {
            "concept": friendly(r.concept_key),
            "concept_key": r.concept_key,   # keep the raw key for API callers
            "mastery": r.mastery,
            "attempts": r.attempts,
        }
        for r in rows
    ]

    return {
        "student_id": str(user.id),
        "weak_areas": [x for x in all_items if x["mastery"] < 0.6],
        "all": all_items,
    }
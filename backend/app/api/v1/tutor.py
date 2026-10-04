from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import current_user, get_tutor_service
from app.db.models.user import User
from app.services.tutor_service import TutorService

router = APIRouter()


class AskRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(min_length=1, max_length=2000)
    mode: str = "teacher"
    subject_id: str | None = None
    chapter_id: str | None = None
    section_id: str | None = None


@router.post("/ask")
async def ask(
    payload: AskRequest,
    user: User = Depends(current_user),
    tutor: TutorService = Depends(get_tutor_service),
):
    try:
        return await tutor.ask(
            student_id=user.student_profile.id,
            mode=payload.mode,
            question=payload.question,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            section_id=payload.section_id,
            session_id=payload.session_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
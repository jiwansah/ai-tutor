import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models.user import User
from app.db.session import get_db, AsyncSessionLocal
from app.repositories.student_repo import StudentRepository
from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
from app.services.tutor_service import TutorService, _build_verified_block, _dedupe_citations, GUIDANCE_MODES
from app.services.rag_service import RAGService
from app.services.llm_service import stream_chat
from app.services.safety_service import check_input
from app.services.math_verifier import verify_question, verify_answer
from app.services.conversation import load_history, build_messages

router = APIRouter()
bearer = HTTPBearer(auto_error=True)


async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
    except Exception:
        raise HTTPException(401, "Invalid token")
    user = await UserRepository(db).get(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user


class AskRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(min_length=1, max_length=2000)
    mode: str = "teacher"
    subject_id: str | None = None
    chapter_id: str | None = None
    section_id: str | None = None


class AnswerRequest(BaseModel):
    session_id: str
    question: str
    student_answer: str
    concept_key: str | None = None


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask")
async def ask(
    payload: AskRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await StudentRepository(db).get_profile_by_user(user.id)
    if not student:
        raise HTTPException(400, "Student profile missing")
    svc = TutorService(db)
    try:
        result = await svc.ask(
            student_id=student.id, mode=payload.mode, question=payload.question,
            subject_id=payload.subject_id, chapter_id=payload.chapter_id,
            section_id=payload.section_id, session_id=payload.session_id,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/answer")
async def submit_answer(
    payload: AnswerRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await StudentRepository(db).get_profile_by_user(user.id)
    if not student:
        raise HTTPException(400, "Student profile missing")
    svc = TutorService(db)
    result = await svc.submit_answer(
        student_id=student.id, session_id=payload.session_id,
        question=payload.question, student_answer=payload.student_answer,
        concept_key=payload.concept_key,
    )
    await db.commit()
    return result


@router.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    user: User = Depends(current_user),
):
    safety = await check_input(payload.question)
    if not safety["ok"]:
        raise HTTPException(400, f"Input blocked: {safety.get('reason')}")

    async def event_generator() -> AsyncIterator[str]:
        try:
            async with AsyncSessionLocal() as db:
                student = await StudentRepository(db).get_profile_by_user(user.id)
                if not student:
                    yield sse("error", {"message": "Student profile missing"})
                    return

                sessions = SessionRepository(db)
                session = await sessions.get_or_create(
                    session_id=payload.session_id,
                    student_id=student.id,
                    mode=payload.mode,
                    subject_id=payload.subject_id,
                    chapter_id=payload.chapter_id,
                    section_id=payload.section_id,
                )

                # Load history BEFORE persisting the new user message
                history = await load_history(db, session.id)
                await sessions.add_message(session.id, "user", safety["text"])
                await db.commit()

                yield sse("session", {"session_id": str(session.id)})

                concept_key = f"section:{payload.section_id}" if payload.section_id else None
                mastery = 0.0
                if concept_key:
                    row = await StudentRepository(db).get_mastery(student.id, concept_key)
                    if row:
                        mastery = row.mastery

                rag = RAGService(db)
                chunks = await rag.retrieve(
                    safety["text"],
                    subject_id=payload.subject_id,
                    chapter_id=payload.chapter_id,
                    section_id=payload.section_id,
                    top_k=5,
                )
                context = RAGService.format_context(chunks)

                qv = verify_question(safety["text"])
                verified_block = _build_verified_block(qv, mode=payload.mode)

                if qv.get("is_math"):
                    yield sse("pre_verify", {
                        "equation": qv["equation"],
                        "variable": qv["variable"],
                        "solutions": qv["solutions"],
                    })

                messages = build_messages(
                    mode=payload.mode,
                    history=history,
                    context=context,
                    mastery=mastery,
                    verified_block=verified_block,
                    question=safety["text"],
                    qv=qv,
                )

                full_answer: list[str] = []
                async for token in stream_chat(messages, temperature=0.4, max_tokens=1500):
                    full_answer.append(token)
                    yield sse("token", {"text": token})

                answer_text = "".join(full_answer)

                citations = _dedupe_citations(chunks)
                yield sse("citations", {"citations": citations})

                verification = None
                if qv.get("is_math") and payload.mode not in GUIDANCE_MODES:
                    verification = verify_answer(safety["text"], answer_text)
                    yield sse("verification", verification)

                await sessions.add_message(
                    session.id,
                    "tutor",
                    answer_text,
                    citations=citations,
                    meta={
                        "mode": payload.mode,
                        "concept_key": concept_key,
                        "verification": verification,
                    },
                )
                await db.commit()

                yield sse("done", {})

        except Exception as e:
            yield sse("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

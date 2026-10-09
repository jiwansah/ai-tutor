import json
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models.user import User
from app.db.session import get_db, AsyncSessionLocal
from app.prompts.no_context import get_no_context_prompt
from app.repositories.student_repo import StudentRepository
from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
from app.services.tutor_service import TutorService, _build_verified_block, _dedupe_citations, GUIDANCE_MODES
from app.services.rag_service import RAGService
from app.services.llm_service import stream_chat, complete_chat
from app.services.assessment_generation import generate_assessment
from app.services.safety_service import check_input
from app.services.math_verifier import verify_question, verify_answer
from app.services.conversation import load_history, build_messages
from app.services.concept_graph import (
    resolve_concept_for_section, diagnose, build_diagnostic_block,
)
from app.services.enrollment import enforce_section_access
from app.services import analytics_service as A
from app.services.intent import detect_intent
from app.services.quiz_grader import extract_answer_key
from app.db.models.curriculum import Class as ClassModel
from sqlalchemy import select

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

    # Enrollment check
    await enforce_section_access(db, user, payload.section_id)

    svc = TutorService(db)
    try:
        result = await svc.ask(
            student_id=student.id,
            mode=payload.mode,
            question=payload.question,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            section_id=payload.section_id,
            session_id=payload.session_id,
            school_id=user.school_id,       # <-- pass through
            class_id=user.class_id,         # <-- pass through
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
        student_id=student.id,
        session_id=payload.session_id,
        question=payload.question,
        student_answer=payload.student_answer,
        concept_key=payload.concept_key,
        school_id=user.school_id,
        class_id=user.class_id,
    )
    await db.commit()
    return result


@router.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    user_class_id=None, inner_db=None):

    safety = await check_input(payload.question)
    if payload.mode == "teacher":
        detected = detect_intent(safety["text"])
        effective_mode = detected or "teacher"
    else:
        effective_mode = payload.mode
    grade = None
    if user_class_id:
        grade = (await inner_db.execute(
            select(ClassModel.grade).where(ClassModel.id == user_class_id)
        )).scalar_one_or_none()

    if not safety["ok"]:
        raise HTTPException(400, f"Input blocked: {safety.get('reason')}")

    # Enrollment check before opening the stream
    await enforce_section_access(db, user, payload.section_id)

    # Capture user enrollment now (session may close inside the generator)
    user_school_id = user.school_id
    user_class_id = user.class_id
    user_id = user.id

    async def event_generator() -> AsyncIterator[str]:
        t0 = time.perf_counter()
        try:
            async with AsyncSessionLocal() as inner_db:
                student = await StudentRepository(inner_db).get_profile_by_user(user_id)
                if not student:
                    yield sse("error", {"message": "Student profile missing"})
                    return

                sessions = SessionRepository(inner_db)
                session = await sessions.get_or_create(
                    session_id=payload.session_id,
                    student_id=student.id,
                    mode=payload.mode,
                    subject_id=payload.subject_id,
                    chapter_id=payload.chapter_id,
                    section_id=payload.section_id,
                )

                history = await load_history(inner_db, session.id)
                await sessions.add_message(session.id, "user", safety["text"])
                await inner_db.commit()

                yield sse("session", {"session_id": str(session.id)})

                # Only run diagnostic when the student is explicitly inside a section.
                # Prevents Math prerequisites leaking into Hindi/English/Science questions.
                concept_key = None
                diag = {}

                if payload.section_id:
                    concept_key = await resolve_concept_for_section(inner_db, payload.section_id)
                    if concept_key:
                        diag = await diagnose(inner_db, student.id, concept_key)

                diagnostic_block = build_diagnostic_block(diag) if diag else ""
                mastery = diag.get("mastery", 0.0) if diag else 0.0

                yield sse("diagnostic", diag)

                rag = RAGService(inner_db)
                chunks = await rag.retrieve(
                    safety["text"],
                    subject_id=payload.subject_id,
                    chapter_id=payload.chapter_id,
                    section_id=payload.section_id,
                    class_id=user_class_id,
                    top_k=5,
                )
                context = RAGService.format_context(chunks)

                has_context = len(chunks) > 0
                system_override = None if has_context else get_no_context_prompt(effective_mode, grade)

                # Still emit the SSE event so the frontend can show its banner
                if not has_context:
                    yield sse("no_context", {
                        "message": "Answering from general knowledge — this topic isn't in your textbook yet."
                    })

                qv = verify_question(safety["text"])
                verified_block = _build_verified_block(qv, mode=payload.mode)
                NO_VERIFY_MODES = {"practice", "quiz", "exam"}
                if qv.get("is_math") and effective_mode not in GUIDANCE_MODES and effective_mode not in NO_VERIFY_MODES:
                    yield sse("pre_verify", {
                        "equation": qv["equation"],
                        "variable": qv["variable"],
                        "solutions": qv["solutions"],
                    })

                messages = build_messages(
                    mode=effective_mode,
                    history=history,
                    context=diagnostic_block + context,
                    mastery=mastery,
                    verified_block=verified_block,
                    question=safety["text"],
                    qv=qv,
                    system_override=system_override,
                    class_grade=grade,  # ← NEW
                )

                full_answer: list[str] = []
                assessment_mode = effective_mode in ("quiz", "exam")
                answer_key = {}
                if assessment_mode:
                    # Keep assessment output buffered so the private key cannot leak.
                    answer_text, answer_key = await generate_assessment(messages, mode=effective_mode, max_tokens=1800)
                    yield sse("token", {"text": answer_text})
                else:
                    async for token in stream_chat(messages, temperature=0.4, max_tokens=1800):
                        full_answer.append(token)
                        yield sse("token", {"text": token})
                    answer_text = "".join(full_answer)

                citations = _dedupe_citations(chunks)
                yield sse("citations", {"citations": citations})
                yield sse("mode", {"mode": effective_mode})

                NO_VERIFY_MODES = {"practice", "quiz", "exam"}
                verification = None
                if qv.get("is_math") and effective_mode not in GUIDANCE_MODES and effective_mode not in NO_VERIFY_MODES:
                    verification = verify_answer(safety["text"], answer_text)
                    yield sse("verification", verification)

                awaiting = payload.mode in ("practice", "quiz", "exam")
                await sessions.add_message(
                    session.id,
                    "tutor",
                    answer_text,
                    citations=citations,
                    meta={
                        "mode": effective_mode,
                        "concept_key": concept_key,
                        "verification": verification,
                        "awaiting_answers": awaiting,
                        "answer_key": {str(k): v for k, v in answer_key.items()} if assessment_mode else {},
                    },
                )

                # ---- ANALYTICS ----
                duration_ms = int((time.perf_counter() - t0) * 1000)

                await A.log_event(
                    inner_db,
                    event_type="question_asked",
                    student_id=student.id,
                    school_id=user_school_id,
                    class_id=user_class_id,
                    section_id=payload.section_id,
                    concept_key=concept_key,
                    mode=payload.mode,
                    duration_ms=duration_ms,
                )

                if verification and verification.get("verified") is not None:
                    await A.log_event(
                        inner_db,
                        event_type="answer_evaluated",
                        student_id=student.id,
                        school_id=user_school_id,
                        class_id=user_class_id,
                        concept_key=concept_key,
                        mode=payload.mode,
                        is_correct=verification["verified"],
                        was_verified=verification["verified"],
                    )

                if diag.get("recommendation") == "review_prerequisite":
                    await A.log_event(
                        inner_db,
                        event_type="prerequisite_flagged",
                        student_id=student.id,
                        school_id=user_school_id,
                        class_id=user_class_id,
                        concept_key=concept_key,
                        mode=payload.mode,
                        extra={"prerequisite": diag.get("recommended_prerequisite")},
                    )
                # ---- /ANALYTICS ----

                await inner_db.commit()
                awaiting = effective_mode in ("practice", "quiz", "exam")
                yield sse("done", {"awaiting_answers": awaiting, "effective_mode": effective_mode})

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

import time
import re
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.prompts.no_context import get_no_context_prompt
from app.repositories.session_repo import SessionRepository
from app.repositories.student_repo import StudentRepository
from app.services.rag_service import RAGService
from app.services.llm_service import complete_chat
from app.services.assessment_generation import generate_assessment
from app.services.safety_service import check_input
from app.services.knowledge_tracing import update_mastery
from app.services.spaced_repetition import next_review
from app.services.math_verifier import verify_question, verify_answer
from app.services.conversation import load_history, build_messages
from app.services.concept_graph import diagnose, resolve_concept_for_section, build_diagnostic_block
from app.services import analytics_service as A
from app.services.intent import detect_intent, normalize_mode, is_general_question
from app.services.quiz_grader import extract_answer_key
from app.db.models.curriculum import Class as ClassModel
from sqlalchemy import select
logger = structlog.get_logger()

GUIDANCE_MODES: set[str] = set()


def _is_assessment_followup(question: str, mode: str) -> bool:
    if mode not in {"quiz", "exam"}:
        return False
    q = (question or "").strip().lower()
    if len(q) > 100:
        return False
    return bool(re.search(
        r"\b(more|few more|another|again|continue|next|from this chapter|this chapter|more questions|more quiz|few questions)\b", q
    ))


def _build_retrieval_query(question: str, history: list[dict], mode: str) -> str:
    """Use prior quiz content to retrieve relevant chapter chunks for short follow-ups."""
    if not _is_assessment_followup(question, mode):
        return question
    previous_quiz = ""
    for item in reversed(history):
        if item.get("role") == "assistant" and re.search(
            r"(?im)^\s*(?:\*\*)?(?:question\s+1|q1)\b", item.get("content", "")
        ):
            previous_quiz = item.get("content", "")[:1800]
            break
    previous_user_request = ""
    for item in reversed(history):
        if item.get("role") == "user":
            candidate = (item.get("content") or "").strip()
            if candidate and not _is_assessment_followup(candidate, mode):
                previous_user_request = candidate[:300]
                break
    parts = [question]
    if previous_user_request:
        parts.append("Earlier request: " + previous_user_request)
    if previous_quiz:
        parts.append("Previous chapter quiz for retrieval context (create different questions): " + previous_quiz)
    return "\n".join(parts)


def _build_verified_block(qv: dict, mode: str = "teacher") -> str:
    if mode in GUIDANCE_MODES:
        return ""
    if not qv.get("is_math"):
        return ""
    solutions = ", ".join(qv["solutions"])
    return (
        "VERIFIED SOLUTION (from symbolic math engine — treat as ground truth):\n"
        f"  Equation: {qv['equation']}\n"
        f"  Variable: {qv['variable']}\n"
        f"  Solution: {qv['variable']} = {solutions}\n\n"
    )


def _dedupe_citations(chunks: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for c in chunks:
        key = (c["chapter"], c["section"], c["page"])
        if key not in seen:
            seen.add(key)
            out.append({"chapter": c["chapter"], "section": c["section"], "page": c["page"]})
    return out


class TutorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sessions = SessionRepository(db)
        self.students = StudentRepository(db)
        self.rag = RAGService(db)

    async def ask(
        self,
        *,
        student_id,
        mode,
        question,
        subject_id=None,
        chapter_id=None,
        section_id=None,
        session_id=None,
        school_id=None,
        class_id=None,
    ):
        t0 = time.perf_counter()

        safety = await check_input(question)
        # Collapse legacy mode names into the three supported modes.
        requested_mode = normalize_mode(mode)
        detected = detect_intent(safety["text"])
        # Auto-downgrade: exam/quiz mode but the student asked a normal question.
        # Don't let stale mode selection block a teaching answer.
        if (
                detected is None
                and requested_mode in ("exam", "quiz")
                and is_general_question(safety["text"])
        ):
            effective_mode = "teaching"
        else:
            effective_mode = normalize_mode(detected or requested_mode)
        mode = effective_mode
        grade = None
        if class_id:
            grade = (await self.db.execute(
                select(ClassModel.grade).where(ClassModel.id == class_id)
            )).scalar_one_or_none()

        if not safety["ok"]:
            raise ValueError(f"Input blocked: {safety.get('reason')}")

        session = await self.sessions.get_or_create(
            session_id=session_id,
            student_id=student_id,
            mode=effective_mode,
            subject_id=subject_id,
            chapter_id=chapter_id,
            section_id=section_id,
        )

        history = await load_history(
            self.db, session.id,
            exclude_assessment=(effective_mode == "teaching"),
        )
        history_for_prompt = [] if effective_mode in ("quiz", "exam") else history
        # history_for_prompt = [
        #    m for m in history
        #    if not (m["role"] == "assistant" and "couldn't generate" in m["content"].lower())
        # ] if effective_mode in ("quiz", "exam") else history
        await self.sessions.add_message(session.id, "user", safety["text"])

        concept_key = None
        diag = {}
        if section_id:
            concept_key = await resolve_concept_for_section(self.db, section_id)
            if concept_key:
                diag = await diagnose(self.db, student_id, concept_key)

        diagnostic_block = build_diagnostic_block(diag) if diag else ""
        mastery = diag.get("mastery", 0.0) if diag else 0.0

        retrieval_query = _build_retrieval_query(safety["text"], history, effective_mode)
        chunks = await self.rag.retrieve(
            retrieval_query,
            subject_id=subject_id,
            chapter_id=chapter_id,
            section_id=section_id,
            class_id=class_id,
            top_k=5,
        )
        context = RAGService.format_context(chunks)
        no_context = len(chunks) == 0
        # Decide whether to use the standard mode prompt or the no-context prompt
        has_context = len(chunks) > 0
        system_override = None if has_context else get_no_context_prompt(effective_mode, grade)
        qv = verify_question(safety["text"])
        verified_block = _build_verified_block(qv, mode=mode)

        augmented_context = diagnostic_block + context
        # Look up subject and chapter names so the LLM knows what it's writing about
        subject_name = None
        chapter_name = None
        from app.db.models.curriculum import Subject, Chapter
        if subject_id:
            subject_name = (await self.db.execute(
                select(Subject.name).where(Subject.id == subject_id)
            )).scalar_one_or_none()
        if chapter_id:
            chapter_name = (await self.db.execute(
                select(Chapter.title).where(Chapter.id == chapter_id)
            )).scalar_one_or_none()

        messages = build_messages(
            mode=effective_mode,
            history=history_for_prompt,
            context=augmented_context,
            mastery=mastery,
            verified_block=verified_block,
            question=safety["text"],
            qv=qv,
            system_override=system_override,
            class_grade=grade,
            subject_name=subject_name,  # NEW
            chapter_name=chapter_name,  # NEW
        )

        answer_key = {}
        if effective_mode == "exam":
            if not has_context and chapter_id:
                answer = (
                    "I can't generate an exam for this chapter yet — no content has been "
                    "ingested. Please ask your teacher to upload the chapter, or choose a "
                    "chapter that has content."
                )
            else:
                from app.services.exam_builder import generate_exam_paper
                from app.prompts.no_context import _exam_spec_for_grade, requested_response_language
                spec = _exam_spec_for_grade(grade)
                answer, answer_key = await generate_exam_paper(
                    subject_name=subject_name or "",
                    class_grade=grade,
                    chapter_name=chapter_name,
                    context=augmented_context,
                    spec=spec,
                    language=requested_response_language(safety["text"]),
                )
                if not answer:
                    answer = "I couldn't generate a valid exam paper. Please try a different chapter."
                    answer_key = {}
        elif effective_mode == "quiz":
            answer, answer_key = await generate_assessment(
                messages, mode="quiz", max_tokens=1800, question=safety["text"],
            )
        else:
            answer = await complete_chat(messages, temperature=0.4, max_tokens=1500)

        verification = None
        if qv.get("is_math") and mode not in GUIDANCE_MODES and mode not in ("quiz", "exam"):
            verification = verify_answer(safety["text"], answer)

        citations = _dedupe_citations(chunks)

        await self.sessions.add_message(
            session.id,
            "tutor",
            answer,
            citations=citations,
            meta={
                "mode": effective_mode,
                "concept_key": concept_key,
                "verification": verification,
                "diagnostic": diag,
                # Store the private key alongside the exact generated assessment.
                "answer_key": {str(k): v for k, v in answer_key.items()},
                "awaiting_answers": effective_mode in ("quiz", "exam"),
            },
        )

        # ---- ANALYTICS ----
        duration_ms = int((time.perf_counter() - t0) * 1000)

        await A.log_event(
            self.db,
            event_type="question_asked",
            student_id=student_id,
            school_id=school_id,
            class_id=class_id,
            subject_id=subject_id,
            chapter_id=chapter_id,
            section_id=section_id,
            concept_key=concept_key,
            mode=mode,
            duration_ms=duration_ms,
        )

        if verification and verification.get("verified") is not None:
            await A.log_event(
                self.db,
                event_type="answer_evaluated",
                student_id=student_id,
                school_id=school_id,
                class_id=class_id,
                concept_key=concept_key,
                mode=mode,
                is_correct=verification["verified"],
                was_verified=verification["verified"],
            )

        if diag.get("recommendation") == "review_prerequisite":
            await A.log_event(
                self.db,
                event_type="prerequisite_flagged",
                student_id=student_id,
                school_id=school_id,
                class_id=class_id,
                concept_key=concept_key,
                mode=mode,
                extra={"prerequisite": diag.get("recommended_prerequisite")},
            )
        # ---- /ANALYTICS ----

        return {
            "session_id": str(session.id),
            "answer": answer,
            "citations": citations,
            "mode": mode,
            "concept_key": concept_key,
            "verification": verification,
            "diagnostic": diag,
            "no_context": not has_context,
            "awaiting_answers": mode in ("quiz", "exam"),  # NEW
        }

    async def submit_answer(
        self,
        *,
        student_id,
        session_id,
        question,
        student_answer,
        concept_key=None,
        school_id=None,
        class_id=None,
    ):
        from app.services.evaluator_service import evaluate_answers

        # Load the tutor's previous message so the grader knows what was asked
        last_tutor = await self.sessions.get_last_tutor_message(session_id)
        tutor_text = last_tutor.content if last_tutor else ""
        # The key is stored as message metadata and never sent to the student.
        # The key is stored as message metadata and never sent to the student.
        # Small models can drift; also try to recover key from the exam text.
        raw_key = (last_tutor.meta or {}).get("answer_key", {}) if last_tutor else {}
        try:
            answer_key = {int(k): str(v) for k, v in (raw_key or {}).items() if str(v).strip()}
        except (AttributeError, TypeError, ValueError):
            answer_key = {}

        # Fallback: parse the saved paper text for an [ANSWER_KEY:...] or
        # **ANSWER_KEY:** block if meta was lost.
        if not answer_key and tutor_text:
            from app.services.quiz_grader import extract_answer_key
            _, recovered = extract_answer_key(tutor_text)
            if recovered:
                answer_key = recovered
                logger.info("recovered_answer_key_from_message", count=len(recovered))

        result = await evaluate_answers(
            tutor_message=tutor_text,
            student_answer=student_answer,
            question=question,
            answer_key=answer_key,
            assessment_mode=bool(last_tutor and (last_tutor.meta or {}).get("mode") in ("quiz", "exam")),
        )

        # Defensive: evaluate_answers always returns a dict, but guard anyway.
        if not result:
            result = {
                "is_correct": False,
                "per_question_correct": [],
                "student_answers": [student_answer],
                "correct_answers": [],
                "score_percent": 0,
                "feedback": "I couldn't grade that answer.",
                "source": "no_result",
            }
        is_correct = bool(result["is_correct"])

        # Update mastery via knowledge tracing
        new_mastery = 0.0
        if concept_key:
            prior = await self.students.get_mastery(student_id, concept_key)
            p = prior.mastery if prior else 0.2
            new_mastery = update_mastery(p, is_correct)
            await self.students.upsert_mastery(student_id, concept_key, new_mastery, is_correct)

        # Log the attempt
        await self.sessions.log_attempt(
            student_id=student_id,
            concept_key=concept_key or "unknown",
            question=question,
            answer=student_answer,
            is_correct=is_correct,
            confidence=result.get("score_percent", 0) / 100.0,
            method_valid=is_correct,
            meta={
                "session_id": str(session_id),
                "per_question_correct": result.get("per_question_correct", []),
                "correct_answers": result.get("correct_answers", []),
                "grader": result.get("source", "llm"),
            },
        )

        # Analytics
        await A.log_event(
            self.db,
            event_type="student_submitted",
            student_id=student_id,
            school_id=school_id,
            class_id=class_id,
            concept_key=concept_key,
            is_correct=is_correct,
        )

        return {
            "is_correct": is_correct,
            "score_percent": result.get("score_percent", 0),
            "per_question_correct": result.get("per_question_correct", []),
            "student_answers": result.get("student_answers", []),
            "correct_answers": result.get("correct_answers", []),
            "feedback": result.get("feedback", ""),
            "grader": result.get("source", "llm"),
            "new_mastery": new_mastery,
            "next_review": next_review(new_mastery).isoformat(),
        }
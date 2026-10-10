import time
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
from app.services.intent import detect_intent
from app.services.quiz_grader import extract_answer_key
from app.db.models.curriculum import Class as ClassModel
from sqlalchemy import select


GUIDANCE_MODES = {"socratic", "hint", "practice"}


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
        # Auto-switch mode if the student asked for questions in a non-quiz mode
        if mode == "teacher":
            detected = detect_intent(safety["text"])
            effective_mode = detected or "teacher"
        else:
            effective_mode = mode
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
            mode=mode,
            subject_id=subject_id,
            chapter_id=chapter_id,
            section_id=section_id,
        )

        history = await load_history(self.db, session.id)
        await self.sessions.add_message(session.id, "user", safety["text"])

        concept_key = None
        diag = {}
        if section_id:
            concept_key = await resolve_concept_for_section(self.db, section_id)
            if concept_key:
                diag = await diagnose(self.db, student_id, concept_key)

        diagnostic_block = build_diagnostic_block(diag) if diag else ""
        mastery = diag.get("mastery", 0.0) if diag else 0.0

        chunks = await self.rag.retrieve(
            safety["text"],
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

        messages = build_messages(
            mode=effective_mode,
            history=history,
            context=augmented_context,
            mastery=mastery,
            verified_block=verified_block,
            question=safety["text"],
            qv=qv,
            system_override=system_override,
            class_grade=grade,  # ← NEW
        )

        assessment_mode = effective_mode in ("quiz", "exam")
        answer_key = {}
        if assessment_mode:
            answer, answer_key = await generate_assessment(messages, mode=effective_mode, max_tokens=1800, question=safety["text"])
        else:
            answer = await complete_chat(messages, temperature=0.4, max_tokens=1500)

        verification = None
        if qv.get("is_math") and mode not in GUIDANCE_MODES and mode not in ("practice", "quiz", "exam"):
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
                "awaiting_answers": effective_mode in ("practice", "quiz", "exam"),
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
            "awaiting_answers": mode in ("practice", "quiz", "exam"),  # NEW
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
        raw_key = (last_tutor.meta or {}).get("answer_key", {}) if last_tutor else {}
        try:
            answer_key = {int(k): str(v) for k, v in raw_key.items()}
        except (AttributeError, TypeError, ValueError):
            answer_key = {}

        result = await evaluate_answers(
            tutor_message=tutor_text,
            student_answer=student_answer,
            question=question,
            answer_key=answer_key,
            assessment_mode=bool(last_tutor and (last_tutor.meta or {}).get("mode") in ("quiz", "exam")),
        )

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
from app.repositories.session_repo import SessionRepository
from app.repositories.student_repo import StudentRepository
from app.services.rag_service import RAGService
from app.services.llm_service import complete_chat
from app.services.safety_service import check_input
from app.services.knowledge_tracing import update_mastery
from app.services.spaced_repetition import next_review
from app.services.math_verifier import verify_question, verify_answer
from app.services.conversation import load_history, build_messages
from sqlalchemy.ext.asyncio import AsyncSession


GUIDANCE_MODES = {"socratic", "hint", "practice"}

def _build_verified_block(qv: dict, mode: str = "teacher") -> str:
    if mode in GUIDANCE_MODES:
        return ""   # don't leak the answer in guidance modes
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
    ):
        safety = await check_input(question)
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

        # Load history BEFORE saving the new user message
        history = await load_history(self.db, session.id)
        await self.sessions.add_message(session.id, "user", safety["text"])

        concept_key = f"section:{section_id}" if section_id else None
        mastery = 0.0
        if concept_key:
            row = await self.students.get_mastery(student_id, concept_key)
            if row:
                mastery = row.mastery

        chunks = await self.rag.retrieve(
            safety["text"], subject_id, chapter_id, section_id, top_k=5,
        )
        context = RAGService.format_context(chunks)

        qv = verify_question(safety["text"])
        verified_block = _build_verified_block(qv, mode=mode)

        messages = build_messages(
            mode=mode,
            history=history,
            context=context,
            mastery=mastery,
            verified_block=verified_block,
            question=safety["text"],
            qv=qv,
        )

        answer = await complete_chat(messages, temperature=0.4, max_tokens=1500)

        verification = verify_answer(safety["text"], answer) if qv.get("is_math") else None
        citations = _dedupe_citations(chunks)

        await self.sessions.add_message(
            session.id,
            "tutor",
            answer,
            citations=citations,
            meta={"mode": mode, "concept_key": concept_key, "verification": verification},
        )

        return {
            "session_id": str(session.id),
            "answer": answer,
            "citations": citations,
            "mode": mode,
            "concept_key": concept_key,
            "verification": verification,
        }

    async def submit_answer(self, *, student_id, session_id, question, student_answer, concept_key=None):
        is_correct = student_answer.strip().lower() in question.lower()
        result = {
            "is_correct": is_correct,
            "correct_answer": "",
            "method_valid": is_correct,
            "confidence": 0.5,
            "feedback": "Looks good." if is_correct else "Not quite — try again.",
        }
        new_mastery = 0.0
        if concept_key:
            prior = await self.students.get_mastery(student_id, concept_key)
            p = prior.mastery if prior else 0.2
            new_mastery = update_mastery(p, is_correct)
            await self.students.upsert_mastery(student_id, concept_key, new_mastery, is_correct)

        await self.sessions.log_attempt(
            student_id=student_id,
            concept_key=concept_key or "unknown",
            question=question,
            answer=student_answer,
            is_correct=is_correct,
            confidence=result["confidence"],
            method_valid=result["method_valid"],
            meta={"session_id": str(session_id)},
        )
        return {
            "evaluation": result,
            "new_mastery": new_mastery,
            "next_review": next_review(new_mastery).isoformat(),
        }

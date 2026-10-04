from app.repositories.session_repo import SessionRepository
from app.repositories.student_repo import StudentRepository
from app.repositories.content_repo import ContentRepository
from app.services.rag_service import RAGService
from app.services.llm_service import complete
from app.services.safety_service import check_input
from app.services.knowledge_tracing import update_mastery
from app.services.spaced_repetition import next_review
from app.services.misconception_service import detect_misconception
from app.tools.math_tool import try_symbolic_verify
from app.prompts.teacher import TEACHER_SYSTEM, TEACHER_USER
from app.prompts.evaluator import EVALUATOR_PROMPT
import json


class TutorService:
    def __init__(
        self,
        session_repo: SessionRepository,
        student_repo: StudentRepository,
        content_repo: ContentRepository,
    ):
        self.sessions = session_repo
        self.students = student_repo
        self.rag = RAGService(content_repo)

    async def ask(self, *, student_id, mode, question, subject_id=None, chapter_id=None, section_id=None, session_id=None):
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

        await self.sessions.add_message(session.id, "user", safety["text"])

        concept_key = f"section:{section_id}" if section_id else None
        mastery_row = (
            await self.students.get_mastery(student_id, concept_key) if concept_key else None
        )
        mastery = mastery_row.mastery if mastery_row else 0.0

        strategy = "scaffold" if mastery < 0.4 else "explain_with_example" if mastery < 0.7 else "challenge"

        chunks = await self.rag.retrieve(
            question, subject_id, chapter_id, section_id, top_k=5
        )
        context = RAGService.format_context(chunks)

        answer = await complete(
            prompt=TEACHER_USER.format(
                strategy=strategy, context=context, mastery=mastery, question=question
            ),
            system=TEACHER_SYSTEM,
            temperature=0.4,
            max_tokens=1200,
        )

        citations = [{"chapter": c["chapter"], "section": c["section"], "page": c["page"]} for c in chunks]

        await self.sessions.add_message(session.id, "tutor", answer, citations=citations)

        return {
            "session_id": str(session.id),
            "answer": answer,
            "citations": citations,
            "strategy": strategy,
            "concept_key": concept_key,
        }

    async def submit_answer(self, *, student_id, session_id, question, student_answer, concept_key=None):
        symbolic = try_symbolic_verify(question, student_answer)
        if symbolic:
            result = {
                "is_correct": symbolic["is_correct"],
                "correct_answer": symbolic.get("correct_answer", ""),
                "method_valid": True,
                "confidence": 0.95,
                "feedback": "Verified symbolically.",
            }
        else:
            raw = await complete(
                EVALUATOR_PROMPT.format(question=question, student_answer=student_answer),
                temperature=0.0,
                json_mode=True,
                max_tokens=400,
            )
            try:
                result = json.loads(raw)
            except Exception:
                result = {"is_correct": False, "method_valid": False, "confidence": 0.5, "feedback": ""}

        new_mastery = 0.0
        if concept_key:
            prior = await self.students.get_mastery(student_id, concept_key)
            prior_mastery = prior.mastery if prior else 0.2
            new_mastery = update_mastery(prior_mastery, result["is_correct"])
            await self.students.upsert_mastery(
                student_id, concept_key, new_mastery, result["is_correct"]
            )

        if not result["is_correct"] and concept_key:
            result["misconception"] = await detect_misconception(
                question, student_answer, result.get("correct_answer", ""), concept_key
            )

        await self.sessions.log_attempt(
            student_id=student_id,
            concept_key=concept_key or "unknown",
            question=question,
            answer=student_answer,
            is_correct=result["is_correct"],
            confidence=result["confidence"],
            method_valid=result["method_valid"],
            meta={"session_id": str(session_id)},
        )

        return {
            "evaluation": result,
            "new_mastery": new_mastery,
            "next_review": next_review(new_mastery, None).isoformat(),
        }
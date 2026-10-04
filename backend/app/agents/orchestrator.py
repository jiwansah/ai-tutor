from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.agents.states import TutorState
from app.agents.diagnoser import diagnose
from app.agents.planner import plan
from app.agents.teacher import teach
from app.agents.evaluator import evaluate
from app.services import knowledge_tracing, spaced_repetition, misconception_service
from app.db.models.student import ConceptMastery
from sqlalchemy import select

logger = structlog.get_logger()


@dataclass
class TutorContext:
    student_id: str
    session_id: str
    mode: str = "teacher"
    subject_id: str | None = None
    chapter_id: str | None = None
    section_id: str | None = None
    concept_key: str | None = None
    state: TutorState = TutorState.IDLE
    history: list[dict] = field(default_factory=list)
    student_mastery: float = 0.0
    strategy: str = "explain"
    metadata: dict[str, Any] = field(default_factory=dict)


async def handle_question(db: AsyncSession, ctx: TutorContext, question: str) -> dict:
    # 1. Diagnose
    ctx.state = TutorState.DIAGNOSING
    diagnosis = await diagnose(db, ctx, question)
    ctx.metadata["diagnosis"] = diagnosis
    ctx.concept_key = diagnosis.get("concept_key") or ctx.concept_key
    ctx.student_mastery = diagnosis.get("mastery", 0.0)

    # 2. Plan
    ctx.state = TutorState.PLANNING
    plan_result = await plan(ctx, diagnosis)
    ctx.strategy = plan_result["strategy"]
    ctx.metadata["plan"] = plan_result

    # 3. Teach
    ctx.state = TutorState.TEACHING
    teaching = await teach(db, ctx, question, plan_result)

    logger.info("tutor_handled", state=ctx.state, strategy=ctx.strategy,
                concept=ctx.concept_key, mastery=ctx.student_mastery)

    return {
        "answer": teaching["answer"],
        "citations": teaching["citations"],
        "strategy": ctx.strategy,
        "concept_key": ctx.concept_key,
        "diagnosis": diagnosis,
        "state": ctx.state.value,
    }


async def handle_student_answer(
    db: AsyncSession, ctx: TutorContext, question: str, student_answer: str
) -> dict:
    ctx.state = TutorState.CHECKING
    result = await evaluate(db, ctx, question, student_answer)

    # Update mastery
    ctx.state = TutorState.UPDATING
    new_mastery = knowledge_tracing.update_mastery(ctx.student_mastery, result["is_correct"])

    # Persist
    if ctx.concept_key:
        stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == ctx.student_id,
            ConceptMastery.concept_key == ctx.concept_key,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            row.mastery = new_mastery
            row.attempts += 1
            row.correct += int(result["is_correct"])
        else:
            db.add(ConceptMastery(
                student_id=ctx.student_id,
                concept_key=ctx.concept_key,
                mastery=new_mastery,
                attempts=1,
                correct=int(result["is_correct"]),
            ))

    # Misconception detection
    if not result["is_correct"]:
        misc = await misconception_service.detect_misconception(
            question=question,
            student_answer=student_answer,
            correct_answer=result.get("correct_answer", ""),
            concept=ctx.concept_key or "",
        )
        result["misconception"] = misc

    return {
        "evaluation": result,
        "new_mastery": new_mastery,
        "next_review": spaced_repetition.next_review(new_mastery, None).isoformat(),
    }
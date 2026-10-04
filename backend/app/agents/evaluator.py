from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.orchestrator import TutorContext
from app.services.llm_service import complete
from app.prompts.evaluator import EVALUATOR_PROMPT
from app.tools.math_tool import try_symbolic_verify
import json


async def evaluate(
    db: AsyncSession, ctx: TutorContext, question: str, student_answer: str
) -> dict:
    # Try symbolic verification for math
    symbolic = try_symbolic_verify(question, student_answer)

    if symbolic is not None:
        return {
            "is_correct": symbolic["is_correct"],
            "correct_answer": symbolic.get("correct_answer", ""),
            "method_valid": True,
            "confidence": 0.95,
            "feedback": "Verified symbolically.",
        }

    # Fall back to LLM evaluator
    raw = await complete(
        EVALUATOR_PROMPT.format(question=question, student_answer=student_answer),
        temperature=0.0,
        json_mode=True,
        max_tokens=400,
    )
    try:
        data = json.loads(raw)
    except Exception:
        data = {"is_correct": False, "method_valid": False, "confidence": 0.5, "feedback": ""}

    return {
        "is_correct": data.get("is_correct", False),
        "correct_answer": data.get("correct_answer", ""),
        "method_valid": data.get("method_valid", False),
        "confidence": data.get("confidence", 0.5),
        "feedback": data.get("feedback", ""),
    }
"""
Grade a student's answer against the tutor's previous message.

- Math questions: SymPy first (deterministic, fast).
- Everything else: LLM grader (handles MCQ, short-text, multi-part).
"""
import json

from app.services.llm_service import complete
from app.services.math_verifier import verify_question, verify_answer
from app.prompts.evaluator import EVALUATOR_SYSTEM, EVALUATOR_USER


async def evaluate_answers(
    *,
    tutor_message: str,
    student_answer: str,
    question: str,
) -> dict:
    """
    Returns:
        {
          "is_correct": bool,
          "per_question_correct": [bool, ...],
          "student_answers": [str, ...],
          "correct_answers": [str, ...],
          "score_percent": int,
          "feedback": str,
          "source": "sympy" | "llm",
        }
    """
    # ---- Path 1: Math → SymPy ----
    qv = verify_question(question)
    if qv.get("is_math"):
        v = verify_answer(question, student_answer)
        if v.get("verified") is not None:
            correct = bool(v["verified"])
            return {
                "is_correct": correct,
                "per_question_correct": [correct],
                "student_answers": [v.get("llm_answer") or student_answer],
                "correct_answers": qv.get("solutions", []),
                "score_percent": 100 if correct else 0,
                "feedback": (
                    "Correct!" if correct
                    else f"Not quite. The correct answer is {', '.join(qv.get('solutions', []))}."
                ),
                "source": "sympy",
            }

    # ---- Path 2: LLM grader ----
    raw = await complete(
        prompt=EVALUATOR_USER.format(
            tutor_message=(tutor_message or "(no previous tutor message)")[:4000],
            student_answer=student_answer[:2000],
        ),
        system=EVALUATOR_SYSTEM,
        temperature=0.0,
        max_tokens=600,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        # Ensure all required keys
        data.setdefault("is_correct", False)
        data.setdefault("per_question_correct", [])
        data.setdefault("student_answers", [student_answer])
        data.setdefault("correct_answers", [])
        data.setdefault("score_percent", 0)
        data.setdefault("feedback", "")
    except Exception:
        data = {
            "is_correct": False,
            "per_question_correct": [],
            "student_answers": [student_answer],
            "correct_answers": [],
            "score_percent": 0,
            "feedback": "I couldn't grade that answer. Please try rephrasing.",
        }

    data["source"] = "llm"
    return data

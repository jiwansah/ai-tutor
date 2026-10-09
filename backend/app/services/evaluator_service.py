"""
Grade a student's answer.

Strategy:
  1. If the tutor's message contains math equations → deterministic grader.
     If it bails, refuse to grade (LLM lies on math).
  2. Otherwise → LLM grader with phi4-mini (fine for letter-matching MCQs).
"""
import json
import re

from app.services.llm_service import complete
from app.services.math_verifier import verify_question, verify_answer
from app.services.quiz_grader import grade_quiz
from app.prompts.evaluator import EVALUATOR_SYSTEM, EVALUATOR_USER
from app.config import settings


def _looks_like_math_message(text: str) -> bool:
    """Does the tutor's message contain equations?"""
    if not text:
        return False
    # Look for x + 5 = 9 style patterns
    return bool(re.search(r"[a-zA-Z]\s*[\+\-\*/\^]\s*\d+\s*=", text)) or \
           bool(re.search(r"\d+\s*[a-zA-Z]\s*=", text))


def _strip_json_wrappers(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```\s*$", "", t)
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        t = t[first:last + 1]
    return t.strip()


async def evaluate_answers(
    *,
    tutor_message: str,
    student_answer: str,
    question: str,
) -> dict:
    tutor_message = tutor_message or ""

    # ---- Path 1: Deterministic grader for MCQs (works for math AND any
    #              MCQ where the correct option can be inferred) ----
    deterministic = grade_quiz(tutor_message, student_answer)
    if deterministic is not None:
        return deterministic

    # ---- Path 2: Single-question math via SymPy ----
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

    # ---- If it's a math question but we couldn't parse it → refuse (no LLM lies) ----
    if _looks_like_math_message(tutor_message):
        return {
            "is_correct": False,
            "per_question_correct": [],
            "student_answers": [student_answer],
            "correct_answers": [],
            "score_percent": 0,
            "feedback": (
                "I couldn't grade that math answer automatically. "
                "Please answer in the format A/B/C/D."
            ),
            "source": "unsupported_math",
        }

    # ---- Path 3: Non-math → LLM grader ----
    raw = await complete(
        prompt=EVALUATOR_USER.format(
            tutor_message=tutor_message[:4000],
            student_answer=student_answer[:2000],
        ),
        system=EVALUATOR_SYSTEM,
        model=settings.LLM_MODEL_LARGE,   # phi4-mini is fine for MCQs
        temperature=0.0,
        max_tokens=600,
        json_mode=True,
    )

    raw = _strip_json_wrappers(raw)
    try:
        data = json.loads(raw)
        data.setdefault("is_correct", False)
        data.setdefault("per_question_correct", [])
        data.setdefault("student_answers", [student_answer])
        data.setdefault("correct_answers", [])
        data.setdefault("score_percent", 0)
        data.setdefault("feedback", "")
        data["source"] = "llm"
        return data
    except Exception:
        return {
            "is_correct": False,
            "per_question_correct": [],
            "student_answers": [student_answer],
            "correct_answers": [],
            "score_percent": 0,
            "feedback": "I couldn't grade that answer. Please try again.",
            "source": "llm_parse_error",
        }

from app.services.llm_service import complete
from app.prompts.evaluator import MISCONCEPTION_PROMPT
import json

async def detect_misconception(
    question: str,
    student_answer: str,
    correct_answer: str,
    concept: str,
) -> dict:
    prompt = MISCONCEPTION_PROMPT.format(
        concept=concept,
        question=question,
        student_answer=student_answer,
        correct_answer=correct_answer,
    )
    raw = await complete(prompt, temperature=0.0, json_mode=True, max_tokens=300)
    try:
        return json.loads(raw)
    except Exception:
        return {"misconception": None, "explanation": ""}
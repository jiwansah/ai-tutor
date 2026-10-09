"""Generate quizzes/exams and retry once when the private grading key is missing."""
from app.services.llm_service import complete_chat
from app.services.quiz_grader import extract_answer_key


async def generate_assessment(messages: list[dict], *, mode: str, max_tokens: int = 1800) -> tuple[str, dict[int, str]]:
    raw = await complete_chat(messages, temperature=0.2, max_tokens=max_tokens)
    visible, key = extract_answer_key(raw)
    if key:
        return visible, key

    # Some models ignore formatting instructions, especially for non-English quizzes.
    # Ask for a full regeneration rather than guessing a key from the question text.
    retry_messages = [
        *messages,
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": (
                "REPAIR REQUIRED: Your previous assessment omitted the required private grading key. "
                "Regenerate the entire assessment from scratch in the language required by the system prompt. "
                "Keep exactly the required number of questions, ensure each MCQ has exactly one correct option, "
                "and append a valid [[ANSWER_KEY:1=A,2=C,3=B]] marker with an entry for every question. "
                "The marker is backend-only and must not be included in the visible assessment except as this final marker."
            ),
        },
    ]
    raw = await complete_chat(retry_messages, temperature=0.1, max_tokens=max_tokens)
    visible, key = extract_answer_key(raw)
    return visible, key

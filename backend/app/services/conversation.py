"""
Build the chat message array from session history + current context.
"""
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.session import Message
from app.prompts.tutor_modes import get_system_prompt

MAX_HISTORY_MESSAGES = 8


async def load_history(
    db: AsyncSession, session_id, limit: int = MAX_HISTORY_MESSAGES,
) -> list[dict]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()
    return [
        {"role": "assistant" if m.role == "tutor" else "user", "content": m.content}
        for m in rows
    ]


_QUESTION_MARKERS = re.compile(
    r"\b(how|what|why|when|where|which|who|solve|explain|tell|show|help|find|calculate)\b",
    re.IGNORECASE,
)
_MATH_OPERATOR = re.compile(r"[=+\-*/^]|^\s*-?\d+(\.\d+)?\s*$")


def looks_like_reply(text: str) -> bool:
    t = text.strip()
    if len(t) > 60:
        return False
    if "?" in t:
        return False
    if _QUESTION_MARKERS.search(t):
        return False
    if _MATH_OPERATOR.search(t):
        return True
    if len(t.split()) <= 5:
        return True
    return False


_NEW_QUESTION_TEMPLATE = """Student's class: {class_label}
Student mastery on this concept: {mastery:.2f} (0 = new, 1 = mastered)

Textbook context:
{context}

{verified_block}Student question:
{question}
"""

_REPLY_TEMPLATE = """The student just replied to your previous message.

{private_answer}Student's reply: "{reply}"

Your job:
1. Compare the student's reply to the correct solution above (if provided).
2. If the student HAS GIVEN THE CORRECT FINAL ANSWER:
   → Confirm warmly: "Perfect! x = <value>. You've solved it."
   → STOP. Do NOT ask any further question. Do NOT continue the lesson.
3. If the student is PARTIALLY correct (right operation, wrong value, or right value, wrong operation):
   → Acknowledge the right part, then ask ONE small question about the other part.
4. If the student is WRONG:
   → Say "Not quite — let's look again." Then ask a simpler question.
5. If the student is stuck ("I don't know", "help", "stuck"):
   → Give a small hint, then ask a simpler question.

CRITICAL:
- NEVER reveal the answer yourself. Only confirm AFTER the student provides it.
- If the problem is solved, END. Do not keep asking.
"""


def _private_answer_block(qv: dict | None) -> str:
    """Give the LLM the correct answer privately — never to reveal, only to recognize."""
    if not qv or not qv.get("is_math"):
        return ""
    var = qv["variable"]
    sols = ", ".join(qv["solutions"])
    return (
        f"PRIVATE — DO NOT REVEAL THIS UNLESS THE STUDENT SAYS IT FIRST:\n"
        f"  The correct final answer is {var} = {sols}.\n"
        f"  Use this ONLY to recognize when the student has solved the problem.\n\n"
    )



def build_messages(
    *,
    mode: str,
    history: list[dict],
    context: str,
    mastery: float,
    verified_block: str,
    question: str,
    qv: dict | None = None,
    system_override: str | None = None,
    class_grade: int | None = None,          # ← NEW
) -> list[dict]:
    system_content = system_override or get_system_prompt(mode)

    messages: list[dict] = [
        {"role": "system", "content": system_content},
    ]
    messages.extend(history)

    is_reply = (
        mode in ("socratic", "hint")
        and len(history) > 0
        and looks_like_reply(question)
    )

    if is_reply:
        content = _REPLY_TEMPLATE.format(
            private_answer=_private_answer_block(qv),
            reply=question,
        )
    else:
        class_label = f"Class {class_grade}" if class_grade else "Unknown"
        content = _NEW_QUESTION_TEMPLATE.format(
            class_label=class_label,
            mastery=mastery,
            context=context,
            verified_block=verified_block,
            question=question,
        )

    messages.append({"role": "user", "content": content})
    return messages

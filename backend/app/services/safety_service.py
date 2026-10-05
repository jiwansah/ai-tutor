import re
from app.config import settings

PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[PHONE]"),
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"), "[EMAIL]"),
]
BLOCKED = ["self-harm", "suicide", "weapon", "drugs"]


async def check_input(text: str) -> dict:
    if len(text) > settings.MAX_INPUT_LENGTH:
        return {"ok": False, "reason": "too_long"}
    low = text.lower()
    for topic in BLOCKED:
        if topic in low:
            return {"ok": False, "reason": "unsafe_topic", "topic": topic}
    return {"ok": True, "text": redact_pii(text)}


def redact_pii(text: str) -> str:
    for p, r in PII_PATTERNS:
        text = p.sub(r, text)
    return text

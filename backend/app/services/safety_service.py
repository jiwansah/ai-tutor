import re
from app.config import settings

PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[PHONE]"),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"), "[EMAIL]"),
]

BLOCKED_TOPICS = [
    "self-harm", "suicide", "weapon", "drugs", "explicit",
]

async def check_input(text: str) -> dict:
    if len(text) > settings.MAX_INPUT_LENGTH:
        return {"ok": False, "reason": "too_long"}

    lowered = text.lower()
    for topic in BLOCKED_TOPICS:
        if topic in lowered:
            return {"ok": False, "reason": "unsafe_topic", "topic": topic}

    return {"ok": True, "text": redact_pii(text)}


def redact_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


async def check_output(text: str) -> dict:
    # Light output check; extend with moderation API
    return {"ok": True, "text": text}
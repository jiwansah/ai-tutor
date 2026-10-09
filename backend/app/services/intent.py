"""
Detect intent from the student's message text.
If they ask for questions in Teacher mode, we auto-switch for that turn.
"""
import re

_QUIZ = re.compile(r"\b(quiz|quize|mcq|multiple[- ]choice)\b", re.I)
_EXAM = re.compile(r"\b(mock\s+(test|exam)|test\s+me|exam|exam\s+paper)\b", re.I)
_PRACTICE = re.compile(
    r"\b(give|show|ask|send)\s+me\s+(some\s+)?(question|questions|problems?)\b"
    r"|\b(practice|worksheet)\s+(question|questions|problems?)\b",
    re.I,
)


def detect_intent(text: str) -> str | None:
    if not text:
        return None
    if _EXAM.search(text):
        return "exam"
    if _QUIZ.search(text):
        return "quiz"
    if _PRACTICE.search(text):
        return "practice"
    return None

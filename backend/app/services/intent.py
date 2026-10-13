"""Canonical mode names and lightweight request-intent detection."""
import re

_MODE_ALIASES = {
    "teaching": "teaching", "teacher": "teaching", "socratic": "teaching",
    "hint": "teaching", "doubt": "teaching", "revision": "teaching",
    "practice": "quiz", "homework": "quiz", "quiz": "quiz", "exam": "exam",
}


def normalize_mode(mode: str | None) -> str:
    """Return one of the only supported modes: teaching, quiz, or exam."""
    return _MODE_ALIASES.get((mode or "teaching").strip().lower(), "teaching")


_QUIZ = re.compile(r"\b(quiz|quize|mcq|multiple[- ]choice)\b", re.I)
_EXAM = re.compile(r"\b(mock\s+(test|exam)|test\s+me|exam|exam\s+paper)\b", re.I)
_QUESTIONS = re.compile(
    r"\b(give|show|ask|send)\s+me\s+(some\s+)?(question|questions|problems?)\b"
    r"|\b(practice|worksheet)\s+(question|questions|problems?)\b",
    re.I,
)

# Words that signal a general question rather than an assessment request
_GENERAL_QUESTION_STARTERS = re.compile(
    r"^\s*(?:what|why|how|who|when|where|which|can you|could you|please|"
    r"explain|tell me|describe|help me|i (?:want|need|don'?t|didn'?t)|"
    r"give me a hint|show me)",
    re.IGNORECASE,
)

# Short answer pattern: "1. x=4  2. y=5" or "1 A, 2 B, 3 C"
_LOOKS_LIKE_ANSWERS = re.compile(
    r"^\s*\d+\s*[.\")\-:]?\s*(?:[A-Da-d]|[\w\u0900-\u097F=+\-*/\s]+?)"
    r"(?:\s*[\n,;]|\s*$)",
    re.MULTILINE,
)


# Explicit assessment keywords
_ASSESSMENT_KEYWORDS = re.compile(
    r"\b(exam|test|quiz|mcq|questions?|paper|assessment)\b",
    re.IGNORECASE,
)


def is_general_question(text: str) -> bool:
    """
    True when the message reads as a normal student question,
    not as an exam request or answer submission.
    """
    t = (text or "").strip()
    if not t:
        return False
    # If it explicitly mentions exam/quiz → not a general question
    if _ASSESSMENT_KEYWORDS.search(t):
        return False
    # If it looks like short answers to a previous assessment → not a question
    if _LOOKS_LIKE_ANSWERS.match(t) and len(t) < 400:
        return False
    # Starts with a question word
    if _GENERAL_QUESTION_STARTERS.match(t):
        return True
    # Contains a question mark
    if "?" in t or "?" in t:  # covers Devanagari question mark too
        return True
    return False

def detect_intent(text: str) -> str | None:
    """Auto-route explicit assessment requests made while in Teaching mode."""
    if not text:
        return None
    if _EXAM.search(text):
        return "exam"
    if _QUIZ.search(text) or _QUESTIONS.search(text):
        return "quiz"
    return None

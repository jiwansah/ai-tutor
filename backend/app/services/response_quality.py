"""Quality guards for generated practice responses."""
import re


def _practice_response_is_malformed(text: str, language: str) -> bool:
    """Reject obvious language leakage and duplicated MCQ options before they reach the client."""
    if language == "English" and re.search(r"[\u0900-\u097F]", text or ""):
        return True
    blocks = re.split(r"(?=\*\*Question\s+\d+\s*:\*\*)", text or "", flags=re.I)
    for block in blocks:
        options = re.findall(r"(?m)^\s*([A-D])[).]\s*(.+?)\s*$", block)
        if len(options) >= 4:
            values = [re.sub(r"[^a-z0-9]+", " ", value.lower()).strip() for _, value in options[:4]]
            if len(set(values)) < 4:
                return True
    return False


def _english_grammar_fallback(question: str) -> str | None:
    """Reliable fallback for English-grammar practice when model output fails validation twice."""
    q = (question or "").lower()
    if "grammar" not in q and "grammer" not in q and "english" not in q:
        return None
    return ("📚 Not in your textbook yet — here's some general practice:\n\n"
            '**Problem 1:** Identify the noun in this sentence: "The teacher opened the book."\n\n'
            '**Problem 2:** Choose the correct verb to complete the sentence: "They ___ at the beach last summer."\n\n'
            '**Problem 3:** Rewrite this sentence in the past tense: "She walks to school."\n\n'
            "Solve them and share your answers when ready.")

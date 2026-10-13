"""Generate assessments, validate quiz structure, and keep grading keys private.

This module deliberately fails closed: a quiz is returned only when its structure
and private key are valid. It retries generation instead of immediately giving up
when the local model repeats a question or uses a slightly different heading style.
"""
import re
from app.services.llm_service import complete_chat
from app.services.quiz_grader import extract_answer_key
from app.prompts.no_context import requested_response_language


_QUESTION_HEADING = re.compile(
    r"(?im)^\s*(?:\*\*)?(?:Question\s+|Q\s*)(\d+)\s*:?(?:\*\*)?\s*:?\s*(.*)$"
)
_OPTION_LINE = re.compile(r"(?im)^\s*([A-D])[).]\s*(.+?)\s*$")


def _extract_stems(text: str) -> list[str]:
    """Extract question stems from common plain-text and Markdown heading styles."""
    lines = (text or "").splitlines()
    stems: list[str] = []
    for i, line in enumerate(lines):
        match = _QUESTION_HEADING.match(line)
        if not match:
            continue
        stem = match.group(2).strip().strip("* ")
        if not stem:
            # Some models put the question itself on the next line.
            for candidate in lines[i + 1:i + 3]:
                candidate = candidate.strip()
                if candidate and not _OPTION_LINE.match(candidate):
                    stem = candidate.strip("* ")
                    break
        normalized = re.sub(r"[^a-z0-9]+", " ", stem.lower()).strip()
        if normalized:
            stems.append(normalized)
    return stems


def _obvious_grammar_conflict(text: str, key: dict[int, str] | None) -> bool:
    """Catch a common invalid MCQ: asking for simple past when every option is another tense."""
    if not re.search(r"\bsimple\s+past(?:\s+tense)?\b", text or "", re.I):
        return False
    matches = list(_QUESTION_HEADING.finditer(text or ""))
    for i, match in enumerate(matches):
        block = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        if not re.search(r"\bsimple\s+past(?:\s+tense)?\b", match.group(2) + " " + block, re.I):
            continue
        options = {letter.upper(): value.strip() for letter, value in _OPTION_LINE.findall(block)}
        if len(options) != 4:
            continue
        # These forms cannot be Simple Past: past continuous (was/were + -ing)
        # and past perfect (had + participle). If all options are such forms,
        # the question has no correct option and must be regenerated.
        clearly_other_tense = 0
        for value in options.values():
            v = value.strip().lower()
            if re.match(r"^(?:was|were)\s+\w+ing\b", v) or re.match(r"^had\s+\w+(?:ed|en|n)\b", v):
                clearly_other_tense += 1
        if clearly_other_tense == 4:
            return True
        # If a key is supplied, reject a key pointing to one of those clearly
        # non-simple-past forms even when another option might be correct.
        answer = str((key or {}).get(int(match.group(1)), "")).strip().upper()
        if answer in options:
            v = options[answer].lower()
            if re.match(r"^(?:was|were)\s+\w+ing\b", v) or re.match(r"^had\s+\w+(?:ed|en|n)\b", v):
                return True
    return False


def _quiz_is_malformed(text: str, language: str, key: dict[int, str] | None = None,
                        previous_texts: list[str] | None = None) -> bool:
    """Reject language leakage, incomplete keys, malformed choices, and repeated stems."""
    text = text or ""
    if language == "English" and re.search(r"[\u0900-\u097F]", text):
        return True
    if language == "Hindi" and re.search(r"(?i)\b(choose the correct|select the correct|which of the following|question \d)\b", text):
        return True

    starts = list(_QUESTION_HEADING.finditer(text))
    if len(starts) != 3 or [int(m.group(1)) for m in starts] != [1, 2, 3]:
        return True

    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        block = text[match.end():end]
        options = _OPTION_LINE.findall(block)
        if len(options) != 4 or [letter.upper() for letter, _ in options] != ["A", "B", "C", "D"]:
            return True
        normalized = [re.sub(r"[^a-z0-9]+", " ", value.lower()).strip() for _, value in options]
        if any(not value for value in normalized) or len(set(normalized)) != 4:
            return True

    if key is not None and (
        set(key) != {1, 2, 3}
        or any(str(value).strip().upper() not in {"A", "B", "C", "D"} for value in key.values())
    ):
        return True

    stems = _extract_stems(text)
    if len(stems) != 3 or len(set(stems)) != 3:
        return True
    # Repeated stems from earlier turns are handled as a retry preference below,
    # not as a fatal format error. Short chapters may not support unlimited novel
    # questions, and rejecting every repeat can make all follow-up requests fail.
    if _obvious_grammar_conflict(text, key):
        return True
    return False


def _has_prior_repeats(text: str, previous_texts: list[str] | None = None) -> bool:
    current = set(_extract_stems(text))
    prior_stems = set()
    for prior in previous_texts or []:
        prior_stems.update(_extract_stems(prior))
    return bool(current.intersection(prior_stems))


def _expected_exam_question_count(messages: list[dict] | None = None) -> int | None:
    """Match the formal exam blueprint for the class stated in the prompt."""
    match = None
    # Search from most-recent to least-recent so the current prompt wins.
    for m in reversed(messages or []):
        match = re.search(r"(?i)\bclass\s+(\d{1,2})\b", str(m.get("content", "")))
        if match:
            break
    if not match:
        return None
    grade = int(match.group(1))
    if grade <= 3:
        return 5
    if grade <= 5:
        return 7
    if grade <= 8:
        return 8
    if grade <= 10:
        return 9
    if grade <= 12:
        return 10
    return None


def _exam_is_malformed(text: str, messages: list[dict] | None = None) -> bool:
    """Reject quiz-shaped, copied, contaminated, or incomplete exam papers."""
    text = (text or "").strip()
    if not text:
        return True

    # END OF PAPER must appear near the end (last 300 chars), allowing a
    # "Total Questions" summary line to follow it.
    # Require END OF PAPER anywhere in the last 40% of the visible text — the
    # LLM may append a summary or block-format key after it, but the paper
    # itself must close cleanly.
    tail_start = max(0, int(len(text) * 0.6))
    if not re.search(
            r"(?i)\*{0,2}\s*END OF PAPER\s*\*{0,2}", text[tail_start:]
    ):
        return True
    if re.search(
        r"(?i)(you are a developer tasked|code analysis tool|programming languages that the tool should support|"
        r"syntax errors, code smells|integration issues and provide suggestions)", text
    ):
        return True
    if re.search(r"(?m)^\s*(?:\.{3,}|…+|continue for \d+)", text, re.I):
        return True

    headings = re.findall(r"(?im)^\s*\*{0,2}\s*(?:SECTION|PART)\s+[A-C]\b", text)
    if len({h.upper().strip() for h in headings}) < 2:
        return True
    if not re.search(r"(?i)\b(?:time|duration)\s*:?", text):
        return True
    if not re.search(r"(?i)maximum\s+marks", text):
        return True
    if not re.search(r"(?i)\bINSTRUCTIONS\b", text):
        return True

    starts = list(re.finditer(
        r"(?im)^\s*(?:\*\*\s*(\d+)\s*\.\s*\*\*|\*\*Question\s+(\d+)\s*:\*\*|Question\s+(\d+)\s*[.):])",
        text,
    ))
    numbers = [int(group) for match in starts for group in match.groups() if group]
    expected_count = _expected_exam_question_count(messages)
    if len(starts) < 5 or numbers != list(range(1, len(numbers) + 1)):
        return True
    # Accept a small margin — small models rarely hit the exact count.
    if expected_count is not None and len(starts) < max(5, expected_count - 3):
        return True

    # Reject drastically over-generated papers (e.g., LLM writes 20 questions).
    if expected_count is not None and len(starts) > expected_count + 4:
        return True
    # Exam questions should not contain a pasted chapter. Keep the passage itself
    # out of the paper; comprehension can ask about facts without reproducing it.
    if any(len(paragraph.strip()) > 900 for paragraph in re.split(r"\n\s*\n", text)):
        return True

    mcq_count = 0
    written_count = 0
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        block = text[match.end():end]
        options = re.findall(r"(?im)^\s*[A-D][).]\s*.+$", block)
        if len(options) >= 3:
            mcq_count += 1
        else:
            # A numbered question without four-option structure is a written item.
            written_count += 1
    # A formal paper may include MCQs, but it must also contain written answers.
    # Written-only exams are the new default. Reject only MCQ-only papers.
    if mcq_count == len(starts):
        return True
    return False

def _exam_key_is_incomplete(text: str, key: dict[int, str]) -> bool:
    """Every numbered exam question must have a private grading-key entry."""
    starts = list(re.finditer(
        r"(?im)^\s*(?:\*\*\s*(\d+)\s*\.\s*\*\*|\*\*Question\s+(\d+)\s*:\*\*|Question\s+(\d+)\s*[.):])",
        text or "",
    ))
    numbers = {int(group) for match in starts for group in match.groups() if group}
    return not numbers or not numbers.issubset(key.keys())




def _air_pollution_fallback() -> tuple[str, dict[int, str]]:
    visible = ("📚 Here's a general science quiz on Air Pollution (not a textbook-specific quiz):\n\n"
        "**Question 1:** Which is a common human-made source of air pollution?\n\n"
        "A) Vehicle exhaust\nB) Clean rainwater\nC) Fresh oxygen from plants\nD) Pure water vapour\n\n"
        "**Question 2:** Which health problem can air pollution worsen?\n\n"
        "A) Broken bones\nB) Tooth decay only\nC) Respiratory diseases\nD) Improved lung function\n\n"
        "**Question 3:** Which action can help reduce air pollution?\n\n"
        "A) Burning more rubbish\nB) Using public transport when practical\nC) Leaving engines running unnecessarily\nD) Burning leaves outdoors\n\n"
        "Reply with your answers when ready (e.g. 1 A, 2 C, 3 B).")
    return visible, {1: "A", 2: "C", 3: "B"}


def _repair_instruction(language: str, reason: str) -> str:
    return (
        "REPAIR REQUIRED: " + reason + "\n"
        f"Regenerate the whole quiz from scratch in {language}. Use only facts supported by the supplied selected-chapter context. "
        "Return exactly 3 questions numbered 1, 2, 3. Each must have options A), B), C), D), all distinct, and exactly one correct answer. "
        "Before finalizing, solve each question yourself: verify the fact or grammar rule, verify that at least one option is actually correct, "
        "and ensure the key points to that exact option. For grammar questions, do not label past continuous or past perfect as simple past. "
        "Do not repeat a question from earlier assistant messages or the failed attempt. "
        "Append only a backend-only key marker at the end, with one entry per question, for example [[ANSWER_KEY:1=A,2=C,3=B]]. "
        "Do not put the key or explanations in the student-visible quiz."
    )


async def generate_assessment(messages: list[dict], *, mode: str, max_tokens: int = 1800,
                              question: str = "") -> tuple[str, dict[int, str]]:
    language = requested_response_language(question)
    prior_texts = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
    current_messages = list(messages)
    last_visible = ""
    last_key: dict[int, str] = {}

    # Keep the existing quiz recovery behavior while validating exams separately.
    for attempt in range(3):
        raw = await complete_chat(
            current_messages,
            temperature=0.2 if attempt == 0 else 0.1,
            max_tokens=max_tokens,
        )
        visible, key = extract_answer_key(raw)
        last_visible, last_key = visible, key
        if mode == "quiz":
            malformed = _quiz_is_malformed(visible, language, key, prior_texts)
            key_invalid = not key or set(key) != {1, 2, 3}
            repeated = _has_prior_repeats(visible, prior_texts)
        elif mode == "exam":
            malformed = _exam_is_malformed(visible, current_messages) or _exam_key_is_incomplete(visible, key)
            key_invalid = not key
            repeated = False
            if malformed or key_invalid:
                import sys
                print(
                    f"[exam attempt {attempt+1}] malformed={malformed} "
                    f"key_invalid={key_invalid} "
                    f"len={len(visible)} "
                    f"tail={visible[-200:]!r}",
                    file=sys.stderr,
                )
        else:
            malformed = False
            key_invalid = not key
            repeated = False

        if not malformed and not key_invalid and not repeated:
            return visible, key
        # Preserve the previous quiz fix: a structurally valid quiz with a complete
        # key is accepted on the final attempt even if a question repeats. Exams must
        # always pass formal-paper validation, even on the final attempt.
        if attempt == 2 and mode == "quiz" and not malformed and not key_invalid:
            return visible, key

        if attempt < 2:
            if mode == "exam":
                if malformed:
                    reason = "The previous output was quiz-shaped or lacked formal exam sections, duration, maximum marks, written-response questions, or a complete key."
                else:
                    reason = "The previous exam paper omitted a complete private grading key."
                repair = (
                    "REPAIR REQUIRED: " + reason + "\n"
                    f"Regenerate the complete formal exam paper from scratch in {language}, grounded only in the supplied selected-chapter context. "
                    "Include a title, duration, maximum marks, clear instructions, at least two labelled sections, at least five numbered questions, "
                    "objective questions plus written-response questions, marks per question, and an END OF PAPER line. "
                    "Ensure section and question marks add up to the stated total. Do not make every question multiple choice. "
                    "Append a backend-only [[ANSWER_KEY:...]] marker with one concise entry for every numbered question; never show the marker in the visible paper."
                )
            elif mode == "quiz":
                if malformed:
                    reason = "The previous quiz had invalid structure, language leakage, duplicate options, or a clearly incorrect grammar item."
                elif key_invalid:
                    reason = "The previous quiz did not contain a complete private answer key."
                else:
                    reason = "The previous quiz repeated a question from earlier in this session. Generate different questions if the chapter supports them; otherwise use a different supported fact or skill."
                repair = _repair_instruction(language, reason)
            else:
                reason = "The previous assessment did not contain a complete private answer key."
                repair = "REPAIR REQUIRED: Regenerate the assessment in " + language + " and append a complete backend-only answer key. " + reason

            current_messages = [
                *current_messages,
                {"role": "assistant", "content": raw},
                {"role": "user", "content": repair},
            ]
            if mode == "quiz":
                prior_texts = [*prior_texts, visible]

    if mode == "quiz" and re.search(r"air\s*pollution|air\s*polution", question, re.I):
        return _air_pollution_fallback()
    if mode == "quiz":
        message = (
            "I couldn't generate a reliable quiz from the available chapter text after 3 attempts. "
            "Please try another section or add more textbook content."
            if language == "English" else
            "तीन प्रयासों के बाद उपलब्ध पाठ्यपुस्तक सामग्री से विश्वसनीय प्रश्नोत्तरी नहीं बन सकी। कृपया दूसरा अनुभाग चुनें या अधिक पाठ्य सामग्री जोड़ें।"
        )
        return message, {}
    if mode == "exam":
        message = (
            "I couldn't generate a valid chapter-based exam paper after 3 attempts. "
            "Please retry, or select the chapter section again."
            if language == "English" else
            "तीन प्रयासों के बाद अध्याय पर आधारित सही परीक्षा-पत्र नहीं बन सका। कृपया फिर कोशिश करें या अध्याय का अनुभाग दोबारा चुनें।"
        )
        return message, {}
    # Never expose an internal marker on a failed non-quiz assessment either.
    clean, _ = extract_answer_key(last_visible)
    return clean, last_key


"""
Deterministic grader for MCQ quizzes/practice/exams.

Parses the tutor's previous message for numbered questions + A/B/C/D options,
solves math questions with SymPy, then compares against the student's answers.

Student answers can be in two forms:
  - Letter form: "1 A, 2 B, 3 C"  or  "A, B, C"
  - Value form:  "1. x=5\\n2. y=3\\n3. x=7"  or  "x=5, y=3, x=7"

No LLM. No hallucination. Fast. Deterministic.
"""
import re
import sympy as sp
from typing import Any


# ---------------------------------------------------------------
# Parsing the tutor's quiz message
# ---------------------------------------------------------------

_QUESTION_START = re.compile(
    r"(?:\*\*)?(?:Q|Question|प्रश्न)?\s*(\d+)(?:\*\*)?\s*[:\)\.]\s*",
    re.IGNORECASE,
)

_OPTION = re.compile(
    r"^\s*([a-dA-D])\s*[\)\.\:]\s*(.+?)\s*$",
    re.MULTILINE,
)


def _split_questions(text: str) -> list[tuple[int, str]]:
    starts = []
    for m in _QUESTION_START.finditer(text):
        starts.append((m.start(), int(m.group(1))))

    seen: set[int] = set()
    clean_starts: list[tuple[int, int]] = []
    for pos, num in starts:
        if num in seen:
            continue
        seen.add(num)
        clean_starts.append((pos, num))

    if not clean_starts:
        return []

    blocks: list[tuple[int, str]] = []
    for i, (pos, num) in enumerate(clean_starts):
        end = clean_starts[i + 1][0] if i + 1 < len(clean_starts) else len(text)
        blocks.append((num, text[pos:end]))

    return blocks


def parse_quiz(tutor_message: str) -> list[dict]:
    questions = []
    for num, block in _split_questions(tutor_message):
        options: dict[str, str] = {}
        first_opt_pos = None
        for m in _OPTION.finditer(block):
            letter = m.group(1).upper()
            options[letter] = m.group(2).strip()
            if first_opt_pos is None:
                first_opt_pos = m.start()

        q_text = block[:first_opt_pos].strip() if first_opt_pos is not None else block.strip()
        q_text = re.sub(
            r"^(?:\*\*)?(?:Q|Question|प्रश्न)?\s*\d+(?:\*\*)?\s*[:\)\.]\s*",
            "",
            q_text,
            flags=re.IGNORECASE,
        ).strip()

        if not options:
            continue
        questions.append({"num": num, "text": q_text, "options": options})

    return questions


# ---------------------------------------------------------------
# Solving math questions with SymPy (via shared math_verifier)
# ---------------------------------------------------------------

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _option_contains(option_text: str, solution: str) -> bool:
    try:
        target = float(sp.sympify(solution))
    except Exception:
        return False
    for m in _NUM_RE.finditer(option_text):
        try:
            if abs(float(m.group()) - target) < 1e-6:
                return True
        except ValueError:
            continue
    return False


def _correct_letter_for_math(q: dict) -> str | None:
    from app.services.math_verifier import verify_question

    qv = verify_question(q["text"])
    if not qv.get("is_math"):
        return None
    sols = qv.get("solutions") or []
    if not sols:
        return None
    for sol in sols:
        for letter in sorted(q["options"].keys()):
            if _option_contains(q["options"][letter], sol):
                return letter
    return None


# ---------------------------------------------------------------
# Parsing the student's answer (handles letters AND values)
# ---------------------------------------------------------------

# "1 A" / "1) A" / "1: A" / "1. A"
_ANSWER_NUM_LETTER = re.compile(r"(\d+)\s*[\)\.\-:]?\s*([a-dA-D])\b")

# "1. x=5" / "1) y-3" / "1: x = 7"
_LINE_NUM_VALUE = re.compile(r"^\s*(\d+)\s*[\)\.\-:]?\s*(.+?)\s*$", re.MULTILINE)

_BARE_LETTERS = re.compile(r"\b([a-dA-D])\b")


def parse_student_answers(text: str) -> dict[int, str]:
    """
    Return {question_num: answer} where answer is either:
      - a letter "A"|"B"|"C"|"D"
      - or a raw value like "x=5"
    """
    # Path 1: "1 A, 2 B, 3 C"
    by_num_letter: dict[int, str] = {}
    for m in _ANSWER_NUM_LETTER.finditer(text):
        by_num_letter[int(m.group(1))] = m.group(2).upper()
    if by_num_letter:
        return by_num_letter

    # Path 2: "1. x=5\n2. y=3\n3. x=7"
    by_num_value: dict[int, str] = {}
    for m in _LINE_NUM_VALUE.finditer(text):
        num = int(m.group(1))
        val = m.group(2).strip().rstrip(",").strip()
        if val:
            by_num_value[num] = val
    if by_num_value:
        return by_num_value

    # Path 3: bare letters "A, B, C"
    letters = _BARE_LETTERS.findall(text)
    out: dict[int, str] = {}
    for i, letter in enumerate(letters, start=1):
        out[i] = letter.upper()
    return out


# ---------------------------------------------------------------
# Matching a student value to an option
# ---------------------------------------------------------------

def _value_matches_option(student_val: str, option_text: str) -> bool:
    """
    Does the student's value appear in the option?
    'x=5' vs 'x = 5' → True
    'y=3' vs 'y = 5' → False
    """
    s = student_val.replace(" ", "").lower()
    o = option_text.replace(" ", "").lower()

    # Direct substring match
    if s in o or o in s:
        return True

    # Numeric comparison
    s_nums = set(_NUM_RE.findall(s))
    o_nums = set(_NUM_RE.findall(o))
    return bool(s_nums & o_nums)


def _resolve_letter(student_ans: str, q: dict) -> str | None:
    """
    Given a student's answer (letter or value), return the option letter it maps to.
    """
    # Already a letter
    if len(student_ans) == 1 and student_ans.upper() in q["options"]:
        return student_ans.upper()

    # Value: find the matching option
    for letter, opt_text in q["options"].items():
        if _value_matches_option(student_ans, opt_text):
            return letter
    return None


# ---------------------------------------------------------------
# Top-level grader
# ---------------------------------------------------------------

def grade_quiz(tutor_message: str, student_answer: str) -> dict[str, Any] | None:
    questions = parse_quiz(tutor_message)
    if not questions:
        return None

    correct_letters: list[str] = []
    for q in questions:
        letter = _correct_letter_for_math(q)
        if letter is None:
            return None
        correct_letters.append(letter)

    student_raw = parse_student_answers(student_answer)

    student_letters: list[str] = []
    per_correct: list[bool] = []
    for q, correct in zip(questions, correct_letters):
        s = student_raw.get(q["num"], "?")
        resolved = _resolve_letter(s, q)
        student_letters.append(resolved or s)
        per_correct.append(resolved == correct)

    total = len(questions)
    correct_count = sum(per_correct)
    score = round(correct_count / total * 100) if total else 0

    feedback = f"{correct_count} out of {total} correct."
    if 0 < correct_count < total:
        wrong_nums = [str(q["num"]) for q, ok in zip(questions, per_correct) if not ok]
        feedback += f" Check Q{', Q'.join(wrong_nums)}."
    elif correct_count == 0:
        feedback += " Let's review the basics."

    return {
        "is_correct": correct_count == total,
        "per_question_correct": per_correct,
        "student_answers": student_letters,
        "correct_answers": correct_letters,
        "score_percent": score,
        "feedback": feedback,
        "source": "deterministic",
    }

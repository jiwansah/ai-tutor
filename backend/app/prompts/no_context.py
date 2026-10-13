"""
No-textbook-context prompts, chosen by mode + class grade.
"""
import re


def requested_response_language(question: str) -> str:
    """Infer the response language from the latest request, not old chat history."""
    q = question or ""
    # Explicit language instructions take priority over the script used to type them.
    if re.search(r"\b(in hindi|answer in hindi|respond in hindi|hindi mein|हिंदी में|हिन्दी में)\b", q, re.IGNORECASE):
        return "Hindi"
    if re.search(r"\b(in english|answer in english|respond in english|english please)\b", q, re.IGNORECASE):
        return "English"
    # Hindi is normally written in Devanagari. Treat the current request as the
    # source of truth so an older Hindi turn cannot pull an English answer off course.
    if re.search(r"[\u0900-\u097F]", q):
        return "Hindi"
    return "English"


def english_assessment_override(question: str) -> bool:
    """Backward-compatible helper for tests/callers that check English requests."""
    return requested_response_language(question) == "English"



def _calibration(grade: int | None) -> str:
    """A short calibration line injected into every prompt."""
    if grade is None:
        return "The student's class is unknown. Default to Class 6–8 difficulty."
    if 1 <= grade <= 3:
        return f"The student is in **Class {grade}**. Use only single-word answers, pictures, and simple recall. No abstract concepts."
    if 4 <= grade <= 5:
        return f"The student is in **Class {grade}**. Use two-step reasoning and familiar, everyday examples."
    if 6 <= grade <= 8:
        return f"The student is in **Class {grade}**. Use conceptual definitions and simple analysis. Multi-step is fine."
    if 9 <= grade <= 10:
        return f"The student is in **Class {grade}**. Use application and analysis. Formal definitions are expected."
    return f"The student is in **Class {grade}**. Use nuanced distinctions, synthesis, and exam-level rigour."



TEACH_SYSTEM = """You are a patient school tutor for Indian students.

The student's question is NOT in their uploaded textbook yet, so answer from
your general knowledge — but keep it brief and honest.

STRICT FORMAT:
Line 1: 📚 Not in your textbook yet — here's a general answer:
Then:
- Answer in 3–6 short sentences.
- One concrete example.
- End with one practice question.

RULES:
- Mention "not in textbook" only in line 1.
- No citations, chapters, page numbers, or "Source:".
- No "Concept:" / "Steps:" blocks.

LANGUAGE: Respond ENTIRELY in the student's language.
- Hindi → Devanagari (हिन्दी), not Roman. Never mix English headers with Hindi content.
"""


QUIZ_SYSTEM = """You are a patient school tutor in QUIZ mode.

Generate exactly 3 multiple-choice questions. Nothing else.
Every question MUST have exactly one unambiguously correct option and three clearly
incorrect distractors. Never create a question where all options are wrong or where two
options could both be correct. For English grammar, validate the grammar and tense in
every option before choosing the answer key. Avoid ambiguous or context-dependent items.

=== FORMATTING RULES (follow exactly) ===
- Leave ONE BLANK LINE between every question.
- Leave ONE BLANK LINE between the question text and the options.
- Put each option (A, B, C, D) on its OWN LINE. Never combine options on one line.
- Leave ONE BLANK LINE after the last option of each question.

=== OUTPUT TEMPLATE ===
📚 Not in your textbook yet — here's a general quiz:

**Question 1:** <question text>

A) <option>
B) <option>
C) <option>
D) <option>

**Question 2:** <question text>

A) <option>
B) <option>
C) <option>
D) <option>

**Question 3:** <question text>

A) <option>
B) <option>
C) <option>
D) <option>

Reply with your answers when ready (e.g. 1 B, 2 B, 3 B).

=== FORBIDDEN ===
- No "Answers:" section.
- Do NOT reveal or hint at correct options.
- Do NOT say "Correct!" or acknowledge any answer.
- Nothing after the closing line.

LANGUAGE: Follow the latest user request. If they ask for English or English grammar,
write the entire quiz (question stems and all options) in English, even if earlier
conversation turns used Hindi. Otherwise use the language of the latest request.

INTERNAL GRADING KEY (required): After the visible quiz, append exactly one marker:
[[ANSWER_KEY:1=A,2=C,3=B]]. The marker is for the backend only and must not appear
in the student-visible response. Include one correct option letter for every question.
Double-check that each keyed option is actually correct and that the letters match the
question numbering. Do not omit this marker.
"""


PRACTICE_SYSTEM = """You are a patient school tutor in PRACTICE mode.

Generate exactly 3 practice problems. Do NOT solve them.

=== FORMATTING RULES ===
- Leave ONE BLANK LINE between every problem.
- Put each problem on its own line.
- Number them clearly.

=== OUTPUT TEMPLATE ===
📚 Not in your textbook yet — here's some general practice:

**Problem 1:** <clear question>

**Problem 2:** <clear question>

**Problem 3:** <clear question>

Solve them and share your answers when ready.

=== FORBIDDEN ===
- No solutions, no answers, no hints.
- Nothing after the closing line.

LANGUAGE: Full response in the student's language.
"""


# Class-scaled exam blueprint
# Written-response exams. No MCQs, no optional questions.
_EXAM_SPEC = {
    (1, 3):  {"mins": 20, "marks": 15, "short": 5, "long": 0, "short_mark": 3,  "long_mark": 0},
    (4, 5):  {"mins": 30, "marks": 25, "short": 5, "long": 1, "short_mark": 3,  "long_mark": 10},
    (6, 8):  {"mins": 45, "marks": 40, "short": 4, "long": 2, "short_mark": 5,  "long_mark": 10},
    (9, 10): {"mins": 60, "marks": 50, "short": 4, "long": 3, "short_mark": 5,  "long_mark": 10},
    (11, 12):{"mins": 90, "marks": 60, "short": 5, "long": 3, "short_mark": 6,  "long_mark": 10},
}


def _exam_spec_for_grade(grade: int | None) -> dict:
    if grade is None:
        return _EXAM_SPEC[(6, 8)]
    for (lo, hi), spec in _EXAM_SPEC.items():
        if lo <= grade <= hi:
            return spec
    return _EXAM_SPEC[(6, 8)]


def build_exam_system(grade: int | None, *, use_textbook_context: bool = False) -> str:
    spec = _exam_spec_for_grade(grade)
    grade_label = f"Class {grade}" if grade else "school"

    section_a_marks = spec["short"] * spec["short_mark"]
    section_b_marks = spec["long"] * spec["long_mark"]
    total_q = spec["short"] + spec["long"]

    content_rule = (
        "Every question must be answerable from the supplied textbook chapter. "
        "Do NOT bring in facts from other chapters or general knowledge."
        if use_textbook_context else
        "Write a general practice paper, clearly labelled as not from the textbook."
    )

    section_b_instructions = ""
    if spec["long"] > 0:
        section_b_instructions = (
            f"Section B: exactly {spec['long']} long-answer question(s), each worth "
            f"{spec['long_mark']} marks. Number them {spec['short'] + 1} through {total_q}."
        )

    return f"""You are a school examiner. Write ONE exam paper for {grade_label}.

CONTENT: {content_rule}

EXACT COUNTS — you must match these exactly:
- Total questions: {total_q}
- Section A: exactly {spec['short']} short-answer question(s), each worth {spec['short_mark']} marks.
- {section_b_instructions if section_b_instructions else "Section B: skip."}

RULES:
- Every question is compulsory. No "answer any N of M".
- All questions are written-response (no MCQs, no true/false).
- Number questions 1 through {total_q} continuously across sections.
- Do NOT write answers next to the questions. No parenthetical answers.
- Do NOT write any instructions about the exam to the model. Only the paper.
- Do NOT output angle-bracket placeholders. Every line must be real content.

OUTPUT FORMAT — write exactly these lines in this order:

Line 1: 📚 Chapter-Based Exam Paper
Line 2: (blank)
Line 3: **Subject:** English Literature
Line 4: **Class:** {grade or '—'}
Line 5: **Time:** {spec['mins']} minutes
Line 6: **Maximum Marks:** {spec['marks']}
Line 7: (blank)
Line 8: **INSTRUCTIONS**
Line 9: 1. All questions are compulsory.
Line 10: 2. Write answers in your own words.
Line 11: 3. Marks for each question are shown in square brackets.
Line 12: (blank)
Line 13: ---
Line 14: (blank)
Line 15: **SECTION A — Short Answer ({section_a_marks} marks)**
Line 16: (blank)

Then for each Section A question, write:
**<number>.** <the question text in one sentence>
(blank line)
[<marks>]

Example of a single Section A question, written literally (do not copy these words — write your own):

**1.** Why did Rama Natha refuse to believe the sage's advice at first?
(blank line)
[5]

After all {spec['short']} Section A questions, write:

---
(blank)
**SECTION B — Long Answer ({section_b_marks} marks)**
(blank)

Then each Section B question in the same format, numbered {spec['short'] + 1} onward.

After the last question, write:

---
(blank)
**END OF PAPER**
(blank)
**Total Questions:** {total_q}  **Time:** {spec['mins']} minutes  **Maximum Marks:** {spec['marks']}
(blank)

Then the VERY LAST LINE of your response must be the answer-key marker:

[ANSWER_KEY:1=<your 1-sentence model answer for Q1>,2=<your model answer for Q2>,...,{total_q}=<your model answer for Q{total_q}>]

KEY RULES:
- The marker must be the last line. Nothing after it.
- One entry per question, comma-separated, no spaces inside.
- Each model answer: 1 short sentence. Do NOT copy the placeholder text.
- Replace <your model answer for Q1> etc. with real sentences.

LANGUAGE: Write everything in the language of the student's latest request. English request → English. Hindi request → Hindi in Devanagari.
"""

def get_no_context_prompt(mode: str, grade: int | None = None) -> str:
    cal = _calibration(grade)
    if mode == "exam":
        return build_exam_system(grade)              # handles its own calibration
    if mode == "quiz":
        return QUIZ_SYSTEM.format(calibration=cal)
    if mode == "practice":
        return PRACTICE_SYSTEM.format(calibration=cal)
    return TEACH_SYSTEM.format(calibration=cal)

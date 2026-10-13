"""Assemble a formatted exam paper from LLM-generated JSON questions.

The LLM produces a JSON list of questions + model answers.
Python does all formatting. This removes every failure mode where a
small model was asked to produce a multi-section, hand-formatted paper.
"""
import json
import re
import structlog

from app.services.llm_service import complete_chat
from app.prompts.exam_json import EXAM_JSON_SYSTEM, EXAM_JSON_USER

logger = structlog.get_logger()


async def generate_exam_paper(
    *,
    subject_name: str,
    class_grade: int | None,
    chapter_name: str | None,
    context: str,
    spec: dict,
    language: str = "English",
) -> tuple[str, dict[int, str]]:
    """
    Returns (paper_text, answer_key).
    On failure returns ("", {}). Caller supplies the user-facing message.
    """
    total_q = spec["short"] + spec["long"]

    prompt = EXAM_JSON_USER.format(
        subject=subject_name or "General",
        grade=class_grade if class_grade is not None else "—",
        chapter=chapter_name or "—",
        short_count=spec["short"],
        short_marks=spec["short_mark"],
        long_count=spec["long"],
        long_marks=spec["long_mark"],
        total_q=total_q,
        context=(context or "(no textbook content available)")[:6000],
        language=language,
    )

    for attempt in range(3):
        try:
            raw = await complete_chat(
                [
                    {"role": "system", "content": EXAM_JSON_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2 if attempt == 0 else 0.1,
                max_tokens=2000,
                json_mode=True,
            )
        except Exception as e:
            logger.warning("exam_builder_llm_error", attempt=attempt + 1, error=str(e))
            continue

        raw = _strip_json_wrappers(raw)
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("exam_builder_json_error", attempt=attempt + 1, error=str(e), preview=raw[:200])
            continue

        questions_raw = data.get("questions")
        key_raw = data.get("answer_key") or {}

        if not isinstance(questions_raw, list) or len(questions_raw) != total_q:
            logger.warning("exam_builder_bad_questions_list", got=len(questions_raw) if isinstance(questions_raw, list) else -1, want=total_q)
            continue

        # ---- Validate + normalize questions ----
        normalized: list[dict] = []
        for i, q in enumerate(questions_raw):
            if not isinstance(q, dict):
                normalized = []
                break
            text = (q.get("text") or "").strip()
            if not text:
                normalized = []
                break
            expected_marks = spec["short_mark"] if i < spec["short"] else spec["long_mark"]
            normalized.append({
                "number": i + 1,
                "text": text,
                "marks": expected_marks,   # trust spec, not the LLM's number
                "section": "A" if i < spec["short"] else "B",
            })
        if not normalized:
            continue

        # ---- Validate + normalize answer key ----
        key: dict[int, str] = {}
        if isinstance(key_raw, dict):
            for k, v in key_raw.items():
                try:
                    num = int(k)
                except (ValueError, TypeError):
                    continue
                val = str(v).strip()
                if val:
                    key[num] = val
        if len(key) != total_q:
            logger.warning("exam_builder_bad_key", got=len(key), want=total_q)
            continue

        paper = _format_paper(
            subject=subject_name or "General",
            class_grade=class_grade,
            spec=spec,
            questions=normalized,
        )
        return paper, key

    return "", {}


def _strip_json_wrappers(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```\s*$", "", t)
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        t = t[first:last + 1]
    return t.strip()


def _format_paper(
    *,
    subject: str,
    class_grade: int | None,
    spec: dict,
    questions: list[dict],
) -> str:
    total_q = len(questions)
    total_marks = sum(q["marks"] for q in questions)

    section_a = [q for q in questions if q["section"] == "A"]
    section_b = [q for q in questions if q["section"] == "B"]

    lines: list[str] = [
        "📚 Chapter-Based Exam Paper",
        "",
        f"**Subject:** {subject}",
        f"**Class:** {class_grade if class_grade is not None else '—'}",
        f"**Time:** {spec['mins']} minutes",
        f"**Maximum Marks:** {total_marks}",
        "",
        "**INSTRUCTIONS**",
        "1. All questions are compulsory.",
        "2. Write answers in your own words.",
        "3. Marks for each question are shown in square brackets.",
        "",
        "---",
        "",
    ]

    if section_a:
        a_marks = sum(q["marks"] for q in section_a)
        lines.append(f"**SECTION A — Short Answer ({a_marks} marks)**")
        lines.append("")
        for q in section_a:
            lines.append(f"**{q['number']}.** {q['text']}")
            lines.append("")
            lines.append(f"[{q['marks']}]")
            lines.append("")

    if section_b:
        b_marks = sum(q["marks"] for q in section_b)
        lines.append("---")
        lines.append("")
        lines.append(f"**SECTION B — Long Answer ({b_marks} marks)**")
        lines.append("")
        for q in section_b:
            lines.append(f"**{q['number']}.** {q['text']}")
            lines.append("")
            lines.append(f"[{q['marks']}]")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**END OF PAPER**")
    lines.append("")
    lines.append(
        f"**Total Questions:** {total_q}  **Time:** {spec['mins']} minutes  "
        f"**Maximum Marks:** {total_marks}"
    )

    return "\n".join(lines)

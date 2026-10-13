"""JSON-mode prompt for exam question generation.

The LLM only returns structured questions + answer key. Python then
formats the paper. Small models are far more reliable at producing a
JSON list than at producing a multi-section prose document.
"""

EXAM_JSON_SYSTEM = """You generate exam questions as structured JSON only.
Return ONLY valid JSON. No prose, no markdown, no explanation, no code fences.
The JSON must match the requested schema exactly."""


EXAM_JSON_USER = """Write exam questions for the chapter below.

Subject: {subject}
Class: {grade}
Chapter: {chapter}
Language: {language}

TEXTBOOK CONTENT (use ONLY this content for question material):
{context}

TASK:
Write exactly {short_count} short-answer question(s) worth {short_marks} marks each,
and exactly {long_count} long-answer question(s) worth {long_marks} marks each.
Total questions: {total_q}.

RULES:
- Every question must be answerable from the TEXTBOOK CONTENT above.
- Do NOT use facts from other chapters or outside knowledge.
- Short-answer questions expect 1-2 sentence answers.
- Long-answer questions expect a paragraph-length answer.
- All questions are written-response. No multiple choice.
- Number questions 1 through {total_q} continuously.
- Provide one short model answer per question in the answer_key.

RETURN EXACTLY THIS JSON SHAPE, with real values:

{{
  "questions": [
    {{"number": 1, "text": "the first question text", "marks": {short_marks}}},
    {{"number": 2, "text": "the second question text", "marks": {short_marks}}},
    {{"number": {total_q}, "text": "the last question text", "marks": {long_marks}}}
  ],
  "answer_key": {{
    "1": "one-sentence model answer for Q1",
    "2": "one-sentence model answer for Q2",
    "{total_q}": "one-sentence model answer for Q{total_q}"
  }}
}}

Write every field in {language}. Return JSON only. Nothing before or after it.
"""

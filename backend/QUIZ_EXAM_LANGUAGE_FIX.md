# Quiz / Exam language and grading-key fix

## Changes
- Quiz and exam prompts in the no-textbook-context path now require an internal `[[ANSWER_KEY:...]]` marker, so the backend can store a key for grading.
- Quiz prompts explicitly require exactly one unambiguous correct option and three incorrect distractors.
- Exam prompts explicitly require a key entry for every question, including short/long-answer questions.
- The latest request overrides earlier chat language for English / English grammar assessments. In quiz, exam, and practice modes, a request mentioning English forces question stems, instructions, and options to be written in English.
- The private answer-key marker continues to be stripped before the assessment is shown to the student.

## Validation
Run from the backend directory:

```bash
python -m pytest -q tests/test_answer_key_grading.py tests/test_english_assessment_prompts.py
```

The included tests cover deterministic answer-key grading, the no-context quiz key requirement, English-request detection, and full exam key instructions.

## Important limitation
Grading against a saved answer key is deterministic. However, an LLM can still generate a wrong key or an invalid question. The prompt now explicitly guards against ambiguous multiple-choice questions, but strict high-stakes grading should use teacher-reviewed question banks and rubrics.

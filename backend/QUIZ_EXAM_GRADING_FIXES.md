# Quiz and Exam Grading Fixes

## Follow-up fix for `/api/v1/tutor/answer` HTTP 500

The grader call passed `answer_key` and `assessment_mode`, but `evaluate_answers()` did not accept those keyword arguments. This raised a Python `TypeError` and surfaced as HTTP 500. The evaluator signature now accepts both arguments. The non-streaming tutor path also extracts and stores the private answer key, and detected quiz/exam intent is passed through to the prompt builder. The no-context exam prompt now requests an internal grading marker without exposing it in the visible paper.

## What changed
- Quiz/exam generation now requests a private `[[ANSWER_KEY:...]]` marker.
- Assessment responses are buffered until generation finishes; the marker is removed before the response is sent to the frontend.
- The parsed answer key is saved in the tutor message metadata, not in the visible answer.
- Answer submission compares responses against that saved key deterministically, without asking the LLM to re-grade the assessment.
- If a quiz/exam key is missing, grading fails safely with an explanatory message instead of inventing a score.
- Removed the duplicate `submit_answer` method and replaced dangerous substring/number-overlap option matching with normalized exact matching.
- Added regression tests for key extraction, answer matching, partial scores, and missing answers.

## Important accuracy note
The *comparison* against a saved key is deterministic. The local language model still authors the questions and key, so this cannot honestly guarantee 100% factual correctness of every generated question/key. For high-stakes or truly guaranteed grading, use a teacher-reviewed question bank with stored correct answers and rubrics. Free-response answers that permit synonyms or equivalent explanations need a reviewed rubric or human review; strict normalized text comparison can reject a valid synonym.

## Validation
- `python -m compileall app` passes.
- `python -m pytest -q tests/test_answer_key_grading.py` passes (4 tests).
- The full test suite could not be collected in this environment because `pgvector` is not installed (`ModuleNotFoundError`). Install the backend dependencies and rerun the full suite in the project's Docker environment.

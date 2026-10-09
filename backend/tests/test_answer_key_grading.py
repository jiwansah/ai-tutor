from app.services.quiz_grader import extract_answer_key, grade_with_answer_key


def test_extracts_and_removes_private_key():
    visible, key = extract_answer_key("Q1: 2+2?\\nA) 3\\nB) 4\\n[[ANSWER_KEY:1=B]]")
    assert "ANSWER_KEY" not in visible
    assert key == {1: "B"}


def test_mcq_grading_is_exact():
    result = grade_with_answer_key("1 B, 2 A, 3 D", {1: "B", 2: "C", 3: "D"})
    assert result["per_question_correct"] == [True, False, True]
    assert result["score_percent"] == 67
    assert result["correct_answers"] == ["B", "C", "D"]


def test_short_answer_is_normalized_but_not_substring_matched():
    result = grade_with_answer_key("1. Photosynthesis", {1: "photo synthesis"})
    assert result["is_correct"] is True

    result = grade_with_answer_key("1. 15", {1: "5"})
    assert result["is_correct"] is False


def test_missing_answer_is_incorrect():
    result = grade_with_answer_key("1 A", {1: "A", 2: "C"})
    assert result["per_question_correct"] == [True, False]


def test_evaluator_accepts_answer_key_arguments():
    import ast
    from pathlib import Path

    source = Path("app/services/evaluator_service.py").read_text()
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "evaluate_answers")
    names = {arg.arg for arg in fn.args.kwonlyargs}
    assert {"answer_key", "assessment_mode"} <= names

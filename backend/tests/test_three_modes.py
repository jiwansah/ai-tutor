from app.services.intent import normalize_mode, detect_intent
from app.prompts.tutor_modes import MODES, get_system_prompt
from app.prompts.no_context import get_no_context_prompt


def test_only_three_canonical_modes():
    assert set(MODES) == {"teaching", "quiz", "exam"}
    assert normalize_mode("teacher") == "teaching"
    assert normalize_mode("socratic") == "teaching"
    assert normalize_mode("hint") == "teaching"
    assert normalize_mode("practice") == "quiz"
    assert normalize_mode("revision") == "teaching"
    assert normalize_mode("quiz") == "quiz"
    assert normalize_mode("exam") == "exam"


def test_teaching_intent_routes_assessment_requests():
    assert detect_intent("Give me some questions from this chapter") == "quiz"
    assert detect_intent("Give me a quiz on Air Pollution") == "quiz"
    assert detect_intent("Create a mock exam") == "exam"
    assert detect_intent("Give me brief information about this chapter") is None


def test_legacy_no_context_modes_normalize():
    assert get_no_context_prompt("teacher", 7) == get_no_context_prompt("teaching", 7)
    assert get_no_context_prompt("practice", 7) == get_no_context_prompt("quiz", 7)

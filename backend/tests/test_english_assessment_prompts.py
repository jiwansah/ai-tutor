from app.prompts.no_context import get_no_context_prompt
from app.prompts.no_context import english_assessment_override


def test_no_context_quiz_requires_internal_answer_key():
    prompt = get_no_context_prompt("quiz", 7)
    assert "INTERNAL GRADING KEY (required)" in prompt
    assert "[[ANSWER_KEY:1=A,2=C,3=B]]" in prompt
    assert "Do not omit this marker" in prompt


def test_english_grammar_request_is_detected_as_language_override():
    assert english_assessment_override("Give me some questions on English grammar nouns")
    assert english_assessment_override("Give me some question in English")
    assert not english_assessment_override("मुझे हिंदी में प्रश्न दीजिए")


def test_exam_key_instruction_requires_all_question_numbers():
    prompt = get_no_context_prompt("exam", 7)
    assert "Include EVERY question number" in prompt
    assert "Do not omit any question" in prompt


def test_language_is_based_on_latest_question_for_all_modes():
    from app.prompts.no_context import requested_response_language

    assert requested_response_language("What is a noun? Give examples.") == "English"
    assert requested_response_language("संज्ञा क्या है? उदाहरण दीजिए।") == "Hindi"
    assert requested_response_language("Explain photosynthesis in simple terms.") == "English"
    assert requested_response_language("Please answer in Hindi: what is a noun?") == "Hindi"

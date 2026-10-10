from app.services.response_quality import _practice_response_is_malformed, _english_grammar_fallback


def test_english_practice_rejects_hindi_script():
    assert _practice_response_is_malformed("Question 1: <सुनने के लिए सही वाक्यांश>", "English")


def test_practice_rejects_duplicate_mcq_options():
    text = """**Question 1:** Choose the correct sentence.
A) She is happy.
B) She is happy.
C) She is happy.
D) She is happy.
"""
    assert _practice_response_is_malformed(text, "English")


def test_practice_accepts_distinct_english_options():
    text = """**Question 1:** Choose the correct sentence.
A) She is happy.
B) She are happy.
C) She be happy.
D) She were happy.
"""
    assert not _practice_response_is_malformed(text, "English")


def test_english_grammar_fallback_is_valid_english_practice():
    result = _english_grammar_fallback("Give me some Question on English Grammer")
    assert result and "Problem 1" in result and "Problem 3" in result
    assert not _practice_response_is_malformed(result, "English")

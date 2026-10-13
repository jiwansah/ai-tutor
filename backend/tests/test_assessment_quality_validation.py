from app.services.assessment_generation import _quiz_is_malformed

VALID = """**Question 1:** What causes air pollution?
A) Vehicle exhaust
B) Clean rainwater
C) Fresh oxygen
D) Pure water

**Question 2:** Which issue can pollution worsen?
A) Broken bones
B) Tooth growth
C) Respiratory diseases
D) Better eyesight

**Question 3:** Which action helps reduce pollution?
A) Burn more rubbish
B) Use public transport
C) Idle engines
D) Burn leaves
"""


def test_quiz_validator_requires_complete_key_and_unique_options():
    assert not _quiz_is_malformed(VALID, "English", {1: "A", 2: "C", 3: "B"})
    assert _quiz_is_malformed(VALID, "English", {1: "A", 2: "C"})
    duplicate = VALID.replace("B) Clean rainwater", "B) Vehicle exhaust")
    assert _quiz_is_malformed(duplicate, "English", {1: "A", 2: "C", 3: "B"})


def test_quiz_validator_rejects_language_leakage_and_repeats():
    assert _quiz_is_malformed(VALID + "\nसही उत्तर", "English", {1: "A", 2: "C", 3: "B"})
    assert _quiz_is_malformed(VALID, "English", {1: "A", 2: "C", 3: "B"}, [VALID])

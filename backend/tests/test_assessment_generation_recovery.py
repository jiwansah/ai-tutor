import pytest
from app.services.assessment_generation import _quiz_is_malformed, generate_assessment

VALID = """**Question 1:** Which animal is mentioned in the story?
A) Elephant
B) Tiger
C) Whale
D) Penguin

**Question 2:** Which word is a noun?
A) Quickly
B) Blue
C) Friendship
D) Run

**Question 3:** Which action helps a friend?
A) Ignore them
B) Help them
C) Hide from them
D) Laugh at them
"""


def test_rejects_simple_past_question_with_no_simple_past_option():
    quiz = """**Question 1:** Which verb is in the Simple Past Tense?
A) was looking
B) was missing
C) had ordered
D) was munching

**Question 2:** Which animal is mentioned?
A) Elephant
B) Tiger
C) Whale
D) Penguin

**Question 3:** Which word is a noun?
A) Quickly
B) Blue
C) Friendship
D) Run
"""
    assert _quiz_is_malformed(quiz, "English", {1: "C", 2: "A", 3: "C"})


def test_accepts_plain_and_markdown_heading_styles():
    assert not _quiz_is_malformed(VALID, "English", {1: "A", 2: "C", 3: "B"})


@pytest.mark.asyncio
async def test_retries_three_times_then_returns_safe_failure(monkeypatch):
    from app.services import assessment_generation as module
    calls = 0
    async def fake_complete_chat(*args, **kwargs):
        nonlocal calls
        calls += 1
        return "not a valid quiz"
    monkeypatch.setattr(module, "complete_chat", fake_complete_chat)
    visible, key = await generate_assessment([], mode="quiz", question="Give me a quiz on Friendship")
    assert calls == 3
    assert key == {}
    assert "after 3 attempts" in visible
    assert "ANSWER_KEY" not in visible

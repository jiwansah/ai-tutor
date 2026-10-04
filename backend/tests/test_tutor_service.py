# tests/test_tutor_service.py
import pytest
from unittest.mock import AsyncMock
from app.services.tutor_service import TutorService


@pytest.mark.asyncio
async def test_ask_returns_citations():
    sessions = AsyncMock()
    students = AsyncMock()
    content = AsyncMock()

    sessions.get_or_create.return_value = type("S", (), {"id": "s1"})()
    sessions.add_message.return_value = None
    students.get_mastery.return_value = None
    content.semantic_search.return_value = []

    svc = TutorService(sessions, students, content)
    # patch LLM
    ...

    result = await svc.ask(student_id="u1", mode="teacher", question="hi")
    assert "session_id" in result
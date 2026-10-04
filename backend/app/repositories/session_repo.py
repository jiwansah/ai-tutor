from sqlalchemy import select
from app.db.models.session import TutorSession, Message, Attempt
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[TutorSession]):
    model = TutorSession

    async def get_or_create(
        self,
        session_id: str | None,
        student_id,
        mode: str,
        subject_id=None,
        chapter_id=None,
        section_id=None,
    ) -> TutorSession:
        if session_id:
            existing = await self.get(session_id)
            if existing:
                return existing
        s = TutorSession(
            student_id=student_id,
            mode=mode,
            subject_id=subject_id,
            chapter_id=chapter_id,
            section_id=section_id,
        )
        self.db.add(s)
        await self.db.flush()
        return s

    async def add_message(self, session_id, role: str, content: str, citations=None, meta=None):
        m = Message(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            meta=meta or {},
        )
        self.db.add(m)
        await self.db.flush()
        return m

    async def list_messages(self, session_id, limit: int = 100):
        return list((await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )).scalars().all())

    async def log_attempt(self, **kwargs) -> Attempt:
        a = Attempt(**kwargs)
        self.db.add(a)
        await self.db.flush()
        return a
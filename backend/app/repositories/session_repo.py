from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.session import TutorSession, Message, Attempt


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, session_id) -> TutorSession | None:
        return (await self.db.execute(
            select(TutorSession).where(TutorSession.id == session_id)
        )).scalar_one_or_none()

    async def get_or_create(self, session_id, student_id, mode,
                            subject_id=None, chapter_id=None, section_id=None):
        if session_id:
            existing = await self.get(session_id)
            if existing:
                return existing
        s = TutorSession(student_id=student_id, mode=mode,
                         subject_id=subject_id, chapter_id=chapter_id, section_id=section_id)
        self.db.add(s)
        await self.db.flush()
        return s

    async def add_message(self, session_id, role, content, citations=None, meta=None):
        m = Message(session_id=session_id, role=role, content=content,
                    citations=citations or [], meta=meta or {})
        self.db.add(m)
        await self.db.flush()
        return m

    async def log_attempt(self, **kwargs) -> Attempt:
        a = Attempt(**kwargs)
        self.db.add(a)
        await self.db.flush()
        return a


    async def get_last_tutor_message(self, session_id):
        from app.db.models.session import Message
        stmt = (
            select(Message)
            .where(Message.session_id == session_id, Message.role == "tutor")
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


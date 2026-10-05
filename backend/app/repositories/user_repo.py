from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.db.models.student import StudentProfile


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        return (await self.db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    async def get(self, user_id) -> User | None:
        return (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    async def add(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user

    async def create_student_profile(self, user_id) -> StudentProfile:
        p = StudentProfile(user_id=user_id)
        self.db.add(p)
        await self.db.flush()
        return p

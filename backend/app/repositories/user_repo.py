from sqlalchemy import select
from app.db.models.user import User, UserRole
from app.db.models.student import StudentProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return (await self.db.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()

    async def create_student_profile(self, user_id) -> StudentProfile:
        profile = StudentProfile(user_id=user_id)
        self.db.add(profile)
        await self.db.flush()
        return profile
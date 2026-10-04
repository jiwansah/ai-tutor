from app.repositories.user_repo import UserRepository
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.db.models.user import User, UserRole
from fastapi import HTTPException, status


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, email: str, password: str, full_name: str, role: str, language: str = "en"):
        if await self.user_repo.get_by_email(email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole(role),
            language=language,
        )
        await self.user_repo.add(user)

        if user.role == UserRole.STUDENT:
            await self.user_repo.create_student_profile(user.id)

        return self._tokens(user)

    async def login(self, email: str, password: str):
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
        return self._tokens(user)

    def _tokens(self, user: User) -> dict:
        return {
            "access_token": create_access_token(str(user.id), user.role.value),
            "refresh_token": create_refresh_token(str(user.id)),
            "user": user,
        }
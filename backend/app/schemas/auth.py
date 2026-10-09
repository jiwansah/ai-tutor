from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from app.db.models.user import User, UserRole
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.STUDENT
    language: str = "en"
    # Student enrollment (required for students, ignored for others)
    school_id: UUID | None = None
    class_id: UUID | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    language: str
    school_id: UUID | None = None
    class_id: UUID | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class UpdateMeRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    language: str | None = Field(default=None, min_length=2, max_length=10)
    preferred_style: str | None = Field(default=None, max_length=30)
    school_id: UUID | None = None      # NEW
    class_id: UUID | None = None       # NEW


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

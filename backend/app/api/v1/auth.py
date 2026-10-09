from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from sqlalchemy import select
from app.db.models.curriculum import Class as ClassModel
from uuid import UUID
from pydantic import BaseModel, EmailStr


router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(payload.email):
        raise HTTPException(409, "Email already registered")

    # Validate student enrollment
    if payload.role == UserRole.STUDENT:
        if not payload.school_id or not payload.class_id:
            raise HTTPException(400, "Students must specify school_id and class_id")
        # Verify the class belongs to the school
        from app.db.models.curriculum import Class as ClassModel
        cls = (await db.execute(
            select(ClassModel).where(
                ClassModel.id == payload.class_id,
                ClassModel.school_id == payload.school_id,
            )
        )).scalar_one_or_none()
        if not cls:
            raise HTTPException(400, "Class does not belong to the given school")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole(payload.role.value),
        language=payload.language,
        school_id=payload.school_id,
        class_id=payload.class_id,
    )
    await repo.add(user)
    if user.role == UserRole.STUDENT:
        await repo.create_student_profile(user.id)

    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


# ---------------------------------------------------------------
# Profile
# ---------------------------------------------------------------

from app.deps_helpers import current_user
from app.db.models.student import StudentProfile
from app.schemas.auth import UpdateMeRequest, ChangePasswordRequest


class MeResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    language: str
    school_id: UUID | None = None
    class_id: UUID | None = None
    preferred_style: str | None = None

    model_config = {"from_attributes": True}


@router.get("/me", response_model=MeResponse)
async def get_me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    preferred = None
    if user.role == UserRole.STUDENT:
        profile = (await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        )).scalar_one_or_none()
        if profile:
            preferred = profile.preferred_style

    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        language=user.language,
        school_id=user.school_id,
        class_id=user.class_id,
        preferred_style=preferred,
    )


@router.patch("/me", response_model=MeResponse)
async def update_me(
    payload: UpdateMeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.language is not None:
        user.language = payload.language
    if payload.preferred_style is not None and user.role == UserRole.STUDENT:
        profile = (await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        )).scalar_one_or_none()
        if profile:
            profile.preferred_style = payload.preferred_style

    # --- Enrollment change (students only) ---
    if user.role == UserRole.STUDENT and (payload.school_id or payload.class_id):
        new_school = payload.school_id or user.school_id
        new_class = payload.class_id or user.class_id

        if not new_school or not new_class:
            raise HTTPException(400, "Both school and class must be set")

        # Validate the class belongs to the school
        from app.db.models.curriculum import Class as ClassModel
        cls = (await db.execute(
            select(ClassModel).where(
                ClassModel.id == new_class,
                ClassModel.school_id == new_school,
            )
        )).scalar_one_or_none()
        if not cls:
            raise HTTPException(400, "Selected class does not belong to the selected school")

        user.school_id = new_school
        user.class_id = new_class

    await db.commit()
    await db.refresh(user)
    return await get_me(user=user, db=db)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if payload.old_password == payload.new_password:
        raise HTTPException(400, "New password must be different from current password")

    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"status": "ok", "message": "Password updated"}

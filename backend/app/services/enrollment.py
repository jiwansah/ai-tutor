from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.db.models.user import User, UserRole
from app.db.models.curriculum import School, Class, Subject, Book, Chapter, Section


async def student_can_access_section(
    db: AsyncSession, user: User, section_id: str | None
) -> bool:
    """
    True if the section belongs to a school+class the student is enrolled in.
    Non-students (teachers/admins) always pass.
    """
    if user.role in (UserRole.TEACHER, UserRole.ADMIN):
        return True
    if not section_id:
        return True  # general questions allowed

    if not user.school_id or not user.class_id:
        raise HTTPException(403, "Student is not enrolled in any school/class")

    # Check section → chapter → book → subject → class → school
    stmt = (
        select(Section.id)
        .join(Chapter, Section.chapter_id == Chapter.id)
        .join(Book, Chapter.book_id == Book.id)
        .join(Subject, Book.subject_id == Subject.id)
        .join(Class, Subject.class_id == Class.id)
        .where(
            Section.id == section_id,
            Class.id == user.class_id,
            Class.school_id == user.school_id,
        )
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return row is not None


async def enforce_section_access(db: AsyncSession, user: User, section_id: str | None) -> None:
    if not await student_can_access_section(db, user, section_id):
        raise HTTPException(403, "This section is not part of your enrolled class")

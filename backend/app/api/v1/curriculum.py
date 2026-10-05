from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.curriculum import School, Class, Subject, Book, Chapter, Section

router = APIRouter()


@router.get("/schools")
async def list_schools(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(School))).scalars().all()
    return [{"id": str(s.id), "name": s.name, "board": s.board} for s in rows]


@router.get("/classes/{school_id}")
async def list_classes(school_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Class).where(Class.school_id == school_id))).scalars().all()
    return [{"id": str(c.id), "grade": c.grade} for c in rows]


@router.get("/subjects/{class_id}")
async def list_subjects(class_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Subject).where(Subject.class_id == class_id))).scalars().all()
    return [{"id": str(s.id), "name": s.name} for s in rows]


@router.get("/chapters/{subject_id}")
async def list_chapters(subject_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Chapter).join(Book, Chapter.book_id == Book.id).where(Book.subject_id == subject_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": str(c.id), "number": c.number, "title": c.title} for c in rows]


@router.get("/sections/{chapter_id}")
async def list_sections(chapter_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Section).where(Section.chapter_id == chapter_id))).scalars().all()
    return [{"id": str(s.id), "number": s.number, "title": s.title} for s in rows]

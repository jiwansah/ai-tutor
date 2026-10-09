from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.curriculum import School, Class, Subject

router = APIRouter()


@router.get("/schools")
async def public_schools(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(School).order_by(School.name)
    )).scalars().all()
    return [{"id": str(s.id), "name": s.name, "board": s.board} for s in rows]


@router.get("/schools/{school_id}/classes")
async def public_classes(school_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Class).where(Class.school_id == school_id).order_by(Class.grade)
    )).scalars().all()
    return [{"id": str(c.id), "grade": c.grade} for c in rows]


@router.get("/classes/{class_id}/subjects")
async def public_subjects(class_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Subject).where(Subject.class_id == class_id).order_by(Subject.name)
    )).scalars().all()
    return [{"id": str(s.id), "name": s.name} for s in rows]

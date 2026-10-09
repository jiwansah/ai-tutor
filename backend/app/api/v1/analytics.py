from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps_helpers import current_user
from app.db.models.user import User
from app.services import analytics_service as A

router = APIRouter()


def require_teacher_or_admin(user: User = Depends(current_user)) -> User:
    if user.role.value not in ("teacher", "admin"):
        raise HTTPException(403, "Teacher or admin role required")
    return user


def _parse_uuid(value: str, name: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError):
        raise HTTPException(400, f"Invalid {name}: expected a UUID, got '{value}'")


@router.get("/school/{school_id}/summary")
async def school_summary(
    school_id: str,
    days: int = Query(30, ge=1, le=365),
    _: User = Depends(require_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    sid = _parse_uuid(school_id, "school_id")
    return await A.school_summary(db, sid, days)


@router.get("/school/{school_id}/trend")
async def school_trend(
    school_id: str,
    days: int = Query(14, ge=1, le=90),
    _: User = Depends(require_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    sid = _parse_uuid(school_id, "school_id")
    return await A.school_trend(db, sid, days)


@router.get("/class/{class_id}/summary")
async def class_summary(
    class_id: str,
    days: int = Query(30, ge=1, le=365),
    _: User = Depends(require_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    cid = _parse_uuid(class_id, "class_id")
    return await A.class_summary(db, cid, days)


@router.post("/rollup/{day}")
async def trigger_rollup(
    day: str,
    _: User = Depends(require_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    # Validate YYYY-MM-DD
    from datetime import datetime
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, f"Invalid day: expected YYYY-MM-DD, got '{day}'")

    await A.compute_daily_rollup(db, day)
    return {"status": "ok", "day": day}

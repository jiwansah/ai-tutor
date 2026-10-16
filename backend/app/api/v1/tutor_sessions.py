"""List and fetch a student's past tutor sessions."""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.session import TutorSession, Message
from app.db.models.curriculum import Subject, Chapter, Section
from app.repositories.student_repo import StudentRepository
from app.api.v1.tutor import current_user

router = APIRouter()


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the student's recent sessions, newest first."""
    profile = await StudentRepository(db).get_profile_by_user(user.id)
    if not profile:
        raise HTTPException(400, "Student profile missing")

    # Fetch sessions
    sessions = list((await db.execute(
        select(TutorSession)
        .where(TutorSession.student_id == profile.id)
        .order_by(desc(TutorSession.created_at))
        .limit(limit)
    )).scalars().all())

    if not sessions:
        return []

    session_ids = [s.id for s in sessions]

    # Message count per session
    counts = dict((await db.execute(
        select(Message.session_id, func.count(Message.id))
        .where(Message.session_id.in_(session_ids))
        .group_by(Message.session_id)
    )).all())

    # First user message per session (as a preview/title)
    first_msgs: dict[uuid.UUID, str] = {}
    rows = (await db.execute(
        select(Message.session_id, Message.content, Message.created_at)
        .where(Message.session_id.in_(session_ids), Message.role == "user")
        .order_by(Message.session_id, Message.created_at)
    )).all()
    for sid, content, _ in rows:
        if sid not in first_msgs:
            first_msgs[sid] = (content or "").strip()[:120]

    # Resolve subject / chapter / section names
    subject_ids = {s.subject_id for s in sessions if s.subject_id}
    chapter_ids = {s.chapter_id for s in sessions if s.chapter_id}
    section_ids = {s.section_id for s in sessions if s.section_id}

    subject_map, chapter_map, section_map = {}, {}, {}
    if subject_ids:
        for sid, name in (await db.execute(
            select(Subject.id, Subject.name).where(Subject.id.in_(subject_ids))
        )).all():
            subject_map[sid] = name
    if chapter_ids:
        for cid, title in (await db.execute(
            select(Chapter.id, Chapter.title).where(Chapter.id.in_(chapter_ids))
        )).all():
            chapter_map[cid] = title
    if section_ids:
        for sid, title in (await db.execute(
            select(Section.id, Section.title).where(Section.id.in_(section_ids))
        )).all():
            section_map[sid] = title

    return [
        {
            "id": str(s.id),
            "mode": s.mode,
            "subject": subject_map.get(s.subject_id),
            "chapter": chapter_map.get(s.chapter_id),
            "section": section_map.get(s.section_id),
            "preview": first_msgs.get(s.id, "(empty)"),
            "message_count": counts.get(s.id, 0),
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the full message history for one of the student's sessions."""
    profile = await StudentRepository(db).get_profile_by_user(user.id)
    if not profile:
        raise HTTPException(400, "Student profile missing")

    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session_id")

    session = (await db.execute(
        select(TutorSession).where(TutorSession.id == sid)
    )).scalar_one_or_none()
    if not session or session.student_id != profile.id:
        raise HTTPException(404, "Session not found")

    msgs = list((await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
    )).scalars().all())

    return {
        "id": str(session.id),
        "mode": session.mode,
        "subject_id": str(session.subject_id) if session.subject_id else None,
        "chapter_id": str(session.chapter_id) if session.chapter_id else None,
        "section_id": str(session.section_id) if session.section_id else None,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "citations": m.citations or [],
                "meta": m.meta or {},
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }
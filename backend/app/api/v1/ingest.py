from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.user import User
from app.deps import require_role
from app.db.models.curriculum import Chapter, Section, Book
from app.db.models.content import ContentChunk
from app.services.ingest_service import chunk_section_text
from app.services.embedding_service import embed_batch

router = APIRouter()


@router.post("/section")
async def ingest_section(
    section_id: str = Form(...),
    text: str = Form(...),
    user: User = Depends(require_role("teacher", "admin")),
    db: AsyncSession = Depends(get_db),
):
    section = (await db.execute(select(Section).where(Section.id == section_id))).scalar_one_or_none()
    if not section:
        raise HTTPException(404, "Section not found")

    chunks = chunk_section_text(text)  # returns list[dict(text, type, page)]
    embeddings = embed_batch([c["text"] for c in chunks])

    for c, emb in zip(chunks, embeddings):
        db.add(ContentChunk(
            section_id=section.id,
            chunk_type=c.get("type", "concept"),
            text=c["text"],
            page=c.get("page"),
            embedding=emb,
            meta={},
        ))

    await db.commit()
    return {"ingested": len(chunks), "section_id": section_id}
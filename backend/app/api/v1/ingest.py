from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.curriculum import Section
from app.db.models.content import ContentChunk
from app.repositories.content_repo import ContentRepository
from app.api.v1.tutor import current_user
from app.db.models.user import User
from app.services.embedding_service import embed_batch

router = APIRouter()


@router.post("/section")
async def ingest_section(
    section_id: str = Form(...),
    text: str = Form(...),
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    section = (await db.execute(
        select(Section).where(Section.id == section_id)
    )).scalar_one_or_none()
    if not section:
        raise HTTPException(404, "Section not found")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise HTTPException(400, "No content")

    embeddings = await embed_batch(paragraphs)

    chunks = []
    for para, emb in zip(paragraphs, embeddings):
        chunks.append(ContentChunk(
            section_id=section.id,
            chunk_type="concept",
            text=para,
            page=section.start_page,
            embedding=emb,
            meta={},
        ))

    await ContentRepository(db).bulk_insert(chunks)
    await db.commit()
    return {"ingested": len(chunks), "dim": len(embeddings[0]) if embeddings else 0}

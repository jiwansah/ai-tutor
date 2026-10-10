"""
Bulk PDF ingest endpoints.

Flow:
  1. POST /upload          → save PDF, create job, background-parse
  2. GET  /jobs/{id}       → poll status
  3. GET  /jobs/{id}/preview → see parsed chapters/sections
  4. PATCH /jobs/{id}      → teacher edits parsed_data
  5. POST /jobs/{id}/approve → commit content + embeddings
  6. DELETE /jobs/{id}     → discard
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.db.models.ingest import IngestJob
from app.db.models.curriculum import Book, Chapter, Section
from app.db.models.content import ContentChunk
from app.db.models.user import User
from app.deps_helpers import current_user
from app.services.pdf_parser import parse_pdf, parsed_to_dict
from app.services.embedding_service import embed_batch

router = APIRouter()

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_MB = 50
EMBED_BATCH = 16


# ---------------------------------------------------------------
# Auth
# ---------------------------------------------------------------

def _require_teacher(user: User = Depends(current_user)) -> User:
    if user.role.value not in ("teacher", "admin"):
        raise HTTPException(403, "Teacher or admin role required")
    return user


# ---------------------------------------------------------------
# Background processors
# ---------------------------------------------------------------

async def _parse_job(job_id: str) -> None:
    """Parse the uploaded PDF and fill parsed_data."""
    async with AsyncSessionLocal() as db:
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return

        job = (await db.execute(
            select(IngestJob).where(IngestJob.id == job_uuid)
        )).scalar_one_or_none()
        if not job:
            return

        try:
            job.status = "parsing"
            job.progress = 5
            await db.commit()

            parsed = parse_pdf(job.file_path)
            data = parsed_to_dict(parsed)

            job.page_count = data["page_count"]
            job.parsed_data = data
            job.status = "preview_ready"
            job.progress = 100
            await db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = f"Parse error: {str(e)[:400]}"
            await db.commit()


async def _approve_job(job_id: str) -> None:
    """Create chapters, sections, and content_chunks with embeddings."""
    async with AsyncSessionLocal() as db:
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return

        job = (await db.execute(
            select(IngestJob).where(IngestJob.id == job_uuid)
        )).scalar_one_or_none()
        if not job or not job.parsed_data:
            return

        try:
            job.status = "publishing"
            job.progress = 0
            await db.commit()

            chapters = (job.parsed_data or {}).get("chapters", [])
            total_chunks = sum(
                len(s.get("chunks", []))
                for ch in chapters
                for s in ch.get("sections", [])
            ) or 1
            processed = 0

            for ch_data in chapters:
                chapter = Chapter(
                    book_id=job.book_id,
                    number=int(ch_data.get("number") or 0),
                    title=(ch_data.get("title") or "").strip() or f"Chapter {ch_data.get('number')}",
                )
                db.add(chapter)
                await db.flush()

                for sec_data in ch_data.get("sections", []):
                    section = Section(
                        chapter_id=chapter.id,
                        number=str(sec_data.get("number") or "").strip() or "1.1",
                        title=(sec_data.get("title") or "").strip() or "Untitled",
                        start_page=sec_data.get("start_page"),
                        end_page=sec_data.get("end_page"),
                    )
                    db.add(section)
                    await db.flush()

                    chunks = sec_data.get("chunks", [])
                    if not chunks:
                        continue

                    texts = [c.get("text", "") for c in chunks if c.get("text")]
                    embeddings: list[list[float]] = []
                    for i in range(0, len(texts), EMBED_BATCH):
                        batch = texts[i:i + EMBED_BATCH]
                        embs = await embed_batch(batch)
                        embeddings.extend(embs)
                        processed += len(batch)
                        job.progress = min(99, int((processed / total_chunks) * 100))
                        await db.commit()

                    for c, emb in zip(chunks, embeddings):
                        db.add(ContentChunk(
                            section_id=section.id,
                            chunk_type="concept",
                            text=c.get("text", ""),
                            page=c.get("page"),
                            embedding=emb,
                            meta={},
                        ))
                    await db.commit()

            job.status = "approved"
            job.progress = 100
            job.published_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = f"Approve error: {str(e)[:400]}"
            await db.commit()


# ---------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------

@router.post("/upload", status_code=201)
async def upload_pdf(
    background: BackgroundTasks,
    book_id: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    try:
        book_uuid = uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(400, "Invalid book_id")

    book = (await db.execute(select(Book).where(Book.id == book_uuid))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(413, f"File too large (max {MAX_FILE_MB} MB, got {size_mb:.1f} MB)")

    unique = uuid.uuid4()
    safe_name = f"{unique}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(content)

    job = IngestJob(
        teacher_id=user.id,
        book_id=book_uuid,
        filename=file.filename,
        file_path=str(file_path),
        file_size_kb=len(content) // 1024,
        status="pending",
        progress=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background.add_task(_parse_job, str(job.id))

    return {
        "id": str(job.id),
        "filename": job.filename,
        "status": job.status,
        "progress": job.progress,
        "page_count": job.page_count,
        "book_id": str(job.book_id),
        "file_size_kb": job.file_size_kb,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "published_at": None,
    }


@router.get("/jobs")
async def list_jobs(
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(IngestJob)
        .where(IngestJob.teacher_id == user.id)
        .order_by(IngestJob.created_at.desc())
        .limit(50)
    )
    jobs = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "id": str(j.id),
            "filename": j.filename,
            "status": j.status,
            "progress": j.progress,
            "page_count": j.page_count,
            "book_id": str(j.book_id),
            "file_size_kb": j.file_size_kb,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat(),
            "published_at": j.published_at.isoformat() if j.published_at else None,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    job = await _fetch_job(db, job_id, user.id)
    return {
        "id": str(job.id),
        "filename": job.filename,
        "status": job.status,
        "progress": job.progress,
        "page_count": job.page_count,
        "file_size_kb": job.file_size_kb,
        "book_id": str(job.book_id),
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "published_at": job.published_at.isoformat() if job.published_at else None,
    }


@router.get("/jobs/{job_id}/preview")
async def get_preview(
    job_id: str,
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    job = await _fetch_job(db, job_id, user.id)
    if job.status not in ("preview_ready", "publishing", "approved"):
        raise HTTPException(400, f"Preview not ready (status: {job.status})")
    return job.parsed_data or {}


class UpdateParsedDataRequest(BaseModel):
    parsed_data: dict


@router.patch("/jobs/{job_id}")
async def update_parsed(
    job_id: str,
    payload: UpdateParsedDataRequest,
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    job = await _fetch_job(db, job_id, user.id)
    if job.status not in ("preview_ready",):
        raise HTTPException(400, f"Cannot edit in status: {job.status}")

    job.parsed_data = payload.parsed_data
    await db.commit()
    return {"status": "ok"}


@router.post("/jobs/{job_id}/approve")
async def approve_job(
    job_id: str,
    background: BackgroundTasks,
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    job = await _fetch_job(db, job_id, user.id)
    if job.status != "preview_ready":
        raise HTTPException(400, f"Can only approve preview_ready jobs (current: {job.status})")

    background.add_task(_approve_job, str(job.id))
    return {"status": "publishing", "job_id": str(job.id)}


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    user: User = Depends(_require_teacher),
    db: AsyncSession = Depends(get_db),
):
    job = await _fetch_job(db, job_id, user.id)

    # Remove file from disk
    try:
        Path(job.file_path).unlink(missing_ok=True)
    except Exception:
        pass

    await db.delete(job)
    await db.commit()


# ---------------------------------------------------------------
# Helper
# ---------------------------------------------------------------

async def _fetch_job(db: AsyncSession, job_id: str, teacher_id) -> IngestJob:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, "Invalid job_id")

    job = (await db.execute(
        select(IngestJob).where(IngestJob.id == job_uuid)
    )).scalar_one_or_none()

    if not job:
        raise HTTPException(404, "Job not found")

    # Only the owning teacher (or admin) can touch it
    if job.teacher_id != teacher_id:
        # Allow admins
        # (you can extend this if you have admins)
        raise HTTPException(403, "Not your job")

    return job

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps_helpers import current_user
from app.db.models.user import User
from app.db.models.curriculum import School, Class, Subject, Book, Chapter, Section
from app.db.models.concept import Concept, ConceptPrerequisite, ConceptMisconception
from app.db.models.content import ContentChunk
from app.services.embedding_service import embed_batch
from app.repositories.content_repo import ContentRepository

router = APIRouter()


# ---------------------------------------------------------------
# Role guard
# ---------------------------------------------------------------

def require_teacher(user: User = Depends(current_user)) -> User:
    if user.role.value not in ("teacher", "admin"):
        raise HTTPException(403, "Teacher or admin role required")
    return user


# ---------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------

class SchoolIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    board: str = Field(min_length=1, max_length=50)
    city: str | None = None


class ClassIn(BaseModel):
    school_id: str
    grade: int


class SubjectIn(BaseModel):
    class_id: str
    name: str = Field(min_length=1, max_length=80)


class BookIn(BaseModel):
    subject_id: str
    title: str
    publisher: str | None = None
    edition: str | None = None


class ChapterIn(BaseModel):
    book_id: str
    number: int
    title: str
    description: str | None = None


class SectionIn(BaseModel):
    chapter_id: str
    number: str
    title: str
    start_page: int | None = None
    end_page: int | None = None


class SectionIngestIn(BaseModel):
    text: str = Field(min_length=1)


class ConceptIn(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    name: str
    description: str | None = None
    class_id: str | None = None        # NEW
    subject_id: str | None = None      # NEW
    primary_section_id: str | None = None
    learning_objectives: list[str] = []
    order_index: int = 0


class ConceptUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    class_id: str | None = None
    subject_id: str | None = None
    primary_section_id: str | None = None
    learning_objectives: list[str] | None = None
    order_index: int | None = None


class PrereqIn(BaseModel):
    prerequisite_key: str
    strength: str = "required"


class MisconceptionIn(BaseModel):
    label: str
    description: str | None = None
    remedy: str | None = None
    order_index: int = 0


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def _get_or_404(db: AsyncSession, model, id):
    row = (await db.execute(select(model).where(model.id == id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"{model.__name__} not found")
    return row


def _row_id(x):
    return str(x.id)


# ---------------------------------------------------------------
# Curriculum CRUD
# ---------------------------------------------------------------

@router.get("/schools")
async def list_schools(_: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(School).order_by(School.name))).scalars().all()
    return [{"id": _row_id(r), "name": r.name, "board": r.board, "city": r.city} for r in rows]


@router.post("/schools", status_code=201)
async def create_school(payload: SchoolIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    s = School(name=payload.name, board=payload.board, city=payload.city)
    db.add(s)
    await db.flush()
    return {"id": _row_id(s), "name": s.name}


@router.get("/schools/{school_id}/classes")
async def list_classes(school_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Class).where(Class.school_id == school_id).order_by(Class.grade)
    )).scalars().all()
    return [{"id": _row_id(r), "grade": r.grade} for r in rows]


@router.post("/classes", status_code=201)
async def create_class(payload: ClassIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, School, payload.school_id)
    c = Class(school_id=payload.school_id, grade=payload.grade)
    db.add(c)
    await db.flush()
    return {"id": _row_id(c), "grade": c.grade}


@router.get("/classes/{class_id}/subjects")
async def list_subjects(class_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Subject).where(Subject.class_id == class_id).order_by(Subject.name)
    )).scalars().all()
    return [{"id": _row_id(r), "name": r.name} for r in rows]


@router.post("/subjects", status_code=201)
async def create_subject(payload: SubjectIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, Class, payload.class_id)
    s = Subject(class_id=payload.class_id, name=payload.name)
    db.add(s)
    await db.flush()
    return {"id": _row_id(s), "name": s.name}


@router.get("/subjects/{subject_id}/books")
async def list_books(subject_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Book).where(Book.subject_id == subject_id).order_by(Book.title)
    )).scalars().all()
    return [{"id": _row_id(r), "title": r.title, "publisher": r.publisher} for r in rows]


@router.post("/books", status_code=201)
async def create_book(payload: BookIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, Subject, payload.subject_id)
    b = Book(subject_id=payload.subject_id, title=payload.title,
             publisher=payload.publisher, edition=payload.edition)
    db.add(b)
    await db.flush()
    return {"id": _row_id(b), "title": b.title}


@router.get("/books/{book_id}/chapters")
async def list_chapters(book_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.number)
    )).scalars().all()
    return [{"id": _row_id(r), "number": r.number, "title": r.title} for r in rows]


@router.post("/chapters", status_code=201)
async def create_chapter(payload: ChapterIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, Book, payload.book_id)
    c = Chapter(book_id=payload.book_id, number=payload.number,
                title=payload.title, description=payload.description)
    db.add(c)
    await db.flush()
    return {"id": _row_id(c), "title": c.title, "number": c.number}


@router.get("/chapters/{chapter_id}/sections")
async def list_sections(chapter_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Section).where(Section.chapter_id == chapter_id).order_by(Section.number)
    )).scalars().all()
    return [
        {"id": _row_id(r), "number": r.number, "title": r.title,
         "start_page": r.start_page, "end_page": r.end_page}
        for r in rows
    ]


@router.post("/sections", status_code=201)
async def create_section(payload: SectionIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, Chapter, payload.chapter_id)
    s = Section(chapter_id=payload.chapter_id, number=payload.number,
                title=payload.title, start_page=payload.start_page,
                end_page=payload.end_page)
    db.add(s)
    await db.flush()
    return {"id": _row_id(s), "title": s.title, "number": s.number}


# ---------------------------------------------------------------
# Section content ingest
# ---------------------------------------------------------------

@router.get("/sections/{section_id}/chunks")
async def list_chunks(section_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, Section, section_id)
    rows = (await db.execute(
        select(ContentChunk)
        .where(ContentChunk.section_id == section_id)
        .order_by(ContentChunk.created_at)
    )).scalars().all()
    return [
        {"id": _row_id(c), "type": c.chunk_type, "text": c.text,
         "page": c.page, "created_at": c.created_at.isoformat()}
        for c in rows
    ]


@router.post("/sections/{section_id}/ingest")
async def ingest_section_content(
    section_id: str,
    payload: SectionIngestIn,
    _: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    section = await _get_or_404(db, Section, section_id)
    paragraphs = [p.strip() for p in payload.text.split("\n\n") if p.strip()]
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


@router.delete("/sections/{section_id}/chunks", status_code=204)
async def delete_section_chunks(section_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ContentChunk).where(ContentChunk.section_id == section_id))
    await db.commit()


# ---------------------------------------------------------------
# Concepts
# ---------------------------------------------------------------

@router.get("/concepts")
async def teacher_list_concepts(
    class_id: str | None = None,
    subject_id: str | None = None,
    include_global: bool = True,
    _: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    from app.repositories.concept_repo import ConceptRepository
    concepts = await ConceptRepository(db).list_for_scope(class_id, subject_id, include_global)
    return [
        {
            "key": c.key,
            "name": c.name,
            "description": c.description,
            "class_id": str(c.class_id) if c.class_id else None,
            "subject_id": str(c.subject_id) if c.subject_id else None,
            "primary_section_id": str(c.primary_section_id) if c.primary_section_id else None,
            "is_global": c.class_id is None and c.subject_id is None,
            "learning_objectives": c.learning_objectives or [],
            "order_index": c.order_index,
        }
        for c in concepts
    ]


@router.post("/concepts", status_code=201)
async def create_concept(
    payload: ConceptIn,
    _: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(Concept).where(Concept.key == payload.key))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Concept key already exists")
    c = Concept(
        key=payload.key,
        name=payload.name,
        description=payload.description,
        class_id=payload.class_id or None,
        subject_id=payload.subject_id or None,
        primary_section_id=payload.primary_section_id or None,
        learning_objectives=payload.learning_objectives,
        order_index=payload.order_index,
    )
    db.add(c)
    await db.flush()
    return {"key": c.key, "name": c.name}


@router.patch("/concepts/{key}")
async def update_concept(
    key: str,
    payload: ConceptUpdateIn,
    _: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    c = (await db.execute(select(Concept).where(Concept.key == key))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Concept not found")
    if payload.name is not None:
        c.name = payload.name
    if payload.description is not None:
        c.description = payload.description
    if payload.class_id is not None:
        c.class_id = payload.class_id or None
    if payload.subject_id is not None:
        c.subject_id = payload.subject_id or None
    if payload.primary_section_id is not None:
        c.primary_section_id = payload.primary_section_id or None
    if payload.learning_objectives is not None:
        c.learning_objectives = payload.learning_objectives
    if payload.order_index is not None:
        c.order_index = payload.order_index
    await db.commit()
    return {"key": c.key, "name": c.name}


@router.delete("/concepts/{key}", status_code=204)
async def delete_concept(key: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Concept).where(Concept.key == key))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Concept not found")
    await db.execute(delete(ConceptPrerequisite).where(
        (ConceptPrerequisite.concept_id == c.id) | (ConceptPrerequisite.prerequisite_id == c.id)
    ))
    await db.execute(delete(ConceptMisconception).where(ConceptMisconception.concept_id == c.id))
    await db.delete(c)
    await db.commit()


@router.post("/concepts/{key}/prerequisites", status_code=201)
async def add_prerequisite(key: str, payload: PrereqIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    concept = (await db.execute(select(Concept).where(Concept.key == key))).scalar_one_or_none()
    prereq = (await db.execute(select(Concept).where(Concept.key == payload.prerequisite_key))).scalar_one_or_none()
    if not concept or not prereq:
        raise HTTPException(404, "Concept or prerequisite not found")
    if concept.id == prereq.id:
        raise HTTPException(400, "A concept cannot be its own prerequisite")

    existing = (await db.execute(
        select(ConceptPrerequisite).where(
            ConceptPrerequisite.concept_id == concept.id,
            ConceptPrerequisite.prerequisite_id == prereq.id,
        )
    )).scalar_one_or_none()
    if existing:
        return {"status": "already_exists"}

    db.add(ConceptPrerequisite(
        concept_id=concept.id, prerequisite_id=prereq.id, strength=payload.strength,
    ))
    await db.commit()
    return {"status": "ok"}


@router.delete("/concepts/{key}/prerequisites/{prereq_key}", status_code=204)
async def remove_prerequisite(key: str, prereq_key: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    concept = (await db.execute(select(Concept).where(Concept.key == key))).scalar_one_or_none()
    prereq = (await db.execute(select(Concept).where(Concept.key == prereq_key))).scalar_one_or_none()
    if not concept or not prereq:
        raise HTTPException(404, "Concept not found")
    await db.execute(delete(ConceptPrerequisite).where(
        ConceptPrerequisite.concept_id == concept.id,
        ConceptPrerequisite.prerequisite_id == prereq.id,
    ))
    await db.commit()


@router.post("/concepts/{key}/misconceptions", status_code=201)
async def add_misconception(key: str, payload: MisconceptionIn, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Concept).where(Concept.key == key))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Concept not found")
    m = ConceptMisconception(
        concept_id=c.id, label=payload.label, description=payload.description,
        remedy=payload.remedy, order_index=payload.order_index,
    )
    db.add(m)
    await db.flush()
    return {"id": str(m.id)}


@router.delete("/concepts/{key}/misconceptions/{misconception_id}", status_code=204)
async def remove_misconception(key: str, misconception_id: str, _: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ConceptMisconception).where(ConceptMisconception.id == misconception_id))
    await db.commit()


# ---------------------------------------------------------------
# Graph view
# ---------------------------------------------------------------

@router.get("/graph")
async def concept_graph(_: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    concepts = list((await db.execute(select(Concept).order_by(Concept.order_index))).scalars().all())
    edges = list((await db.execute(select(ConceptPrerequisite))).scalars().all())
    id_to_key = {c.id: c.key for c in concepts}

    return {
        "nodes": [
            {"key": c.key, "name": c.name, "order_index": c.order_index}
            for c in concepts
        ],
        "edges": [
            {
                "from": id_to_key.get(e.prerequisite_id),
                "to": id_to_key.get(e.concept_id),
                "strength": e.strength,
            }
            for e in edges
        ],
    }

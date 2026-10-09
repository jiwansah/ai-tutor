from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps_helpers import current_user
from app.db.models.user import User
from app.repositories.concept_repo import ConceptRepository
from app.repositories.student_repo import StudentRepository
from app.services.concept_graph import diagnose


router = APIRouter()


@router.get("/")
async def list_concepts(
    class_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    include_global: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    repo = ConceptRepository(db)
    concepts = await repo.list_for_scope(class_id, subject_id, include_global)
    return [
        {
            "key": c.key,
            "name": c.name,
            "description": c.description,
            "class_id": str(c.class_id) if c.class_id else None,
            "subject_id": str(c.subject_id) if c.subject_id else None,
            "primary_section_id": str(c.primary_section_id) if c.primary_section_id else None,
            "learning_objectives": c.learning_objectives or [],
            "is_global": c.class_id is None and c.subject_id is None,
            "order_index": c.order_index,
        }
        for c in concepts
    ]


@router.get("/{key}")
async def get_concept(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    repo = ConceptRepository(db)
    concept = await repo.get_by_key(key)
    if not concept:
        raise HTTPException(404, "Concept not found")

    prereqs = await repo.get_prerequisites(concept.id)
    misconceptions = await repo.get_misconceptions(concept.id)

    return {
        "key": concept.key,
        "name": concept.name,
        "description": concept.description,
        "class_id": str(concept.class_id) if concept.class_id else None,
        "subject_id": str(concept.subject_id) if concept.subject_id else None,
        "primary_section_id": str(concept.primary_section_id) if concept.primary_section_id else None,
        "is_global": concept.class_id is None and concept.subject_id is None,
        "learning_objectives": concept.learning_objectives or [],
        "prerequisites": [
            {
                "key": p.key,
                "name": p.name,
                "primary_section_id": str(p.primary_section_id) if p.primary_section_id else None,
            }
            for p in prereqs
        ],
        "misconceptions": [
            {
                "id": str(m.id),
                "label": m.label,
                "description": m.description,
                "remedy": m.remedy,
            }
            for m in misconceptions
        ],
    }


@router.get("/by-section/{section_id}")
async def get_concept_for_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    concept = await ConceptRepository(db).get_for_section(section_id)
    if not concept:
        return {"concept": None}
    return {
        "concept": {
            "key": concept.key,
            "name": concept.name,
            "learning_objectives": concept.learning_objectives or [],
        }
    }


@router.get("/diagnostic/{concept_key}")
async def get_diagnostic(
    concept_key: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await StudentRepository(db).get_profile_by_user(user.id)
    if not student:
        raise HTTPException(400, "Student profile missing")
    return await diagnose(db, student.id, concept_key)

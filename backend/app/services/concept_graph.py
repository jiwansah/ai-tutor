"""
Diagnostic: given a student and a target concept, check mastery
on the concept and its prerequisites. Recommend next action.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.concept_repo import ConceptRepository
from app.repositories.student_repo import StudentRepository


MASTERY_WEAK = 0.4
MASTERY_OK = 0.7


async def resolve_concept_for_section(db: AsyncSession, section_id: str | None) -> str | None:
    """If a section is linked to a concept, return the concept key; else None."""
    if not section_id:
        return None
    concept = await ConceptRepository(db).get_for_section(section_id)
    return concept.key if concept else None


async def diagnose(
    db: AsyncSession,
    student_id,
    concept_key: str | None,
) -> dict:
    """
    Check the student's mastery on the target concept and all prerequisites.
    Returns a diagnostic with a recommendation.
    """
    result = {
        "concept_key": concept_key,
        "mastery": 0.0,
        "prerequisites": [],
        "recommendation": "proceed",
        "recommended_prerequisite": None,
        "misconceptions": [],
    }

    if not concept_key:
        return result

    concepts = ConceptRepository(db)
    students = StudentRepository(db)

    concept = await concepts.get_by_key(concept_key)
    if not concept:
        return result

    # Target mastery
    row = await students.get_mastery(student_id, concept_key)
    result["mastery"] = row.mastery if row else 0.0

    # Misconceptions recorded by the student on this concept
    if row and row.misconceptions:
        result["misconceptions"] = list(row.misconceptions.keys())

    # Prerequisites
    prereqs = await concepts.get_prerequisites(concept.id)
    weakest = None
    for p in prereqs:
        prow = await students.get_mastery(student_id, p.key)
        pm = prow.mastery if prow else 0.0
        status = "weak" if pm < MASTERY_WEAK else "ok" if pm >= MASTERY_OK else "developing"
        result["prerequisites"].append({
            "key": p.key,
            "name": p.name,
            "mastery": pm,
            "status": status,
            "primary_section_id": str(p.primary_section_id) if p.primary_section_id else None,
        })
        if status == "weak" and (weakest is None or pm < weakest["mastery"]):
            weakest = result["prerequisites"][-1]

    # Recommendation
    if weakest:
        result["recommendation"] = "review_prerequisite"
        result["recommended_prerequisite"] = weakest["key"]
    elif result["mastery"] < MASTERY_WEAK:
        result["recommendation"] = "scaffold"
    elif result["mastery"] >= MASTERY_OK:
        result["recommendation"] = "challenge"
    else:
        result["recommendation"] = "proceed"

    return result


def build_diagnostic_block(diag: dict) -> str:
    """
    Turn a diagnostic into a short text block to inject into the LLM prompt.
    """
    if not diag.get("concept_key"):
        return ""

    parts = [f"STUDENT DIAGNOSTIC for '{diag['concept_key']}':"]
    parts.append(f"  Current mastery: {diag['mastery']:.2f}")

    prereqs = diag.get("prerequisites") or []
    if prereqs:
        parts.append("  Prerequisites:")
        for p in prereqs:
            parts.append(f"    - {p['name']}: mastery {p['mastery']:.2f} ({p['status']})")

    rec = diag.get("recommendation")
    if rec == "review_prerequisite":
        rec_key = diag.get("recommended_prerequisite")
        rec_name = next(
            (p["name"] for p in prereqs if p["key"] == rec_key), rec_key
        )
        parts.append(
            f"  RECOMMENDATION: Student is weak on prerequisite '{rec_name}'. "
            f"Briefly revise that concept BEFORE teaching the current one. "
            f"Start with: 'Before we tackle this, let's quickly refresh <prerequisite>...'"
        )
    elif rec == "scaffold":
        parts.append("  RECOMMENDATION: Student is new to this. Use small steps and hints.")
    elif rec == "challenge":
        parts.append("  RECOMMENDATION: Student is confident. Move fast, ask harder questions.")
    else:
        parts.append("  RECOMMENDATION: Student is ready. Teach normally.")

    misconceptions = diag.get("misconceptions") or []
    if misconceptions:
        parts.append(f"  Known misconceptions: {', '.join(misconceptions)}")

    return "\n".join(parts) + "\n\n"

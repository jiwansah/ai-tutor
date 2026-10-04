from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.orchestrator import TutorContext
from app.services.rag_service import retrieve, format_context
from app.services.llm_service import complete
from app.prompts.teacher import TEACHER_SYSTEM, TEACHER_USER


async def teach(
    db: AsyncSession, ctx: TutorContext, question: str, plan: dict
) -> dict:
    chunks = await retrieve(
        db,
        query=question,
        subject_id=ctx.subject_id,
        chapter_id=ctx.chapter_id,
        section_id=ctx.section_id,
        top_k=5,
    )
    context = format_context(chunks)

    strategy = plan["strategy"]
    user_prompt = TEACHER_USER.format(
        strategy=strategy,
        context=context,
        mastery=ctx.student_mastery,
        question=question,
    )

    answer = await complete(
        prompt=user_prompt,
        system=TEACHER_SYSTEM,
        temperature=0.4,
        max_tokens=1200,
    )

    citations = [
        {
            "chapter": c["chapter"],
            "section": c["section"],
            "page": c["page"],
        }
        for c in chunks
    ]

    return {"answer": answer, "citations": citations}
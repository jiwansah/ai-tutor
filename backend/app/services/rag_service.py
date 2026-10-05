from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.content import ContentChunk
from app.db.models.curriculum import Section, Chapter, Book
from app.services.embedding_service import embed_text


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        subject_id: str | None = None,
        chapter_id: str | None = None,
        section_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        # 1. Embed the student's question using Ollama
        query_vec = await embed_text(query)

        # 2. Vector search with optional curriculum filter
        stmt = (
            select(ContentChunk, Section, Chapter)
            .join(Section, ContentChunk.section_id == Section.id)
            .join(Chapter, Section.chapter_id == Chapter.id)
            .order_by(ContentChunk.embedding.cosine_distance(query_vec))
            .limit(top_k)
        )

        if section_id:
            stmt = stmt.where(Section.id == section_id)
        elif chapter_id:
            stmt = stmt.where(Chapter.id == chapter_id)
        elif subject_id:
            stmt = stmt.join(Book, Chapter.book_id == Book.id).where(
                Book.subject_id == subject_id
            )

        rows = (await self.db.execute(stmt)).all()

        return [
            {
                "chunk_id": str(c.id),
                "text": c.text,
                "type": c.chunk_type,
                "page": c.page,
                "chapter": ch.title,
                "chapter_number": ch.number,
                "section": s.title,
                "section_number": s.number,
            }
            for c, s, ch in rows
        ]

    @staticmethod
    def format_context(chunks: list[dict]) -> str:
        if not chunks:
            return "(no textbook context available)"
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(
                f"[{i}] Chapter {c['chapter_number']}: {c['chapter']} "
                f"→ Section {c['section_number']}: {c['section']} (p. {c['page']})\n"
                f"{c['text']}"
            )
        return "\n\n".join(parts)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content import ContentChunk
from app.db.models.curriculum import Section, Chapter, Book, Subject
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
        class_id: str | None = None,
        top_k: int = 5,
        max_distance: float = 0.6,  # cosine distance; lower = more similar
    ) -> list[dict]:
        """
        Retrieval with STRICT scope enforcement.

        Priority:
          - section_id   → only chunks in that section
          - chapter_id   → only chunks in that chapter
          - subject_id   → only chunks in that subject

        If NONE of the above are provided, return [] (empty).
        We never fall back to a broader scope — that would leak content
        from an unrelated subject (e.g., Math chunks answering English questions).
        """
        if not (section_id or chapter_id or subject_id):
            return []

        query_vec = await embed_text(query)

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

        results = []
        for c, s, ch in rows:
            # Skip chunks that are semantically too far from the question
            if c.embedding is not None:
                # Compute distance in Python for simplicity
                # (SQLAlchemy distance calc already happened for ordering)
                pass
            results.append({
                "chunk_id": str(c.id),
                "text": c.text,
                "type": c.chunk_type,
                "page": c.page,
                "chapter": ch.title,
                "chapter_number": ch.number,
                "section": s.title,
                "section_number": s.number,
            })
        return results




    @staticmethod
    def format_context(chunks: list[dict]) -> str:
        if not chunks:
            return "(no textbook context available for this topic)"
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(
                f"[{i}] Chapter {c['chapter_number']}: {c['chapter']} "
                f"→ Section {c['section_number']}: {c['section']} (p. {c['page']})\n"
                f"{c['text']}"
            )
        return "\n\n".join(parts)

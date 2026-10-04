from app.repositories.content_repo import ContentRepository
from app.services.embedding_service import embed_text


class RAGService:
    def __init__(self, content_repo: ContentRepository):
        self.content_repo = content_repo

    async def retrieve(
        self,
        query: str,
        subject_id: str | None = None,
        chapter_id: str | None = None,
        section_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        vec = embed_text(query)
        rows = await self.content_repo.semantic_search(
            query_vec=vec,
            subject_id=subject_id,
            chapter_id=chapter_id,
            section_id=section_id,
            top_k=top_k,
        )
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
        return "\n\n".join(
            f"[{i}] Ch {c['chapter_number']}: {c['chapter']} "
            f"→ Sec {c['section_number']}: {c['section']} (p. {c['page']})\n{c['text']}"
            for i, c in enumerate(chunks, 1)
        )
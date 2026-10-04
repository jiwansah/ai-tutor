from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models.content import ContentChunk
from app.db.models.curriculum import Section, Chapter, Book
from app.repositories.base import BaseRepository


class ContentRepository(BaseRepository[ContentChunk]):
    model = ContentChunk

    async def semantic_search(
        self,
        query_vec: list[float],
        subject_id: str | None = None,
        chapter_id: str | None = None,
        section_id: str | None = None,
        top_k: int = 5,
    ) -> list[tuple[ContentChunk, Section, Chapter]]:
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
            stmt = stmt.join(Book, Chapter.book_id == Book.id).where(Book.subject_id == subject_id)

        return (await self.db.execute(stmt)).all()

    async def bulk_insert_chunks(self, chunks: list[ContentChunk]) -> None:
        self.db.add_all(chunks)
        await self.db.flush()
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.content import ContentChunk


class ContentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_insert(self, chunks: list[ContentChunk]) -> None:
        self.db.add_all(chunks)
        await self.db.flush()

from typing import Generic, TypeVar, Type
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)

class BaseRepository(Generic[ModelT]):
    model: Type[ModelT]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID | str) -> ModelT | None:
        return (await self.db.execute(
            select(self.model).where(self.model.id == id)
        )).scalar_one_or_none()

    async def get_or_raise(self, id: UUID | str) -> ModelT:
        obj = await self.get(id)
        if not obj:
            raise ValueError(f"{self.model.__name__} {id} not found")
        return obj

    async def list(self, **filters) -> list[ModelT]:
        stmt = select(self.model)
        for k, v in filters.items():
            stmt = stmt.where(getattr(self.model, k) == v)
        return list((await self.db.execute(stmt)).scalars().all())

    async def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def delete(self, id: UUID | str) -> None:
        await self.db.execute(delete(self.model).where(self.model.id == id))
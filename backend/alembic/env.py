
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context
import asyncio
import os

from app.db.base import Base
from app.db.models import user, curriculum, content, student, session  # noqa

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read the async URL from env — do NOT rely on config.get_section()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://tutor:tutor@postgres:5432/tutor",
)


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
"""add ingest_jobs

Revision ID: 3db4bd7cc714
Revises: 8fd08d2adb01
Create Date: 2026-10-10 07:54:27.789051
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects import postgresql


revision = '3db4bd7cc714'
down_revision = '8fd08d2adb01'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'ingest_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('teacher_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('books.id'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size_kb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parsed_data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_ingest_jobs_teacher_id', 'ingest_jobs', ['teacher_id'])
    op.create_index('ix_ingest_jobs_book_id', 'ingest_jobs', ['book_id'])
    op.create_index('ix_ingest_jobs_status', 'ingest_jobs', ['status'])


def downgrade() -> None:
    op.drop_table('ingest_jobs')
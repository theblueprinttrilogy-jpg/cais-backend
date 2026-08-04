"""Add code_references table with vector embedding support.

Revision ID: 002_add_code_references
Revises: 001_initial_schema
Create Date: 2026-08-03 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '002_add_code_references'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure the vector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create the code_references table
    op.create_table(
        'code_references',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('jurisdiction', sa.String(50), nullable=False, index=True),
        sa.Column('code_type', sa.String(50), nullable=False, index=True),
        sa.Column('section', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('full_text', sa.Text, nullable=True),
        sa.Column('severity', sa.String(50), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )

    # Add a composite index for common queries
    op.create_index('ix_code_references_jurisdiction_code_type', 'code_references',
                    ['jurisdiction', 'code_type'])


def downgrade() -> None:
    # Drop the table
    op.drop_table('code_references')
    # Optionally drop the extension, but we keep it to avoid affecting other tables
    # op.execute("DROP EXTENSION IF EXISTS vector")

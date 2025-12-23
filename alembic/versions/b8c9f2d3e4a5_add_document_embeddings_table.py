"""Add document_embeddings table for RAG vector storage

Revision ID: b8c9f2d3e4a5
Revises: ae7aa9f92c8a
Create Date: 2025-12-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9f2d3e4a5'
down_revision: Union[str, Sequence[str], None] = 'ae7aa9f92c8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create document_embeddings table for RAG vector storage.
    
    The next migration (c9d0e1f2a3b4) will:
    1. CREATE EXTENSION IF NOT EXISTS vector;
    2. ALTER COLUMN embedding TYPE vector(384);
    3. CREATE INDEX using HNSW for fast similarity search.
    """
    op.create_table(
        'document_embeddings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        # Stored as Text initially, converted to vector(384) by migration c9d0e1f2a3b4
        sa.Column('embedding', sa.Text(), nullable=False),
        # Note: Cannot use 'metadata' as column name (SQLAlchemy reserved)
        sa.Column('chunk_metadata', sa.JSON(), default={}),
        sa.Column('namespace', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on namespace for efficient filtering
    with op.batch_alter_table('document_embeddings', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_document_embeddings_namespace'), 
            ['namespace'], 
            unique=False
        )


def downgrade() -> None:
    """Remove document_embeddings table."""
    with op.batch_alter_table('document_embeddings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_document_embeddings_namespace'))
    
    op.drop_table('document_embeddings')

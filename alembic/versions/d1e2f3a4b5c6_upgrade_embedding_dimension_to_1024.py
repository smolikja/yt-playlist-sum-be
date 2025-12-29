"""Upgrade embedding dimension to 1024 for multilingual-e5-large model

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2025-12-29 16:52:00.000000

This migration:
1. Drops existing embeddings (incompatible dimensions)
2. Alters embedding column from vector(384) to vector(1024)
3. Recreates the HNSW index for the new dimension

BREAKING CHANGE: All existing embeddings will be deleted!
They need to be regenerated with the new model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade embedding dimension from 384 to 1024.
    
    Model change: all-MiniLM-L6-v2 (384) -> intfloat/multilingual-e5-large (1024)
    
    IMPORTANT: This deletes all existing embeddings!
    They will be regenerated on next playlist summarization.
    """
    # Step 1: Drop the existing HNSW index (dimension-specific)
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_embedding_hnsw;")
    
    # Step 2: Delete all existing embeddings (incompatible dimensions)
    op.execute("DELETE FROM document_embeddings;")
    
    # Step 3: Alter column to new dimension
    op.execute("""
        ALTER TABLE document_embeddings 
        ALTER COLUMN embedding TYPE vector(1024) 
        USING NULL::vector(1024);
    """)
    
    # Step 4: Recreate HNSW index for 1024-dim vectors
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_hnsw
        ON document_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)


def downgrade() -> None:
    """
    Revert to 384 dimensions (all-MiniLM-L6-v2).
    
    IMPORTANT: This also deletes all existing embeddings!
    """
    # Drop the 1024-dim HNSW index
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_embedding_hnsw;")
    
    # Delete all embeddings
    op.execute("DELETE FROM document_embeddings;")
    
    # Revert to 384 dimensions
    op.execute("""
        ALTER TABLE document_embeddings 
        ALTER COLUMN embedding TYPE vector(384) 
        USING NULL::vector(384);
    """)
    
    # Recreate HNSW index for 384-dim vectors
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_hnsw
        ON document_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)

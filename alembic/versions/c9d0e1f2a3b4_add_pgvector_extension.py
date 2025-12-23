"""Add pgvector extension and update embedding column type

Revision ID: c9d0e1f2a3b4
Revises: b8c9f2d3e4a5
Create Date: 2025-12-22 19:00:00.000000

This migration:
1. Creates the pgvector extension (required for vector operations)
2. Alters the embedding column to use the native vector(384) type
3. Creates an HNSW index for fast similarity search

IMPORTANT: 
- The PostgreSQL user must have privileges to CREATE EXTENSION
- This migration will FAIL HARD if pgvector is not available (by design)
- The database must be running pgvector/pgvector:pg16 or similar
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9f2d3e4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enable pgvector extension and convert embedding column to vector type.
    
    This migration will fail hard if:
    - pgvector extension is not installed in PostgreSQL
    - The database user lacks CREATE EXTENSION privileges
    
    This is intentional: without pgvector, the RAG system cannot function.
    """
    # Step 1: Ensure the pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Step 2: Alter the embedding column from TEXT to vector(384)
    # 384 is the dimension for all-MiniLM-L6-v2 embedding model
    op.execute("""
        ALTER TABLE document_embeddings 
        ALTER COLUMN embedding TYPE vector(384) 
        USING embedding::vector(384);
    """)
    
    # Step 3: Create HNSW index for fast approximate nearest neighbor search
    # Using cosine distance operator (vector_cosine_ops)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_hnsw
        ON document_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)


def downgrade() -> None:
    """Revert to TEXT column for embedding storage."""
    # Drop the HNSW index
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_embedding_hnsw;")
    
    # Convert embedding column back to TEXT
    op.execute("""
        ALTER TABLE document_embeddings 
        ALTER COLUMN embedding TYPE TEXT 
        USING embedding::text;
    """)
    
    # Note: We don't drop the extension as other tables may use it

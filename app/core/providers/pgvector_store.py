"""
PostgreSQL + pgvector implementation of VectorStore.

This module provides a vector store backed by PostgreSQL with the
pgvector extension, using SQLAlchemy for database operations.
"""
from typing import Optional
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.providers.vector_store import VectorStore, DocumentChunk, SearchResult


class PgVectorStore(VectorStore):
    """
    PostgreSQL + pgvector implementation of VectorStore.
    
    Uses PostgreSQL's pgvector extension for efficient similarity search.
    Supports HNSW indexing for fast approximate nearest neighbor queries.
    
    Example:
        store = PgVectorStore(session=db_session)
        await store.upsert_documents(chunks, namespace="playlist_123")
        results = await store.search_similarity(
            query_embedding=[0.1, 0.2, ...],
            top_k=5,
            namespace="playlist_123",
        )
    """
    
    TABLE_NAME = "document_embeddings"
    
    # Security: Whitelist of allowed metadata keys for filter queries
    # Prevents SQL injection through key interpolation in JSONB filters
    ALLOWED_METADATA_KEYS = frozenset({
        "video_id", "video_title", "chunk_index", "start_time", "end_time"
    })
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the pgvector store.
        
        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session
    
    async def upsert_documents(
        self,
        chunks: list[DocumentChunk],
        namespace: Optional[str] = None,
    ) -> int:
        """
        Insert or update document chunks with embeddings.
        
        Uses PostgreSQL's ON CONFLICT for upsert semantics.
        """
        if not chunks:
            return 0
        
        logger.debug(f"Upserting {len(chunks)} documents to namespace: {namespace}")
        
        count = 0
        for chunk in chunks:
            if chunk.embedding is None:
                logger.warning(f"Skipping chunk {chunk.id} - no embedding")
                continue
            
            # Convert embedding list to pgvector format
            embedding_str = f"[{','.join(str(x) for x in chunk.embedding)}]"
            metadata_str = json.dumps(chunk.metadata)
            
            # Use CAST() syntax instead of :: to avoid asyncpg parameter confusion
            await self.session.execute(
                text("""
                    INSERT INTO document_embeddings (id, content, embedding, chunk_metadata, namespace)
                    VALUES (:id, :content, CAST(:embedding AS vector), CAST(:chunk_metadata AS jsonb), :namespace)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        chunk_metadata = EXCLUDED.chunk_metadata,
                        namespace = EXCLUDED.namespace
                """),
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "embedding": embedding_str,
                    "chunk_metadata": metadata_str,
                    "namespace": namespace,
                }
            )
            count += 1
        
        await self.session.commit()
        logger.info(f"Upserted {count} documents to {self.TABLE_NAME}")
        return count
    
    async def search_similarity(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_metadata: Optional[dict] = None,
    ) -> list[SearchResult]:
        """
        Cosine similarity search using pgvector <=> operator.
        
        The <=> operator computes cosine distance. We convert to similarity
        by computing 1 - distance.
        """
        # Convert query embedding to pgvector format
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
        
        # Build dynamic WHERE clause
        where_clauses = ["1=1"]
        params: dict = {
            "query_embedding": embedding_str,
            "top_k": top_k,
        }
        
        if namespace:
            where_clauses.append("namespace = :namespace")
            params["namespace"] = namespace
        
        if filter_metadata:
            for key, value in filter_metadata.items():
                # Security: Validate key against whitelist before SQL interpolation
                if key not in self.ALLOWED_METADATA_KEYS:
                    raise ValueError(f"Invalid metadata filter key: {key}")
                # Use ->> operator for JSONB text extraction
                where_clauses.append(f"chunk_metadata->>'{key}' = :meta_{key}")
                params[f"meta_{key}"] = str(value)
        
        where_sql = " AND ".join(where_clauses)
        
        logger.debug(f"Similarity search: top_k={top_k}, namespace={namespace}")
        
        # Use CAST() syntax instead of :: for asyncpg compatibility
        result = await self.session.execute(
            text(f"""
                SELECT id, content, chunk_metadata,
                       1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM {self.TABLE_NAME}
                WHERE {where_sql}
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
            """),
            params
        )
        
        rows = result.fetchall()
        
        search_results = []
        for row in rows:
            # Parse metadata back from JSON
            metadata = row.chunk_metadata if isinstance(row.chunk_metadata, dict) else json.loads(row.chunk_metadata or "{}")
            
            search_results.append(
                SearchResult(
                    chunk=DocumentChunk(
                        id=row.id,
                        content=row.content,
                        metadata=metadata,
                    ),
                    score=float(row.similarity),
                )
            )
        
        logger.debug(f"Found {len(search_results)} results")
        return search_results
    
    async def delete_by_namespace(self, namespace: str) -> int:
        """Delete all documents in a namespace."""
        logger.info(f"Deleting documents in namespace: {namespace}")
        
        result = await self.session.execute(
            text(f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE namespace = :namespace
            """),
            {"namespace": namespace}
        )
        
        await self.session.commit()
        count = result.rowcount
        logger.info(f"Deleted {count} documents from namespace: {namespace}")
        return count

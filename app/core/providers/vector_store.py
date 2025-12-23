"""
Abstract base class for vector stores.

This module defines a vendor-neutral interface for vector databases.
Concrete implementations (pgvector, Qdrant) must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    """
    A chunk of document with embedding and metadata.
    
    Attributes:
        id: Unique identifier for the chunk (e.g., "{video_id}_{chunk_index}").
        content: The text content of the chunk.
        embedding: The embedding vector (optional, can be set after creation).
        metadata: Additional metadata (video_id, start_time, end_time, etc.).
    """
    
    id: str
    content: str
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(frozen=True)


class SearchResult(BaseModel):
    """
    Result from a similarity search.
    
    Attributes:
        chunk: The matched document chunk.
        score: Similarity score (higher is more similar, typically 0-1 for cosine).
    """
    
    chunk: DocumentChunk
    score: float
    
    model_config = ConfigDict(frozen=True)


class VectorStore(ABC):
    """
    Abstract interface for vector databases.
    
    Implementations must provide:
    - upsert_documents: Insert or update document chunks
    - search_similarity: Find similar documents by embedding
    - delete_by_namespace: Remove all documents in a namespace
    
    Example:
        store = PgVectorStore(session=db_session)
        await store.upsert_documents(chunks, namespace="playlist_123")
        results = await store.search_similarity(
            query_embedding=[0.1, 0.2, ...],
            top_k=5,
            namespace="playlist_123",
        )
    """
    
    @abstractmethod
    async def upsert_documents(
        self,
        chunks: list[DocumentChunk],
        namespace: Optional[str] = None,
    ) -> int:
        """
        Insert or update document chunks with embeddings.
        
        Args:
            chunks: List of document chunks with embeddings.
            namespace: Optional grouping key (e.g., playlist_id).
            
        Returns:
            Count of documents upserted.
        """
        ...
    
    @abstractmethod
    async def search_similarity(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """
        Search for similar documents by embedding.
        
        Args:
            query_embedding: The query vector.
            top_k: Maximum number of results to return.
            namespace: Filter by namespace (e.g., playlist_id).
            filter_metadata: Additional metadata filters.
            
        Returns:
            List of SearchResult objects, sorted by similarity (descending).
        """
        ...
    
    @abstractmethod
    async def delete_by_namespace(self, namespace: str) -> int:
        """
        Delete all documents in a namespace.
        
        Args:
            namespace: The namespace to delete.
            
        Returns:
            Count of documents deleted.
        """
        ...

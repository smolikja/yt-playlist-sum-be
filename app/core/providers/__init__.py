"""
Provider abstraction layer for model-agnostic AI integration.
"""
from app.core.providers.llm_provider import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
)
from app.core.providers.embedding_provider import (
    EmbeddingProvider,
)
from app.core.providers.vector_store import (
    VectorStore,
    DocumentChunk,
    SearchResult,
)
from app.core.providers.enums import (
    LLMProviderType,
    EmbeddingProviderType,
    VectorStoreType,
)

__all__ = [
    # LLM
    "LLMProvider",
    "LLMMessage", 
    "LLMResponse",
    # Embedding
    "EmbeddingProvider",
    # Vector Store
    "VectorStore",
    "DocumentChunk",
    "SearchResult",
    # Enums
    "LLMProviderType",
    "EmbeddingProviderType",
    "VectorStoreType",
]

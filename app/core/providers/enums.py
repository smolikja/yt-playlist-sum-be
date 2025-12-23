"""
Enums for provider type configuration.
"""
from enum import Enum


class LLMProviderType(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    GROQ = "groq"
    OPENAI = "openai"


class EmbeddingProviderType(str, Enum):
    """Supported embedding providers."""
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OPENAI = "openai"


class VectorStoreType(str, Enum):
    """Supported vector store backends."""
    PGVECTOR = "pgvector"
    QDRANT = "qdrant"

"""
Dependency injection factories for FastAPI.

This module provides factory functions for creating service instances
with proper dependency injection. Providers are selected based on config.
"""
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db_session

# Repositories
from app.repositories.video import VideoRepository
from app.repositories.chat import ChatRepository

# Legacy services (to be migrated)
from app.services.proxy import ProxyService
from app.services.youtube import YouTubeService
from app.services.llm import LLMService

# New provider interfaces
from app.core.providers.llm_provider import LLMProvider
from app.core.providers.embedding_provider import EmbeddingProvider
from app.core.providers.vector_store import VectorStore

# Provider type enums
from app.models.enums import LLMProviderType, EmbeddingProviderType

# Concrete providers
from app.core.providers.gemini_provider import GeminiProvider
from app.core.providers.groq_provider import GroqProvider
from app.core.providers.sentence_transformer_embedding import SentenceTransformerEmbedding
from app.core.providers.pgvector_store import PgVectorStore

# New services
from app.services.chunking import TranscriptChunker
from app.services.ingestion import IngestionService
from app.services.summarization import SummarizationService
from app.services.retrieval import RetrievalService
from app.services.chat import ChatService


# =============================================================================
# PROVIDER FACTORIES
# =============================================================================

@lru_cache
def get_chat_llm_provider() -> LLMProvider:
    """
    Get LLM provider for chat operations.
    
    Default: Gemini (configured in settings.CHAT_LLM_PROVIDER)
    """
    provider_type = settings.CHAT_LLM_PROVIDER
    
    if provider_type == LLMProviderType.GEMINI:
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL_NAME,
        )
    elif provider_type == LLMProviderType.GROQ:
        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_NAME,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")


@lru_cache
def get_summary_llm_provider() -> LLMProvider:
    """
    Get LLM provider for summarization operations.
    
    Default: Groq/Llama (configured in settings.SUMMARY_LLM_PROVIDER)
    """
    provider_type = settings.SUMMARY_LLM_PROVIDER
    
    if provider_type == LLMProviderType.GROQ:
        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_NAME,
        )
    elif provider_type == LLMProviderType.GEMINI:
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL_NAME,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """
    Get embedding provider for vector operations.
    
    Default: SentenceTransformer (configured in settings.EMBEDDING_PROVIDER)
    """
    provider_type = settings.EMBEDDING_PROVIDER
    
    if provider_type == EmbeddingProviderType.SENTENCE_TRANSFORMER:
        return SentenceTransformerEmbedding(
            model_name=settings.EMBEDDING_MODEL,
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider_type}")


def get_vector_store(
    db: AsyncSession = Depends(get_db_session),
) -> VectorStore:
    """Get vector store for similarity search."""
    return PgVectorStore(session=db)


# =============================================================================
# LEGACY SERVICE FACTORIES (for backward compatibility)
# =============================================================================

@lru_cache
def get_proxy_service() -> ProxyService:
    """Get proxy service for YouTube API calls."""
    return ProxyService(
        host=settings.DATAIMPULSE_HOST,
        port=settings.DATAIMPULSE_PORT,
        login=settings.DATAIMPULSE_LOGIN,
        password=settings.DATAIMPULSE_PASSWORD,
    )


def get_video_repository(
    db: AsyncSession = Depends(get_db_session),
) -> VideoRepository:
    """Get video repository for transcript caching."""
    return VideoRepository(db)


def get_chat_repository(
    db: AsyncSession = Depends(get_db_session),
) -> ChatRepository:
    """Get chat repository for conversation persistence."""
    return ChatRepository(db)


def get_youtube_service(
    proxy_service: ProxyService = Depends(get_proxy_service),
    video_repository: VideoRepository = Depends(get_video_repository),
) -> YouTubeService:
    """Get YouTube service for playlist/transcript extraction."""
    return YouTubeService(
        proxy_service=proxy_service,
        video_repository=video_repository,
    )


@lru_cache
def get_llm_service() -> LLMService:
    """
    Get legacy LLM service.
    
    DEPRECATED: Use get_chat_llm_provider() or get_summary_llm_provider() instead.
    """
    return LLMService(
        gemini_api_key=settings.GEMINI_API_KEY,
        gemini_model_name=settings.GEMINI_MODEL_NAME,
        groq_api_key=settings.GROQ_API_KEY,
        groq_model_name=settings.GROQ_MODEL_NAME,
    )


# =============================================================================
# NEW RAG SERVICE FACTORIES
# =============================================================================

@lru_cache
def get_chunker() -> TranscriptChunker:
    """Get transcript chunker with default settings."""
    return TranscriptChunker(
        chunk_size=1000,
        chunk_overlap=200,
        min_chunk_size=100,
    )


def get_ingestion_service(
    chunker: TranscriptChunker = Depends(get_chunker),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> IngestionService:
    """Get ingestion service for indexing transcripts."""
    return IngestionService(
        chunker=chunker,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def get_summarization_service(
    llm_provider: LLMProvider = Depends(get_summary_llm_provider),
) -> SummarizationService:
    """Get summarization service for Map-Reduce summary."""
    return SummarizationService(llm_provider=llm_provider)


def get_retrieval_service(
    llm_provider: LLMProvider = Depends(get_chat_llm_provider),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RetrievalService:
    """Get retrieval service for RAG context search."""
    return RetrievalService(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def get_chat_service(
    youtube_service: YouTubeService = Depends(get_youtube_service),
    summarization_service: SummarizationService = Depends(get_summarization_service),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_llm_provider: LLMProvider = Depends(get_chat_llm_provider),
    chat_repository: ChatRepository = Depends(get_chat_repository),
) -> ChatService:
    """
    Get chat service with full RAG integration.
    
    Wires together:
    - YouTubeService for playlist extraction
    - SummarizationService for Map-Reduce summarization
    - IngestionService for vector indexing
    - RetrievalService for RAG context retrieval
    - LLMProvider for chat generation
    """
    return ChatService(
        youtube_service=youtube_service,
        summarization_service=summarization_service,
        ingestion_service=ingestion_service,
        retrieval_service=retrieval_service,
        chat_llm_provider=chat_llm_provider,
        chat_repository=chat_repository,
    )
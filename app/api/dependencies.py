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
from app.services.extractive import ExtractiveSummarizer


# =============================================================================
# PROVIDER FACTORIES
# =============================================================================

@lru_cache
def get_gemini_provider() -> LLMProvider:
    """
    Get Gemini LLM provider.
    
    Used for:
    - Summarization (large context window, high TPM)
    - RAG-enhanced chat (quality for complex retrieval)
    """
    return GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL_NAME,
    )


@lru_cache
def get_groq_provider() -> LLMProvider:
    """
    Get Groq LLM provider.
    
    Used for:
    - Fast chat without RAG (optimized for speed)
    """
    return GroqProvider(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_NAME,
    )


# Aliases for specific use cases (for clarity in dependency injection)
def get_summary_llm_provider() -> LLMProvider:
    """Get LLM provider for summarization (Gemini - large context, high TPM)."""
    return get_gemini_provider()


def get_rag_chat_llm_provider() -> LLMProvider:
    """Get LLM provider for RAG-enhanced chat (Gemini - quality for retrieval)."""
    return get_gemini_provider()


def get_fast_chat_llm_provider() -> LLMProvider:
    """Get LLM provider for fast chat without RAG (Groq - speed optimized)."""
    return get_groq_provider()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """
    Get embedding provider for vector operations.
    
    Uses SentenceTransformer with model from settings.EMBEDDING_MODEL.
    Default: all-MiniLM-L6-v2 (fast, good quality)
    """
    return SentenceTransformerEmbedding(
        model_name=settings.EMBEDDING_MODEL,
    )


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

from app.core.constants import RAGConfig, ExtractiveSummaryConfig

# ... (rest of imports)

@lru_cache
def get_chunker() -> TranscriptChunker:
    """Get transcript chunker with default settings."""
    return TranscriptChunker(
        chunk_size=RAGConfig.CHUNK_SIZE,
        chunk_overlap=RAGConfig.CHUNK_OVERLAP,
        min_chunk_size=RAGConfig.MIN_CHUNK_SIZE,
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


@lru_cache
def get_extractive_summarizer() -> ExtractiveSummarizer:
    """
    Get extractive summarizer for pre-processing transcripts.
    
    Uses TextRank algorithm with multi-language tokenizer support.
    """
    return ExtractiveSummarizer(
        sentences_per_video=ExtractiveSummaryConfig.SENTENCES_PER_VIDEO,
        fallback_sentence_count=ExtractiveSummaryConfig.FALLBACK_SENTENCE_COUNT,
    )


def get_summarization_service(
    llm_provider: LLMProvider = Depends(get_summary_llm_provider),
    extractive_summarizer: ExtractiveSummarizer = Depends(get_extractive_summarizer),
) -> SummarizationService:
    """Get summarization service for Map-Reduce summary with extractive pre-processing."""
    return SummarizationService(
        llm_provider=llm_provider,
        extractive_summarizer=extractive_summarizer,
    )


def get_retrieval_service(
    llm_provider: LLMProvider = Depends(get_rag_chat_llm_provider),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RetrievalService:
    """Get retrieval service for RAG context search (uses Gemini)."""
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
    rag_llm_provider: LLMProvider = Depends(get_rag_chat_llm_provider),
    fast_llm_provider: LLMProvider = Depends(get_fast_chat_llm_provider),
    chat_repository: ChatRepository = Depends(get_chat_repository),
) -> ChatService:
    """
    Get chat service with full RAG integration.
    
    Wires together:
    - YouTubeService for playlist extraction
    - SummarizationService for Map-Reduce summarization (Gemini)
    - IngestionService for vector indexing
    - RetrievalService for RAG context retrieval (Gemini)
    - RAG LLM Provider for context-aware chat (Gemini)
    - Fast LLM Provider for quick chat without RAG (Groq)
    """
    return ChatService(
        youtube_service=youtube_service,
        summarization_service=summarization_service,
        ingestion_service=ingestion_service,
        retrieval_service=retrieval_service,
        rag_llm_provider=rag_llm_provider,
        fast_llm_provider=fast_llm_provider,
        chat_repository=chat_repository,
    )


# =============================================================================
# JOB SERVICE FACTORIES
# =============================================================================

from app.repositories.job import JobRepository
from app.services.job_service import JobService


def get_job_repository(
    db: AsyncSession = Depends(get_db_session),
) -> JobRepository:
    """Get job repository for job persistence."""
    return JobRepository(db)


def get_job_service(
    job_repository: JobRepository = Depends(get_job_repository),
    chat_repository: ChatRepository = Depends(get_chat_repository),
) -> JobService:
    """Get job service for background job management."""
    return JobService(
        job_repository=job_repository,
        chat_repository=chat_repository,
    )


# =============================================================================
# STANDALONE FACTORIES (for background worker - no Depends)
# =============================================================================

def create_youtube_service(db: AsyncSession) -> YouTubeService:
    """Create YouTube service with DB session (for background worker)."""
    proxy = get_proxy_service()
    video_repo = VideoRepository(db)
    return YouTubeService(proxy_service=proxy, video_repository=video_repo)


def create_summarization_service() -> SummarizationService:
    """Create summarization service without FastAPI Depends (for background worker)."""
    return SummarizationService(
        llm_provider=get_summary_llm_provider(),
        extractive_summarizer=get_extractive_summarizer(),
    )


async def create_ingestion_service(db: AsyncSession) -> IngestionService:
    """Create ingestion service with DB session (for background worker)."""
    return IngestionService(
        chunker=get_chunker(),
        embedding_provider=get_embedding_provider(),
        vector_store=PgVectorStore(session=db),
    )


async def create_retrieval_service(db: AsyncSession) -> RetrievalService:
    """Create retrieval service with DB session (for background worker)."""
    return RetrievalService(
        llm_provider=get_rag_chat_llm_provider(),
        embedding_provider=get_embedding_provider(),
        vector_store=PgVectorStore(session=db),
    )
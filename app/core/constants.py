"""
Application-wide constants and configuration limits.

Refactored into static classes for better namespace management and discoverability.
"""

class PaginationConfig:
    """Configuration for API pagination."""
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100


class MessageConfig:
    """Configuration for chat messages and history."""
    MAX_LENGTH = 10_000  # Characters
    MAX_PER_CONVERSATION = 1000
    HISTORY_CONTEXT_SIZE = 5  # Messages included in LLM context


class RateLimitConfig:
    """Rate limiting thresholds (requests per minute)."""
    SUMMARIZE = "10/minute"
    CHAT = "30/minute"


class RAGConfig:
    """Configuration for RAG (Retrieval Augmented Generation) pipeline."""
    MAX_TRANSCRIPT_CHARS = 16_000  # ~4000 tokens per video (Safety limit)
    CHUNK_SIZE = 1000  # Characters per chunk (~250 tokens)
    CHUNK_OVERLAP = 200  # Characters overlap between chunks
    MIN_CHUNK_SIZE = 100
    EMBEDDING_BATCH_SIZE = 32
    TOP_K = 5  # Number of chunks to retrieve


class YouTubeConfig:
    """Configuration for YouTube service."""
    CONCURRENCY_LIMIT = 5  # Max parallel transcript fetches


class ExtractiveSummaryConfig:
    """Configuration for extractive pre-summarization (zero LLM cost)."""
    SENTENCES_PER_VIDEO = 50       # Max sentences to extract per video
    FALLBACK_SENTENCE_COUNT = 30   # When language tokenizer not supported
    MIN_TEXT_LENGTH = 500          # Skip extraction for texts shorter than this
    COMPRESSION_RATIO = 0.15       # Target 15% of original content
    # Threshold: only apply extractive pre-processing for large content
    ACTIVATION_THRESHOLD = 100_000  # chars (~25k tokens)
"""
Application-wide constants for limits and configuration.

These values are used for validation and should be shared with frontend.
"""

# =============================================================================
# PAGINATION LIMITS
# =============================================================================

CONVERSATIONS_DEFAULT_LIMIT = 20
CONVERSATIONS_MAX_LIMIT = 100


# =============================================================================
# MESSAGE LIMITS
# =============================================================================

MAX_MESSAGE_LENGTH = 10_000  # Characters
MAX_MESSAGES_PER_CONVERSATION = 1000
CHAT_HISTORY_CONTEXT_SIZE = 5  # Messages included in LLM context


# =============================================================================
# RATE LIMITS (requests per minute)
# =============================================================================

RATE_LIMIT_SUMMARIZE = "10/minute"
RATE_LIMIT_CHAT = "30/minute"


# =============================================================================
# CHUNKING & RAG LIMITS
# =============================================================================

MAX_TRANSCRIPT_CHARS = 16_000  # ~4000 tokens per video
CHUNK_SIZE = 1000  # Characters per chunk (~250 tokens)
CHUNK_OVERLAP = 200  # Characters overlap between chunks
MIN_CHUNK_SIZE = 100
EMBEDDING_BATCH_SIZE = 32
RAG_TOP_K = 5  # Number of chunks to retrieve


# =============================================================================
# YOUTUBE LIMITS
# =============================================================================

YOUTUBE_CONCURRENCY_LIMIT = 5  # Max parallel transcript fetches

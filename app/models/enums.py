"""
Enums for type-safe values across the application.
"""
from enum import Enum


class MessageRole(str, Enum):
    """Role for messages stored in database (conversation history)."""
    USER = "user"
    MODEL = "model"


class LLMRole(str, Enum):
    """Role for LLM provider messages (OpenAI/Gemini/Groq compatible)."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMProviderType(str, Enum):
    """Supported LLM provider types for configuration."""
    GEMINI = "gemini"
    GROQ = "groq"


class JobStatus(str, Enum):
    """Status of a background summarization job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoStatus(str, Enum):
    """Status of video transcript processing."""
    SUCCESS = "success"  # Full transcript available
    FALLBACK_DESCRIPTION = "fallback_description"  # Using video description
    NO_CONTENT = "no_content"  # No transcript AND no description
    PRIVATE = "private"  # Video is private
    BLOCKED = "blocked"  # IP blocked after retries
    ERROR = "error"  # Other error during processing

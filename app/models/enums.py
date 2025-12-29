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

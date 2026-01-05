"""
Application configuration using pydantic-settings.
"""
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    PROJECT_NAME: str = "Youtube Playlist Summarizer"
    BACKEND_CORS_ORIGINS: Union[List[str], str]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # Gemini API
    GEMINI_MODEL_NAME: str
    GEMINI_API_KEY: str
    
    # Groq API
    GROQ_MODEL_NAME: str
    GROQ_API_KEY: str

    # Database
    DATABASE_URL: str
    
    # DataImpulse Proxy
    DATAIMPULSE_HOST: str
    DATAIMPULSE_PORT: int
    DATAIMPULSE_LOGIN: str
    DATAIMPULSE_PASSWORD: str

    # Auth
    SECRET_KEY: str

    # RAG Configuration
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"

    # Summarization Limits (based on LLM context window)
    # Formula: MAX_CHARS = CONTEXT_TOKENS * 4 * SAFETY_MARGIN
    # Example for Gemini (1M tokens): 1_000_000 * 4 * 0.5 = 2_000_000 chars
    SUMMARIZATION_MAX_INPUT_CHARS: int = 2_000_000    # Max chars for single video input
    SUMMARIZATION_BATCH_THRESHOLD: int = 3_000_000   # Threshold: batch vs map-reduce
    SUMMARIZATION_CHUNK_SIZE: int = 2_000_000         # Chunk size for map-reduce

    # Background Jobs Configuration
    PUBLIC_SUMMARIZATION_TIMEOUT_SECONDS: int = 100   # Timeout for public users
    JOB_MAX_CONCURRENT_PER_USER: int = 3              # Max active jobs per user
    JOB_TIMEOUT_SECONDS: int = 600                    # 10 minutes max per job
    JOB_EXPIRY_DAYS: int = 3                          # Days until job auto-delete

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

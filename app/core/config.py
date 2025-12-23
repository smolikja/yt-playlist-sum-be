"""
Application configuration using pydantic-settings.
"""
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.enums import LLMProviderType, EmbeddingProviderType, VectorStoreType


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

    # RAG Configuration - using type-safe enums
    CHAT_LLM_PROVIDER: LLMProviderType = LLMProviderType.GEMINI
    SUMMARY_LLM_PROVIDER: LLMProviderType = LLMProviderType.GROQ
    EMBEDDING_PROVIDER: EmbeddingProviderType = EmbeddingProviderType.SENTENCE_TRANSFORMER
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_STORE: VectorStoreType = VectorStoreType.PGVECTOR

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

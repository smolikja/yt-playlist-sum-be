from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

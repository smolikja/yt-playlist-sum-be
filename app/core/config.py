from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Youtube Playlist Summarizer"

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

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

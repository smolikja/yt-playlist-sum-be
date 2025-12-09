from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Youtube Playlist Summarizer"
    GEMINI_API_KEY: str
    DATABASE_URL: str
    
    # DataImpulse Proxy Settings
    DATAIMPULSE_HOST: str | None = None
    DATAIMPULSE_PORT: int | None = None
    DATAIMPULSE_LOGIN: str | None = None
    DATAIMPULSE_PASSWORD: str | None = None

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

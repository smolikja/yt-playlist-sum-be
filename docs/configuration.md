# Configuration

The application uses environment variables for configuration, managed with `pydantic-settings`.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://dev:dev@localhost:5432/ytsum_dev` |
| `SECRET_KEY` | JWT signing secret | `supersecretkey123` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `GROQ_API_KEY` | Groq API key | `gsk_...` |

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` | Gemini model for chat |
| `GROQ_MODEL_NAME` | `meta-llama/llama-4-scout-17b-16e-instruct` | Groq model for summarization |
| `CHAT_LLM_PROVIDER` | `gemini` | Provider for chat (`gemini` or `groq`) |
| `SUMMARY_LLM_PROVIDER` | `groq` | Provider for summarization |

### RAG Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `sentence_transformers` | Embedding backend |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Model for embeddings |
| `VECTOR_STORE` | `pgvector` | Vector database backend |

### Proxy Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAIMPULSE_HOST` | `gw.dataimpulse.com` | Proxy hostname |
| `DATAIMPULSE_PORT` | `823` | Proxy port |
| `DATAIMPULSE_LOGIN` | - | Proxy username |
| `DATAIMPULSE_PASSWORD` | - | Proxy password |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Allowed origins |

## Example .env

```env
# Gemini API
GEMINI_MODEL_NAME=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here

# Groq API
GROQ_MODEL_NAME=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_API_KEY=your_groq_api_key_here

# Database (PostgreSQL with pgvector - use docker-compose.yml)
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/ytsum_dev

# DataImpulse Proxy
DATAIMPULSE_HOST=gw.dataimpulse.com
DATAIMPULSE_PORT=823
DATAIMPULSE_LOGIN=
DATAIMPULSE_PASSWORD=

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# JWT Secret
SECRET_KEY=supersecretkey123
```

## Settings Class

Located in `app/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    # ... more fields
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()
```

## Accessing Settings

```python
from app.core.config import settings

print(settings.DATABASE_URL)
print(settings.GEMINI_API_KEY)
```

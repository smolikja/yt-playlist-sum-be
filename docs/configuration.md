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
| `EMBEDDING_PROVIDER` | `sentence_transformer` | Embedding backend |
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

---

## Application Constants

Defined in `app/core/constants.py`:

### Pagination
| Constant | Value | Description |
|----------|-------|-------------|
| `CONVERSATIONS_DEFAULT_LIMIT` | 20 | Default conversations per page |
| `CONVERSATIONS_MAX_LIMIT` | 100 | Max conversations per page |

### Messages
| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_MESSAGE_LENGTH` | 10,000 | Max chars per chat message |
| `MAX_MESSAGES_PER_CONVERSATION` | 1,000 | Max messages in conversation |
| `CHAT_HISTORY_CONTEXT_SIZE` | 5 | Messages sent to LLM |

### Rate Limits
| Constant | Value | Description |
|----------|-------|-------------|
| `RATE_LIMIT_SUMMARIZE` | 10/minute | Summarize endpoint |
| `RATE_LIMIT_CHAT` | 30/minute | Chat endpoint |

### RAG
| Constant | Value | Description |
|----------|-------|-------------|
| `CHUNK_SIZE` | 1,000 | Chars per chunk |
| `CHUNK_OVERLAP` | 200 | Overlap between chunks |
| `RAG_TOP_K` | 5 | Chunks retrieved |
| `EMBEDDING_BATCH_SIZE` | 32 | Batch size for embeddings |

### YouTube
| Constant | Value | Description |
|----------|-------|-------------|
| `YOUTUBE_CONCURRENCY_LIMIT` | 5 | Parallel transcript fetches |
| `MAX_TRANSCRIPT_CHARS` | 16,000 | Max chars per video |

---

## Settings Class

Located in `app/core/config.py`:

```python
from pydantic_settings import BaseSettings
from app.models.enums import LLMProviderType

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    
    # Type-safe provider selection
    CHAT_LLM_PROVIDER: LLMProviderType = LLMProviderType.GEMINI
    SUMMARY_LLM_PROVIDER: LLMProviderType = LLMProviderType.GROQ
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

## Accessing Configuration

```python
from app.core.config import settings
from app.core.constants import MAX_MESSAGE_LENGTH

print(settings.CHAT_LLM_PROVIDER)  # LLMProviderType.GEMINI
print(MAX_MESSAGE_LENGTH)          # 10000
```

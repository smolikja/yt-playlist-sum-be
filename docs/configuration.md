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
| `GEMINI_MODEL_NAME` | (see .env.example) | Gemini model for summarization and RAG chat |
| `GROQ_MODEL_NAME` | (see .env.example) | Groq model for fast chat without RAG |

> **Note:** LLM provider assignments are hardcoded:
> - **Summarization** → Gemini (large context, high TPM)
> - **Chat with RAG** → Gemini (quality for retrieval)
> - **Chat without RAG** → Groq (fast inference)

### RAG Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | SentenceTransformer model for embeddings |

**Alternative embedding models:**
- `all-MiniLM-L6-v2` - Fast, English-only (22M params)
- `all-mpnet-base-v2` - Higher quality, English-only (109M params)
- `paraphrase-multilingual-MiniLM-L12-v2` - Multilingual, faster (118M params)

### Summarization Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `SUMMARIZATION_MAX_INPUT_CHARS` | `2000000` | Max chars for single video input |
| `SUMMARIZATION_BATCH_THRESHOLD` | `3000000` | Threshold: batch vs map-reduce |
| `SUMMARIZATION_CHUNK_SIZE` | `2000000` | Chunk size for map-reduce |

**Calculation formula:**

```
MAX_CHARS = CONTEXT_TOKENS × 4 × SAFETY_MARGIN
```

| Model | Context | Recommended MAX_INPUT |
|-------|---------|---------------------|
| Gemini 2.5 Flash | 1M tokens | 2,000,000 chars |
| Llama 3.3 70B | 128k tokens | 256,000 chars |
| GPT-4 Turbo | 128k tokens | 256,000 chars |

> **Note:** Use 0.5 safety margin to leave room for prompt + response tokens.

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

Defined in `app/core/constants.py`, constants are grouped by functional area:

### Pagination (`PaginationConfig`)
| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_LIMIT` | 20 | Default conversations per page |
| `MAX_LIMIT` | 100 | Max conversations per page |

### Messages (`MessageConfig`)
| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_LENGTH` | 10,000 | Max chars per chat message |
| `MAX_PER_CONVERSATION` | 1,000 | Max messages in conversation |
| `HISTORY_CONTEXT_SIZE` | 5 | Messages sent to LLM |

### Rate Limits (`RateLimitConfig`)
| Constant | Value | Description |
|----------|-------|-------------|
| `SUMMARIZE` | 10/minute | Summarize endpoint |
| `CHAT` | 30/minute | Chat endpoint |

### RAG & Summarization (`RAGConfig` / `SummarizationConfig`)
| Constant | Value | Description |
|----------|-------|-------------|
| `RAGConfig.CHUNK_SIZE` | 1,000 | Chars per chunk |
| `RAGConfig.CHUNK_OVERLAP` | 200 | Overlap between chunks |
| `RAGConfig.TOP_K` | 5 | Chunks retrieved |
| `SummarizationConfig.MAX_SINGLE_VIDEO_CHARS` | 2M | Limit per video |
| `SummarizationConfig.MAX_BATCH_CONTEXT_CHARS` | 3M | Batch limit |

### Extractive Pre-Processing (`ExtractiveSummaryConfig`)
| Constant | Value | Description |
|----------|-------|-------------|
| `ACTIVATION_THRESHOLD` | 100,000 | Chars threshold to enable extraction |
| `COMPRESSION_RATIO` | 0.15 | Target 15% of original content |
| `SENTENCES_PER_VIDEO` | 50 | Max sentences to extract per video |
| `FALLBACK_SENTENCE_COUNT` | 30 | Fallback for unsupported languages |

### YouTube (`YouTubeConfig`)
| Constant | Value | Description |
|----------|-------|-------------|
| `CONCURRENCY_LIMIT` | 5 | Parallel transcript fetches |

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
from app.core.constants import MessageConfig

print(settings.CHAT_LLM_PROVIDER)    # LLMProviderType.GEMINI
print(MessageConfig.MAX_LENGTH)      # 10000
```

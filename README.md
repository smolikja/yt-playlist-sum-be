# YouTube Playlist Summarizer Backend

A FastAPI-based backend for summarizing YouTube playlists using AI. Features RAG-enhanced chat with vector search and multi-provider LLM support.

## Features

- **Playlist Summarization** - Extract and summarize YouTube playlist transcripts
- **RAG-Enhanced Chat** - Context-aware conversations with vector similarity search
- **Multi-Provider LLMs** - Support for Gemini and Groq with model-agnostic architecture
- **Transcript Caching** - PostgreSQL-backed caching to minimize API calls
- **JWT Authentication** - Secure user authentication with FastAPI Users

## Quick Start

```bash
# Install dependencies
uv sync

# Start PostgreSQL with pgvector
docker-compose up -d

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run migrations
uv run alembic upgrade head

# Start server
uv run uvicorn app.main:app --reload
```

API available at http://localhost:8000

## Documentation

| Document | Description |
|----------|-------------|
| **[Architecture](docs/architecture.md)** | System overview, request flows, design principles |
| **[API Reference](docs/api-reference.md)** | Complete endpoint documentation |
| **[RAG Pipeline](docs/rag-pipeline.md)** | Vector indexing and retrieval system |
| **[Authentication](docs/authentication.md)** | JWT auth with FastAPI Users |
| **[YouTube Service](docs/youtube-service.md)** | Playlist extraction and transcript caching |
| **[LLM Providers](docs/llm-providers.md)** | Gemini, Groq, and provider abstraction |
| **[Database](docs/database.md)** | PostgreSQL schema and migrations |
| **[Configuration](docs/configuration.md)** | Environment variables reference |
| **[Development](docs/development.md)** | Setup guide and project structure |

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL with pgvector
- **LLMs:** Google Gemini, Groq (Llama)
- **Embeddings:** SentenceTransformers (all-MiniLM-L6-v2)
- **Auth:** FastAPI Users + JWT
- **Package Manager:** uv

## Project Structure

```
yt-playlist-sum-be/
├── app/
│   ├── api/          # Routes, auth, dependencies
│   ├── core/         # Config, DB, providers
│   ├── models/       # Pydantic & SQLAlchemy models
│   ├── repositories/ # Data access layer
│   └── services/     # Business logic
├── docs/             # Documentation
├── alembic/          # Database migrations
├── tests/            # Test suite
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/summarize` | Summarize a YouTube playlist |
| POST | `/api/v1/chat` | Chat within a conversation context |
| GET | `/api/v1/conversations` | List user conversations |
| GET | `/api/v1/conversations/{id}` | Get conversation details |
| DELETE | `/api/v1/conversations/{id}` | Delete a conversation |

Full documentation: [API Reference](docs/api-reference.md)

## Configuration

Required environment variables:

```env
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/ytsum_dev
SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
```

Full reference: [Configuration](docs/configuration.md)

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

## License

MIT

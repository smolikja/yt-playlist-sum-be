# Development Guide

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for PostgreSQL)

## Setup

```bash
# Clone repository
git clone <repository-url>
cd yt-playlist-sum-be

# Install dependencies
uv sync

# Start PostgreSQL
docker-compose up -d

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload
```

## Project Structure

```
yt-playlist-sum-be/
├── alembic/              # Database migrations
│   └── versions/
├── app/
│   ├── api/              # FastAPI routes and dependencies
│   │   ├── auth.py       # Authentication setup
│   │   ├── dependencies.py
│   │   └── endpoints.py
│   ├── core/             # Core configuration and utilities
│   │   ├── config.py     # Settings
│   │   ├── db.py         # Database connection
│   │   ├── providers/    # LLM, embedding, vector store abstractions
│   │   └── ...
│   ├── models/           # Pydantic and SQLAlchemy models
│   │   ├── api.py        # Request/response schemas
│   │   ├── sql.py        # Database models
│   │   └── youtube.py    # YouTube data models
│   ├── repositories/     # Data access layer
│   └── services/         # Business logic
│       ├── chat.py       # Main orchestration
│       ├── chunking.py   # Transcript chunking
│       ├── ingestion.py  # RAG indexing
│       ├── retrieval.py  # RAG retrieval
│       ├── summarization.py
│       └── youtube.py    # YouTube integration
├── docs/                 # Documentation
├── tests/                # Test suite
├── docker-compose.yml    # Local PostgreSQL
├── pyproject.toml        # Dependencies
└── README.md
```

## Commands

| Command | Description |
|---------|-------------|
| `uv sync` | Install dependencies |
| `uv run uvicorn app.main:app --reload` | Start dev server |
| `uv run alembic upgrade head` | Apply migrations |
| `uv run alembic revision --autogenerate -m "msg"` | Create migration |
| `uv run pytest` | Run tests |
| `uv add <package>` | Add dependency |

## Code Style

- Type hints on all functions
- Async/await for I/O operations
- Dependency injection via FastAPI `Depends()`
- Loguru for logging

## Adding a New Feature

1. **Model** - Define Pydantic schemas in `app/models/`
2. **Repository** - Add data access in `app/repositories/`
3. **Service** - Implement business logic in `app/services/`
4. **Endpoint** - Create API route in `app/api/endpoints.py`
5. **Dependency** - Wire up in `app/api/dependencies.py`
6. **Migration** - Update database if needed

## Testing

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_chat.py -v

# With coverage
uv run pytest --cov=app
```

## Debugging

Enable SQL logging:
```python
# app/core/db.py
engine = create_async_engine(db_url, echo=True)
```

Check logs:
```bash
tail -f logs/app.log
```

## API Documentation

When server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

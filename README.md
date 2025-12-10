# Youtube Playlist Summarizer Backend

A FastAPI-based backend application designed to summarize YouTube playlists using the Gemini API. This project serves as the server-side component for processing playlist data, caching transcripts, and generating concise, interactive summaries.

## Features

- **FastAPI Framework:** High-performance, easy-to-learn, fast-to-code, ready for production.
- **Modern Python:** Built with Python 3.14+ and type hints.
- **Dependency Management:** Uses `uv` for blazing fast package management and virtual environment handling.
- **Database Architecture:** Uses SQLAlchemy with async support and Alembic for migrations.
- **Efficient Caching:** Caches YouTube video transcripts to minimize external API calls.
- **Configuration:** Robust settings management using `pydantic-settings`.

## Tech Stack

- **Language:** Python 3.14+
- **Framework:** FastAPI
- **Database:** SQLAlchemy (Async), Alembic
- **AI/LLM:** Google Gemini API
- **Package Manager:** uv
- **Environment Management:** python-dotenv, pydantic-settings

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed on your machine.
- Python 3.14+ (managed by uv).

### Installation

1. **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd yt-playlist-sum-be
    ```

2. **Install dependencies:**

    ```bash
    uv sync
    ```

### Configuration

1. **Environment Variables:**

    Copy the example environment file to `.env`:

    ```bash
    cp .env.example .env
    ```

2. **Update Settings:**

    Open `.env` and configure your keys:

    ```env
    # Gemini API Configuration
    GEMINI_MODEL_NAME=gemini-2.5-flash
    GEMINI_API_KEY=your_gemini_api_key_here

    # Database Configuration
    DATABASE_URL=sqlite+aiosqlite:///./sql_app.db
    # Production recommended:
    # DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

    # DataImpulse Proxy
    DATAIMPULSE_HOST=gw.dataimpulse.com
    DATAIMPULSE_PORT=823
    DATAIMPULSE_LOGIN=
    DATAIMPULSE_PASSWORD=
    ```

### Database Setup

This project uses **Alembic** for database migrations. Before running the application, you must initialize the database schema.

1. **Run Migrations:**

    Apply the latest database changes:

    ```bash
    uv run alembic upgrade head
    ```

### Running the Application

You can start the server using `uv run` to ensure it uses the project's virtual environment.

**Development Mode (with auto-reload):**

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## Development Workflow & Best Practices

### Database Migrations

When modifying `app/models/sql.py`, always create a new migration to keep the database schema in sync.

1. **Make changes** to SQLAlchemy models.
2. **Generate a migration script:**

    ```bash
    uv run alembic revision --autogenerate -m "describe your changes"
    ```

3. **Verify the generated script** in `alembic/versions/`.
4. **Apply the migration:**

    ```bash
    uv run alembic upgrade head
    ```

### Testing

Tests are located in the `tests/` directory.

```bash
# Run all tests (assuming pytest is installed/configured)
uv run pytest
```

### Dependency Management

To add a new dependency:

```bash
uv add <package-name>
```

To update dependencies:

```bash
uv lock --upgrade
```

## API Documentation

FastAPI provides automatic interactive documentation. Once the server is running, visit:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```text
yt-playlist-sum-be/
├── alembic/          # Database migration scripts
├── app/
│   ├── api/          # API route endpoints
│   ├── core/         # Core config, DB connection, logging
│   ├── models/       # Pydantic and SQLAlchemy models
│   ├── repositories/ # Data access layer
│   ├── services/     # Business logic (LLM, YouTube, Chat)
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── .env              # Environment variables (do not commit secrets)
├── pyproject.toml    # Project dependencies and settings
└── README.md         # Project documentation
```

# Youtube Playlist Summarizer Backend

A FastAPI-based backend application designed to summarize YouTube playlists using the Gemini API. This project serves as the server-side component for processing playlist data and generating concise summaries.

## Features

- **FastAPI Framework:** High-performance, easy-to-learn, fast-to-code, ready for production.
- **Modern Python:** Built with Python 3.14+ and type hints.
- **Dependency Management:** Uses `uv` for blazing fast package management and virtual environment handling.
- **Configuration:** Robust settings management using `pydantic-settings`.
- **Health Check:** Standardized endpoint for service health monitoring.

## Tech Stack

- **Language:** Python 3.14+
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Package Manager:** uv
- **Environment Management:** python-dotenv, pydantic-settings

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed on your machine.

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
    cp .env .env.local # Or just ensure .env exists
    ```

2. **Update Settings:**

    Open `.env` and configure your keys:

    ```env
    GEMINI_API_KEY=your_actual_gemini_api_key
    
    # For SQLite (default, easy setup)
    DATABASE_URL=sqlite:///./sql_app.db
    
    # For PostgreSQL (recommended for production)
    # DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
    ```

### Database Setup

This project uses **Alembic** for database migrations. Before running the application, you must initialize the database schema.

1. **Run Migrations:**

    Apply the latest database changes:

    ```bash
    uv run alembic upgrade head
    ```
    
    This command will create the necessary tables (e.g., `videos`) in your configured database.

### Running the Application

You can start the server using `uv run` to ensure it uses the project's virtual environment.

**Development Mode (with auto-reload):**

```bash
uv run uvicorn app.main:app --reload
```

Or using the convenience script if you retained the direct execution method:

```bash
uv run app/main.py
```

The API will be available at `http://localhost:8000`.

### API Documentation

FastAPI provides automatic interactive documentation. Once the server is running, visit:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```text
yt-playlist-sum-be/
├── app/
│   ├── api/          # API route endpoints
│   ├── core/         # Core config and security
│   ├── services/     # Business logic and external services
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── .env              # Environment variables (do not commit secrets)
├── pyproject.toml    # Project dependencies and settings
└── README.md         # Project documentation
```

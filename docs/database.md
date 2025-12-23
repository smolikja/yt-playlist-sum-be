# Database

The application uses PostgreSQL with the pgvector extension for vector similarity search.

## Requirements

- PostgreSQL 16+
- pgvector extension

## Docker Setup (Development)

```bash
docker-compose up -d
```

This starts PostgreSQL with pgvector at `localhost:5432`.

**docker-compose.yml:**
```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: ytsum_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    volumes:
      - pgdata:/var/lib/postgresql/data
```

## Connection

```env
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/ytsum_dev
```

## Schema

### Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false
);
```

### Videos (Transcript Cache)
```sql
CREATE TABLE videos (
    id VARCHAR PRIMARY KEY,        -- YouTube video ID
    title VARCHAR,
    transcript JSON,               -- Transcript segments array
    language VARCHAR DEFAULT 'en',
    created_at TIMESTAMP
);
```

### Conversations
```sql
CREATE TABLE conversations (
    id VARCHAR PRIMARY KEY,        -- UUID
    user_id UUID REFERENCES users(id),
    playlist_url VARCHAR,
    title VARCHAR,
    summary TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Messages
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR REFERENCES conversations(id),
    role VARCHAR NOT NULL,         -- 'user' or 'model'
    content TEXT NOT NULL,
    created_at TIMESTAMP
);
```

### Document Embeddings (Vector Store)
```sql
CREATE TABLE document_embeddings (
    id VARCHAR PRIMARY KEY,        -- {video_id}_{chunk_index}
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    chunk_metadata JSONB,
    namespace VARCHAR,             -- Playlist URL
    created_at TIMESTAMP
);

-- HNSW index for similarity search
CREATE INDEX ix_document_embeddings_embedding_hnsw
ON document_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Migrations

Managed with Alembic.

```bash
# Apply all migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Rollback one step
uv run alembic downgrade -1
```

### Migration History

| Revision | Description |
|----------|-------------|
| `ae7aa9f92c8a` | Initial migration (users, videos, conversations, messages) |
| `b8c9f2d3e4a5` | Add document_embeddings table |
| `c9d0e1f2a3b4` | Enable pgvector extension, convert to vector type, add HNSW index |

## SQLAlchemy Models

Located in `app/models/sql.py`:

- `User` - FastAPI Users integration
- `VideoModel` - Cached transcripts
- `ConversationModel` - Chat sessions
- `MessageModel` - Chat messages
- `DocumentEmbedding` - Vector store entries

## Async Session

```python
from app.core.db import get_db_session

async def my_function(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User))
    users = result.scalars().all()
```

## Repositories

Data access layer in `app/repositories/`:

- `VideoRepository` - Transcript CRUD
- `ChatRepository` - Conversations and messages

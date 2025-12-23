from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://") and "asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

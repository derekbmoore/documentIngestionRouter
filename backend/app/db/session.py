"""
Database Session — Async SQLAlchemy
=====================================
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.db.models import Base

engine = create_async_engine(settings.database_url, echo=False, pool_size=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables (dev convenience — use Alembic in prod)."""
    async with engine.begin() as conn:
        # Enable extensions
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        )
        await conn.create_all(Base.metadata)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

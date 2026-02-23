from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base
from fastapi import HTTPException
from app.config import settings
from app.database.models import Base
from typing import Optional

# Lazy initialization
_engine: Optional[AsyncEngine] = None
_AsyncSessionLocal: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Get or create database engine (requires DATABASE_URL)."""
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set (required for direct DB / crawler / docs)")
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get or create session factory."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        engine = get_engine()
        _AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _AsyncSessionLocal


# Note: Engine and session factory are lazy-initialized via get_engine() and get_session_factory()
# This avoids DB connection attempts on module import


async def get_db() -> AsyncSession:
    """Dependency for getting database session (only when DATABASE_URL is set)."""
    if not settings.DATABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not set. Use Supabase API for chat/templates/knowledge-rules.",
        )
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database - create all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    engine = get_engine()
    await engine.dispose()


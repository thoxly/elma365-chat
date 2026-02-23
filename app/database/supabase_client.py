"""Supabase API client for backend (no direct DB connection)."""
from typing import Optional, Union
from fastapi import Depends, HTTPException

from app.config import settings

_client: Optional["SupabaseClient"] = None


def get_supabase_client():
    """Get or create Supabase client (singleton)."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_PUBLISHABLE_DEFAULT_KEY) must be set"
            )
        from supabase import create_client
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _client


def get_supabase():
    """FastAPI dependency: yield Supabase client."""
    try:
        yield get_supabase_client()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def use_supabase() -> bool:
    """True if app should use Supabase API instead of direct DB for chat/templates/rules."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


async def get_supabase_optional():
    """Yield Supabase client if configured, else None."""
    if use_supabase():
        try:
            yield get_supabase_client()
        except ValueError:
            yield None
    else:
        yield None


async def get_db_or_supabase():
    """Yield Supabase client when using API, else DB session. For chat/templates/knowledge-rules."""
    if use_supabase():
        try:
            yield get_supabase_client()
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
    else:
        from app.database.database import get_session_factory
        if not settings.DATABASE_URL:
            raise HTTPException(
                status_code=503,
                detail="Set DATABASE_URL or Supabase (SUPABASE_URL + SUPABASE_ANON_KEY)",
            )
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

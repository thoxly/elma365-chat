"""Supabase API client for backend (no direct DB connection)."""
import logging
from typing import Optional, Union
from fastapi import Depends, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)
_client: Optional["SupabaseClient"] = None


def get_supabase_client():
    """Get or create Supabase client (singleton)."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            logger.debug("Supabase client: SUPABASE_URL or Publishable Key not set")
            raise ValueError(
                "SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY (or SUPABASE_PUBLISHABLE_DEFAULT_KEY) must be set"
            )
        logger.debug("Creating Supabase client: url=%s, key_len=%s", settings.SUPABASE_URL, len(settings.SUPABASE_ANON_KEY or ""))
        from supabase import create_client
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        logger.info("Supabase client created successfully (storage backend: Supabase API)")
    return _client


def get_supabase():
    """FastAPI dependency: yield Supabase client."""
    try:
        yield get_supabase_client()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def use_supabase() -> bool:
    """True if app should use Supabase API instead of direct DB for chat/templates/rules."""
    use = bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)
    logger.debug("use_supabase() -> %s (SUPABASE_URL=%s, ANON_KEY_set=%s)", use, bool(settings.SUPABASE_URL), bool(settings.SUPABASE_ANON_KEY))
    return use


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
        logger.debug("get_db_or_supabase: using Supabase API path")
        try:
            client = get_supabase_client()
            yield client
        except ValueError as e:
            logger.warning("get_db_or_supabase: Supabase config error: %s", e)
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            logger.exception("get_db_or_supabase: Supabase client failed: %s", e)
            raise HTTPException(status_code=503, detail=f"Supabase failed: {e}")
    else:
        logger.debug("get_db_or_supabase: using direct DATABASE_URL path")
        from app.database.database import get_session_factory
        if not settings.DATABASE_URL:
            logger.debug("get_db_or_supabase: DATABASE_URL not set")
            raise HTTPException(
                status_code=503,
                detail="Set DATABASE_URL or Supabase (SUPABASE_URL + VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY)",
            )
        session_factory = get_session_factory()
        async with session_factory() as session:
            logger.debug("get_db_or_supabase: yielded DB session")
            try:
                yield session
            finally:
                await session.close()

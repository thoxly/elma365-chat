#!/usr/bin/env python3
"""
Check connection to Supabase (PostgreSQL) database.
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database.database import get_session_factory
from app.config import settings


async def check_db() -> bool:
    """Return True if DB connection and basic checks pass."""
    print("Checking database connection...")
    print(f"URL (masked): {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
    print()

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
            print("✅ Connection: OK")

            result = await session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'docs')"
            ))
            docs_exists = result.scalar()
            if docs_exists:
                result = await session.execute(text("SELECT COUNT(*) FROM docs"))
                count = result.scalar()
                print(f"✅ Table 'docs': exists ({count} rows)")
            else:
                print("⚠️  Table 'docs': not found (run migrations)")

            result = await session.execute(text(
                "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')"
            ))
            exts = [r[0] for r in result.fetchall()]
            if 'vector' in exts and 'pg_trgm' in exts:
                print("✅ Extensions: vector, pg_trgm")
            else:
                print(f"⚠️  Extensions: {exts} (run in Supabase SQL: CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;)")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print()
    print("Database check complete.")
    return True


if __name__ == "__main__":
    ok = asyncio.run(check_db())
    sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""
Check all services: Supabase, backend (Cloud Run), and optionally frontend (Vercel).
Set env: DATABASE_URL, API_URL (backend), FRONTEND_URL (optional).
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def check_db():
    print("=" * 50)
    print("1. Database (Supabase)")
    print("=" * 50)
    try:
        from scripts.check_db_connection import check_db as run_db_check
        return await run_db_check()
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False


async def check_backend():
    print()
    print("=" * 50)
    print("2. Backend (Cloud Run / local)")
    print("=" * 50)
    base_url = os.environ.get("API_URL", "http://localhost:8000")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url.rstrip('/')}/health") as resp:
                if resp.status == 200:
                    print(f"✅ Backend at {base_url}: OK")
                    return True
                else:
                    print(f"❌ Backend: status {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Backend: {e}")
        return False


async def check_frontend():
    print()
    print("=" * 50)
    print("3. Frontend (Vercel)")
    print("=" * 50)
    url = os.environ.get("FRONTEND_URL", "https://elma365-chat.vercel.app")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    print(f"✅ Frontend at {url}: OK")
                    return True
                else:
                    print(f"⚠️  Frontend: status {resp.status}")
                    return False
    except Exception as e:
        print(f"⚠️  Frontend: {e}")
        return False


async def main():
    print("ELMA365-chat: checking all services")
    print()

    db_ok = await check_db()
    backend_ok = await check_backend()
    frontend_ok = await check_frontend()

    print()
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Database:  {'✅' if db_ok else '❌'}")
    print(f"Backend:   {'✅' if backend_ok else '❌'}")
    print(f"Frontend:  {'✅' if frontend_ok else '❌'}")
    print()

    if not db_ok or not backend_ok:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

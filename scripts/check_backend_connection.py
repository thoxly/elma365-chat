#!/usr/bin/env python3
"""
Check backend (Cloud Run or local) availability.
Usage: python scripts/check_backend_connection.py [BASE_URL]
Default BASE_URL: http://localhost:8000
"""
import asyncio
import sys
import os

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)


async def check(url: str):
    base = url.rstrip("/")
    print(f"Checking backend at: {base}")
    print()

    async with aiohttp.ClientSession() as session:
        # Health
        try:
            async with session.get(f"{base}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ /health: {data.get('status', 'ok')}")
                else:
                    print(f"❌ /health: status {resp.status}")
        except Exception as e:
            print(f"❌ /health: {e}")
            return

        # API docs (optional)
        try:
            async with session.get(f"{base}/api/docs") as resp:
                if resp.status == 200:
                    print("✅ /api/docs: available")
                else:
                    print(f"⚠️  /api/docs: status {resp.status}")
        except Exception as e:
            print(f"⚠️  /api/docs: {e}")

    print()
    print("Backend check complete.")


def main():
    base_url = os.environ.get("API_URL", "http://localhost:8000")
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    asyncio.run(check(base_url))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to initialize database tables.
This creates all tables defined in models.py.
"""
import asyncio
import sys
from app.database import init_db

async def main():
    """Initialize database tables."""
    try:
        print("Creating database tables...")
        await init_db()
        print("Database tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)











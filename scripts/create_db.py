#!/usr/bin/env python3
"""
Script to create PostgreSQL database if it doesn't exist.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

def get_database_url():
    """Get DATABASE_URL from environment or config."""
    # Try to get from environment first
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        # Try to load from config
        try:
            from app.config import settings
            db_url = settings.DATABASE_URL
        except ImportError:
            # Default fallback
            db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/tz-hz"
    
    return db_url

def create_database():
    """Create database if it doesn't exist."""
    # Parse DATABASE_URL to extract database name
    db_url = get_database_url()
    
    # Extract database name from URL
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    if 'postgresql+asyncpg://' in db_url:
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    # Split URL to get database name
    parts = db_url.split('/')
    if len(parts) < 2:
        print("Error: Invalid DATABASE_URL format")
        sys.exit(1)
    
    db_name = parts[-1].split('?')[0]  # Remove query parameters if any
    
    # Create connection URL without database name (connect to 'postgres' database)
    admin_url = '/'.join(parts[:-1]) + '/postgres'
    
    print(f"Connecting to PostgreSQL server...")
    print(f"Database name: {db_name}")
    
    try:
        # Connect to PostgreSQL server (using 'postgres' database)
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            exists = result.fetchone() is not None
            
            if exists:
                print(f"Database '{db_name}' already exists.")
            else:
                # Create database
                print(f"Creating database '{db_name}'...")
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"Database '{db_name}' created successfully!")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"Error creating database: {e}")
        print("\nMake sure PostgreSQL is running and credentials are correct.")
        print(f"Connection URL (admin): {admin_url.replace(admin_url.split('@')[0].split('://')[1] if '@' in admin_url else '', '***@')}")
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)


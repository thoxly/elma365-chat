from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database (Supabase)
    # Default: local PostgreSQL. Override with Supabase connection string in .env
    # Example: postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.udcyreqnpyqhibessawi.supabase.co:5432/postgres
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tz-hz"
    
    # Crawler settings
    CRAWL_BASE_URL: str = "https://elma365.com"
    CRAWL_MAX_DEPTH: int = 10
    CRAWL_DELAY: float = 1.0  # seconds between requests
    CRAWL_MAX_CONCURRENT: int = 5
    
    # Output settings
    OUTPUT_DIR: str = "data/crawled"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # LLM settings (DeepSeek V3.2 for agents - reasoning-first model built for agents)
    # DeepSeek-V3.2: Supports "Thinking in Tool-Use" - integrates thinking directly into tool-use
    #   - Supports tool calls in both thinking and non-thinking modes
    #   - Model name: "deepseek-chat" (V3.2) - RECOMMENDED for agents with MCP tools
    #   - API endpoint: https://api.deepseek.com/v1/chat/completions
    #
    # DeepSeek-V3.2-Speciale: Advanced reasoning capabilities, but NO tool calls support
    #   - Model name: "deepseek-chat" (same name, but different endpoint)
    #   - API endpoint: https://api.deepseek.com/v3.2_speciale_expires_on_20251215
    #   - WARNING: Does NOT support function calling - agents with MCP tools will fail!
    #   - Available until Dec 15, 2025, 15:59 UTC
    #   - Use only if you disable MCP tools or use for non-agent tasks
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"  # Standard V3.2 endpoint
    DEEPSEEK_MODEL: str = "deepseek-chat"  # V3.2 - reasoning-first with Thinking in Tool-Use support
    
    # OpenAI settings (for use with agents when selected)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    OPENAI_MODEL: str = "gpt-5.1-2025-11-13"
    
    # Embeddings settings (MUST remain on OpenAI - do not change)
    OPENAI_MODEL_EMBEDDING: str = "text-embedding-3-small"
    OPENAI_API_URL_EMBEDDING: str = "https://api.openai.com/v1/embeddings"
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    
    # MCP settings
    MCP_SERVER_MODE: str = "http"  # stdin or http
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


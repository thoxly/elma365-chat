from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


def _read_env(*keys: str) -> Optional[str]:
    for key in keys:
        v = os.environ.get(key)
        if v:
            return v
    return None


class Settings(BaseSettings):
    # Supabase API (preferred for Cloud Run: no DB password, use URL + anon key)
    # Cloud Run: SUPABASE_URL or VITE_SUPABASE_URL; SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_DEFAULT_KEY
    SUPABASE_URL: Optional[str] = Field(
        default_factory=lambda: os.environ.get("VITE_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    )
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default_factory=lambda: os.environ.get("SUPABASE_PUBLISHABLE_DEFAULT_KEY")
        or os.environ.get("VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )

    # Database direct (optional: for crawler/docs/vector search; omit in Cloud Run when using only Supabase API)
    # Example: postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
    DATABASE_URL: Optional[str] = None
    
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


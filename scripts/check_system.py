#!/usr/bin/env python3
"""
Скрипт для проверки готовности системы к запуску.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database.database import get_session_factory
from mcp.client import MCPClient


async def check_database():
    """Проверка подключения к базе данных."""
    print("🔍 Проверка базы данных...")
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            # Простой запрос для проверки подключения
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ База данных: OK")
        return True
    except Exception as e:
        print(f"❌ База данных: ОШИБКА - {e}")
        return False


async def check_mcp_server():
    """Проверка доступности MCP сервера."""
    print("🔍 Проверка MCP сервера...")
    try:
        mcp_client = MCPClient(transport="http")
        tools = await mcp_client.list_tools()
        if tools:
            print(f"✅ MCP сервер: OK (найдено инструментов: {len(tools)})")
            return True
        else:
            print("⚠️  MCP сервер: доступен, но инструменты не найдены")
            return False
    except Exception as e:
        print(f"❌ MCP сервер: ОШИБКА - {e}")
        print("   Убедитесь, что FastAPI сервер запущен: uvicorn app.main:app --reload")
        return False


def check_config():
    """Проверка конфигурации."""
    print("🔍 Проверка конфигурации...")
    errors = []
    
    # Check DeepSeek API key for agents
    if not settings.DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY не установлен (требуется для агентов)")
    else:
        print("✅ DEEPSEEK_API_KEY: установлен (для агентов)")
    
    # Check OpenAI API key for embeddings
    if not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY не установлен (требуется для embeddings)")
    else:
        print("✅ OPENAI_API_KEY: установлен (для embeddings)")
    
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL не установлен")
    else:
        print(f"✅ DATABASE_URL: установлен ({settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'скрыт'})")
    
    if errors:
        print(f"❌ Ошибки конфигурации:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Конфигурация: OK")
    return True


async def main():
    """Основная функция проверки."""
    print("=" * 50)
    print("Проверка готовности системы к запуску")
    print("=" * 50)
    print()
    
    all_ok = True
    
    # Проверка конфигурации
    if not check_config():
        all_ok = False
    print()
    
    # Проверка базы данных
    if not await check_database():
        all_ok = False
    print()
    
    # Проверка MCP сервера
    if not await check_mcp_server():
        all_ok = False
    print()
    
    print("=" * 50)
    if all_ok:
        print("✅ Система готова к запуску!")
        print()
        print("Следующие шаги:")
        print("1. Запустите FastAPI сервер: uvicorn app.main:app --reload")
    else:
        print("❌ Система не готова. Исправьте ошибки выше.")
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())


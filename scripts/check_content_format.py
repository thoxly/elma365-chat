#!/usr/bin/env python3
"""Проверка формата content в базе данных."""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database.database import get_session_factory
from app.database.models import Doc

async def main():
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Получаем последний документ (самый новый)
        result = await session.execute(select(Doc).order_by(Doc.id.desc()).limit(1))
        doc = result.scalar_one_or_none()
        
        if not doc:
            print("Нет документов в базе")
            return
        
        print(f"Документ: {doc.doc_id}")
        print(f"URL: {doc.url}")
        print("\n=== Содержимое content ===")
        content = doc.content or {}
        
        # Проверяем наличие HTML
        has_html = 'html' in content
        has_blocks = 'blocks' in content
        has_sections = 'sections' in content
        has_metadata = 'metadata' in content
        
        print(f"  Есть HTML: {has_html}")
        print(f"  Есть blocks: {has_blocks}")
        print(f"  Есть sections: {has_sections}")
        print(f"  Есть metadata: {has_metadata}")
        
        if has_html:
            html_len = len(content['html'])
            print(f"  Длина HTML: {html_len} символов")
            print(f"  ❌ ПРОБЛЕМА: HTML не должен сохраняться!")
        else:
            print(f"  ✓ HTML не сохранен (правильно)")
        
        if has_blocks:
            blocks_count = len(content['blocks'])
            print(f"  Количество blocks: {blocks_count}")
        
        if has_metadata:
            metadata = content['metadata']
            print(f"  Metadata keys: {list(metadata.keys())}")
            if 'plain_text' in metadata:
                plain_len = len(metadata['plain_text'])
                print(f"  Длина plain_text в metadata: {plain_len} символов")
        
        print("\n=== Первые 500 символов content (JSON) ===")
        content_json = json.dumps(content, ensure_ascii=False, indent=2)
        print(content_json[:500])
        if len(content_json) > 500:
            print("...")

if __name__ == "__main__":
    asyncio.run(main())


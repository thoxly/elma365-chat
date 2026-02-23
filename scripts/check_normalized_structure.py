#!/usr/bin/env python3
"""Проверка структуры нормализованного документа."""
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
        # Получаем документ platform-distribution
        result = await session.execute(
            select(Doc).where(Doc.doc_id == 'platform-distribution')
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            print("Документ platform-distribution не найден")
            return
        
        print(f"Документ: {doc.doc_id}")
        print(f"Title: {doc.title}")
        print("\n=== Metadata ===")
        content = doc.content or {}
        metadata = content.get('metadata', {})
        print(f"  Headers: {metadata.get('headers', [])}")
        print(f"  Breadcrumbs: {metadata.get('breadcrumbs', [])}")
        print(f"  Plain_text length: {len(metadata.get('plain_text', ''))}")
        
        print("\n=== Sections ===")
        sections = content.get('sections', [])
        print(f"  Количество секций: {len(sections)}")
        
        for i, section in enumerate(sections, 1):
            print(f"\n  Секция {i}:")
            print(f"    Title: '{section.get('title', '')}'")
            print(f"    Type: {section.get('type', '')}")
            items = section.get('items', [])
            print(f"    Items count: {len(items)}")
            
            if section.get('type') == 'comparison':
                print("    Comparison items:")
                for item in items[:2]:  # Показываем первые 2
                    if isinstance(item, dict):
                        name = item.get('name', '')
                        benefits = item.get('benefits', [])
                        print(f"      - {name}: {len(benefits)} benefits")
                        if benefits:
                            print(f"        Пример: {benefits[0][:50]}...")
            elif section.get('type') == 'list':
                print("    List items:")
                for item in items[:3]:  # Показываем первые 3
                    print(f"      - {str(item)[:60]}...")
            elif section.get('type') == 'links':
                print("    Links:")
                for item in items[:3]:
                    if isinstance(item, dict):
                        print(f"      - {item.get('label', '')} -> {item.get('url', '')}")
        
        print("\n=== Plain_text preview (первые 500 символов) ===")
        plain_text = metadata.get('plain_text', '')
        print(plain_text[:500])
        if len(plain_text) > 500:
            print("...")

if __name__ == "__main__":
    asyncio.run(main())




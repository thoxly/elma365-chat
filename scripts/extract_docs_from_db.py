#!/usr/bin/env python3
"""
Скрипт для извлечения всего текста из таблицы docs в БД
и преобразования JSONB блоков в нормальный текст с заголовками.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_session_factory, close_db
from app.database.models import Doc


def block_to_text(block: Dict[str, Any]) -> str:
    """
    Преобразует блок в текстовое представление с сохранением структуры.
    
    Args:
        block: Блок из content.blocks
        
    Returns:
        Текстовое представление блока
    """
    block_type = block.get('type')
    
    if block_type == 'header':
        level = block.get('level', 1)
        text = block.get('text', '')
        # Создаем markdown заголовок
        return f"{'#' * level} {text}\n"
    
    elif block_type == 'paragraph':
        # Проверяем наличие children (для ссылок)
        if 'children' in block:
            text_parts = []
            for child in block['children']:
                if isinstance(child, str):
                    text_parts.append(child)
                elif isinstance(child, dict) and child.get('type') == 'link':
                    link_text = child.get('text', '')
                    # Можно добавить ссылку, но для простоты просто текст
                    text_parts.append(link_text)
            return ' '.join(text_parts) + '\n\n'
        else:
            text = block.get('text', '')
            return f"{text}\n\n"
    
    elif block_type == 'list':
        items = block.get('items', [])
        ordered = block.get('ordered', False)
        result = []
        
        for i, item in enumerate(items, 1):
            if isinstance(item, str):
                item_text = item
            elif isinstance(item, list):
                # Элемент со ссылками
                item_parts = []
                for child in item:
                    if isinstance(child, str):
                        item_parts.append(child)
                    elif isinstance(child, dict) and child.get('type') == 'link':
                        item_parts.append(child.get('text', ''))
                item_text = ' '.join(item_parts)
            else:
                item_text = str(item)
            
            if ordered:
                result.append(f"{i}. {item_text}")
            else:
                result.append(f"- {item_text}")
        
        return '\n'.join(result) + '\n\n'
    
    elif block_type == 'code_block':
        code = block.get('code', '')
        language = block.get('language', '')
        if language:
            return f"```{language}\n{code}\n```\n\n"
        else:
            return f"```\n{code}\n```\n\n"
    
    elif block_type == 'table':
        header = block.get('header', [])
        rows = block.get('rows', [])
        result = []
        
        # Заголовок таблицы
        if header:
            result.append('| ' + ' | '.join(str(cell) for cell in header) + ' |')
            result.append('| ' + ' | '.join(['---'] * len(header)) + ' |')
        
        # Строки
        for row in rows:
            if isinstance(row, list):
                result.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')
            elif isinstance(row, dict):
                result.append('| ' + ' | '.join(str(v) for v in row.values()) + ' |')
        
        return '\n'.join(result) + '\n\n'
    
    elif block_type == 'special_block':
        kind = block.get('kind', '')
        heading = block.get('heading', kind)
        text = block.get('text', '')
        
        if heading:
            return f"**{heading}**\n\n{text}\n\n"
        else:
            return f"{text}\n\n"
    
    elif block_type == 'image':
        alt = block.get('alt', '')
        src = block.get('src', '')
        if alt:
            return f"![{alt}]({src})\n\n"
        else:
            return f"![]({src})\n\n"
    
    else:
        # Неизвестный тип блока - просто возвращаем строковое представление
        return f"{block}\n\n"


def content_to_text(content: Optional[Dict[str, Any]]) -> str:
    """
    Преобразует JSONB content в читаемый текст.
    
    Args:
        content: JSONB объект content из таблицы docs
        
    Returns:
        Текстовое представление документа
    """
    if not content:
        return ""
    
    blocks = content.get('blocks', [])
    if not blocks:
        return ""
    
    result = []
    
    # Добавляем метаданные если есть
    metadata = content.get('metadata', {})
    if metadata:
        title = metadata.get('title')
        if title:
            result.append(f"# {title}\n\n")
    
    # Преобразуем блоки
    for block in blocks:
        text = block_to_text(block)
        result.append(text)
    
    return ''.join(result)


async def extract_all_docs_from_db() -> Dict[str, Any]:
    """
    Извлекает все документы из БД и преобразует их в текст.
    
    Returns:
        Dict с полем context содержащим весь текст
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Получаем все документы через raw SQL для избежания проблем с отсутствующими колонками
        from sqlalchemy import text
        
        # Проверяем какие колонки есть в таблице
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'docs'
        """)
        result = await session.execute(check_query)
        columns = [row[0] for row in result.fetchall()]
        
        # Формируем список полей для SELECT
        select_fields = ['id', 'doc_id', 'url', 'title', 'section', 'content']
        if 'normalized_path' in columns:
            select_fields.append('normalized_path')
        
        fields_str = ', '.join(select_fields)
        query = text(f"SELECT {fields_str} FROM docs ORDER BY id")
        result = await session.execute(query)
        rows = result.fetchall()
        
        # Преобразуем в объекты для удобства
        class DocRow:
            def __init__(self, row_data, field_names):
                for i, field in enumerate(field_names):
                    setattr(self, field, row_data[i] if i < len(row_data) else None)
        
        docs = [DocRow(row, select_fields) for row in rows]
        
        print(f"Найдено документов в БД: {len(docs)}")
        
        combined_text = []
        processed_docs = []
        
        for doc in docs:
            # Преобразуем content в текст
            doc_text = content_to_text(doc.content)
            
            if doc_text:
                # Добавляем заголовок с информацией о документе
                doc_header = f"# Документ: {doc.title or doc.doc_id}\n\n"
                # Проверяем наличие normalized_path (может не быть в старых версиях БД)
                normalized_path = getattr(doc, 'normalized_path', None)
                if normalized_path:
                    doc_header += f"**Путь:** {normalized_path}\n\n"
                if doc.url:
                    doc_header += f"**URL:** {doc.url}\n\n"
                
                combined_text.append(doc_header)
                combined_text.append(doc_text)
                combined_text.append("\n\n---\n\n")
                
                processed_docs.append({
                    'doc_id': doc.doc_id,
                    'title': doc.title,
                    'normalized_path': getattr(doc, 'normalized_path', None),
                    'url': doc.url
                })
                
                print(f"Обработан: {doc.doc_id} - {doc.title or 'без названия'}")
        
        context = ''.join(combined_text)
        
        return {
            "context": context,
            "metadata": {
                "total_docs": len(docs),
                "processed_docs": len(processed_docs),
                "docs": processed_docs
            }
        }


async def main():
    """Основная функция скрипта."""
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    print("Начинаю извлечение документов из базы данных...\n")
    
    try:
        # Извлекаем документы
        result = await extract_all_docs_from_db()
        
        # Создаем выходную папку
        output_dir = base_dir / "context_output"
        output_dir.mkdir(exist_ok=True)
        
        # Сохраняем результат
        output_file = output_dir / "docs_context_from_db.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Готово! Результат сохранен в: {output_file}")
        print(f"   Размер контекста: {len(result['context'])} символов")
        print(f"   Обработано документов: {result['metadata']['processed_docs']}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        raise
    finally:
        # Закрываем соединения с БД
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())


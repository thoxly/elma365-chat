#!/usr/bin/env python3
"""
Скрипт для извлечения всего текста из папок docs и domain
с сохранением структуры заголовков в поле context.
"""

import os
import json
from pathlib import Path
from typing import List, Dict


def read_markdown_file(file_path: Path) -> str:
    """Читает markdown файл и возвращает его содержимое."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_all_docs(base_dir: Path, folders: List[str]) -> Dict[str, str]:
    """
    Извлекает все markdown файлы из указанных папок.
    
    Returns:
        Dict с ключами - относительными путями файлов, значениями - содержимое
    """
    docs = {}
    
    for folder in folders:
        folder_path = base_dir / folder
        if not folder_path.exists():
            print(f"Предупреждение: папка {folder} не найдена")
            continue
            
        # Рекурсивно ищем все .md файлы
        for md_file in folder_path.rglob('*.md'):
            relative_path = str(md_file.relative_to(base_dir))
            content = read_markdown_file(md_file)
            docs[relative_path] = content
            print(f"Обработан файл: {relative_path}")
    
    return docs


def combine_docs_with_structure(docs: Dict[str, str]) -> str:
    """
    Объединяет все документы в один текст с сохранением структуры заголовков.
    
    Формат:
    # Название файла
    Содержимое файла
    
    ---
    
    # Следующий файл
    ...
    """
    combined = []
    
    # Сортируем файлы для детерминированного порядка
    sorted_files = sorted(docs.items())
    
    for file_path, content in sorted_files:
        # Добавляем заголовок с путем к файлу
        combined.append(f"# Файл: {file_path}\n")
        combined.append(content)
        combined.append("\n\n---\n\n")
    
    return "\n".join(combined)


def main():
    """Основная функция скрипта."""
    # Определяем базовую директорию (корень проекта)
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    # Папки для обработки
    folders = ['docs', 'domain']
    
    print(f"Начинаю извлечение документов из папок: {', '.join(folders)}")
    print(f"Базовая директория: {base_dir}\n")
    
    # Извлекаем все документы
    docs = extract_all_docs(base_dir, folders)
    
    if not docs:
        print("Ошибка: не найдено ни одного markdown файла!")
        return
    
    print(f"\nВсего найдено файлов: {len(docs)}")
    
    # Объединяем документы с сохранением структуры
    context = combine_docs_with_structure(docs)
    
    # Создаем выходную структуру
    output_data = {
        "context": context,
        "metadata": {
            "total_files": len(docs),
            "files": list(docs.keys()),
            "folders_processed": folders
        }
    }
    
    # Создаем выходную папку
    output_dir = base_dir / "context_output"
    output_dir.mkdir(exist_ok=True)
    
    # Сохраняем результат
    output_file = output_dir / "docs_context.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Готово! Результат сохранен в: {output_file}")
    print(f"   Размер контекста: {len(context)} символов")
    print(f"   Количество файлов: {len(docs)}")


if __name__ == "__main__":
    main()







# Правила знаний (Knowledge Rules)

## Назначение

Правила ELMA365 (архитектура, процессы, UI, словарь, паттерны) хранятся в БД в таблице **knowledge_rules**. Это позволяет редактировать их через API и веб-интерфейс без изменения кода.

## Типы правил (rule_type)

- `architecture_rules` — архитектурные правила
- `process_rules` — правила процессов
- `ui_rules` — правила UI
- `dictionary` — словарь (YAML)
- `patterns` — инженерные паттерны (YAML)

## Формат content (JSONB)

- Для Markdown: `{"text": "содержимое .md"}`
- Для YAML: `{"yaml": <распарсенный объект>}` или хранение как структурированный JSON

## Миграция из файлов

Исходные файлы лежат в `data/knowledge_rules/`. Однократный перенос в БД:

```bash
python scripts/migrate_rules_to_db.py
```

## API

- Список: `GET /api/knowledge-rules/`
- Одно правило: `GET /api/knowledge-rules/{rule_type}`
- Обновление: `PUT /api/knowledge-rules/{rule_type}` (body: content, updated_by?)

См. [docs/api.md](../docs/api.md).

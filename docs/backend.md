# Backend (FastAPI)

## Структура

- **app/main.py** — точка входа, роутеры, CORS
- **app/config.py** — настройки (Pydantic Settings), переменные из `.env`
- **app/api/** — маршруты: routes (краулер, документы), chat_routes, templates_routes, knowledge_rules_routes
- **app/services/** — бизнес-логика: knowledge_rules_service, chat_service, flexible_agent
- **app/database/** — models.py (SQLAlchemy), database.py (сессии, get_db)
- **app/crawler/**, **app/normalizer/**, **app/embeddings/** — краулер и база знаний
- **mcp/** — MCP-сервер и клиент (client.py, server_http.py, tools/, core/)

## Запуск

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Для Cloud Run порт задаётся переменной `PORT` (по умолчанию 8080).

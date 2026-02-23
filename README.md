# ELMA365 Chat

Гибкая платформа для работы с документацией ELMA365 через чат-интерфейс.

## Возможности

- **Чат** — диалог с ассистентом по документации ELMA365, с опорой на MCP (поиск по базе знаний).
- **Шаблоны заданий** — настраиваемые сценарии (промпт, системный промпт, MCP-инструменты, правила из БД).
- **Правила в БД** — правила ELMA365 хранятся в PostgreSQL и редактируются через API.
- **Краулер и база знаний** — сбор и нормализация документации, embeddings, MCP-инструменты.

## Быстрый старт

1. Клонировать репозиторий и перейти в каталог проекта.
2. Создать виртуальное окружение и установить зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate   # или venv\Scripts\activate на Windows
   pip install -r requirements.txt
   ```
3. Скопировать `.env.example` в `.env` и задать `DATABASE_URL` (например Supabase).
4. Выполнить миграции:
   ```bash
   alembic upgrade head
   ```
5. (Опционально) Перенести правила из файлов в БД:
   ```bash
   python scripts/migrate_rules_to_db.py
   ```
6. Запустить бэкенд:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
7. Запустить фронт (в отдельном терминале):
   ```bash
   cd frontend && npm install && npm run dev
   ```

Подробнее: [QUICK_START.md](QUICK_START.md).

## Развёртывание

- **Фронт:** Vercel — https://elma365-chat.vercel.app/ (Root Directory: `frontend`, переменная `VITE_API_URL`).
- **Бэкенд:** Google Cloud Run (деплой из GitHub, переменные в консоли).
- **БД:** Supabase (PostgreSQL, расширения `vector`, `pg_trgm`).

Подробные шаги и проверка подключений: [DEPLOYMENT.md](DEPLOYMENT.md).

## Документация

- [QUICK_START.md](QUICK_START.md) — установка и первый запуск.
- [DEPLOYMENT.md](DEPLOYMENT.md) — развёртывание (Supabase, Vercel, Cloud Run).
- [docs/](docs/) — техническая документация (API, БД, backend, frontend).
- [domain/](domain/) — доменные правила (MCP, чат, шаблоны, правила знаний).
- [docs/DOCUMENTATION_RULES.md](docs/DOCUMENTATION_RULES.md) — правила ведения документации.

## Структура проекта

```
elma365-chat/
├── app/                 # FastAPI: main, config, api, services, database, crawler, normalizer, embeddings
├── mcp/                 # MCP-сервер и клиент (client.py, server_http.py, tools/, core/)
├── frontend/            # Vite + React (чат, шаблоны, правила)
├── data/knowledge_rules/ # Файлы правил (для миграции в БД)
├── domain/              # Доменная документация
├── docs/                # Техническая документация
├── alembic/             # Миграции БД
├── scripts/             # Скрипты (краулер, миграция правил, проверка подключений)
├── Dockerfile           # Для Cloud Run
├── requirements.txt
└── .env.example
```

## Проверка подключений

- БД: `python scripts/check_db_connection.py`
- Бэкенд: `python scripts/check_backend_connection.py [URL]`
- Всё: `API_URL=... DATABASE_URL=... python scripts/check_all_services.py`

## API

Swagger UI: `http://localhost:8000/docs` (или URL бэкенда в продакшене).

Основные группы: краулер/документы (`/api`), чат (`/api/chat`), шаблоны (`/api/templates`), правила (`/api/knowledge-rules`), MCP (`/mcp`). Подробнее: [docs/api.md](docs/api.md).

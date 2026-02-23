# База данных

## Обзор

Проект использует **PostgreSQL** (рекомендуется **Supabase**). Подключение задаётся переменной `DATABASE_URL` в формате `postgresql+asyncpg://...` для асинхронного доступа через asyncpg.

## Таблицы

- **docs** — документы ELMA365 (краулер), с полем `embedding` (pgvector)
- **doc_chunks** — чанки документов для поиска
- **entities** — сущности из нормализованного контента
- **specifications** — спецификации (опционально)
- **crawler_state** — состояние краулера
- **knowledge_rules** — правила ELMA365 (редактируемые в БД)
- **task_templates** — шаблоны заданий для чата
- **chat_messages** — сообщения чата
- **chat_documents** — загруженные в чат документы

## Миграции (Alembic)

- Команды: `alembic upgrade head`, `alembic revision --autogenerate -m "описание"`
- Файлы миграций: `alembic/versions/`
- Подключение к БД берётся из `app.config.settings.DATABASE_URL`

## Supabase

1. Создать проект на [supabase.com](https://supabase.com).
2. В SQL Editor выполнить: `CREATE EXTENSION IF NOT EXISTS vector;` и `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
3. В Settings → Database скопировать connection string, подставить пароль.
4. В `.env` задать: `DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres`
5. Выполнить миграции: `alembic upgrade head`

Проверка подключения: `python scripts/check_db_connection.py`

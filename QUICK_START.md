# Быстрый старт elma365-chat

## Требования

- Python 3.11+
- Node.js 18+ (для фронта)
- PostgreSQL (рекомендуется Supabase)

## 1. Клонирование и окружение

```bash
git clone https://github.com/thoxly/elma365-chat.git
cd elma365-chat
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. База данных

### Вариант A: Supabase

1. Создайте проект на [supabase.com](https://supabase.com).
2. В SQL Editor выполните:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```
3. В Settings → Database скопируйте connection string и подставьте пароль.

### Вариант B: Локальный PostgreSQL

Установите PostgreSQL, создайте БД и при необходимости установите расширения `vector` и `pg_trgm`.

### Настройка .env

```bash
cp .env.example .env
# Отредактируйте .env:
# DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@host:5432/postgres
# DEEPSEEK_API_KEY=...
# OPENAI_API_KEY=...  (для embeddings краулера)
```

## 3. Миграции

```bash
alembic upgrade head
```

## 4. Миграция правил (опционально)

Перенос правил из `data/knowledge_rules/` в БД:

```bash
python scripts/migrate_rules_to_db.py
```

## 5. Запуск бэкенда

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: http://localhost:8000/health и http://localhost:8000/docs

## 6. Запуск фронта

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173. По умолчанию фронт обращается к бэкенду по адресу `http://localhost:8000` (можно переопределить через `VITE_API_URL` в `.env` в папке frontend).

## 7. Проверка системы

```bash
python scripts/check_system.py
```

Проверяются конфигурация, подключение к БД и доступность MCP.

## Дальше

- Развёртывание: [DEPLOYMENT.md](DEPLOYMENT.md)
- API: [docs/api.md](docs/api.md)
- Правила документации: [docs/DOCUMENTATION_RULES.md](docs/DOCUMENTATION_RULES.md)

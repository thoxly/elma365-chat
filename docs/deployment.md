# Развёртывание

Детальные инструкции см. в [DEPLOYMENT.md](../DEPLOYMENT.md) в корне проекта.

Кратко:
- **БД:** Supabase, connection string в `DATABASE_URL`, миграции Alembic
- **Backend:** Google Cloud Run (Dockerfile в корне), переменные в консоли Cloud Run
- **Frontend:** Vercel, Root Directory = `frontend`, переменная `VITE_API_URL` = URL бэкенда
- **Проверка:** `scripts/check_db_connection.py`, `scripts/check_backend_connection.py`, `scripts/check_all_services.py`

#!/bin/sh
set -e

# При наличии DATABASE_URL выполняем миграции перед стартом приложения.
# На Cloud Run переменные окружения задаются при деплое.
if [ -n "$DATABASE_URL" ]; then
  echo "Running database migrations (DATABASE_URL is set)..."
  alembic upgrade head
  echo "Migrations done."
else
  echo "Skipping migrations (DATABASE_URL not set; using Supabase API only or no DB)."
fi

exec "$@"

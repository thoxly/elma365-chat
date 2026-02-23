# Развёртывание elma365-chat

## Обзор

- **Фронт:** Vercel — https://elma365-chat.vercel.app/
- **Бэкенд:** Google Cloud Run (деплой из GitHub)
- **БД:** Supabase (PostgreSQL)

---

## 1. База данных (Supabase)

### Подключение

Connection string:
```
postgresql://postgres:[YOUR-PASSWORD]@db.udcyreqnpyqhibessawi.supabase.co:5432/postgres
```

Для приложения используйте asyncpg-формат:
```
postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.udcyreqnpyqhibessawi.supabase.co:5432/postgres
```

### Настройка

1. Создайте проект на [supabase.com](https://supabase.com) (или используйте существующий).
2. В **SQL Editor** выполните:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```
3. В **Settings → Database** скопируйте connection string и подставьте пароль.
4. В `.env` (локально) или в переменных окружения бэкенда задайте:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres
   ```

### Миграции

```bash
# Локально (с настроенным DATABASE_URL)
alembic upgrade head
```

### Проверка

```bash
python scripts/check_db_connection.py
```

Если не работает: проверьте пароль, что расширения `vector` и `pg_trgm` включены, и что хост доступен (firewall/whitelist Supabase).

---

## 2. Backend (Google Cloud Run)

### Деплой из репозитория

CI/CD уже настроен: «Continuously deploy from a repository». При пуше в ветку сборка и деплой запускаются автоматически.

### Переменные окружения (Cloud Run)

В консоли Cloud Run → сервис → Edit & deploy new revision → Variables:

**Подключение к данным (один из вариантов):**

- **Вариант A — Supabase API** (рекомендуется: не нужен пароль БД):
  - **VITE_SUPABASE_URL** или **SUPABASE_URL** — URL проекта, например `https://rqcegznybflakuxjqkqu.supabase.co`
  - **SUPABASE_PUBLISHABLE_DEFAULT_KEY** или **SUPABASE_ANON_KEY** — publishable/anon ключ (`sb_publishable_***`)
  - Чат, шаблоны и правила знаний работают через API. Эндпоинты краулера/docs требуют DATABASE_URL (вариант B).

- **Вариант B — прямое подключение к PostgreSQL:**
  - **DATABASE_URL** — connection string в формате `postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres` (пароль с спецсимволами — в URL-кодировке: `@` → `%40`, `#` → `%23`).

**Остальные переменные:**

- **DEEPSEEK_API_KEY** — ключ для LLM
- **OPENAI_API_KEY** — ключ для embeddings (краулер)
- **LOG_LEVEL** — например `INFO`
- **CRAWL_BASE_URL** — например `https://elma365.com`

Остальные опционально по [.env.example](.env.example).

### Dockerfile

В корне репозитория есть `Dockerfile`. Cloud Run использует его для сборки образа (если настроена сборка из репозитория).

### CORS

В [app/main.py](app/main.py) включён CORS с `allow_origins=["*"]`. Для продакшена можно ограничить: `["https://elma365-chat.vercel.app"]`.

### Проверка

```bash
# Подставьте URL вашего сервиса Cloud Run
python scripts/check_backend_connection.py https://your-service.run.app
```

Или откройте в браузере: `https://your-service.run.app/health` и `https://your-service.run.app/docs`.

Если не работает: проверьте логи Cloud Run, переменные окружения (SUPABASE_URL + ключ или DATABASE_URL), что контейнер слушает `PORT` (по умолчанию 8080).

---

## 3. Frontend (Vercel)

### Настройка проекта

1. Импортируйте репозиторий в [vercel.com](https://vercel.com).
2. **Root Directory:** укажите `frontend`.
3. **Build Command:** `npm run build` (по умолчанию для Vite).
4. **Output Directory:** `dist`.
5. **Environment Variables:**
   - **VITE_API_URL** — URL бэкенда на Cloud Run (например `https://elma365-chat-xxx.run.app`).

### vercel.json

В `frontend/vercel.json` заданы `buildCommand`, `outputDirectory` и rewrites для SPA.

### Домен

По умолчанию Vercel даёт домен вида `elma365-chat.vercel.app`. Production URL: https://elma365-chat.vercel.app/

### Проверка

После деплоя откройте https://elma365-chat.vercel.app/ и убедитесь, что запросы к API уходят на правильный бэкенд (DevTools → Network). Если запросы падают — проверьте `VITE_API_URL` и CORS на бэкенде.

---

## 4. Проверка всех сервисов

```bash
export DATABASE_URL="postgresql+asyncpg://..."
export API_URL="https://your-backend.run.app"
export FRONTEND_URL="https://elma365-chat.vercel.app"
python scripts/check_all_services.py
```

---

## Troubleshooting

| Проблема | Что проверить |
|----------|----------------|
| Нет подключения к БД | Пароль в DATABASE_URL, расширения vector/pg_trgm, доступность хоста |
| Бэкенд не стартует на Cloud Run | Логи ревизии, переменные окружения, порт 8080 |
| Фронт не видит API | VITE_API_URL на Vercel, CORS на бэкенде |
| 404 на фронте при прямом переходе по URL | Rewrites в vercel.json (SPA fallback на index.html) |

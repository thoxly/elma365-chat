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

**При деплое на Cloud Run** миграции запускаются автоматически: при старте контейнера, если задана переменная **DATABASE_URL**, выполняется `alembic upgrade head` (см. `docker-entrypoint.sh` и `Dockerfile`). Отдельно ничего запускать не нужно.

Локально (с настроенным DATABASE_URL):

```bash
alembic upgrade head
```

**Таблица сессий чата (`chat_sessions`):** если используете только Supabase API (без миграций), создайте таблицу в SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
  id SERIAL PRIMARY KEY,
  session_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT 'Новый чат',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_chat_sessions_session_id ON chat_sessions(session_id);
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
  - **VITE_SUPABASE_URL** или **SUPABASE_URL** — URL проекта, например `https://xxx.supabase.co`
  - **VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY** или **SUPABASE_PUBLISHABLE_DEFAULT_KEY** — Publishable Key из дашборда Supabase (не Anon Key (Legacy))
  - Чат, шаблоны и правила знаний работают через API. Эндпоинты краулера/docs требуют DATABASE_URL (вариант B).

- **Вариант B — прямое подключение к PostgreSQL:**
  - **DATABASE_URL** — connection string в формате `postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres` (пароль с спецсимволами — в URL-кодировке: `@` → `%40`, `#` → `%23`). При наличии DATABASE_URL при каждом деплое перед стартом приложения автоматически выполняются миграции (`alembic upgrade head`).

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

### 500 Internal Server Error на /api/chat и /api/templates

Если все запросы к `/api/chat/sessions`, `/api/chat/sessions/.../history`, `/api/chat/messages`, `/api/templates/` и т.п. возвращают **500**, ошибка возникает уже внутри обработчика (маршрут найден, зависимость `get_db_or_supabase` отработала). Чтобы увидеть **реальную причину**:

1. **Включите подробные логи:** в Cloud Run → сервис → Edit & deploy new revision → Variables добавьте/измените:
   - **LOG_LEVEL=DEBUG**
2. **Откройте логи ревизии** (Logs), воспроизведите 500 (например, откройте чат или список шаблонов).
3. **Найдите строку с ошибкой:** ищите по тексту:
   - `Error listing sessions:`, `Error getting history:`, `Supabase API error:` — сразу после неё будет **тип исключения** и **сообщение** (например `RuntimeError: Supabase API error: ...` или от Supabase/сети).
   - Полный traceback пишется при `exc_info=True`; если лог обрезан, первая строка с типом и текстом исключения уже даёт причину.

**Типичные причины 500 при использовании Supabase API:**

| Причина | Что сделать |
|--------|--------------|
| Неверный ключ (401/403 от Supabase) | В Cloud Run должен быть **Publishable Key** из дашборда Supabase (Settings → API). Не используйте «Anon Key (Legacy)». Переменные: `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY` или `SUPABASE_PUBLISHABLE_DEFAULT_KEY`. |
| SUPABASE_URL или ключ не заданы | Задайте оба: `VITE_SUPABASE_URL` (или `SUPABASE_URL`) и один из ключей выше. Иначе приложение попытается использовать DATABASE_URL; если и его нет — будет 503, не 500. |
| RLS (Row Level Security) блокирует запросы | В Supabase (Table Editor → таблица → RLS) проверьте политики для таблиц `chat_sessions`, `chat_messages`, `task_templates`. Для сервисного ключа/anon может понадобиться политика SELECT/INSERT/UPDATE для нужных ролей. |
| Таблицы отсутствуют | Если проект новый, создайте таблицы в SQL Editor (см. раздел «База данных» выше и миграции). При использовании только Supabase API миграции не создают таблицы автоматически — их нужно создать вручную или через миграции с DATABASE_URL. |

**Чек-лист переменных окружения (Cloud Run) при 500:**

- `VITE_SUPABASE_URL` или `SUPABASE_URL` — URL вида `https://xxxx.supabase.co`
- `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY` или `SUPABASE_PUBLISHABLE_DEFAULT_KEY` — именно Publishable Key (не Anon Legacy)
- Либо вместо Supabase API: `DATABASE_URL=postgresql+asyncpg://...` (тогда чат/шаблоны работают через прямое подключение к БД)

---

| Проблема | Что проверить |
|----------|----------------|
| Нет подключения к БД | Пароль в DATABASE_URL, расширения vector/pg_trgm, доступность хоста |
| Бэкенд не стартует на Cloud Run | Логи ревизии, переменные окружения, порт 8080 |
| Фронт не видит API | VITE_API_URL на Vercel, CORS на бэкенде |
| 404 на фронте при прямом переходе по URL | Rewrites в vercel.json (SPA fallback на index.html) |
| 500 на /api/chat/sessions/... /history | См. раздел выше «500 Internal Server Error на /api/chat и /api/templates»; проверить Publishable Key и RLS. |
| Отладка чата/БД | В Cloud Run задать **LOG_LEVEL=DEBUG** — в логах: выбор хранилища (Supabase API / direct DB), вызовы get_history/list_sessions, сообщение «Supabase API error:» при сбое запроса к API |

# План переделки elma365-chat: веб-интерфейс, Vercel, очистка

**Репозиторий:** https://github.com/thoxly/elma365-chat  
**Локальный путь:** `/Users/shoxy/Projects-web/elma365-chat`

---

## Часть 1. Очистка проекта (удалить лишнее)

### 1.1 Сохранить правила и MCP-клиент

- Создать `data/knowledge_rules/` и скопировать туда файлы правил (без `_OLD`):
  - `ARCHITECTURE_RULES_ELMA365.md`
  - `PROCESS_RULES_ELMA365.md`
  - `UI_RULES_ELMA365.md`
  - `elma365_arch_dictionary.yml`
  - `ENGINEERING_PATTERNS_ELMA365.yml`
- Перенести `agents/mcp_client.py` → `mcp/client.py`.

### 1.2 Удалить директории

| Удалить | Причина |
|--------|---------|
| `pipeline/` | Жёсткий пайплайн, не нужен в чат-версии |
| `agents/` | Все агенты и схемы пайплайна (правила уже в `data/knowledge_rules`) |
| `telegram/` | Старый Telegram-бот |
| `frontend/` | Старый фронтенд (пайплайн-интерфейс) |

### 1.3 Удалить файлы

| Файл | Причина |
|------|---------|
| `app/api/pipeline_routes.py` | API пайплайна |
| `app/services/pipeline_service.py` | Сервис пайплайна |
| `app/database/models.py` | Удалить только класс `Run` (таблица `runs`) |

### 1.4 Удалить/обновить скрипты (опционально)

- Удалить: `scripts/full_pipeline.py`, `scripts/test_pipeline_5_pages.py` (пайплайн).
- Удалить или переписать: `scripts/check_system.py` (использует `agents.mcp_client` → после переноса можно вызывать `mcp.client`).

### 1.5 Документация и мусор

- Удалить: `docs/TELEGRAM_BOT_USER_FLOW.md` (про бота).
- Удалить дубликаты: `README_NEW.md`, `REFACTORING.md` — либо влить полезное в README и удалить.
- Папка `elma_th-hz-ishod` (если есть в корне) — удалить, если это копия/архив.
- Логи: `logs/*.log` — уже в `.gitignore`, при необходимости почистить локально.

### 1.6 Итоговая структура после очистки

```
elma365-chat/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── utils.py
│   ├── schemas.py
│   ├── api/
│   │   └── routes.py          # краулер, документы, нормализация
│   ├── crawler/
│   ├── normalizer/
│   ├── embeddings/
│   ├── database/
│   └── services/              # без pipeline_service
├── mcp/
│   ├── client.py             # перенесён из agents
│   ├── core/
│   ├── tools/
│   ├── server_http.py
│   └── server_stdin.py
├── data/
│   └── knowledge_rules/      # правила для миграции в БД
├── domain/
├── docs/                     # без TELEGRAM_BOT_USER_FLOW
├── alembic/
├── scripts/                  # только краулер/нормализация/БД
├── .env.example
├── requirements.txt
├── HANDOFF.md
├── QUICK_START.md
├── PLAN.md                   # этот файл
└── README.md
```

---

## Часть 2. Переделка на веб-интерфейс

### 2.1 Целевая функциональность

1. **Чат с документацией ELMA365**
   - Сообщения пользователь/ассистент.
   - Контекст: загруженные документы + MCP (поиск по базе знаний).
   - Гибкий агент по шаблону (без жёсткого пайплайна).

2. **Шаблоны заданий (Task Templates)**
   - CRUD через API и веб-интерфейс.
   - Шаблон: имя, промпт, системный промпт, список MCP-инструментов, список правил из БД.

3. **Правила ELMA365**
   - Хранение в БД (таблица `knowledge_rules`).
   - Редактирование через веб (админка или отдельная страница).

4. **База знаний (оставить как есть)**
   - Краулер, нормализатор, embeddings, MCP-инструменты.

### 2.2 Backend (FastAPI)

- Добавить модели: `KnowledgeRule`, `TaskTemplate`, `ChatMessage`, `ChatDocument` (см. HANDOFF.md).
- Добавить сервисы: `KnowledgeRulesService`, `ChatService`.
- Добавить агента: `FlexibleAgent` (шаблон + MCP + правила из БД).
- Добавить API:
  - `app/api/chat_routes.py` — чат (отправка сообщений, загрузка документов, история).
  - `app/api/templates_routes.py` — CRUD шаблонов.
  - `app/api/knowledge_rules_routes.py` — чтение/обновление правил.
- Миграции Alembic для новых таблиц.
- Скрипт миграции правил из `data/knowledge_rules/` в БД.

### 2.3 Frontend (новый)

- Отдельное приложение в `frontend/` (Vite + React или Next.js).
- Страницы:
  - Чат (основная).
  - Шаблоны заданий (список, создание, редактирование).
  - Правила (список, редактирование текста/YAML).
- Запросы к API бэкенда (CORS настроен в FastAPI).

---

## Часть 3. Развёртывание на Vercel

### 3.1 Вариант A (рекомендуемый): Frontend на Vercel, Backend отдельно

- **Vercel:** только фронтенд из `frontend/`.
  - В настройках проекта указать Root Directory: `frontend`.
  - Build Command / Output — по выбранному фреймворку (Vite/Next).
  - Environment variables: `VITE_API_URL` (или `NEXT_PUBLIC_API_URL`) = URL бэкенда.
- **Backend:** развернуть на **Railway**, **Render** или **Fly.io**.
  - Там запускать `uvicorn app.main:app --host 0.0.0.0`.
  - Переменные: `DATABASE_URL` (Supabase), ключи API (DeepSeek, OpenAI и т.д.).
- В репозитории можно монорепо: корень — бэкенд, `frontend/` — отдельное приложение для Vercel.

### 3.2 Вариант B: Всё на Vercel

- Frontend — как в варианте A.
- Backend — через Vercel Serverless Functions (Python): обёртка над FastAPI возможна, но ограничения по времени выполнения и холодный старт. Для MCP, краулера и долгих задач не идеально.
- Имеет смысл только если бэкенд остаётся минимальным (прокси к внешним API и БД без тяжёлой логики).

### 3.3 Рекомендация

- **Frontend:** Vercel (из папки `frontend/`).
- **Backend:** Railway или Render, БД — Supabase (уже в плане).
- В README указать два деплоя и ссылки (например, `https://elma365-chat.vercel.app` и `https://elma365-chat-api.railway.app`).

### 3.4 Подготовка репозитория к Vercel

- В корне или в `frontend/` добавить конфиг под выбранный фреймворк (например `vercel.json` в `frontend/` при Root Directory = `frontend`).
- В `.env.example` и в документации описать:
  - для фронта: `VITE_API_URL` / `NEXT_PUBLIC_API_URL`;
  - для бэка: `DATABASE_URL`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY` и т.д.

---

## Часть 4. Порядок работ

1. **Очистка (сейчас)**  
   Выполнить пункты 1.1–1.5, обновить README и .gitignore.

2. **Бэкенд: модели и миграции**  
   Добавить таблицы для правил, шаблонов, чата; применить миграции к Supabase.

3. **Бэкенд: сервисы и API**  
   KnowledgeRulesService, ChatService, FlexibleAgent; chat_routes, templates_routes, knowledge_rules_routes.

4. **Миграция правил**  
   Скрипт переноса из `data/knowledge_rules/` в БД.

5. **Фронтенд**  
   Инициализация приложения в `frontend/`, чат, шаблоны, правила.

6. **Деплой**  
   Frontend → Vercel, Backend → Railway/Render, описание в README.

---

## Чеклист очистки (выполнить первым)

- [ ] Создать `data/knowledge_rules/`, скопировать 5 файлов правил (без _OLD).
- [ ] Перенести `agents/mcp_client.py` в `mcp/client.py`.
- [ ] Удалить `pipeline/`, `telegram/`, `frontend/`, `agents/`.
- [ ] Удалить `app/api/pipeline_routes.py`, `app/services/pipeline_service.py`.
- [ ] Удалить класс `Run` из `app/database/models.py`.
- [ ] Удалить `scripts/full_pipeline.py`, `scripts/test_pipeline_5_pages.py`.
- [ ] Удалить `docs/TELEGRAM_BOT_USER_FLOW.md`.
- [ ] При необходимости удалить `README_NEW.md`, `REFACTORING.md`, папку `elma_th-hz-ishod`.
- [ ] Обновить README под новый проект и деплой (Vercel + backend).
- [ ] Добавить в `.gitignore` при необходимости: `frontend/node_modules`, `data/*.db` и т.д.

После этого репозиторий готов к поэтапной переделке на веб и развёртыванию на Vercel (фронт) + выбранном хостинге для API.

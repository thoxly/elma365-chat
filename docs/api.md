# API

## Базовый URL

- Локально: `http://localhost:8000`
- В продакшене: URL бэкенда на Cloud Run

Полная документация (Swagger): `{BASE_URL}/docs`

## Основные группы

### Краулер и документы (`/api`)

- Запуск краулера, статус, список документов, нормализация — см. [app/api/routes.py](../app/api/routes.py)

### Чат (`/api/chat`)

- `POST /api/chat/messages` — отправить сообщение, получить ответ (body: user_id, session_id, message, template_id?)
- `GET /api/chat/sessions/{session_id}/history?user_id=` — история чата
- `POST /api/chat/documents` — загрузить документ (form: user_id, session_id, file)

### Шаблоны заданий (`/api/templates`)

- `GET /api/templates/` — список шаблонов
- `GET /api/templates/{id}` — один шаблон
- `POST /api/templates/` — создать (body: name, description, prompt, system_prompt, tools?, knowledge_rules?)
- `PUT /api/templates/{id}` — обновить
- `DELETE /api/templates/{id}` — удалить

### Правила (`/api/knowledge-rules`)

- `GET /api/knowledge-rules/` — все правила
- `GET /api/knowledge-rules/{rule_type}` — одно правило
- `PUT /api/knowledge-rules/{rule_type}` — обновить (body: content, updated_by?)

### MCP

- `GET /mcp/tools/list` — список MCP-инструментов
- `POST /mcp/tools/call` — вызов инструмента

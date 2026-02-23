# Передача дел: elma365-chat

## Контекст проекта

### Что было сделано

1. **Создана копия проекта** из `elma_tz_hz` в `elma365-chat`
   - Скопированы все файлы (кроме .git, venv, кэша)
   - Инициализирован новый git репозиторий
   - Проект находится в `/Users/shoxy/elma_tz_hz/elma365-chat/`

2. **Причина создания нового проекта:**
   - Старый проект (`elma_tz_hz`) имеет жесткую логику пайплайна (ValidatorAgent → ProcessExtractor → ArchitectAgent → CriticAgent → ScopeAgent)
   - Нужна гибкая система, где можно:
     - Просто работать с документацией ELMA365 через чат
     - Валидировать процессы по запросу
     - Помогать с архитектурой на основе произвольных вводных
     - Создавать шаблоны заданий через интерфейс (не через код)
     - Редактировать правила ELMA365 через интерфейс

## Требования к новому проекту

### Основные функции

1. **Чат-интерфейс**
   - Простой чат для работы с документацией ELMA365
   - Возможность загрузки документов в контекст чата
   - Использование MCP для доступа к документации

2. **Шаблоны заданий (Task Templates)**
   - Создание шаблонов через интерфейс (не через код)
   - Шаблон = промпт + системный промпт + какие MCP инструменты использовать + какие правила применять
   - Пример: ValidatorAgent можно превратить в шаблон "Валидация процесса"
   - При выполнении задания можно выбрать шаблон и применить к тексту

3. **Редактируемые правила ELMA365**
   - Правила должны храниться в БД (не в файлах)
   - Редактирование через интерфейс
   - Правила:
     - `ARCHITECTURE_RULES_ELMA365.md`
     - `PROCESS_RULES_ELMA365.md`
     - `UI_RULES_ELMA365.md`
     - `elma365_arch_dictionary.yml`
     - `ENGINEERING_PATTERNS_ELMA365.yml`

4. **Гибкий агент**
   - Работает по шаблону задания
   - Использует MCP для доступа к документации
   - Загружает правила из БД
   - Не имеет жесткой логики пайплайна

## Что оставить из старого проекта

### ✅ Оставить (нужно для нового проекта)

1. **MCP сервер и клиент**
   - `mcp/` - полностью (core, tools, server_http.py, server_stdin.py)
   - `agents/mcp_client.py` - переместить в `mcp/client.py` для удобства

2. **База знаний**
   - `app/crawler/` - краулер документации
   - `app/normalizer/` - нормализатор HTML
   - `app/embeddings/` - embeddings для поиска
   - `app/database/` - модели БД (Doc, DocChunk, Entity)
   - `app/api/routes.py` - API endpoints для краулера и документов
   - `app/main.py` - FastAPI приложение

3. **Конфигурация**
   - `app/config.py`
   - `app/utils.py`
   - `.env.example` - шаблон переменных окружения

4. **Правила ELMA365 (файлы - для миграции в БД)**
   - `agents/ARCHITECTURE_RULES_ELMA365.md`
   - `agents/PROCESS_RULES_ELMA365.md`
   - `agents/UI_RULES_ELMA365.md`
   - `agents/elma365_arch_dictionary.yml`
   - `agents/ENGINEERING_PATTERNS_ELMA365.yml`

5. **Скрипты для базы знаний**
   - `scripts/start_crawl.py`
   - `scripts/renormalize_all.py`
   - Другие скрипты для работы с документацией

6. **Документация**
   - `domain/` - документация по MCP, архитектуре
   - `docs/` - техническая документация

### ❌ Удалить (не нужно для нового проекта)

1. **Жесткий пайплайн**
   - `agents/` - удалить все агенты (кроме mcp_client.py, который нужно переместить)
   - `pipeline/` - удалить полностью
   - `app/api/pipeline_routes.py` - удалить
   - `app/services/pipeline_service.py` - удалить

2. **Старые интерфейсы**
   - `telegram/` - старый Telegram бот (удалить)
   - `frontend/` - старый фронтенд (удалить)

3. **Специфичные модели БД (опционально)**
   - `app/database/models.py` - удалить модель `Run` (она для пайплайна)
   - Можно оставить `CrawlerState` если нужен

4. **Валидаторы пайплайна**
   - `pipeline/validators.py` - удалить (специфично для пайплайна)

5. **Схемы данных агентов**
   - `agents/models/schemas.py` - удалить (специфично для пайплайна)

## Что нужно добавить

### 1. Модели БД для правил и шаблонов

**Файл:** `app/database/models.py` (добавить к существующим моделям)

```python
class KnowledgeRule(Base):
    """Хранение правил ELMA365 в БД"""
    __tablename__ = "knowledge_rules"
    
    id = Column(Integer, primary_key=True)
    rule_type = Column(String, unique=True, index=True)  # architecture_rules, process_rules, ui_rules, dictionary, patterns
    content = Column(JSONB)  # Для YAML - dict, для MD - {"text": "..."}
    version = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String, nullable=True)  # Кто обновил (user_id или "system")


class TaskTemplate(Base):
    """Шаблоны заданий"""
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # "Валидация процесса"
    description = Column(Text)  # Описание шаблона
    prompt = Column(Text, nullable=False)  # Промпт для LLM
    system_prompt = Column(Text)  # Системный промпт
    tools = Column(JSONB)  # Список MCP инструментов ["elma365.search_docs", ...]
    knowledge_rules = Column(JSONB)  # Какие правила применять ["architecture_rules", "process_rules"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)


class ChatMessage(Base):
    """Сообщения в чате"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)  # Сессия чата
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=True)  # Если использован шаблон
    attachments = Column(JSONB)  # Загруженные документы
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatDocument(Base):
    """Документы, загруженные в чат"""
    __tablename__ = "chat_documents"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content = Column(Text)  # Текст документа
    file_type = Column(String)  # txt, pdf, docx, etc.
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2. Сервис для работы с правилами

**Файл:** `app/services/knowledge_rules_service.py`

```python
class KnowledgeRulesService:
    """Сервис для работы с правилами ELMA365"""
    
    async def get_rule(self, rule_type: str) -> dict:
        """Получить правило по типу"""
        
    async def update_rule(self, rule_type: str, content: dict, updated_by: str):
        """Обновить правило"""
        
    async def get_all_rules(self) -> dict:
        """Получить все правила"""
        
    async def migrate_from_files(self):
        """Мигрировать правила из файлов в БД (одноразовая операция)"""
```

### 3. Гибкий агент

**Файл:** `chat/agents/flexible_agent.py`

```python
class FlexibleAgent:
    """Гибкий агент, работающий по шаблону"""
    
    def __init__(self, template: TaskTemplate, mcp_client: MCPClient, rules_service: KnowledgeRulesService):
        self.template = template
        self.mcp_client = mcp_client
        self.rules_service = rules_service
    
    async def execute(self, user_input: str, context: dict = None):
        """Выполнить задание по шаблону"""
        # 1. Загрузить правила из БД
        # 2. Построить промпт из шаблона + правила + контекст
        # 3. Выполнить через LLM с доступом к MCP инструментам
        # 4. Вернуть результат
```

### 4. Сервис чата

**Файл:** `chat/chat_service.py`

```python
class ChatService:
    """Сервис для работы с чатом"""
    
    async def send_message(self, user_id: str, session_id: str, message: str, template_id: int = None):
        """Отправить сообщение в чат"""
        
    async def upload_document(self, user_id: str, session_id: str, file: bytes, filename: str):
        """Загрузить документ в контекст чата"""
        
    async def get_history(self, user_id: str, session_id: str):
        """Получить историю чата"""
```

### 5. API endpoints

**Файл:** `app/api/chat_routes.py`

```python
router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/messages")
async def send_message(...):
    """Отправить сообщение в чат"""
    
@router.post("/documents")
async def upload_document(...):
    """Загрузить документ"""
    
@router.get("/sessions/{session_id}/history")
async def get_history(...):
    """Получить историю чата"""
```

**Файл:** `app/api/templates_routes.py`

```python
router = APIRouter(prefix="/templates", tags=["templates"])

@router.post("/")
async def create_template(...):
    """Создать шаблон задания"""
    
@router.put("/{template_id}")
async def update_template(...):
    """Обновить шаблон"""
    
@router.get("/")
async def list_templates(...):
    """Список шаблонов"""
    
@router.delete("/{template_id}")
async def delete_template(...):
    """Удалить шаблон"""
```

**Файл:** `app/api/knowledge_rules_routes.py`

```python
router = APIRouter(prefix="/knowledge-rules", tags=["knowledge-rules"])

@router.get("/{rule_type}")
async def get_rule(rule_type: str):
    """Получить правило"""
    
@router.put("/{rule_type}")
async def update_rule(rule_type: str, content: dict):
    """Обновить правило"""
    
@router.get("/")
async def list_rules():
    """Список всех правил"""
```

### 6. Миграция Alembic

**Файл:** `alembic/versions/add_knowledge_rules_and_templates.py`

```python
def upgrade():
    # Создать таблицы knowledge_rules, task_templates, chat_messages, chat_documents
```

### 7. Скрипт миграции правил из файлов

**Файл:** `scripts/migrate_rules_to_db.py`

```python
async def migrate_rules():
    """Перенести правила из файлов в БД"""
    # Читать файлы из agents/
    # Сохранять в БД через KnowledgeRulesService
```

### 8. Новый фронтенд (чат)

**Структура:** `frontend/` (новый)
- Чат-интерфейс
- Управление шаблонами
- Редактирование правил
- Загрузка документов

## План работы

### Этап 1: Очистка проекта
1. ✅ Удалить `agents/` (кроме mcp_client.py)
2. ✅ Переместить `agents/mcp_client.py` → `mcp/client.py`
3. ✅ Удалить `pipeline/`
4. ✅ Удалить `telegram/`
5. ✅ Удалить старый `frontend/`
6. ✅ Удалить `app/api/pipeline_routes.py`
7. ✅ Удалить `app/services/pipeline_service.py`
8. ✅ Очистить `app/database/models.py` от модели `Run`

### Этап 2: Настройка Supabase
1. Создать проект на https://supabase.com
2. Включить расширение pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Получить connection string и настроить `DATABASE_URL` в `.env`
4. Проверить подключение к БД

### Этап 3: Добавление моделей БД
1. Добавить модели `KnowledgeRule`, `TaskTemplate`, `ChatMessage`, `ChatDocument`
2. Создать миграцию Alembic
3. Применить миграцию к Supabase БД

### Этап 4: Сервисы
1. Создать `KnowledgeRulesService`
2. Создать `FlexibleAgent`
3. Создать `ChatService`

### Этап 5: API
1. Создать `chat_routes.py`
2. Создать `templates_routes.py`
3. Создать `knowledge_rules_routes.py`
4. Подключить роутеры в `app/main.py`

### Этап 6: Миграция правил
1. Создать скрипт `migrate_rules_to_db.py`
2. Запустить миграцию правил из файлов в БД

### Этап 7: Фронтенд
1. Создать новый чат-интерфейс
2. Добавить управление шаблонами
3. Добавить редактирование правил

## Технические детали

### Зависимости (оставить из requirements.txt)
- FastAPI, uvicorn
- SQLAlchemy, asyncpg, alembic
- aiohttp, beautifulsoup4
- python-telegram-bot (если нужен новый бот)
- pydantic
- pgvector (для embeddings) - **включено в Supabase автоматически**

### Настройка Supabase

1. **Создать проект на https://supabase.com**
2. **Включить расширение pgvector:**
   - Открыть SQL Editor в Supabase Dashboard
   - Выполнить: `CREATE EXTENSION IF NOT EXISTS vector;`
3. **Получить connection string:**
   - Settings → Database → Connection string
   - Формат: `postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
   - Или использовать connection pooling string для лучшей производительности

### Переменные окружения (.env)
- `DATABASE_URL` - Supabase PostgreSQL connection string (формат: `postgresql+asyncpg://postgres:[password]@[host]:5432/postgres`)
- `SUPABASE_URL` - URL проекта Supabase (опционально, для прямого API доступа)
- `SUPABASE_KEY` - API ключ Supabase (опционально)
- `DEEPSEEK_API_KEY` - для LLM агентов
- `OPENAI_API_KEY` - для embeddings
- Остальные из `.env.example`

### База данных (Supabase)
- **Использовать Supabase PostgreSQL** - облачная база данных с расширением pgvector
- Таблицы: `docs`, `doc_chunks`, `entities` (существующие)
- Новые таблицы: `knowledge_rules`, `task_templates`, `chat_messages`, `chat_documents`
- **Важно:** Supabase автоматически поддерживает pgvector для векторного поиска
- Подключение через стандартный PostgreSQL connection string (asyncpg драйвер)

## Важные моменты

1. **MCP клиент** - переместить из `agents/mcp_client.py` в `mcp/client.py` для удобства
2. **База данных** - использовать **Supabase** (PostgreSQL с pgvector), не локальный PostgreSQL
3. **Правила** - сначала хранить в файлах, потом мигрировать в Supabase БД
4. **Шаблоны** - создавать через API/интерфейс, не через код
5. **Гибкость** - агент должен работать по любому шаблону, не иметь жесткой логики
6. **Документация** - сохранить доступ к документации через MCP
7. **pgvector** - расширение уже включено в Supabase, не нужно устанавливать отдельно

## Контакты и контекст

- Исходный проект: `/Users/shoxy/elma_tz_hz/`
- Новый проект: `/Users/shoxy/elma_tz_hz/elma365-chat/`
- Git репозиторий: инициализирован, готов к работе

## Следующие шаги

1. Начать с Этапа 1 (очистка проекта)
2. Проверить, что MCP и база знаний работают
3. Добавить модели БД
4. Реализовать сервисы и API
5. Создать фронтенд

---

**Дата создания:** 2026-02-22
**Статус:** Готов к работе

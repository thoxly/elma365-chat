# Схемы входов/выходов агентов

Этот документ содержит JSON схемы для входных и выходных данных всех агентов. Эти схемы используются для валидации ответов, написания тестов и гарантии стабильности системы.

## AS-IS (ProcessExtractor Output)

**Агент:** ProcessExtractor  
**Вход:** Текст транскрипции (строка)  
**Выход:** AS-IS JSON

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["process_name", "description", "steps"],
  "properties": {
    "process_name": {
      "type": "string",
      "description": "Название процесса"
    },
    "description": {
      "type": "string",
      "description": "Описание процесса"
    },
    "actors": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Список ролей/участников процесса",
      "default": []
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step_number", "action"],
        "properties": {
          "step_number": {
            "type": "integer",
            "description": "Номер шага (начиная с 1)"
          },
          "actor": {
            "type": "string",
            "description": "Роль, выполняющая шаг"
          },
          "action": {
            "type": "string",
            "description": "Действие, выполняемое на шаге"
          },
          "output": {
            "type": "string",
            "description": "Результат шага (может быть 'неизвестно')"
          }
        }
      },
      "description": "Список шагов процесса"
    },
    "triggers": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Триггеры, запускающие процесс",
      "default": []
    },
    "outcomes": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Результаты процесса",
      "default": []
    }
  }
}
```

### Пример валидного AS-IS

```json
{
  "process_name": "Согласование документов",
  "description": "Процесс согласования документов через email с участием нескольких ролей",
  "actors": ["Инициатор", "Согласующий", "Утверждающий"],
  "steps": [
    {
      "step_number": 1,
      "actor": "Инициатор",
      "action": "Отправляет документ на согласование",
      "output": "Email с документом"
    },
    {
      "step_number": 2,
      "actor": "Согласующий",
      "action": "Проверяет документ",
      "output": "Решение (согласовано/отклонено)"
    },
    {
      "step_number": 3,
      "actor": "Утверждающий",
      "action": "Утверждает документ",
      "output": "Утвержденный документ"
    }
  ],
  "triggers": ["Создание нового документа"],
  "outcomes": ["Согласованный документ"]
}
```

### Пример с "неизвестно"

```json
{
  "process_name": "Согласование документов",
  "description": "Процесс согласования документов",
  "actors": ["Инициатор", "неизвестно"],
  "steps": [
    {
      "step_number": 1,
      "actor": "Инициатор",
      "action": "Отправляет документ",
      "output": "неизвестно"
    }
  ],
  "triggers": ["неизвестно"],
  "outcomes": ["Согласованный документ"]
}
```

### Валидация

Валидация выполняется в `pipeline/validators.py`:

- Проверка наличия обязательных полей: `process_name`, `description`, `steps`
- Проверка структуры `steps`: каждый шаг должен иметь `step_number` и `action`
- Проверка типов данных

## Архитектура (ArchitectAgent Output)

**Агент:** ArchitectAgent  
**Вход:** AS-IS JSON  
**Выход:** Архитектура JSON

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["process_name", "elma365_components"],
  "properties": {
    "process_name": {
      "type": "string",
      "description": "Название процесса"
    },
    "elma365_components": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "name", "description", "justification"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["workflow", "app", "page", "widget", "module", "microservice", "integration"],
            "description": "Тип компонента ELMA365"
          },
          "name": {
            "type": "string",
            "description": "Название компонента"
          },
          "description": {
            "type": "string",
            "description": "Описание компонента"
          },
          "justification": {
            "type": "string",
            "description": "Обоснование выбора компонента (обязательно должно ссылаться на документацию)"
          },
          "configuration": {
            "type": "object",
            "description": "Конфигурация компонента (опционально)",
            "default": {}
          }
        }
      },
      "description": "Список компонентов ELMA365"
    },
    "data_model": {
      "type": "object",
      "properties": {
        "entities": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "type": {"type": "string"},
              "attributes": {
                "type": "array",
                "items": {"type": "string"}
              }
            }
          },
          "default": []
        },
        "attributes": {
          "type": "array",
          "items": {"type": "string"},
          "default": []
        }
      },
      "default": {}
    },
    "integrations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "type": {"type": "string"},
          "description": {"type": "string"}
        }
      },
      "default": []
    },
    "automation_rules": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "description": {"type": "string"},
          "trigger": {"type": "string"},
          "action": {"type": "string"}
        }
      },
      "default": []
    }
  }
}
```

### Пример валидной архитектуры

```json
{
  "process_name": "Согласование документов",
  "elma365_components": [
    {
      "type": "workflow",
      "name": "Процесс согласования документов",
      "description": "Бизнес-процесс для согласования документов с участием нескольких ролей",
      "justification": "Ссылка на статью: /help/platform/workflow.html. Паттерн 'согласование' найден через MCP. Процесс требует участия нескольких ролей и условий.",
      "configuration": {}
    }
  ],
  "data_model": {
    "entities": [
      {
        "name": "Документ",
        "type": "entity",
        "attributes": ["Название", "Дата создания", "Статус"]
      }
    ],
    "attributes": []
  },
  "integrations": [],
  "automation_rules": [
    {
      "name": "Отправка уведомлений",
      "description": "Автоматическая отправка уведомлений участникам процесса",
      "trigger": "Изменение статуса документа",
      "action": "Отправить уведомление"
    }
  ]
}
```

### Валидация

Валидация выполняется в `pipeline/validators.py`:

- Проверка наличия обязательных полей: `process_name`, `elma365_components`
- Проверка структуры `elma365_components`: каждый компонент должен иметь `type`, `name`, `description`, `justification`
- Проверка типа компонента: должен быть из списка допустимых значений
- Проверка наличия обоснования: `justification` не должен быть пустым

## Scope (ScopeAgent Output)

**Агент:** ScopeAgent  
**Вход:** Архитектура JSON  
**Выход:** Scope JSON

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["project_name", "objectives", "scope"],
  "properties": {
    "project_name": {
      "type": "string",
      "description": "Название проекта"
    },
    "objectives": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Цели проекта"
    },
    "scope": {
      "type": "object",
      "required": ["in_scope", "out_of_scope"],
      "properties": {
        "in_scope": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Что входит в scope проекта"
        },
        "out_of_scope": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Что не входит в scope проекта"
        }
      }
    },
    "deliverables": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Результаты проекта",
      "default": []
    },
    "success_criteria": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Критерии успеха проекта",
      "default": []
    },
    "timeline": {
      "type": "string",
      "description": "Сроки проекта (может быть 'TBD' или 'unknown')",
      "default": "TBD"
    },
    "resources": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Необходимые ресурсы",
      "default": []
    }
  }
}
```

### Пример валидного Scope

```json
{
  "project_name": "Автоматизация согласования документов",
  "objectives": [
    "Автоматизировать процесс согласования документов",
    "Обеспечить уведомления участникам процесса"
  ],
  "scope": {
    "in_scope": [
      "Бизнес-процесс согласования документов в ELMA365",
      "Уведомления участникам процесса",
      "Отслеживание статуса документов"
    ],
    "out_of_scope": [
      "Интеграция с внешними системами",
      "Мобильное приложение",
      "Кастомные отчеты"
    ]
  },
  "deliverables": [
    "Настроенный бизнес-процесс в ELMA365",
    "Документация по процессу",
    "Инструкция для пользователей"
  ],
  "success_criteria": [
    "Процесс работает автоматически",
    "Все участники получают уведомления",
    "Статус документов отслеживается в реальном времени"
  ],
  "timeline": "TBD",
  "resources": []
}
```

### Пример с "unknown"

```json
{
  "project_name": "Автоматизация процесса",
  "objectives": ["Автоматизировать процесс"],
  "scope": {
    "in_scope": ["Бизнес-процесс"],
    "out_of_scope": ["unknown"]
  },
  "deliverables": ["unknown"],
  "success_criteria": ["Процесс работает"],
  "timeline": "unknown",
  "resources": []
}
```

### Запрещенные поля

Scope **не должен** содержать:

- ❌ Поля форм (детали UI)
- ❌ Интерфейсы (детали дизайна)
- ❌ Сроки реализации (только общее "TBD" или "unknown")
- ❌ Риски проекта
- ❌ Допущения и предположения
- ❌ Технические детали реализации (код, конфигурации)

### Валидация

Валидация выполняется в `pipeline/validators.py`:

- Проверка наличия обязательных полей: `project_name`, `objectives`, `scope`
- Проверка структуры `scope`: должны быть `in_scope` и `out_of_scope`
- Проверка типов данных

## Использование схем

### Валидация ответов

Схемы используются для валидации ответов агентов:

```python
from pipeline.validators import validate_as_is, validate_architecture, validate_scope

# Валидация AS-IS
if not validate_as_is(as_is_result):
    # Обработка ошибки

# Валидация архитектуры
if not validate_architecture(architecture_result):
    # Обработка ошибки

# Валидация scope
if not validate_scope(scope_result):
    # Обработка ошибки
```

### Написание тестов

Схемы используются для написания тестов:

```python
def test_process_extractor_output():
    result = await process_extractor.extract(text)
    assert validate_as_is(result)
    assert "process_name" in result
    assert "steps" in result
    assert isinstance(result["steps"], list)
```

### Гарантия стабильности

Схемы гарантируют, что:

- Агенты всегда возвращают данные в ожидаемом формате
- Изменения в формате данных явно документированы
- Тесты могут проверять структуру данных
- Интеграция между агентами стабильна

## Версионирование схем

При изменении схем необходимо:

1. Обновить этот документ
2. Обновить валидаторы в `pipeline/validators.py`
3. Обновить тесты
4. Указать версию схемы в комментариях

## Связанные документы

- [domain/agents.md](agents.md) — Контракт агентов
- [domain/pipeline.md](pipeline.md) — Правила работы пайплайна
- `pipeline/validators.py` — Реализация валидации
- `agents/models/schemas.py` — Pydantic схемы (Python)


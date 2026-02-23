#!/bin/bash

# Скрипт для запуска бэкенда

echo "🚀 Запуск бэкенда ELMA365 Pipeline..."

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаю..."
    python3 -m venv venv
fi

# Активация виртуального окружения
source venv/bin/activate

# Проверка установки зависимостей
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Установка зависимостей..."
    pip install -r requirements.txt
fi

# Проверка переменных окружения
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Создайте его с необходимыми переменными:"
    echo "   - DATABASE_URL"
    echo "   - DEEPSEEK_API_KEY"
    echo "   - OPENAI_API_KEY"
    echo ""
    echo "Продолжаю запуск..."
fi

# Запуск сервера
echo "✅ Запуск FastAPI сервера на http://localhost:8000"
echo "📝 Логи сохраняются в logs/api_YYYYMMDD.log"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


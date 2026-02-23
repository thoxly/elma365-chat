#!/bin/bash
# Скрипт для безопасного перезапуска системы и бота
# Предотвращает дублирование PID

set -e

PROJECT_DIR="/Users/shoxy/elma_tz_hz"
LOCK_FILE="$PROJECT_DIR/.bot.lock"

echo "=========================================="
echo "🔄 Перезапуск системы ELMA365"
echo "=========================================="
echo ""

cd "$PROJECT_DIR"

# Шаг 1: Остановка всех процессов
echo "1️⃣  Остановка процессов..."

# Остановка FastAPI сервера
echo "   Остановка FastAPI сервера..."
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 2

# Остановка Telegram бота
echo "   Остановка Telegram бота..."
pkill -f "telegram/bot.py" 2>/dev/null || true
sleep 2

# Принудительная остановка, если процессы еще работают
if pgrep -f "uvicorn app.main" > /dev/null; then
    echo "   ⚠️  Принудительная остановка FastAPI..."
    pkill -9 -f "uvicorn app.main" 2>/dev/null || true
    sleep 1
fi

if pgrep -f "telegram/bot.py" > /dev/null; then
    echo "   ⚠️  Принудительная остановка бота..."
    pkill -9 -f "telegram/bot.py" 2>/dev/null || true
    sleep 1
fi

# Шаг 2: Удаление lock файлов
echo ""
echo "2️⃣  Очистка lock файлов..."

if [ -f "$LOCK_FILE" ]; then
    echo "   Удаление .bot.lock..."
    rm -f "$LOCK_FILE"
fi

# Проверка, что процессы действительно остановлены
echo ""
echo "3️⃣  Проверка остановки процессов..."

FASTAPI_RUNNING=$(pgrep -f "uvicorn app.main" | wc -l | tr -d ' ')
BOT_RUNNING=$(pgrep -f "telegram/bot.py" | wc -l | tr -d ' ')

if [ "$FASTAPI_RUNNING" -gt 0 ]; then
    echo "   ⚠️  Предупреждение: FastAPI процессы все еще работают (PID: $(pgrep -f 'uvicorn app.main' | tr '\n' ' '))"
    echo "   Попытка повторной остановки..."
    pkill -9 -f "uvicorn app.main" 2>/dev/null || true
    sleep 2
fi

if [ "$BOT_RUNNING" -gt 0 ]; then
    echo "   ⚠️  Предупреждение: Бот процессы все еще работают (PID: $(pgrep -f 'telegram/bot.py' | tr '\n' ' '))"
    echo "   Попытка повторной остановки..."
    pkill -9 -f "telegram/bot.py" 2>/dev/null || true
    sleep 2
fi

# Финальная проверка
FINAL_FASTAPI=$(pgrep -f "uvicorn app.main" | wc -l | tr -d ' ')
FINAL_BOT=$(pgrep -f "telegram/bot.py" | wc -l | tr -d ' ')

if [ "$FINAL_FASTAPI" -gt 0 ] || [ "$FINAL_BOT" -gt 0 ]; then
    echo "   ❌ Не удалось остановить все процессы!"
    echo "   FastAPI: $FINAL_FASTAPI процессов"
    echo "   Бот: $FINAL_BOT процессов"
    echo ""
    echo "   Попробуйте вручную:"
    echo "   pkill -9 -f 'uvicorn app.main'"
    echo "   pkill -9 -f 'telegram/bot.py'"
    exit 1
fi

echo "   ✅ Все процессы остановлены"
echo ""

# Шаг 3: Активация виртуального окружения
echo "4️⃣  Активация виртуального окружения..."
source venv/bin/activate

# Шаг 4: Запуск FastAPI сервера
echo ""
echo "5️⃣  Запуск FastAPI сервера..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/uvicorn.log 2>&1 &
FASTAPI_PID=$!
sleep 3

# Проверка запуска FastAPI
if ps -p $FASTAPI_PID > /dev/null 2>&1; then
    echo "   ✅ FastAPI запущен (PID: $FASTAPI_PID)"
    # Проверка health endpoint
    sleep 2
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Health check: OK"
    else
        echo "   ⚠️  Health check: не отвечает (возможно, еще запускается)"
    fi
else
    echo "   ❌ FastAPI не запустился. Проверьте логи: tail -f /tmp/uvicorn.log"
    exit 1
fi

# Шаг 5: Запуск Telegram бота
echo ""
echo "6️⃣  Запуск Telegram бота..."
nohup python telegram/bot.py > /tmp/telegram_bot.log 2>&1 &
BOT_PID=$!
sleep 3

# Проверка запуска бота
if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "   ✅ Бот запущен (PID: $BOT_PID)"
    # Проверка lock файла
    if [ -f "$LOCK_FILE" ]; then
        LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null | tr -d ' \n')
        if [ "$LOCK_PID" = "$BOT_PID" ]; then
            echo "   ✅ Lock файл создан корректно (PID: $LOCK_PID)"
        else
            echo "   ⚠️  Lock файл содержит другой PID: $LOCK_PID (ожидался: $BOT_PID)"
        fi
    else
        echo "   ⚠️  Lock файл еще не создан (возможно, бот еще запускается)"
    fi
else
    echo "   ❌ Бот не запустился. Проверьте логи: tail -f /tmp/telegram_bot.log"
    exit 1
fi

# Финальная проверка
echo ""
echo "7️⃣  Финальная проверка..."
sleep 2

# Проверка дублирования процессов
FASTAPI_COUNT=$(pgrep -f "uvicorn app.main" | wc -l | tr -d ' ')
BOT_COUNT=$(pgrep -f "telegram/bot.py" | wc -l | tr -d ' ')

if [ "$FASTAPI_COUNT" -gt 1 ]; then
    echo "   ⚠️  ВНИМАНИЕ: Обнаружено $FASTAPI_COUNT процессов FastAPI!"
    echo "   PID: $(pgrep -f 'uvicorn app.main' | tr '\n' ' ')"
else
    echo "   ✅ FastAPI: 1 процесс (PID: $FASTAPI_PID)"
fi

if [ "$BOT_COUNT" -gt 1 ]; then
    echo "   ⚠️  ВНИМАНИЕ: Обнаружено $BOT_COUNT процессов бота!"
    echo "   PID: $(pgrep -f 'telegram/bot.py' | tr '\n' ' ')"
else
    echo "   ✅ Бот: 1 процесс (PID: $BOT_PID)"
fi

echo ""
echo "=========================================="
echo "✅ Система перезапущена!"
echo "=========================================="
echo ""
echo "📊 Статус:"
echo "   FastAPI: http://localhost:8000 (PID: $FASTAPI_PID)"
echo "   Бот: PID: $BOT_PID"
echo ""
echo "📝 Логи:"
echo "   FastAPI: tail -f /tmp/uvicorn.log"
echo "   Бот: tail -f /tmp/telegram_bot.log"
echo ""
echo "🔍 Проверка статуса:"
echo "   ./check_status.sh"
echo ""






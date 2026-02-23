#!/bin/bash
# Скрипт для проверки статуса системы

echo "=========================================="
echo "📊 Статус системы ELMA365"
echo "=========================================="
echo ""

echo "1️⃣  FastAPI сервер (MCP):"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ РАБОТАЕТ - http://localhost:8000"
    curl -s http://localhost:8000/health
    echo ""
else
    echo "   ❌ НЕ РАБОТАЕТ"
    echo ""
fi

echo "2️⃣  Telegram бот:"
BOT_PID=$(ps aux | grep "telegram/bot.py" | grep -v grep | awk '{print $2}')
if [ -n "$BOT_PID" ]; then
    echo "   ✅ РАБОТАЕТ (PID: $BOT_PID)"
else
    echo "   ❌ НЕ ЗАПУЩЕН"
fi
echo ""

echo "3️⃣  Логи бота (последние 10 строк):"
echo "   ----------------------------------------"
tail -10 /tmp/telegram_bot.log 2>/dev/null || echo "   Логи не найдены"
echo "   ----------------------------------------"
echo ""

echo "4️⃣  Все процессы:"
ps aux | grep -E "(uvicorn|telegram/bot)" | grep -v grep | awk '{printf "   PID: %-6s %s\n", $2, substr($0, index($0,$11))}'
echo ""

echo "=========================================="
echo "📝 Команды для управления:"
echo "   Просмотр логов бота: tail -f /tmp/telegram_bot.log"
echo "   Остановить бота: pkill -f 'telegram/bot.py'"
echo "   Остановить FastAPI: pkill -f 'uvicorn app.main'"
echo "=========================================="








#!/bin/bash
# Скрипт для просмотра логов

LOG_DIR="/Users/shoxy/elma_tz_hz/logs"
TODAY=$(date +%Y%m%d)

echo "=========================================="
echo "📝 Просмотр логов системы"
echo "=========================================="
echo ""

if [ "$1" == "error" ] || [ "$1" == "errors" ]; then
    echo "🔴 Ошибки в логах бота:"
    echo "----------------------------------------"
    grep -i "error\|exception\|traceback" "$LOG_DIR/bot_$TODAY.log" 2>/dev/null | tail -30
    echo ""
    echo "🔴 Ошибки в логах API:"
    echo "----------------------------------------"
    grep -i "error\|exception\|traceback" "$LOG_DIR/api_$TODAY.log" 2>/dev/null | tail -30
elif [ "$1" == "bot" ]; then
    echo "📱 Последние 50 строк лога бота:"
    echo "----------------------------------------"
    tail -50 "$LOG_DIR/bot_$TODAY.log" 2>/dev/null
elif [ "$1" == "api" ]; then
    echo "🌐 Последние 50 строк лога API:"
    echo "----------------------------------------"
    tail -50 "$LOG_DIR/api_$TODAY.log" 2>/dev/null
elif [ "$1" == "follow" ] || [ "$1" == "f" ]; then
    echo "👀 Следим за логами в реальном времени (Ctrl+C для выхода):"
    echo "----------------------------------------"
    tail -f "$LOG_DIR/bot_$TODAY.log" "$LOG_DIR/api_$TODAY.log" 2>/dev/null
else
    echo "Использование: $0 [bot|api|error|follow]"
    echo ""
    echo "Команды:"
    echo "  $0 bot      - показать логи бота"
    echo "  $0 api      - показать логи API"
    echo "  $0 error    - показать только ошибки"
    echo "  $0 follow   - следить за логами в реальном времени"
    echo ""
    echo "📁 Папка с логами: $LOG_DIR"
    echo ""
    echo "Файлы за сегодня:"
    ls -lh "$LOG_DIR"/*"$TODAY".log 2>/dev/null | awk '{print "  " $9, "(" $5 ")"}'
fi





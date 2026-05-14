#!/bin/bash
# Управление реле через HA API (запуск с хоста Pi 3)
# Использование: relay.sh <номер_реле> <on|off>
# Пример: relay.sh 3 on

set -e

RELAY_NUM="$1"
ACTION="$2"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$RELAY_NUM" ] || [ -z "$ACTION" ]; then
    echo "Использование: $0 <номер_реле> <on|off>"
    echo "Пример: $0 3 on"
    exit 1
fi

if [ "$ACTION" != "on" ] && [ "$ACTION" != "off" ]; then
    echo "Ошибка: ACTION должен быть on или off"
    exit 1
fi

ENTITY_ID="switch.vykliuchatel_${RELAY_NUM}"

# Читаем токен из .env проекта
HA_TOKEN="${HA_TOKEN:-}"
if [ -z "$HA_TOKEN" ] && [ -f "$PROJECT_DIR/.env" ]; then
    HA_TOKEN="$(grep -E '^HA_TOKEN=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
fi
HA_TOKEN="${HA_TOKEN:-$(printenv HA_TOKEN)}"

if [ -z "$HA_TOKEN" ]; then
    echo "Ошибка: HA_TOKEN не найден ни в окружении, ни в .env"
    exit 1
fi

curl -s -X POST \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"entity_id\": \"$ENTITY_ID\"}" \
    "http://127.0.0.1:8123/api/services/switch/turn_${ACTION}"

echo ""
echo "Реле $RELAY_NUM -> $ACTION ($ENTITY_ID)"

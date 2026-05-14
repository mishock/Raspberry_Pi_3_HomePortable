#!/usr/bin/env bash
# Сброс pairing HomeKit для контейнера switch (запускать из корня переносимого проекта).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
docker compose exec -T switch sh -lc 'rm -f /app/app/switch.state /app/accessory.state'
docker compose restart switch
echo "HomeKit pairing контейнера switch сброшен (switch.state удалён), сервис перезапущен."
echo "Дальше: 1) «Дом» на iPhone — удалить старый мост «Гараж» при необходимости и добавить снова по коду из switch/app/config.py."
echo "            2) Home Assistant → Настройки → Устройства и службы → Добавить интеграцию → искать связанное с добавлением устройства HomeKit (контроллер)."

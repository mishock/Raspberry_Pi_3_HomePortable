#!/bin/bash
# Обновляет IP-связанные параметры HomeKit/HA после смены сети.
# 1) Обновляет .env -> HAP_BIND_ADDRESS
# 2) Обновляет HA .storage -> advertise_ip для HomeKit Bridge
# 3) Перезапускает switch/homeassistant

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/sync_hap_bind_from_lan.sh --force

STORAGE_JSON="$ROOT/ha_config/.storage/core.config_entries"
if [[ "${EUID}" -eq 0 ]]; then
  python3 scripts/sync_homekit_bridge_advertise_ip.py
elif [[ ! -f "${STORAGE_JSON}" ]] || [[ -w "${STORAGE_JSON}" ]]; then
  # Файл открыт на запись пользователем docker-проекта — sudo не нужен.
  python3 scripts/sync_homekit_bridge_advertise_ip.py
else
  sudo python3 scripts/sync_homekit_bridge_advertise_ip.py
fi
docker compose restart switch homeassistant

echo "network identity synced"

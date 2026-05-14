#!/bin/bash
# Локальный сброс pairing через кнопку HA.
# Очищает HomeKit-записи HA и удаляет switch.state (если том switch смонтирован в /switch_app).

set -euo pipefail

echo "[reset] start"
python3 /config/reset_ha_homekit_controller_storage.py || true

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
bk="/config/.storage/homekit_pairing_reset_${stamp}"
mkdir -p "$bk"

for f in /config/.storage/homekit.*.*; do
  [ -e "$f" ] || continue
  case "$f" in
    *.state|*.aids|*.iids)
      cp -f "$f" "$bk/" || true
      rm -f "$f" || true
      ;;
  esac
done

if [ -f /switch_app/switch.state ]; then
  cp -f /switch_app/switch.state "/switch_app/switch.state.bak_${stamp}" || true
  rm -f /switch_app/switch.state || true
  echo "[reset] removed /switch_app/switch.state"
else
  echo "[reset] /switch_app/switch.state not found"
fi

echo "[reset] done; backup=$bk"

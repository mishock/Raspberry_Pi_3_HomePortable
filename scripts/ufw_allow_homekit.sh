#!/bin/bash
# Открывает входящий TCP для HomeKit на этой машине (нужен sudo, если активен ufw).
# Home Assistant Bridge — отдельный порт в его карточке интеграции; здесь — только мост «Гараж» (51826).

set -euo pipefail

if ! command -v ufw &>/dev/null; then
  echo "ufw не установлен — пропуск."
  exit 0
fi

if ! ufw status | grep -q "Status: active"; then
  echo "ufw не активен — правила не добавлялись."
  exit 0
fi

for port in 51826 21064 21065; do
  if ufw status | grep -qE "${port}/tcp"; then
    echo "Правило для TCP ${port}, похоже, уже есть."
  else
    ufw allow "${port}/tcp" comment "HomeKit / HA bridge (Raspberry_Pi_3_HomePortable)"
    echo "Добавлено: allow ${port}/tcp"
  fi
done

echo "При необходимости: sudo ufw reload && sudo ufw status numbered"

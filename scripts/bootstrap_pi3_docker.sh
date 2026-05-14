#!/bin/bash
# Первичная установка Docker и запуск стека на Raspberry Pi 3 (нужен root).
# Запуск на целевой малине: sudo bash scripts/bootstrap_pi3_docker.sh
# Рабочий каталог — родительский каталог относительно этого скрипта (корень проекта).

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите из корня проекта: sudo bash scripts/bootstrap_pi3_docker.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
# В Debian 13 (trixie) плагин называется пакетом docker-compose (даёт `docker compose`).
apt-get install -y -qq docker.io docker-compose

systemctl enable docker --now

if id pi &>/dev/null; then
  usermod -aG docker pi || true
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  chown pi:pi .env 2>/dev/null || true
fi

# IPv4 для HomeKit mDNS (Tailscale не в приоритете); не затираем ручное HAP_BIND_ADDRESS.
if [[ -x scripts/sync_hap_bind_from_lan.sh ]]; then
  bash scripts/sync_hap_bind_from_lan.sh || true
  chown pi:pi .env 2>/dev/null || true
fi

docker compose build
docker compose up -d

echo "--- контейнеры ---"
docker ps -a --filter name=homeassistant --filter name=switch --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

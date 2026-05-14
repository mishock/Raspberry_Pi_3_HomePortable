#!/bin/bash
# Полное удаление Tailscale на хосте (не Docker): сервис, пакет, репозиторий.
# После этого на Pi может пропасть IPv4 вида 100.x из hostname -I — при необходимости:
#   cd ~/Raspberry_Pi_3_HomePortable && bash scripts/sync_hap_bind_from_lan.sh --force
#   bash scripts/sync_network_identity.sh
# Запуск: sudo bash scripts/remove_tailscale.sh

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Нужны права root: sudo bash $0" >&2
  exit 1
fi

systemctl stop tailscaled 2>/dev/null || true
systemctl disable tailscaled 2>/dev/null || true

export DEBIAN_FRONTEND=noninteractive
if dpkg -l tailscale &>/dev/null; then
  apt-get purge -y tailscale
fi
apt-get autoremove -y

rm -f /etc/apt/sources.list.d/tailscale.list
rm -f /usr/share/keyrings/tailscale-archive-keyring.gpg

echo "Готово: Tailscale снят с автозапуска, пакет удалён, репозиторий pkgs.tailscale.com убран."
echo "Проверка: command -v tailscale (должно быть пусто); ip link show tailscale0 (не найдено)."

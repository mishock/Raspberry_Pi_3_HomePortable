#!/bin/bash
# Подставляет в .env переменную HAP_BIND_ADDRESS — IPv4 домашней LAN для mDNS HomeKit.
# Логика совпадает с switch/app/main.py (приоритет 10/8, 192.168/16; Tailscale 100.64/10 — хуже).
# Запуск из корня проекта: bash scripts/sync_hap_bind_from_lan.sh
# Принудительно перезаписать существующее значение: bash scripts/sync_hap_bind_from_lan.sh --force

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Создан .env из .env.example"
fi

export PYTHONPATH="$(pwd)/switch/app${PYTHONPATH:+:$PYTHONPATH}"
IP="$(
  python3 - <<'PY'
import os
import sys

from hap_lan_ipv4 import pick_lan_ipv4_for_hap

explicit = os.environ.get("HAP_BIND_ADDRESS", "").strip()
if explicit:
    print(explicit)
    raise SystemExit(0)

chosen = pick_lan_ipv4_for_hap()
if not chosen:
    raise SystemExit(1)
print(chosen)
PY
)" || true

if [[ -z "${IP}" ]]; then
  echo "Не удалось определить IPv4 для HAP_BIND_ADDRESS. Задайте вручную в .env" >&2
  exit 1
fi

FORCE="${FORCE}" IP="${IP}" python3 - <<'PY'
from pathlib import Path
import os
import re

path = Path(".env")
text = path.read_text(encoding="utf-8")
force = os.environ["FORCE"] == "1"
ip = os.environ["IP"]

filled = re.search(
    r"(?m)^\s*HAP_BIND_ADDRESS\s*=\s*(\d+\.\d+\.\d+\.\d+)\s*(?:#.*)?$",
    text,
)
if filled and filled.group(1) != ip and not force:
    print(f"HAP_BIND_ADDRESS уже задан как {filled.group(1)}, пропуск (используйте --force).")
    raise SystemExit(0)

pat = re.compile(r"(?m)^\s*(?:#\s*)?HAP_BIND_ADDRESS\s*=.*\n?", re.MULTILINE)
new_line = f"HAP_BIND_ADDRESS={ip}\n"
if pat.search(text):
    text_new = pat.sub(new_line, text, count=1)
else:
    if text and not text.endswith("\n"):
        text += "\n"
    text_new = text + f"\n# IPv4 для HomeKit (mDNS), см. README.\n{new_line}"

path.write_text(text_new, encoding="utf-8")
PY

echo "HAP_BIND_ADDRESS=${IP} записан в .env"

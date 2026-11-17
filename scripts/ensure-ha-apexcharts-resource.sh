#!/usr/bin/env bash
# Обновлено: 2026-11-17
# Гарантирует ресурс Lovelace для apexcharts-card (режим storage игнорирует
# только часть YAML resources; канон — .storage/lovelace_resources).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW="$ROOT/ha_config/www"
JS="$WWW/apexcharts-card.js"
STORAGE="$ROOT/ha_config/.storage/lovelace_resources"
VER="${APEXCHARTS_VER:-2.2.3}"
URL="https://github.com/RomRider/apexcharts-card/releases/download/v${VER}/apexcharts-card.js"

mkdir -p "$WWW"
if [[ ! -f "$JS" ]]; then
  curl -fsSL -o "$JS" "$URL"
fi

python3 - <<PY
import json, pathlib
p = pathlib.Path("$STORAGE")
p.parent.mkdir(parents=True, exist_ok=True)
desired = {
    "version": 1,
    "minor_version": 1,
    "key": "lovelace_resources",
    "data": {
        "items": [
            {
                "id": "apexcharts_card_223",
                "url": "/local/apexcharts-card.js?v=$VER",
                "type": "module",
            }
        ]
    },
}
if p.exists():
    try:
        data = json.loads(p.read_text())
    except Exception:
        data = desired
    items = data.setdefault("data", {}).setdefault("items", [])
    if not any(i.get("url", "").startswith("/local/apexcharts-card.js") for i in items):
        items.append(desired["data"]["items"][0])
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print("added apexcharts resource")
    else:
        print("apexcharts resource already present")
else:
    p.write_text(json.dumps(desired, ensure_ascii=False, indent=2) + "\n")
    print("created lovelace_resources")
PY

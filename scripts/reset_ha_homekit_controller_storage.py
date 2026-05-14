#!/usr/bin/env python3
"""
Сброс интеграции Home Assistant «HomeKit Controller» в .storage (без изменения данных switch в Docker).

Зачем: после смены типа аксессуара на мосту (например старый aid=2 был Switch, стал GarageDoorOpener)
старые записи entity_registry продолжают ссылаться на Switch — возникает KeyError при switch.turn_on.

Запуск на хосте с Docker (рядом с docker-compose.yml переносимого проекта):

  cd ~/Raspberry_Pi_3_HomePortable
  docker compose cp scripts/reset_ha_homekit_controller_storage.py homeassistant:/tmp/reset_hk.py
  docker compose exec -T homeassistant python3 /tmp/reset_hk.py
  docker compose restart homeassistant

Либо из репозитория с ПК скопировать скрипт на Pi и выполнить аналогично.

После перезапуска HA заново настройте при необходимости:
- **HomeKit Device** (контроллер) — код из switch/app/config.py (по умолчанию 123-45-678);
- **HomeKit Bridge** (экспорт в «Дом») — отдельное сопряжение, если используете.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

STORAGE = Path("/config/.storage")
ENTRY_KEY = "core.config_entries"
ENTITY_KEY = "core.entity_registry"
DEVICE_KEY = "core.device_registry"
RESTORE_KEY = "core.restore_state"
HK_MAP_KEY = "homekit_controller-entity-map"

# Домены интеграций Home Assistant, связанные с HomeKit
HK_DOMAINS = frozenset({"homekit_controller", "homekit"})


def _backup_dir() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    b = STORAGE.parent / f".storage_backup_homekit_reset_{ts}"
    b.mkdir(parents=True, exist_ok=False)
    for name in (ENTRY_KEY, ENTITY_KEY, DEVICE_KEY, RESTORE_KEY, HK_MAP_KEY):
        p = STORAGE / name
        if p.is_file():
            shutil.copy2(p, b / name)
    return b


def _load(name: str) -> dict:
    return json.loads((STORAGE / name).read_text(encoding="utf-8"))


def _save(name: str, data: dict) -> None:
    (STORAGE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if not STORAGE.is_dir():
        raise SystemExit(f"Нет каталога {STORAGE} (запускайте внутри контейнера homeassistant)")

    b = _backup_dir()
    print(f"Резервная копия: {b}")

    entries = _load(ENTRY_KEY)
    before = len(entries["data"]["entries"])
    entries["data"]["entries"] = [e for e in entries["data"]["entries"] if e.get("domain") not in HK_DOMAINS]
    removed_e = before - len(entries["data"]["entries"])
    _save(ENTRY_KEY, entries)
    print(f"core.config_entries: удалено записей homekit / homekit_controller: {removed_e}")

    hk_path = STORAGE / HK_MAP_KEY
    if hk_path.is_file():
        hk = _load(HK_MAP_KEY)
        n = len(hk.get("data", {}).get("pairings", {}))
        hk["data"]["pairings"] = {}
        _save(HK_MAP_KEY, hk)
        print(f"{HK_MAP_KEY}: очищено pairings (было {n})")

    ent = _load(ENTITY_KEY)
    old = ent["data"]["entities"]
    ent["data"]["entities"] = [e for e in old if e.get("platform") not in HK_DOMAINS]
    print(f"core.entity_registry: удалено сущностей: {len(old) - len(ent['data']['entities'])}")
    _save(ENTITY_KEY, ent)

    dev = _load(DEVICE_KEY)
    old_d = dev["data"]["devices"]

    def is_hk(d: dict) -> bool:
        for block in d.get("identifiers", []) or []:
            for item in block:
                if isinstance(item, str) and "homekit" in item.lower():
                    return True
        return False

    dev["data"]["devices"] = [d for d in old_d if not is_hk(d)]
    print(f"core.device_registry: удалено устройств: {len(old_d) - len(dev['data']['devices'])}")
    _save(DEVICE_KEY, dev)

    rs = _load(RESTORE_KEY)
    drop_prefixes = (
        "switch.vykliuchatel",
        "button.vykliuchatel",
        "button.garazh",
        "cover.vorot",
        "cover.homekit",
        "homekit.",
    )
    rs_old = rs["data"]

    def keep(st: dict) -> bool:
        eid = (st.get("state") or {}).get("entity_id") or ""
        return not any(eid.startswith(p) for p in drop_prefixes)

    rs["data"] = [x for x in rs_old if keep(x)]
    print(f"core.restore_state: удалено блоков: {len(rs_old) - len(rs['data'])}")
    _save(RESTORE_KEY, rs)

    print(
        "Готово. Перезапустите контейнер homeassistant и при необходимости добавьте "
        "HomeKit Controller и/или HomeKit Bridge заново."
    )


if __name__ == "__main__":
    main()

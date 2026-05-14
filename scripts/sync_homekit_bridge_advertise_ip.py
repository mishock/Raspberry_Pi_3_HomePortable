#!/usr/bin/env python3
"""Синхронизирует advertise_ip у HomeKit Bridge в HA с текущим LAN IPv4."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, UTC
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    storage_path = root / "ha_config" / ".storage" / "core.config_entries"
    if not env_path.exists() or not storage_path.exists():
        print("skip: .env или core.config_entries не найден")
        return 0

    ip = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("HAP_BIND_ADDRESS="):
            value = line.split("=", 1)[1].strip()
            if value:
                ip = value
            break
    if not ip:
        print("skip: HAP_BIND_ADDRESS пуст")
        return 0

    raw = storage_path.read_text(encoding="utf-8")
    obj = json.loads(raw)
    entries = obj.get("data", {}).get("entries", [])

    changed = False
    for entry in entries:
        if entry.get("domain") != "homekit":
            continue
        data = entry.setdefault("data", {})
        if data.get("ip_address") != "0.0.0.0":
            data["ip_address"] = "0.0.0.0"
            changed = True
        if data.get("advertise_ip") != ip:
            data["advertise_ip"] = ip
            changed = True

    if not changed:
        print(f"ok: advertise_ip уже {ip}")
        return 0

    backup = storage_path.with_name(
        f"core.config_entries.bak_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_auto_ip_sync"
    )
    shutil.copy2(storage_path, backup)
    storage_path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"updated: advertise_ip={ip}, backup={backup.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

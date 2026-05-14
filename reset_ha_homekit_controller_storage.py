#!/usr/bin/env python3
"""Локальная очистка HomeKit записей HA в /config/.storage."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, UTC
from pathlib import Path


def backup_dir(storage: Path) -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    b = storage.parent / f".storage_backup_homekit_reset_{ts}"
    b.mkdir(exist_ok=True)
    return b


def backup_file(src: Path, dst_dir: Path) -> None:
    if src.exists():
        shutil.copy2(src, dst_dir / src.name)


def main() -> int:
    storage = Path("/config/.storage")
    if not storage.exists():
        print("skip: /config/.storage not found")
        return 0

    bdir = backup_dir(storage)

    entries_file = storage / "core.config_entries"
    if entries_file.exists():
        backup_file(entries_file, bdir)
        obj = json.loads(entries_file.read_text(encoding="utf-8"))
        entries = obj.get("data", {}).get("entries", [])
        kept = [e for e in entries if e.get("domain") not in ("homekit", "homekit_controller")]
        removed_ids = {e.get("entry_id") for e in entries if e.get("domain") in ("homekit", "homekit_controller")}
        obj["data"]["entries"] = kept
        entries_file.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"core.config_entries: removed={len(entries) - len(kept)}")
    else:
        removed_ids = set()

    ent_map = storage / "homekit_controller-entity-map"
    if ent_map.exists():
        backup_file(ent_map, bdir)
        ent_map.write_text(json.dumps({"version": 1, "minor_version": 1, "key": "homekit_controller-entity-map", "data": {}}, ensure_ascii=False), encoding="utf-8")
        print("homekit_controller-entity-map: cleared")

    reg_file = storage / "core.entity_registry"
    if reg_file.exists():
        backup_file(reg_file, bdir)
        obj = json.loads(reg_file.read_text(encoding="utf-8"))
        entities = obj.get("data", {}).get("entities", [])
        kept_entities = [e for e in entities if e.get("config_entry_id") not in removed_ids]
        obj["data"]["entities"] = kept_entities
        reg_file.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"core.entity_registry: removed={len(entities) - len(kept_entities)}")

    dev_file = storage / "core.device_registry"
    if dev_file.exists():
        backup_file(dev_file, bdir)
        obj = json.loads(dev_file.read_text(encoding="utf-8"))
        devices = obj.get("data", {}).get("devices", [])
        kept_devices = [d for d in devices if not (set(d.get("config_entries", [])) & removed_ids)]
        obj["data"]["devices"] = kept_devices
        dev_file.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"core.device_registry: removed={len(devices) - len(kept_devices)}")

    restore_file = storage / "core.restore_state"
    if restore_file.exists():
        backup_file(restore_file, bdir)
        obj = json.loads(restore_file.read_text(encoding="utf-8"))
        data = obj.get("data", [])
        kept_data = [x for x in data if not str(x.get("state", {}).get("entity_id", "")).startswith(("switch.", "cover."))]
        obj["data"] = kept_data
        restore_file.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"core.restore_state: removed={len(data) - len(kept_data)}")

    print(f"backup={bdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

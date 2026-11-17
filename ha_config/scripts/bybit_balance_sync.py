#!/usr/bin/env python3
"""Синхронизация баланса Bybit с Pi5 → host_status + CSV (для HA на Pi3).

Обновлено: 2026-11-17 — пишет JSON-историю для плавного графика ApexCharts.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path("/config")
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).resolve().parents[1]

HOST_STATUS = CONFIG_DIR / "host_status"
WWW_DIR = CONFIG_DIR / "www"
CSV_PATH = CONFIG_DIR / "data" / "bybit_balance.csv"
HISTORY_JSON = WWW_DIR / "bybit_balance_history.json"
SNAPSHOT_PATH = HOST_STATUS / "bybit_snapshot.json"
BALANCE_FILE = HOST_STATUS / "bybit_balance_usd.txt"
WALLET_FILE = HOST_STATUS / "bybit_wallet_usd.txt"
AVAILABLE_FILE = HOST_STATUS / "bybit_available_usd.txt"

PI5 = os.environ.get("PI5_SSH", "pi@100.102.159.200")
REMOTE_SCRIPT = "/home/pi/Documents/.cursor/scripts/bybit-balance-json.py"
SSH_ID = CONFIG_DIR / ".ssh" / "pi3_to_pi5"
SSH_KNOWN = CONFIG_DIR / "data" / "ssh_known_hosts"
HOST_SSH_KEYS = [
    Path("/home/pi/.ssh/id_ed25519"),
    Path.home() / ".ssh" / "id_ed25519",
    CONFIG_DIR / ".ssh" / "pi3_to_pi5",
]


def pick_ssh_key() -> Path | None:
    for key in HOST_SSH_KEYS:
        if key.is_file() and key.stat().st_size > 50:
            return key
    return None

PROXY_KEYS = ("LD_PRELOAD", "PROXYCHAINS_QUIET_MODE", "PROXYCHAINS_CONF_FILE")
MAX_ASSET_SENSORS = 6


def clean_environ() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in PROXY_KEYS}


def fetch_balance() -> dict:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=30",
        "-o",
        "IdentitiesOnly=yes",
    ]
    ssh_key = pick_ssh_key()
    if ssh_key:
        cmd.extend(["-i", str(ssh_key)])
    if SSH_KNOWN.is_file():
        cmd.extend(
            [
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                f"UserKnownHostsFile={SSH_KNOWN}",
            ]
        )
    else:
        cmd.extend(["-o", "StrictHostKeyChecking=accept-new"])
    cmd.extend([PI5, "python3", REMOTE_SCRIPT])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=90,
        env=clean_environ(),
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "ssh failed").strip())
    line = proc.stdout.strip().splitlines()[-1]
    data = json.loads(line)
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data


def write_text(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")


def fmt_asset(coin: dict) -> str:
    return f"{coin['coin']} · {coin['wallet']:.6g} · ${coin['usd']:.2f}"


def build_history_from_csv() -> dict:
    """Одна точка на день (последний equity) — без ступенек HA history."""
    by_day: dict[str, dict] = {}
    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                day = (row.get("date") or "").strip()
                try:
                    equity = float(row.get("equity_usd") or 0)
                except (TypeError, ValueError):
                    continue
                if not day:
                    continue
                time_s = (row.get("time") or "00:00:00").strip()
                by_day[day] = {
                    "t": f"{day}T{time_s}",
                    "v": round(equity, 2),
                    "wallet": round(float(row.get("wallet_usd") or 0), 2),
                }
    equity_points = [
        {"t": item["t"][:10], "v": item["v"], "ts": item["t"]}
        for day, item in sorted(by_day.items())
    ]
    return {
        "updated": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "equity": equity_points,
    }


def write_history_json() -> Path:
    WWW_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_history_from_csv()
    HISTORY_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return HISTORY_JSON


def write_status(data: dict) -> None:
    HOST_STATUS.mkdir(parents=True, exist_ok=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    equity = float(data["equity_usd"])
    wallet = float(data.get("wallet_usd", 0))
    available = float(data.get("available_usd", 0))

    write_text(BALANCE_FILE, f"{equity:.2f}")
    write_text(WALLET_FILE, f"{wallet:.2f}")
    write_text(AVAILABLE_FILE, f"{available:.2f}")

    SNAPSHOT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    write_text(HOST_STATUS / "bybit_env.txt", data.get("env", ""))
    write_text(HOST_STATUS / "bybit_account_type.txt", data.get("account_type", "UNIFIED"))
    write_text(HOST_STATUS / "bybit_settle_currency.txt", data.get("settle_currency", "USDT"))
    write_text(HOST_STATUS / "bybit_trade_markets.txt", data.get("trade_markets", ""))
    write_text(HOST_STATUS / "bybit_positions_summary.txt", data.get("positions_summary", ""))
    write_text(
        HOST_STATUS / "bybit_unrealised_pnl.txt",
        f"{float(data.get('unrealised_pnl_usd', 0)):.2f}",
    )

    main = data.get("main_coin")
    if main:
        write_text(
            HOST_STATUS / "bybit_main_holding.txt",
            f"{main['coin']} · ${main['usd']:.2f} · {main['pct']:.1f}%",
        )
    else:
        write_text(HOST_STATUS / "bybit_main_holding.txt", "—")

    coins = data.get("coins") or []
    for idx in range(MAX_ASSET_SENSORS):
        path = HOST_STATUS / f"bybit_asset_{idx + 1}.txt"
        if idx < len(coins):
            write_text(path, fmt_asset(coins[idx]))
        else:
            write_text(path, "—")

    sync_local = datetime.now().strftime("%d.%m.%Y %H:%M")
    write_text(HOST_STATUS / "bybit_last_sync.txt", sync_local)

    if not CSV_PATH.exists():
        with CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(
                [
                    "date",
                    "time",
                    "equity_usd",
                    "wallet_usd",
                    "available_usd",
                    "env",
                    "settle_currency",
                    "positions_count",
                    "unrealised_pnl_usd",
                ]
            )

    now = datetime.now()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(
            [
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                f"{equity:.2f}",
                f"{wallet:.2f}",
                f"{available:.2f}",
                data.get("env", ""),
                data.get("settle_currency", ""),
                str(data.get("positions_count", 0)),
                f"{float(data.get('unrealised_pnl_usd', 0)):.2f}",
            ]
        )
    write_history_json()


def main() -> int:
    args = set(sys.argv[1:])
    if "--history-only" in args:
        path = write_history_json()
        print(f"OK history={path}")
        return 0
    try:
        data = fetch_balance()
        write_status(data)
        main_coin = data.get("main_coin") or {}
        print(
            f"OK equity={data['equity_usd']:.2f} USD "
            f"settle={data.get('settle_currency')} "
            f"main={main_coin.get('coin', '—')} "
            f"pos={data.get('positions_count', 0)} "
            f"history={HISTORY_JSON}"
        )
        return 0
    except (OSError, json.JSONDecodeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

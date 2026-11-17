#!/usr/bin/env python3
"""Средний суточный и месячный расход электро (гараж) из CSV показаний.

Обновлено: 2026-11-17 — также пишет JSON-историю для плавных графиков ApexCharts.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

CONFIG_DIR = Path("/config")
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).resolve().parents[1]

CSV_PATH = CONFIG_DIR / "data" / "garage_electric_meter.csv"
HOST_STATUS = CONFIG_DIR / "host_status"
WWW_DIR = CONFIG_DIR / "www"
HISTORY_JSON = WWW_DIR / "garage_meter_history.json"
AVG_DAILY_FILE = HOST_STATUS / "garage_electric_avg_daily.txt"
AVG_MONTHLY_FILE = HOST_STATUS / "garage_electric_avg_monthly.txt"
DAYS_PER_MONTH = 365.25 / 12


def load_readings() -> list[tuple[date, float]]:
    if not CSV_PATH.exists():
        return []
    rows: list[tuple[date, float]] = []
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                day = datetime.strptime(row["date"], "%Y-%m-%d").date()
                kwh = float(row["kwh"])
            except (KeyError, ValueError, TypeError):
                continue
            rows.append((day, kwh))
    rows.sort(key=lambda item: item[0])
    return rows


def compute_averages(rows: list[tuple[date, float]]) -> tuple[float, float]:
    if len(rows) < 2:
        return 0.0, 0.0

    total_kwh = 0.0
    total_days = 0
    for idx in range(1, len(rows)):
        day0, kwh0 = rows[idx - 1]
        day1, kwh1 = rows[idx]
        days = max((day1 - day0).days, 1)
        delta = kwh1 - kwh0
        if delta < 0:
            continue
        total_kwh += delta
        total_days += days

    if total_days <= 0:
        return 0.0, 0.0

    avg_daily = total_kwh / total_days
    avg_monthly = avg_daily * DAYS_PER_MONTH
    return round(avg_daily, 2), round(avg_monthly, 1)


def build_history(rows: list[tuple[date, float]]) -> dict:
    """Точки только по реальным внесениям — без удержания значения между датами."""
    meter = [{"t": day.isoformat(), "v": round(kwh, 2)} for day, kwh in rows]
    avg_daily: list[dict] = []
    avg_monthly: list[dict] = []
    for idx in range(1, len(rows)):
        prefix = rows[: idx + 1]
        d_avg, m_avg = compute_averages(prefix)
        day = rows[idx][0].isoformat()
        avg_daily.append({"t": day, "v": d_avg})
        avg_monthly.append({"t": day, "v": m_avg})
    return {
        "updated": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "meter": meter,
        "avg_daily": avg_daily,
        "avg_monthly": avg_monthly,
    }


def fix_owner(path: Path) -> None:
    if os.geteuid() != 0:
        return
    st = path.parent.stat()
    try:
        os.chown(path, st.st_uid, st.st_gid)
    except OSError:
        pass


def write_history_json(rows: list[tuple[date, float]] | None = None) -> Path:
    if rows is None:
        rows = load_readings()
    WWW_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_history(rows)
    HISTORY_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fix_owner(HISTORY_JSON)
    return HISTORY_JSON


def write_average_files(avg_daily: float, avg_monthly: float) -> None:
    HOST_STATUS.mkdir(parents=True, exist_ok=True)
    AVG_DAILY_FILE.write_text(f"{avg_daily:.2f}\n", encoding="utf-8")
    AVG_MONTHLY_FILE.write_text(f"{avg_monthly:.1f}\n", encoding="utf-8")
    fix_owner(AVG_DAILY_FILE)
    fix_owner(AVG_MONTHLY_FILE)


def recalc_and_write() -> tuple[float, float]:
    rows = load_readings()
    avg_daily, avg_monthly = compute_averages(rows)
    write_average_files(avg_daily, avg_monthly)
    write_history_json(rows)
    return avg_daily, avg_monthly


def main() -> int:
    avg_daily, avg_monthly = recalc_and_write()
    print(
        f"avg_daily={avg_daily:.2f} kWh/d avg_monthly={avg_monthly:.1f} kWh/mo "
        f"history={HISTORY_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

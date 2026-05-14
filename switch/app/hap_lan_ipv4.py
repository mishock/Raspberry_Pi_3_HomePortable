"""Выбор IPv4 для объявления в HomeKit (mDNS advertised_address).

1) Переменная окружения HAP_BIND_ADDRESS (если не пустая).
2) Адрес src у маршрута по умолчанию («тот интерфейс, через который уходит маршрут») —
   чтобы на ELEKTRO_ и других сетях не выбрать «лишний» LAN при нескольких IPv4.
3) То же упорядочивание hostname -I, что раньше (LAN лучше, чем Tailscale 100.x).
"""

from __future__ import annotations

import ipaddress
import os
import re
import subprocess
from typing import Optional


def ipv4_publicity_priority(addr: ipaddress.IPv4Address) -> int:
    """Меньше приоритет — лучше для advertise в домашнем Wi‑Fi."""
    if addr.is_loopback:
        return 300
    if addr.is_link_local:
        return 200
    if addr in ipaddress.ip_network("10.0.0.0/8"):
        return 0
    if addr in ipaddress.ip_network("192.168.0.0/16"):
        return 0
    if addr in ipaddress.ip_network("172.16.0.0/12"):
        return 1
    if addr in ipaddress.ip_network("100.64.0.0/10"):
        return 50
    return 10


def _parse_route_src(route_line: str) -> Optional[str]:
    m = re.search(r"\bsrc\s+(\d+\.\d+\.\d+\.\d+)\b", route_line)
    return m.group(1) if m else None


def default_route_ipv4_src() -> Optional[str]:
    """IPv4 после 'src' в выводе 'ip route get' к внешнему узлу."""
    targets = ("8.8.8.8", "1.1.1.1", "9.9.9.9")
    for tgt in targets:
        try:
            out = subprocess.check_output(
                ["ip", "-4", "route", "get", tgt],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        for line in out.splitlines():
            src = _parse_route_src(line)
            if src:
                try:
                    addr = ipaddress.ip_address(src)
                except ValueError:
                    continue
                if addr.version != 4 or addr.is_loopback or addr.is_link_local:
                    continue
                # Не использовать docker0 / tailscale если маршрут всё-таки туда попал без LAN
                if str(addr).startswith(("172.17.", "172.18.", "172.19.")):
                    continue
                return str(addr)
    return None


def _hostname_i_candidates() -> list[tuple[int, str]]:
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True).strip()
    except (subprocess.CalledProcessError, OSError):
        return []

    candidates: list[tuple[int, str]] = []
    for token in out.split():
        try:
            addr = ipaddress.ip_address(token)
        except ValueError:
            continue
        if addr.version != 4:
            continue
        if token.startswith(("172.17.", "172.18.", "172.19.")):
            continue
        candidates.append((ipv4_publicity_priority(addr), token))
    return candidates


def pick_lan_ipv4_for_hap() -> Optional[str]:
    """Без учёта HAP_BIND_ADDRESS: маршрут по умолчанию, иначе hostname -I."""
    src = default_route_ipv4_src()
    if src:
        try:
            addr = ipaddress.ip_address(src)
        except ValueError:
            addr = None
        if addr and addr.version == 4 and not addr.is_loopback and not addr.is_link_local:
            return src

    c = _hostname_i_candidates()
    if not c:
        return None
    c.sort(key=lambda x: (x[0], x[1]))
    return c[0][1]


def pick_hap_advertised_ipv4() -> Optional[str]:
    """С учётом HAP_BIND_ADDRESS из окружения (как в контейнере switch)."""
    explicit = os.environ.get("HAP_BIND_ADDRESS", "").strip()
    if explicit:
        return explicit
    return pick_lan_ipv4_for_hap()

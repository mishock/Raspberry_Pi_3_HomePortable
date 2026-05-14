#!/usr/bin/env python3
"""Перезапуск контейнера switch через Docker API (unix socket)."""

from __future__ import annotations

import json
import socket
from pathlib import Path

SOCK = "/var/run/docker.sock"
CONTAINER = "switch"


def docker_post(path: str) -> tuple[int, str]:
    req = (
        f"POST {path} HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(req)
        chunks: list[bytes] = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.splitlines()[0].decode("utf-8", errors="replace")
    status = int(status_line.split(" ")[1])
    return status, body.decode("utf-8", errors="replace")


def main() -> int:
    if not Path(SOCK).exists():
        print("docker socket not found")
        return 1

    status, body = docker_post(f"/v1.41/containers/{CONTAINER}/restart?t=10")
    if status in (204, 304):
        print("switch restart requested")
        return 0

    print(f"docker api error status={status} body={body[:500]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

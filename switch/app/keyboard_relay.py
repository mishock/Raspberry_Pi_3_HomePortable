import logging
import os
import select
import sys

import evdev

import urllib.request
import json

HA_BASE = "http://127.0.0.1:8123"
HA_TOKEN = os.environ.get("HA_TOKEN", "")

COVER_ENTITY = "cover.vorota"

KEY_MAP = {
    59: "switch.vykliuchatel_3",
    60: "switch.vykliuchatel_4",
    61: "switch.vykliuchatel_5",
    62: "switch.vykliuchatel_6",
    63: "switch.vykliuchatel_7",
    64: "switch.vykliuchatel_8",
}
UP_CODE = 104   # KEY_PAGEUP
DOWN_CODE = 109  # KEY_PAGEDOWN


def ha_call(service: str, entity_id: str):
    data = json.dumps({"entity_id": entity_id}).encode()
    req = urllib.request.Request(
        f"{HA_BASE}/api/services/{service}",
        data=data,
        headers={
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logging.error("HA call %s %s failed: %s", service, entity_id, e)


def find_keyboard() -> evdev.InputDevice | None:
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if "keyboard" in dev.name.lower() or "mouse" in dev.name.lower():
            caps = dev.capabilities()
            keys = caps.get(1, [])
            if 59 in keys:
                return dev
    return None


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout
    )
    if not HA_TOKEN:
        logging.error("HA_TOKEN not set")
        sys.exit(1)

    dev = find_keyboard()
    if dev is None:
        logging.error("Keyboard with F1 key not found")
        sys.exit(1)
    logging.info("Found keyboard: %s (%s)", dev.name, dev.path)

    logging.info(
        "F1..F6 -> switch.3..8  UP=%s DOWN=%s",
        COVER_ENTITY + " open",
        COVER_ENTITY + " close",
    )

    while True:
        r, _, _ = select.select([dev], [], [])
        if not r:
            continue
        for ev in dev.read():
            if ev.type != 1 or ev.value != 1:
                continue
            code = ev.code
            if code in KEY_MAP:
                ha_call("switch/toggle", KEY_MAP[code])
            elif code == UP_CODE:
                ha_call("cover/open_cover", COVER_ENTITY)
            elif code == DOWN_CODE:
                ha_call("cover/close_cover", COVER_ENTITY)


if __name__ == "__main__":
    main()

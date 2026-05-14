import logging
import os
import threading

import lgpio
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_GARAGE_DOOR_OPENER, CATEGORY_SWITCH
from config import (
    BRIDGE_DISPLAY_NAME,
    FORCE_ALL_RELAYS_SAFE_OFF_AFTER_LOAD,
    GARAGE_CLOSE_BCM,
    GARAGE_DEFAULT_CURRENT_STATE_CLOSED,
    GARAGE_DOOR_DISPLAY_NAME,
    GARAGE_OPEN_BCM,
    GARAGE_PULSE_SECONDS,
    HAP_PORT,
    HOMEKIT_PIN_CODE,
    RELAY_ACTIVE_LOW,
    SENSOR_OPEN_BCM,
    SENSOR_CLOSED_BCM,
    SENSOR_DEBOUNCE_MS,
    SWITCH_CHANNELS,
)
from hap_lan_ipv4 import pick_hap_advertised_ipv4

# HAP GarageDoorOpener / DoorState (кратко см. конфиг-комментарий).
TARGET_OPEN = 0
TARGET_CLOSED = 1
CURRENT_OPEN = 0
CURRENT_CLOSED = 1
CURRENT_OPENING = 2
CURRENT_CLOSING = 3


class GarageDoorRelayAccessory(Accessory):
    """Импульс на CH1 (открыть) / CH2 (закрыть) + концевики NO на BCM 17/27."""

    category = CATEGORY_GARAGE_DOOR_OPENER

    def __init__(
        self,
        driver,
        display_name: str,
        bcm_open: int,
        bcm_close: int,
        bcm_sensor_open: int,
        bcm_sensor_closed: int,
        gpio_chip_handle: int,
        info_serial_number: str,
    ) -> None:
        super().__init__(driver, display_name)
        self._gpio = gpio_chip_handle
        self._open_pin = bcm_open
        self._close_pin = bcm_close
        self._sensor_open_pin = bcm_sensor_open
        self._sensor_closed_pin = bcm_sensor_closed
        self._pulse_lock = threading.Lock()
        self._timers: list[threading.Timer] = []

        initial_out = 1 if RELAY_ACTIVE_LOW else 0
        lgpio.gpio_claim_output(self._gpio, self._open_pin, initial_out)
        lgpio.gpio_claim_output(self._gpio, self._close_pin, initial_out)
        self._both_off()

        lgpio.gpio_claim_input(self._gpio, self._sensor_open_pin, lgpio.SET_PULL_UP)
        lgpio.gpio_claim_input(self._gpio, self._sensor_closed_pin, lgpio.SET_PULL_UP)

        svc = self.add_preload_service("GarageDoorOpener")
        self._char_current = svc.get_characteristic("CurrentDoorState")
        self._char_target = svc.configure_char(
            "TargetDoorState",
            setter_callback=self._set_target_door_state,
        )
        svc.get_characteristic("ObstructionDetected").set_value(False, should_notify=False)

        start_cur = CURRENT_CLOSED if GARAGE_DEFAULT_CURRENT_STATE_CLOSED else CURRENT_OPEN
        start_tar = TARGET_CLOSED if GARAGE_DEFAULT_CURRENT_STATE_CLOSED else TARGET_OPEN
        self._char_current.set_value(start_cur)
        self._char_target.set_value(start_tar)

        self.set_info_service(
            manufacturer="GaragePiHybrid",
            model="GarageDoor-RelayPulse",
            serial_number=info_serial_number,
        )

        self._cb_open = lgpio.callback(
            self._gpio,
            self._sensor_open_pin,
            lgpio.BOTH_EDGES,
            self._on_sensor_open,
        )
        self._cb_closed = lgpio.callback(
            self._gpio,
            self._sensor_closed_pin,
            lgpio.BOTH_EDGES,
            self._on_sensor_closed,
        )

        logging.info(
            "GarageDoor: концевик OPEN на BCM %d, CLOSED на BCM %d, "
            "текущие значения: open=%s closed=%s",
            self._sensor_open_pin,
            self._sensor_closed_pin,
            self._sensor_active(self._sensor_open_pin),
            self._sensor_active(self._sensor_closed_pin),
        )

    def _sensor_active(self, bcm: int) -> bool:
        return lgpio.gpio_read(self._gpio, bcm) == 0

    def _read_door_state_from_sensors(self) -> int | None:
        open_active = self._sensor_active(self._sensor_open_pin)
        closed_active = self._sensor_active(self._sensor_closed_pin)
        if open_active and not closed_active:
            return CURRENT_OPEN
        if closed_active and not open_active:
            return CURRENT_CLOSED
        return None

    def _on_sensor_open(self, chip: int, gpio: int, level: int, tick: int) -> None:
        active = level == 0
        logging.info("Концевик OPEN (BCM %d) -> %s", gpio, "ЗАМКНУТ" if active else "РАЗОМКНУТ")
        if active:
            with self._pulse_lock:
                self._char_current.set_value(CURRENT_OPEN)

    def _on_sensor_closed(self, chip: int, gpio: int, level: int, tick: int) -> None:
        active = level == 0
        logging.info("Концевик CLOSED (BCM %d) -> %s", gpio, "ЗАМКНУТ" if active else "РАЗОМКНУТ")
        if active:
            with self._pulse_lock:
                self._char_current.set_value(CURRENT_CLOSED)

    def _active_level(self) -> int:
        return 0 if RELAY_ACTIVE_LOW else 1

    def _idle_level(self) -> int:
        return 1 if RELAY_ACTIVE_LOW else 0

    def _write_pin(self, bcm: int, active: bool) -> None:
        lgpio.gpio_write(self._gpio, bcm, self._active_level() if active else self._idle_level())

    def _both_off(self) -> None:
        self._write_pin(self._open_pin, False)
        self._write_pin(self._close_pin, False)

    def _cancel_timers(self) -> None:
        for t in self._timers:
            t.cancel()
        self._timers.clear()

    def sync_safe_closed(self) -> None:
        """Железо выкл, в Home — по концевикам."""
        with self._pulse_lock:
            self._cancel_timers()
            self._both_off()
            state = self._read_door_state_from_sensors()
            if state is not None:
                self._char_current.set_value(state)
                self._char_target.set_value(
                    TARGET_CLOSED if state == CURRENT_CLOSED else TARGET_OPEN
                )

    def _finish_pulse(self, relay_pin: int, final_state_if_no_sensor: int) -> None:
        with self._pulse_lock:
            self._write_pin(relay_pin, False)
            self._timers.clear()
            state = self._read_door_state_from_sensors()
            if state is not None:
                self._char_current.set_value(state)
            else:
                self._char_current.set_value(final_state_if_no_sensor)

    def _set_target_door_state(self, value: int) -> None:
        if value not in (TARGET_OPEN, TARGET_CLOSED):
            return

        relay_pin = self._open_pin if value == TARGET_OPEN else self._close_pin
        transitional = CURRENT_OPENING if value == TARGET_OPEN else CURRENT_CLOSING
        final_state = CURRENT_OPEN if value == TARGET_OPEN else CURRENT_CLOSED

        with self._pulse_lock:
            self._cancel_timers()
            self._both_off()
            self._char_current.set_value(transitional)
            self._write_pin(relay_pin, True)
            t = threading.Timer(
                GARAGE_PULSE_SECONDS,
                self._finish_pulse,
                args=(relay_pin, final_state),
            )
            self._timers.append(t)
            t.start()


class RelaySwitchAccessory(Accessory):
    category = CATEGORY_SWITCH

    def __init__(
        self,
        driver,
        display_name: str,
        bcm_pin: int,
        gpio_chip_handle: int,
        info_serial_number: str,
    ) -> None:
        super().__init__(driver, display_name)
        self._gpio = gpio_chip_handle
        self._pin = bcm_pin
        initial = 1 if RELAY_ACTIVE_LOW else 0
        lgpio.gpio_claim_output(self._gpio, self._pin, initial)
        self.relay_off()

        service = self.add_preload_service("Switch")
        self.char_on = service.configure_char("On", setter_callback=self.set_on)

        self.set_info_service(
            manufacturer="GaragePiHybrid",
            model="RelaySwitch",
            serial_number=info_serial_number,
        )

    def relay_on(self) -> None:
        level = 0 if RELAY_ACTIVE_LOW else 1
        lgpio.gpio_write(self._gpio, self._pin, level)

    def relay_off(self) -> None:
        level = 1 if RELAY_ACTIVE_LOW else 0
        lgpio.gpio_write(self._gpio, self._pin, level)

    def set_on(self, value) -> None:
        if value:
            self.relay_on()
            self.char_on.set_value(True)
        else:
            self.relay_off()
            self.char_on.set_value(False)


def main() -> None:
    if len(SWITCH_CHANNELS) != 6:
        raise RuntimeError(f"Ожидается 6 выключателей в SWITCH_CHANNELS, сейчас: {len(SWITCH_CHANNELS)}")

    # Слушать на всех интерфейсах (0.0.0.0): иначе HAP недоступен с localhost, а HA на host network
    # часто подключается к 127.0.0.1. Рекламируемый IPv4 — из hostname -I или HAP_BIND_ADDRESS.
    bind_address = pick_hap_advertised_ipv4()
    persist_path = "/app/app/switch.state" if os.path.exists("/app/app") else "/home/pi/Raspberry_Pi_3_HomePortable/switch/app/switch.state"
    kwargs = {
        "port": HAP_PORT,
        "pincode": HOMEKIT_PIN_CODE.encode(),
        "persist_file": persist_path,
        "listen_address": "0.0.0.0",
    }
    if bind_address:
        kwargs["advertised_address"] = bind_address
        logging.info(
            "HomeKit: advertised_address=%s listen=0.0.0.0 port=%s",
            bind_address,
            HAP_PORT,
        )
    else:
        logging.warning(
            "HomeKit: advertised_address не задан — в .env для сервиса switch задайте HAP_BIND_ADDRESS "
            "(IPv4 в той же сети, что iPhone)."
        )

    driver = AccessoryDriver(**kwargs)
    gpio_handle = lgpio.gpiochip_open(0)

    bridge = Bridge(driver, BRIDGE_DISPLAY_NAME)
    bridge.set_info_service(
        manufacturer="GaragePiHybrid",
        model="HomeKit-Bridge",
        serial_number="rpi3hap-bridge-01",
    )

    garage = GarageDoorRelayAccessory(
        driver,
        GARAGE_DOOR_DISPLAY_NAME,
        GARAGE_OPEN_BCM,
        GARAGE_CLOSE_BCM,
        SENSOR_OPEN_BCM,
        SENSOR_CLOSED_BCM,
        gpio_handle,
        info_serial_number="rpi3hap-garage-CH1-CH2",
    )
    bridge.add_accessory(garage)

    for title, bcm in SWITCH_CHANNELS:
        bridge.add_accessory(
            RelaySwitchAccessory(
                driver,
                title,
                bcm,
                gpio_handle,
                info_serial_number=f"rpi3hap-relay-bcm{bcm}",
            )
        )

    driver.add_accessory(accessory=bridge)

    if FORCE_ALL_RELAYS_SAFE_OFF_AFTER_LOAD:
        garage.sync_safe_closed()
        for acc in bridge.accessories.values():
            if isinstance(acc, RelaySwitchAccessory):
                acc.set_on(False)

    driver.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

APP_NAME = "GaragePiHybrid"

# HomeKit — один мост: гаражные ворота (реле 1–2) + остальные линии выключателями (CH3…CH8).
BRIDGE_DISPLAY_NAME = "Гараж"
HAP_PORT = 51826
HOMEKIT_PIN_CODE = "123-45-678"

# Реле Waveshare RPi Relay Board (B): LOW-active. BCM по `Платы и модули/RPi_Relay_Board_B/PINOUT.md`
RELAY_ACTIVE_LOW = True

# После загрузки `switch.state` перевести реле в безопасное состояние и выровнять UI HomeKit (без импульсов ворот).
FORCE_ALL_RELAYS_SAFE_OFF_AFTER_LOAD = True

# --- Ворота (с концевиками NO, замыкание на GND) ---
GARAGE_DOOR_DISPLAY_NAME = "Ворота"
GARAGE_OPEN_BCM = 5   # CH1 — импульс «открыть»
GARAGE_CLOSE_BCM = 6  # CH2 — импульс «закрыть»
# Длительность удержания реле в «активном» состоянии (сек.), имитация нажатия кнопки привода.
GARAGE_PULSE_SECONDS = 0.45

# Концевики (NO, подтяжка PUD_UP, GND = активен):
SENSOR_OPEN_BCM = 17   # концевик «ворота открыты»
SENSOR_CLOSED_BCM = 27  # концевик «ворота закрыты»
SENSOR_DEBOUNCE_MS = 50  # мс антидребезг

# HomeKit значения DoorState (HAP): 0 открыто, 1 закрыто, 2 открывается, 3 закрывается, 4 остановлено.
GARAGE_DEFAULT_CURRENT_STATE_CLOSED = True

# Обычные выключатели: CH3…CH8 (не пересекаются с GARAGE_* BCM).
SWITCH_CHANNELS: list[tuple[str, int]] = [
    ("Выключатель 3", 13),  # CH3
    ("Выключатель 4", 16),  # CH4
    ("Выключатель 5", 19),  # CH5
    ("Выключатель 6", 20),  # CH6
    ("Выключатель 7", 21),  # CH7
    ("Выключатель 8", 26),  # CH8
]

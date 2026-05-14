# CHANGELOG — Raspberry_Pi_3_HomePortable

## 2026-05-13 (концевики NO на BCM 17/27 для GarageDoor)

- **`config.py`:** добавлены `SENSOR_OPEN_BCM=17`, `SENSOR_CLOSED_BCM=27` (NO, pull-up, GND=активен).
- **`main.py`:** `GarageDoorRelayAccessory` теперь читает концевики через lgpio callback (`BOTH_EDGES`). При замыкании концевика — `CurrentDoorState` обновляется (0=открыто/1=закрыто). После импульса реле — опрос концевиков вместо синтетического состояния.
- **`main.py`:** persist_file выносится динамически (контейнер / хост).
- Контейнер `switch` остановлен, сервис запущен напрямую на Pi 3 (Docker registry недоступен).

## 2026-05-12 (relay.sh переписан + тест всех реле 3-8)

- **Переписан `ha_config/relay.sh`**: вместо неработающего `SUPERVISOR_TOKEN` (нет в контейнерном режиме) скрипт читает `HA_TOKEN` из `.env` проекта и дёргает `http://127.0.0.1:8123/api/services/switch/turn_on|off`.
- Все реле 3-8 протестированы: `relay.sh <N> on|off` работает для каждого.
- Правило: все скрипты для HA кладём в `ha_config/`, они должны работать при перезапуске контейнера.

## 2026-05-12 (реле 3: автостарт + relay.sh v1)

- Создан `ha_config/relay.sh` (v1, через SUPERVISOR_TOKEN — нерабочий в контейнерном режиме). Лежит в `/config/`.

## 2026-05-12 (AGENTS.md для sms_sender + rsync на Pi 3)

- На Pi 5 написан `~/Документы/Проекты/sms_sender/AGENTS.md` — системный промт для проекта `sms_sender` (SMS-отправитель через SIM7000E, без ответа DS).
- Выполнен `rsync` проекта с Pi 5 на Pi 3: `rsync -avh --delete pi5-zt:'~/Документы/Проекты/sms_sender/' ~/sms_sender/`.
- Решено впредь фиксировать все действия в этом CHANGELOG (по запросу пользователя).

## 2026-05-05 (AiNET: исправлен зависающий pairing)

- Диагностика показала, что Pi 3 была подключена к `ELEKTRO_` (`10.1.30.138`), пока телефон тестировался в `AiNET`; из-за этого pairing «висел».
- После перехода Pi 3 в `AiNET` обновился `.env` (`HAP_BIND_ADDRESS=10.0.20.56`), но обычный `docker compose restart switch` не применял новый env внутри уже созданного контейнера.
- Для применения нового advertised IP контейнер `switch` пересоздан (`docker compose up -d --force-recreate switch`), в логах подтверждено: `advertised_address=10.0.20.56`.
- Выполнен повторный полный reset pairing (switch + HA), проверка: `homekit_entries []`.

## 2026-05-05 (кнопка сброса HomeKit pairing в HA)

- В `ha_config/configuration.yaml` добавлены:
  - `shell_command.reset_homekit_pairing_local`
  - скрипт `script.reset_homekit_pairing_and_restart`
  - template button `button.pi3_homekit_reset_button` (`Сброс спаривания HomeKit (Pi3)`).
- В `docker-compose.yml` сервису `homeassistant` добавлен том `./switch/app:/switch_app`, чтобы кнопка могла удалить `switch.state`.
- В `docker-compose.yml` сервису `homeassistant` добавлен том `/var/run/docker.sock:/var/run/docker.sock`, чтобы кнопка могла перезапускать контейнер `switch` автоматически.
- Добавлены файлы:
  - `ha_config/reset_homekit_pairing.sh`
  - `ha_config/reset_ha_homekit_controller_storage.py`
  - `ha_config/restart_switch_container.py`
- Проверено: `python -m homeassistant --script check_config -c /config` проходит успешно на Pi 3.
- Smoke-test: `bash /config/reset_homekit_pairing.sh` внутри контейнера HA — удаляет `switch.state`, очищает HomeKit записи и инициирует рестарт `switch`.

## 2026-05-05 (повторный сброс pairing по запросу)

- На Pi 3 (`10.1.30.138`) выполнен полный сброс HomeKit pairing:
  - `bash scripts/reset_homekit.sh`
  - `reset_ha_homekit_controller_storage.py` внутри контейнера `homeassistant`
  - очистка `homekit.*.{state,aids,iids}` (на момент запуска удалять было нечего: `removed 0`), с резервной папкой `homekit_pairing_reset_*`.
- Перезапущены контейнеры `switch` и `homeassistant`.
- Проверено: `homekit_entries []` в `ha_config/.storage/core.config_entries`.

## 2026-05-06 (Pi 3: установлен ZeroTier и выполнен join в сеть mishock)

- На Pi 3 (`10.1.30.138`) установлен пакет `zerotier-one` (`1.16.1`), сервис включён в автозапуск и `active`.
- Выполнен `zerotier-cli join af78bf9436f8d0ac` (сеть `mishock`).
- Текущее состояние после join: `ACCESS_DENIED` (сеть `PRIVATE`) до подтверждения узла в ZeroTier Central.
- Идентификатор узла Pi 3 для авторизации: `6f6e0ba1d6`.

## 2026-05-06 (скрипт удаления Tailscale на Pi)

- Добавлен **`scripts/remove_tailscale.sh`**: остановка и отключение **`tailscaled`**, **`apt purge tailscale`**, удаление **`/etc/apt/sources.list.d/tailscale.list`** и ключа Tailscale; после удаления рекомендуется **`sync_hap_bind_from_lan.sh --force`** и **`sync_network_identity.sh`** (пропадёт интерфейс **`100.x`** из **`hostname -I`**).
- Выполнено удаление пакета **tailscale** на **Pi 3** (`10.1.30.138`) и **Pi 5** (`10.1.30.126`), репозиторий и **`tailscale0`** сняты; на Pi 3 после удаления запущены **`sync_hap_bind_from_lan.sh --force`** и **`sync_network_identity.sh`**.

## 2026-05-05 (HomeKit: выбор LAN IPv4 и пояснение «Дом» / «Работа» на ELEKTRO_)

- **`switch/app/hap_lan_ipv4.py`:** общая логика выбора IPv4 для `advertised_address`: приоритет **`HAP_BIND_ADDRESS`**, затем **`src` у маршрута по умолчанию** (`ip -4 route get`), иначе **`hostname -I`** с приоритетом LAN над Tailscale.
- **`switch/app/main.py`:** использует `pick_hap_advertised_ipv4()` из модуля выше.
- **`scripts/sync_hap_bind_from_lan.sh`:** записывает в `.env` тот же выбор (через `PYTHONPATH=switch/app`).
- **`README.md`:** раздел про два дома в приложении «Дом», концентратор и сеть ELEKTRO_; уточнён блок про неверный IPv4 в Bonjour.
- **`scripts/sync_network_identity.sh`:** синхронизация `advertise_ip` через `sudo` только если **`core.config_entries` не записывается текущим пользователем** (нет запроса пароля в типичном `docker-compose`‑каталоге у `pi`).

## 2026-05-04 (полный reset pairing для новой сети)

- На `pi@10.1.30.138` выполнен `scripts/reset_homekit.sh` (очищен `switch.state`, перезапуск `switch`).
- Выполнен `scripts/reset_ha_homekit_controller_storage.py` (очищены записи `homekit_controller` и связанные сущности/устройства/restore_state).
- Проверено: в HA (`core.config_entries`) отсутствуют записи доменов `homekit` и `homekit_controller` — можно создавать мост заново в новой сети.

## 2026-05-04 (автосинхронизация после смены Wi‑Fi)

- Добавлен `scripts/sync_homekit_bridge_advertise_ip.py`: синхронизация `advertise_ip` HomeKit Bridge в `ha_config/.storage/core.config_entries` по `HAP_BIND_ADDRESS`.
- Добавлен `scripts/sync_network_identity.sh`: one-shot обновление `HAP_BIND_ADDRESS` + `advertise_ip` и перезапуск `switch/homeassistant`.
- `README.md` дополнен разделом про выполнение `sync_network_identity.sh` после смены сети и вариант с NetworkManager dispatcher.

## 2026-05-04 (Pi 3: установлен Tailscale)

- На целевом узле `pi@10.1.30.138` установлен `tailscale` (версия `1.96.4`), сервис `tailscaled` включён в автозапуск и активен.
- Для управления без root задан оператор: `sudo tailscale set --operator=pi`.
- Узел пока `Logged out`; для завершения привязки нужно открыть URL авторизации:
  - `https://login.tailscale.com/a/6c63467015333`

## 2026-05-04 (применено на Pi 3: 10.1.30.138)

- На целевом узле **`~/Raspberry_Pi_3_HomePortable`** выполнен **`sync_hap_bind_from_lan.sh --force`**: в `.env` установлен **`HAP_BIND_ADDRESS=10.1.30.138`**.
- Выполнен `docker compose up -d --build switch homeassistant`; в логах `switch` подтверждено: **`advertised_address=10.1.30.138`**, `listen=0.0.0.0`, `port=51826`.
- Выполнен чистый сброс HomeKit-состояния: `reset_homekit.sh` + `reset_ha_homekit_controller_storage.py`; затем перезапуск `homeassistant` и `switch`.
- На Pi 3 установлен и включён `ufw`; добавлены inbound-правила: `OpenSSH`, `8123/tcp`, `51826/tcp`, `21064/tcp`, `21065/tcp`, `5353/udp`.
- Для HA Bridge в `core.config_entries` принудительно задано: `ip_address=0.0.0.0`, `advertise_ip=10.1.30.138`, `port=21064` (с резервной копией).
- Сброшены state-файлы HA Bridge (`homekit.*.{state,aids,iids}`) с бэкапом в `/config/.storage/homekit_bridge_state_backup_*`, чтобы убрать устаревшие пары iPhone к HASS Bridge.

## 2026-05-04 (скрипты: HAP_BIND + ufw + bootstrap)

- **`scripts/sync_hap_bind_from_lan.sh`:** автоматическая запись **`HAP_BIND_ADDRESS`** в `.env` (та же логика приоритетов, что в `switch/app/main.py`); опция **`--force`**.
- **`scripts/ufw_allow_homekit.sh`:** при активном **ufw** — правила для TCP **51826**, **21064**, **21065**.
- **`scripts/bootstrap_pi3_docker.sh`:** вызов **`sync_hap_bind_from_lan.sh`** после создания `.env`.
- **`README.md`:** таблица скриптов, шаг **`sync_hap_bind_from_lan.sh`** в варианте B; не копировать **`.env`** с другой машины без повторного **sync**.

## 2026-05-04 (HAP advertised: LAN важнее Tailscale + HAP_BIND_ADDRESS)

- **`switch/app/main.py`:** выбор **`advertised_address`** из `hostname -I` с приоритетом домашних сетей **10/8**, **192.168/16**, затем **172.16–31**, адреса **100.64.0.0/10** (Tailscale и аналоги) — после них; лог при старте с выбранным адресом или предупреждение.
- **`docker-compose.yml`:** для сервиса **`switch`** переменная окружения **`HAP_BIND_ADDRESS`** из `.env`.
- **`.env.example`**, **`README.md`:** пояснение и раздел «прямой мост не переключает, из HA ок».

## 2026-05-04 (README: после HA телефон не видит «Гараж»)

- **`README.md`:** раздел о том, что после сопряжения **HomeKit Device** в HA с мостом «Гараж» прямое добавление того же моста в «Дом» недоступно; варианты: телефон через **Home Kit Bridge** из HA или сброс + только телефон без контроллера в HA. Исправлено противоречие в пункте 4 раздела про плитки HASS Bridge.

## 2026-05-04 (README: плитки HASS Bridge есть, с телефона не управляются)

- **`README.md`:** раздел про «двойной мост» (телефон → HA Home Kit Bridge → HomeKit Controller → мост «Гараж»): проверка журнала, сеть/TCP, advertise IP; рекомендация убрать HASS Bridge из «Дом» и управлять прямым мостом «Гараж».

## 2026-05-04 (README: «Нет ответа» у HASS Bridge без сущностей)

- **`README.md`:** пояснение: **Home Kit Bridge** экспортирует только уже существующие объекты HA; без интеграции **HomeKit Device** к контейнеру `switch` плитки в «Дом» через HASS Bridge нежизнеспособны.

## 2026-05-04 (сброс HA: controller + bridge)

- **`scripts/reset_ha_homekit_controller_storage.py`:** из `core.config_entries` удаляются и **`homekit_controller`**, и **`homekit`** (экспортирующий мост); сущности/устройства с платформой/идентификаторами **homekit**; в **`restore_state`** дополнительно убираются блоки для `entity_id` с префиксом **`homekit.`**.

## 2026-05-04 (HAP listen 0.0.0.0 + анонс LAN)

- **`switch/app/main.py`:** вместо привязки сокета **только** к одному IPv4 (`address=<LAN>`), сокет слушает **`0.0.0.0:51826`**, а клиентам в Bonjour объявляется **`advertised_address`** (IPv4 LAN из `hostname -I` / `HAP_BIND_ADDRESS`). Раньше **localhost не открывал** порт HAP — это ломало **Home Assistant** на `network_mode: host` и любые локальные проверки.
- **`README.md`/`scripts/reset_homekit.sh`:** напоминание про повторную настройку **«Дом»** и интеграции HomeKit **внутри HA** после `./scripts/reset_homekit.sh`.

## 2026-05-04 (уникальные SerialNumber под «Дом» на iPhone)

- **`switch/app/main.py`:** для моста, ворот и каждого выключателя заданы **уникальные** поля **`AccessoryInformation`** (`Manufacturer`, `Model`, **`SerialNumber`**) вместо одного общего **`default`** у pyhap — иначе в приложении **«Дом»** после сопряжения моста часто не отображаются дочерние устройства. После деплоя мост нужно удалить из «Дом» и добавить заново или дождаться обновления конфигурации.
- **`README.md`:** куда смотреть во вкладках «Дом» (комната, настройки моста).

## 2026-05-04 (диагностика HA + скрипт сброса HomeKit Controller)

- **Проблема:** после смены топологии моста (ворота GarageDoorOpener + выключатели) в журналах HA ошибка **`KeyError: ...00000025...`** при вызове **`switch.turn_on`** — характеристика **«On»** не существует у аксессуара «Ворота». В `core.entity_registry` устаревают связи (**`unique_id` ..._aid_2_ на Switch** при том, что AID‑2 уже ворота).
- **Инструмент:** скрипт **`scripts/reset_ha_homekit_controller_storage.py`** — бэкап `.storage_backup_homekit_reset_*`, удаление интеграции `homekit_controller`, очистка `homekit_controller-entity-map`, сущностей/устройств homekit_controller в реестрах, зачистка связанных restore_state-блоков. На Pi‑экземпляре выполнено один раз после деплоя.
- **`README.md`:** блок «ворота но ошибка switch.turn_on» с командами и напоминанием про домен **`cover`**.

## 2026-05-04 (ворота + выключатели)

- **HomeKit:** на мосту **«Гараж»** добавлен аксессуар типа **гаражных ворот** (`GarageDoorOpener`, имя **`GARAGE_DOOR_DISPLAY_NAME`**, по умолчанию «Ворота»): **CH1 (BCM 5)** — импульс «открыть», **CH2 (BCM 6)** — импульс «закрыть»; длительность импульса **`GARAGE_PULSE_SECONDS`**. **Концевики не задействованы** — `CurrentDoorState` после команды задаётся программно (без контроля положения створки).
- **Реле CH3…CH8:** шесть переключателей в `SWITCH_CHANNELS` (прежние «Выключатель 3…8» по тем же BCM).
- **`config.py`:** вместо одного списка **`RELAY_CHANNELS` (×8)** используются **`GARAGE_*`** + **`SWITCH_CHANNELS` (×6)**; **`APP_NAME`** → `GaragePiHybrid`.
- **`README.md`:** описание новой топологии HomeKit и напоминание о **сбросе pairing** при обновлении с варианта «8 выключателей».

## 2026-05-04

- **Switch / реле:** после загрузки `switch.state` опция **`FORCE_ALL_RELAYS_SAFE_OFF_AFTER_LOAD`** (по умолчанию `True`): все каналы переводятся в «выкл» на железе и в характеристиках; после `gpio_claim_output` добавлен явный **`relay_off()`** — корректный уровень сразу после захвата линии (актуально для CH4 и др. LOW-active после ребута).
- **Развёртывание на Pi 3 по LAN (`10.1.30.138`):** каталог **`/home/pi/Raspberry_Pi_3_HomePortable`**; установлены **`docker.io`** + **`docker-compose`** (Debian **trixie**); добавлен **`scripts/bootstrap_pi3_docker.sh`**; контейнеры **`homeassistant`** и **`switch`** подняты (`docker compose up -d`).
- **`README.md`:** вариант A/B установки; предупреждение про **`rsync --delete`** и **`ha_config`**; актуализировано имя пакета Compose для trixie.

## 2026-05-03

- Создан переносимый проект: единый `docker-compose.yml` (HA + Switch, Pi 3), `ha_config`, копия `switch`, `gai.conf`, `.env.example`, `scripts/reset_homekit.sh`.
- В **`README.md`** добавлен блок **«Идея и смысл (для Cursor и продолжающего в новом чате)»**, чтобы новый сеанс сразу ухватывал роль каталога, границу Pi 3 / Pi 5 и источник дубля `switch/`.
- Роль **умного гаража** + **8 выключателей:** HomeKit **Bridge** `BRIDGE_DISPLAY_NAME = "Гараж"` и 8 `Switch` по `RELAY_CHANNELS` (CH1…CH8 / BCM); `APP_NAME = "GaragePi8"`.

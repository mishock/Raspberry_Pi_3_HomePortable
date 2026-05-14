#!/bin/bash
set -e

python app/main.py &
MAIN_PID=$!

# keyboard_relay.py отключён (требует evdev, нет в базовом образе)
# При появлении быстрого интернета — пересобрать switch с evdev и раскомментировать
# echo "Starting keyboard_relay.py (F1-F6 -> HA switches)"
# python app/keyboard_relay.py &
# RELAY_PID=$!
# trap "kill $MAIN_PID $RELAY_PID 2>/dev/null; exit" SIGTERM SIGINT
trap "kill $MAIN_PID 2>/dev/null; exit" SIGTERM SIGINT

wait

#!/bin/bash
# Hermes Gateway Watchdog for WSL
# Auto-restarts the gateway if it crashes (any non-zero exit).
# Exits cleanly on exit code 0 (normal/signal-initiated shutdown).
#
# Usage:
#   chmod +x ~/start-gateway-watchdog.sh
#   nohup ~/start-gateway-watchdog.sh > /dev/null 2>&1 &
#   # On first run, the script auto-kills any old gateway first.
#
# To verify: ss -tlnp | grep 8642
# To stop:   pkill -f start-gateway-watchdog

export PATH="$PATH:$HOME/.local/bin"
GATEWAY_LOG="$HOME/.hermes/logs/gateway.log"
WATCHDOG_LOG="$HOME/.hermes/logs/watchdog.log"

mkdir -p "$HOME/.hermes/logs"
echo "[$(date)] Watchdog started (PID $$)" >> "$WATCHDOG_LOG"

# --- Graceful pre-start cleanup ---
if pgrep -f "hermes gateway run" > /dev/null 2>&1; then
    echo "[$(date)] Old gateway detected, sending SIGTERM..." >> "$WATCHDOG_LOG"
    pkill -f "hermes gateway run" 2>/dev/null
    sleep 2  # Wait for it to release port 8642
fi

while true; do
    echo "[$(date)] Starting gateway..." >> "$WATCHDOG_LOG"
    hermes gateway run >> "$GATEWAY_LOG" 2>&1
    EXIT_CODE=$?

    if [ "$EXIT_CODE" -eq 0 ]; then
        echo "[$(date)] Gateway exited cleanly (code=0), watchdog stops." >> "$WATCHDOG_LOG"
        exit 0
    fi

    echo "[$(date)] Gateway crashed (code=$EXIT_CODE), restarting in 2s..." >> "$WATCHDOG_LOG"
    sleep 2
done
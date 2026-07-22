#!/usr/bin/env bash
# Helper to manage the EdgeMiner2 MT5 Docker instance on this server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
NAME=mt5_best3m
IMAGE=gmag11/metatrader5_vnc:latest
CONFIG_DIR="$ROOT/docker_config"
EA_SRC="$ROOT/Experts"

start() {
  mkdir -p "$CONFIG_DIR"
  sudo chown -R 911:911 "$CONFIG_DIR" 2>/dev/null || true
  docker rm -f "$NAME" 2>/dev/null || true
  docker run -d --name "$NAME" \
    -p 13000:3000 -p 13001:3001 -p 18001:8001 \
    -e CUSTOM_USER=mt5 -e PASSWORD=mt5pass \
    -v "$CONFIG_DIR:/config" \
    -v "$EA_SRC:/ea_src:ro" \
    "$IMAGE"
  echo "Started. Web VNC: http://$(hostname -I | awk '{print $1}'):13000  (mt5 / mt5pass)"
}

stop() { docker rm -f "$NAME" 2>/dev/null || true; echo stopped; }

status() {
  docker ps --filter "name=$NAME"
  echo "VNC: http://$(hostname -I | awk '{print $1}'):13000  user=mt5 pass=mt5pass"
  docker exec "$NAME" ls -la \
    "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/ForgeBest3m_Frozen."* 2>/dev/null || true
}

deploy_ea() {
  MT5="$CONFIG_DIR/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts"
  sudo cp "$EA_SRC/ForgeBest3m_Frozen.mq5" "$MT5/"
  sudo chown 911:911 "$MT5/ForgeBest3m_Frozen.mq5"
  docker exec -u abc -e WINEPREFIX=/config/.wine -e WINEDEBUG=-all -e DISPLAY=:1 "$NAME" \
    bash -c 'cd "/config/.wine/drive_c/Program Files/MetaTrader 5" && wine MetaEditor64.exe "/compile:MQL5/Experts/ForgeBest3m_Frozen.mq5" "/include:MQL5" /log'
  sleep 3
  status
}

# Usage:
#   ./run_mt5.sh start|stop|status|deploy_ea
# Strategy Tester still needs a demo Login/Password/Server in ForgeBest3m_tester.ini
"${1:-status}"

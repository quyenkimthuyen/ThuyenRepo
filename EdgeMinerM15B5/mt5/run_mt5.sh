#!/usr/bin/env bash
# Helper to manage the EdgeMiner2 MT5 Docker instance on this server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
NAME=mt5_best3m
IMAGE=gmag11/metatrader5_vnc:latest
CONFIG_DIR="$ROOT/docker_config"
EA_SRC="$ROOT/Experts"
BRIDGE_DIR="$ROOT/bridge"

start() {
  mkdir -p "$CONFIG_DIR" "$BRIDGE_DIR"
  sudo chown -R 911:911 "$CONFIG_DIR" 2>/dev/null || true
  docker rm -f "$NAME" 2>/dev/null || true
  docker run -d --name "$NAME" \
    -p 13000:3000 -p 13001:3001 -p 18001:8001 \
    -e CUSTOM_USER=mt5 -e PASSWORD=mt5pass \
    -v "$CONFIG_DIR:/config" \
    -v "$EA_SRC:/ea_src:ro" \
    -v "$BRIDGE_DIR:/mt5_bridge" \
    "$IMAGE"
  # Symlink into MT5 Files sandbox (path has spaces — mount at /mt5_bridge)
  sleep 3
  docker exec -u root "$NAME" bash -c '
    mkdir -p "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files"
    rm -rf "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bridge"
    ln -sfn /mt5_bridge "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bridge"
    chown -h abc:abc "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bridge" || true
  ' || true
  echo "Started. Web VNC: http://$(hostname -I | awk '{print $1}'):13000  (mt5 / mt5pass)"
  echo "Bridge dir: $BRIDGE_DIR -> /mt5_bridge -> MQL5/Files/bridge"
}

stop() { docker rm -f "$NAME" 2>/dev/null || true; echo stopped; }

status() {
  docker ps --filter "name=$NAME"
  echo "VNC: http://$(hostname -I | awk '{print $1}'):13000  user=mt5 pass=mt5pass"
  echo "Bridge: $BRIDGE_DIR"
  ls -la "$BRIDGE_DIR" 2>/dev/null || true
  docker exec "$NAME" ls -la \
    "/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/Forge"* 2>/dev/null || true
}

deploy_ea() {
  local MT5="$CONFIG_DIR/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts"
  for ea in ForgeBest3m_Frozen ForgeBest3m_WF ForgeBridge; do
    if [[ -f "$EA_SRC/${ea}.mq5" ]]; then
      sudo cp "$EA_SRC/${ea}.mq5" "$MT5/"
      sudo chown 911:911 "$MT5/${ea}.mq5"
    fi
  done
  docker exec -u abc -e WINEPREFIX=/config/.wine -e WINEDEBUG=-all -e DISPLAY=:1 "$NAME" \
    bash -c 'cd "/config/.wine/drive_c/Program Files/MetaTrader 5" && wine MetaEditor64.exe "/compile:MQL5/Experts/ForgeBridge.mq5" "/include:MQL5" /log'
  sleep 3
  status
}

sync_bridge() {
  # Copy host bridge JSON/CSV into container Files/bridge (if not bind-mounted).
  mkdir -p "$BRIDGE_DIR"
  if docker inspect "$NAME" >/dev/null 2>&1; then
    docker exec -u abc "$NAME" bash -c "mkdir -p /config/.wine/drive_c/Program\ Files/MetaTrader\ 5/MQL5/Files/bridge"
    # Prefer bind-mount; still rsync files for non-mounted setups
    sudo cp -a "$BRIDGE_DIR/." "$CONFIG_DIR/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bridge/" 2>/dev/null || \
      docker cp "$BRIDGE_DIR/." "$NAME:/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bridge/"
    echo "Synced $BRIDGE_DIR -> container Files/bridge"
  else
    echo "Container $NAME not running; files stay in $BRIDGE_DIR"
  fi
}

backtest() {
  # Headless Strategy Tester via MT5 CLI (/portable + /config).
  local INI_SRC="$ROOT/ForgeBest3m_WF_tester.ini"
  local MT5_DIR="$CONFIG_DIR/.wine/drive_c/Program Files/MetaTrader 5"
  [[ -f "$INI_SRC" ]] || { echo "missing $INI_SRC"; exit 1; }
  sudo cp "$INI_SRC" "$MT5_DIR/ForgeBest3m_WF_tester.ini"
  sudo chown 911:911 "$MT5_DIR/ForgeBest3m_WF_tester.ini"
  if [[ -f "$EA_SRC/ForgeBest3m_WF.ex5" ]]; then
    sudo cp "$EA_SRC/ForgeBest3m_WF.ex5" "$MT5_DIR/MQL5/Experts/"
    sudo chown 911:911 "$MT5_DIR/MQL5/Experts/ForgeBest3m_WF.ex5"
  fi
  docker exec -u abc -e WINEPREFIX=/config/.wine -e WINEDEBUG=-all -e DISPLAY=:1 "$NAME" \
    bash -c 'wine taskkill /IM terminal64.exe /F 2>/dev/null; wine taskkill /IM metatester64.exe /F 2>/dev/null; true'
  sleep 2
  echo "Launching CLI tester..."
  docker exec -u abc "$NAME" bash -c '
    d="/config/.wine/drive_c/Program Files/MetaTrader 5/llm-agent"
    [[ -d "$d" && ! -d "${d}.disabled" ]] && mv "$d" "${d}.disabled" || true
  '
  docker exec -u abc -e WINEPREFIX=/config/.wine -e WINEDEBUG=-all -e DISPLAY=:1 -e HOME=/config "$NAME" \
    bash -c 'cd "/config/.wine/drive_c/Program Files/MetaTrader 5" && wine terminal64.exe /portable "/config:C:\\Program Files\\MetaTrader 5\\ForgeBest3m_WF_tester.ini"' \
    >"$ROOT/cli_tester_stdout.log" 2>&1 &
  echo "PID $!. Log: $ROOT/cli_tester_stdout.log"
}

# Usage:
#   ./run_mt5.sh start|stop|status|deploy_ea|sync_bridge|backtest
"${1:-status}"

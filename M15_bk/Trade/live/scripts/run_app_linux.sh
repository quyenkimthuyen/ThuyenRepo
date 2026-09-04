#!/usr/bin/env bash
set -euo pipefail

ACTION="Restart"
PORT=8801
TIMEOUT_SECONDS=30

usage() {
  cat <<'EOF'
Usage: run_app_linux.sh [Start|Restart|Stop|Status] [--port PORT] [--timeout SECONDS]

  Start     Start the Streamlit app if not already running
  Restart   Stop then start (default)
  Stop      Stop the app
  Status    Print RUNNING or STOPPED (exit 1 if stopped)

Options:
  --port PORT           Listen port (default: 8501)
  --timeout SECONDS     Startup health-check timeout (default: 30)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    Start|Restart|Stop|Status)
      ACTION="$1"
      shift
      ;;
    --port)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:?--timeout requires a value}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Invalid --port: $PORT" >&2
  exit 2
fi
if [[ ! "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || (( TIMEOUT_SECONDS < 5 || TIMEOUT_SECONDS > 120 )); then
  echo "Invalid --timeout: $TIMEOUT_SECONDS (allowed 5-120)" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_PATH="$REPO_ROOT/gui/app.py"
PID_FILE="$REPO_ROOT/results/streamlit_app.pid"
APP_URL="http://127.0.0.1:${PORT}"

test_app_health() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 3 "$APP_URL" >/dev/null 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -q -T 3 -O /dev/null "$APP_URL" >/dev/null 2>&1
  else
    python3 - "$APP_URL" <<'PY'
import sys, urllib.request
try:
  urllib.request.urlopen(sys.argv[1], timeout=3)
  raise SystemExit(0)
except Exception:
  raise SystemExit(1)
PY
  fi
}

# Collect PIDs for this app (pidfile + matching streamlit command lines).
get_app_pids() {
  local saved_id pid args
  {
    if [[ -f "$PID_FILE" ]]; then
      saved_id="$(tr -d '[:space:]' <"$PID_FILE" || true)"
      if [[ "$saved_id" =~ ^[0-9]+$ ]] && (( saved_id > 0 )); then
        if kill -0 "$saved_id" 2>/dev/null; then
          printf '%s\n' "$saved_id"
        fi
      fi
    fi

    while read -r pid args; do
      [[ -z "${pid:-}" ]] && continue
      case "$args" in
        *streamlit*"$APP_PATH"*)
          printf '%s\n' "$pid"
          ;;
      esac
    done < <(ps -eo pid=,args= 2>/dev/null || true)
  } | awk 'NF && !seen[$0]++'
}

port_owner_pid() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$PORT" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n1
  elif command -v lsof >/dev/null 2>&1; then
    lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n1
  fi
}

stop_app() {
  local pids pid
  mapfile -t pids < <(get_app_pids)
  for pid in "${pids[@]:-}"; do
    [[ -z "$pid" ]] && continue
    echo "Stopping app PID $pid..."
    kill "$pid" 2>/dev/null || true
  done
  rm -f "$PID_FILE"

  local deadline=$((SECONDS + 10))
  while (( SECONDS < deadline )); do
    mapfile -t pids < <(get_app_pids)
    ((${#pids[@]} == 0)) && break
    for pid in "${pids[@]:-}"; do
      [[ -z "$pid" ]] && continue
      kill -9 "$pid" 2>/dev/null || true
    done
    sleep 0.25
  done
  echo "App stopped."
}

start_app() {
  local pids
  mapfile -t pids < <(get_app_pids)
  if ((${#pids[@]} > 0)) && test_app_health; then
    echo "App is already running: $APP_URL (PID ${pids[0]})"
    return 0
  fi

  local owner
  owner="$(port_owner_pid || true)"
  if [[ -n "${owner:-}" ]]; then
    echo "Port $PORT is already used by PID $owner." >&2
    exit 1
  fi

  local python=""
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    python="$REPO_ROOT/.venv/bin/python"
  elif [[ -x "/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python" ]]; then
    python="/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python"
  elif [[ -x "/home/thuyenng/work/ThuyenRepo/EdgeMinerM15/.venv/bin/python" ]]; then
    python="/home/thuyenng/work/ThuyenRepo/EdgeMinerM15/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    python="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    python="$(command -v python)"
  else
    echo "python3/python not found on PATH (and no .venv)." >&2
    exit 1
  fi

  if ! "$python" -c 'import streamlit' >/dev/null 2>&1; then
    echo "streamlit not installed for: $python" >&2
    echo "Install with: $python -m pip install -r \"$REPO_ROOT/requirements.txt\"" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$PID_FILE")"
  local log_file="$REPO_ROOT/results/streamlit_app.log"

  nohup "$python" -m streamlit run "$APP_PATH" \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false \
    --server.fileWatcherType none \
    >"$log_file" 2>&1 &
  local new_pid=$!
  echo "$new_pid" >"$PID_FILE"
  echo "Starting app PID $new_pid..."

  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if test_app_health; then
      echo "App ready: $APP_URL"
      return 0
    fi
    if ! kill -0 "$new_pid" 2>/dev/null; then
      echo "App process exited during startup. See $log_file" >&2
      exit 1
    fi
    sleep 1
  done
  echo "App did not become ready within $TIMEOUT_SECONDS seconds. See $log_file" >&2
  exit 1
}

case "$ACTION" in
  Start)
    start_app
    ;;
  Restart)
    stop_app
    start_app
    ;;
  Stop)
    stop_app
    ;;
  Status)
    mapfile -t pids < <(get_app_pids)
    if ((${#pids[@]} > 0)) && test_app_health; then
      echo "RUNNING: $APP_URL (PID ${pids[0]})"
    else
      echo "STOPPED"
      exit 1
    fi
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 2
    ;;
esac

#!/usr/bin/env bash
# TrainApp manager — M15 desks only (E21 / G23).
#
#   ./manage.sh Start
#   ./manage.sh Start e21,g23
#   ./manage.sh Stop
#   ./manage.sh Restart e21
#   ./manage.sh Status
#   ./manage.sh Check
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./manage.sh <Start|Stop|Restart|Status|Check> [desks...]

  Start     Start desk Streamlit apps (default: e21 g23)
  Stop      Stop desk apps
  Restart   Stop then start
  Status    Show RUNNING / STOPPED per desk
  Check     Validate desk config (run_desk.py --check)

Desks: e21 g23 all (aliases: eur gbp eur15 gbp15 eurusd gbpusd …)
Env:   MANAGE_TIMEOUT=40  (startup health-check seconds, 5-120)
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ACTION="${1:-Status}"
shift || true

# Case-insensitive actions (Start / ReStart / restart all work).
ACTION="${ACTION,,}"

TIMEOUT_SECONDS="${MANAGE_TIMEOUT:-40}"
APPS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:?--timeout requires a value}"
      shift 2
      ;;
    *)
      APPS+=("$1")
      shift
      ;;
  esac
done

if [[ ${#APPS[@]} -eq 0 ]]; then
  APPS=(e21 g23)
fi

case "$ACTION" in
  start|stop|restart|status|check) ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ ! "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || (( TIMEOUT_SECONDS < 5 || TIMEOUT_SECONDS > 120 )); then
  echo "Invalid timeout: $TIMEOUT_SECONDS (allowed 5-120)" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON=""
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Python not found on PATH" >&2
  exit 1
fi

REQ_FILE="$ROOT/cores/m15/requirements.txt"

ensure_streamlit() {
  if "$PYTHON" -c 'import streamlit' >/dev/null 2>&1; then
    return 0
  fi
  echo "streamlit not installed for: $PYTHON" >&2
  if [[ -f "$REQ_FILE" ]]; then
    echo "Install with: $PYTHON -m pip install -r \"$REQ_FILE\"" >&2
  else
    echo "Install with: $PYTHON -m pip install streamlit" >&2
  fi
  return 1
}

declare -A CATALOG_PORT=(
  [e21]=8911
  [g23]=8931
)
declare -A CATALOG_LABEL=(
  [e21]=E21
  [g23]=G23
)

die() {
  echo "$*" >&2
  exit 1
}

resolve_desk_id() {
  local token="${1,,}"
  token="${token// /}"
  case "$token" in
    all)
      echo "__all__"
      return 0
      ;;
    e31|g33|eur5|gbp5|eurm5|gbpm5|m5e31|m5g33)
      die "M5 desk '$1' is retired. This app only runs M15 desks e21 and g23."
      ;;
    e21|eur15|eurm15|m15e21|eur|eurusd) echo "e21" ;;
    g23|gbp15|gbpm15|m15g23|gbp|gbpusd) echo "g23" ;;
    e21|g23) echo "$token" ;;
    *) die "Unknown desk '$1'. Use e21 g23 or all." ;;
  esac
}

resolve_desk_ids() {
  local -a selected=()
  local raw part id existing
  for raw in "${APPS[@]}"; do
    IFS=',' read -ra parts <<<"${raw// /,}"
    for part in "${parts[@]}"; do
      [[ -z "$part" ]] && continue
      id="$(resolve_desk_id "$part")"
      if [[ "$id" == "__all__" ]]; then
        for id in e21 g23; do
          existing=0
          for s in "${selected[@]:-}"; do
            [[ "$s" == "$id" ]] && existing=1 && break
          done
          (( existing == 0 )) && selected+=("$id")
        done
        continue
      fi
      existing=0
      for s in "${selected[@]:-}"; do
        [[ "$s" == "$id" ]] && existing=1 && break
      done
      (( existing == 0 )) && selected+=("$id")
    done
  done
  ((${#selected[@]} > 0)) || die "No desks selected."
  printf '%s\n' "${selected[@]}"
}

test_app_health() {
  local port="$1"
  local url="http://127.0.0.1:${port}"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 "$url" >/dev/null 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -q -T 2 -O /dev/null "$url" >/dev/null 2>&1
  else
    "$PYTHON" - "$url" <<'PY'
import sys, urllib.request
try:
  urllib.request.urlopen(sys.argv[1], timeout=2)
  raise SystemExit(0)
except Exception:
  raise SystemExit(1)
PY
  fi
}

is_train_app_cmdline() {
  local args="$1"
  [[ "$args" == *"$ROOT"* ]]
}

get_desk_pids() {
  local port="$1"
  local pid args
  {
    while read -r pid args; do
      [[ -z "${pid:-}" ]] && continue
      case "$args" in
        *streamlit*)
          if [[ "$args" == *"--server.port $port"* || "$args" == *"server.port=$port"* ]]; then
            if [[ "$args" == *"$ROOT"* || "$args" == *"LiveCheck/Train/"* || "$args" == *"LiveCheck2/Train/"* ]]; then
              printf '%s\n' "$pid"
            fi
          fi
          ;;
      esac
    done < <(ps -eo pid=,args= 2>/dev/null || true)

    if command -v ss >/dev/null 2>&1; then
      ss -ltnp "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p'
    elif command -v lsof >/dev/null 2>&1; then
      lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
    fi
  } | awk 'NF && !seen[$0]++'
}

stop_desk() {
  local desk_id="$1"
  local port="${CATALOG_PORT[$desk_id]}"
  local label="${CATALOG_LABEL[$desk_id]}"
  local pid
  mapfile -t pids < <(get_desk_pids "$port")
  for pid in "${pids[@]:-}"; do
    [[ -z "$pid" ]] && continue
    echo "Stopping $label PID $pid..."
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    kill -9 "$pid" 2>/dev/null || true
  done
  rm -f "$ROOT/runtime/$desk_id/results/streamlit_app.pid"
  echo "Stopped $label (:$port)"
}

start_desk() {
  local desk_id="$1"
  local port="${CATALOG_PORT[$desk_id]}"
  local label="${CATALOG_LABEL[$desk_id]}"
  local -a pids train_pids existing_pids
  local pid args owner log_file deadline

  mapfile -t pids < <(get_desk_pids "$port")
  train_pids=()
  for pid in "${pids[@]:-}"; do
    [[ -z "$pid" ]] && continue
    args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if is_train_app_cmdline "$args"; then
      train_pids+=("$pid")
    fi
  done

  if ((${#train_pids[@]} > 0)); then
    echo "Already running $label PID ${train_pids[0]} http://127.0.0.1:$port"
    return 0
  fi

  if ((${#pids[@]} > 0)); then
    echo "Releasing port $port from old Train desk..."
    for pid in "${pids[@]}"; do
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
  fi

  echo "==== $label ($desk_id) port $port - Start ===="
  export TRAINAPP_DESK="$desk_id"
  log_file="$ROOT/runtime/$desk_id/results/streamlit_app.log"
  mkdir -p "$(dirname "$log_file")"
  nohup "$PYTHON" "$ROOT/run_desk.py" "$desk_id" --port "$port" \
    >"$log_file" 2>&1 &
  local new_pid=$!

  deadline=$((SECONDS + TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if test_app_health "$port"; then
      echo "App ready: http://127.0.0.1:$port (PID $new_pid)"
      return 0
    fi
    if ! kill -0 "$new_pid" 2>/dev/null; then
      echo "Desk process exited during startup. See $log_file" >&2
      if [[ -f "$log_file" ]]; then
        tail -n 5 "$log_file" >&2 || true
      fi
      return 1
    fi
    sleep 0.5
  done
  echo "Started PID $new_pid but health check timed out - open http://127.0.0.1:$port"
}

show_status() {
  local desk_id="$1"
  local port="${CATALOG_PORT[$desk_id]}"
  local label="${CATALOG_LABEL[$desk_id]}"
  local -a pids train_pids
  local pid args

  mapfile -t pids < <(get_desk_pids "$port")
  train_pids=()
  for pid in "${pids[@]:-}"; do
    [[ -z "$pid" ]] && continue
    args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if is_train_app_cmdline "$args"; then
      train_pids+=("$pid")
    fi
  done

  if ((${#train_pids[@]} > 0)); then
    echo "$label (:$port) RUNNING TrainApp PID ${train_pids[0]}"
  elif ((${#pids[@]} > 0)); then
    echo "$label (:$port) RUNNING old-Train PID ${pids[0]}"
  else
    echo "$label (:$port) STOPPED"
  fi
}

check_desk() {
  local desk_id="$1"
  if ! "$PYTHON" "$ROOT/run_desk.py" "$desk_id" --check; then
    die "Check failed for $desk_id"
  fi
}

mapfile -t SELECTED < <(resolve_desk_ids)
echo "TrainApp manage: ${ACTION^} -> $(IFS=,; echo "${SELECTED[*]}")"

if [[ "$ACTION" == "start" || "$ACTION" == "restart" ]]; then
  ensure_streamlit || exit 1
fi

FAILURES=0
for id in "${SELECTED[@]}"; do
  case "$ACTION" in
    start) start_desk "$id" || FAILURES=$((FAILURES + 1)) ;;
    stop) stop_desk "$id" ;;
    restart)
      stop_desk "$id"
      sleep 1
      start_desk "$id" || FAILURES=$((FAILURES + 1))
      ;;
    status) show_status "$id" ;;
    check) check_desk "$id" || FAILURES=$((FAILURES + 1)) ;;
  esac
done

echo ""
if (( FAILURES > 0 )); then
  echo "Done with $FAILURES failure(s)." >&2
  exit 1
fi
echo "Done."

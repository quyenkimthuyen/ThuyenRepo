#!/usr/bin/env bash
# Fleet manager — start/stop/restart/status every M15 clone under this folder.
#
#   ./manage.sh Status
#   ./manage.sh Start
#   ./manage.sh Stop
#   ./manage.sh Restart
#   ./manage.sh Start M15_RR1
#   ./manage.sh Start RR2 trade
#   ./manage.sh Stop RR1 e21
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./manage.sh <Start|Stop|Restart|Status> [clone-or-app...]

  Start / Stop / Restart / Status   all Streamlit apps under this folder

Filters (optional, mixed):
  clones  M15_RR1 RR1 rr2
  apps    all train trade live e21 g23

Env: MANAGE_TIMEOUT=40   (passed to clone scripts)
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ACTION="${1:-Status}"
shift || true
ACTION="${ACTION,,}"
case "$ACTION" in
  start|stop|restart|status) ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 2
    ;;
esac

TIMEOUT_SECONDS="${MANAGE_TIMEOUT:-40}"
FILTERS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --timeout)
      TIMEOUT_SECONDS="${2:?--timeout requires a value}"
      shift 2
      ;;
    *)
      FILTERS+=("$1")
      shift
      ;;
  esac
done

if [[ ! "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || (( TIMEOUT_SECONDS < 5 || TIMEOUT_SECONDS > 120 )); then
  echo "Invalid timeout: $TIMEOUT_SECONDS (allowed 5-120)" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export MANAGE_TIMEOUT="$TIMEOUT_SECONDS"

WANT_CLONES=()
WANT_APPS=()

map_app() {
  local token="${1,,}"
  case "$token" in
    all) echo all ;;
    train) echo train ;;
    trade|live) echo trade ;;
    e21|eur|eurusd|eur15) echo e21 ;;
    g23|gbp|gbpusd|gbp15) echo g23 ;;
    *) echo "" ;;
  esac
}

for raw in "${FILTERS[@]:-}"; do
  IFS=',' read -ra parts <<<"${raw// /,}"
  for part in "${parts[@]}"; do
    [[ -z "$part" ]] && continue
    mapped="$(map_app "$part")"
    if [[ -n "$mapped" ]]; then
      WANT_APPS+=("$mapped")
    else
      WANT_CLONES+=("$part")
    fi
  done
done
if ((${#WANT_APPS[@]} == 0)); then
  WANT_APPS=(all)
fi

has_app() {
  local want="$1" x
  for x in "${WANT_APPS[@]}"; do
    [[ "$x" == "$want" ]] && return 0
  done
  return 1
}

app_wanted() {
  local kind="$1"
  has_app all && return 0
  case "$kind" in
    train) has_app train || has_app e21 || has_app g23 ;;
    trade) has_app trade ;;
    e21|g23) has_app "$kind" || has_app train ;;
    *) return 1 ;;
  esac
}

train_desk_args() {
  if has_app all || has_app train; then
    echo e21 g23
    return
  fi
  local out=()
  has_app e21 && out+=(e21)
  has_app g23 && out+=(g23)
  echo "${out[*]}"
}

clone_matches() {
  local name="$1"
  ((${#WANT_CLONES[@]} == 0)) && return 0
  local fold="${name,,}"
  local short="$fold"
  [[ "$short" == m15_* ]] && short="${short#m15_}"
  local raw token
  for raw in "${WANT_CLONES[@]}"; do
    token="${raw,,}"
    [[ "$token" == "$fold" || "$token" == "$short" || "$token" == "m15_$short" ]] && return 0
  done
  return 1
}

read_live_port() {
  local path="$1/Trade/shared/constants.py"
  [[ -f "$path" ]] || { echo ""; return 0; }
  awk '/^[[:space:]]*LIVE_APP_PORT[[:space:]]*=/ { gsub(/[^0-9]/, "", $0); print $0; exit }' "$path"
}

discover_clones() {
  local d
  shopt -s nullglob
  for d in "$ROOT"/*/; do
    d="${d%/}"
    if [[ -f "$d/Train/manage.sh" || -f "$d/Trade/live/scripts/run_app_linux.sh" ]]; then
      printf '%s\n' "$d"
    fi
  done
}

mapfile -t ALL_CLONES < <(discover_clones | sort)
CLONES=()
for d in "${ALL_CLONES[@]:-}"; do
  [[ -z "$d" ]] && continue
  name="$(basename "$d")"
  clone_matches "$name" && CLONES+=("$d")
done
if ((${#CLONES[@]} == 0)); then
  echo "No M15 clones matched under $ROOT" >&2
  exit 1
fi

read_desk_port() {
  local yaml="$1/Train/desks/$2.yaml"
  [[ -f "$yaml" ]] || { echo ""; return 0; }
  awk '/^[[:space:]]*port:[[:space:]]*/ { gsub(/[^0-9]/, "", $0); print $0; exit }' "$yaml"
}

port_up() {
  local port="$1" url="http://127.0.0.1:${port}"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 "$url" >/dev/null 2>&1
  else
    return 1
  fi
}

echo "M15 fleet ${ACTION^} -> $(IFS=,; for d in "${CLONES[@]}"; do printf '%s ' "$(basename "$d")"; done)"

if [[ "$ACTION" == "status" ]]; then
  printf "\n%-10s %-10s %-8s %s\n" "CLONE" "APP" "PORT" "STATE"
  printf "%-10s %-10s %-8s %s\n" "-----" "---" "----" "-----"
  for clone in "${CLONES[@]}"; do
    name="$(basename "$clone")"
    if app_wanted train; then
      for desk in e21 g23; do
        app_wanted "$desk" || continue
        p="$(read_desk_port "$clone" "$desk")"
        [[ -n "$p" ]] || continue
        st="STOPPED"
        port_up "$p" && st="RUNNING"
        printf "%-10s %-10s %-8s %s\n" "$name" "train/$desk" "$p" "$st"
      done
    fi
    if app_wanted trade; then
      p="$(read_live_port "$clone")"
      if [[ -n "$p" ]]; then
        st="STOPPED"
        port_up "$p" && st="RUNNING"
        printf "%-10s %-10s %-8s %s\n" "$name" "trade" "$p" "$st"
      fi
    fi
  done
  echo ""
  echo "Done."
  exit 0
fi

FAILURES=0
for clone in "${CLONES[@]}"; do
  name="$(basename "$clone")"
  train_manage="$clone/Train/manage.sh"
  trade_run="$clone/Trade/live/scripts/run_app_linux.sh"

  if [[ -f "$train_manage" ]] && app_wanted train; then
    # shellcheck disable=SC2207
    desks=( $(train_desk_args) )
    if ((${#desks[@]} > 0)); then
      echo ""
      echo "==== $name train (${desks[*]}) ===="
      chmod +x "$train_manage" 2>/dev/null || true
      if ! "$train_manage" "$ACTION" "${desks[@]}"; then
        FAILURES=$((FAILURES + 1))
      fi
    fi
  fi

  if [[ -f "$trade_run" ]] && app_wanted trade; then
    port="$(read_live_port "$clone")"
    [[ -n "$port" ]] || port=8501
    echo ""
    echo "==== $name trade (:$port) ===="
    chmod +x "$trade_run" 2>/dev/null || true
    cap_action="${ACTION^}"
    if ! "$trade_run" "$cap_action" --port "$port" --timeout "$TIMEOUT_SECONDS"; then
      FAILURES=$((FAILURES + 1))
    fi
  fi
done

echo ""
if (( FAILURES > 0 )); then
  echo "Done with $FAILURES failure(s)." >&2
  exit 1
fi
echo "Done."

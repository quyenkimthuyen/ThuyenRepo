#!/usr/bin/env bash
# Manage Streamlit apps for backtestM5 desks (EUR/GBP M5) on Linux.
#
#   ./manage_clones.sh start
#   ./manage_clones.sh stop
#   ./manage_clones.sh restart
#   ./manage_clones.sh status
#   ./manage_clones.sh restart EUR
#   ./manage_clones.sh status all
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-status}"
shift || true

TIMEOUT_SECONDS=30
REQUESTED=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout)
      TIMEOUT_SECONDS="${2:?}"
      shift 2
      ;;
    -h|--help)
      ACTION=help
      shift
      ;;
    *)
      REQUESTED+=("$1")
      shift
      ;;
  esac
done

if [[ ${#REQUESTED[@]} -eq 0 ]]; then
  REQUESTED=(E31 G33)
fi

# key|folder|port|aliases(comma)
CATALOG=(
  "E31|EdgeMinerEURUSDM5|8811|EUR,EURUSD,M5E31,M5"
  "G33|EdgeMinerGBPUSDM5|8831|GBP,GBPUSD,M5G33"
)

norm() {
  echo "$1" | tr '[:lower:]' '[:upper:]' | tr -cd 'A-Z0-9'
}

resolve_keys() {
  local out=() token n key folder port aliases a folder_n matched
  for raw in "$@"; do
    # split on comma
    IFS=',' read -ra parts <<<"$raw"
    for token in "${parts[@]}"; do
      token="$(echo "$token" | xargs)"
      [[ -z "$token" ]] && continue
      n="$(norm "$token")"
      matched=""
      if [[ "$n" == "ALL" ]]; then
        for row in "${CATALOG[@]}"; do
          key="${row%%|*}"
          if [[ ! " ${out[*]-} " =~ " ${key} " ]]; then
            out+=("$key")
          fi
        done
        continue
      fi
      for row in "${CATALOG[@]}"; do
        IFS='|' read -r key folder port aliases <<<"$row"
        folder_n="$(norm "$folder")"
        if [[ "$n" == "$key" || "$n" == "$folder_n" ]]; then
          matched="$key"; break
        fi
        IFS=',' read -ra als <<<"$aliases"
        for a in "${als[@]}"; do
          if [[ "$n" == "$(norm "$a")" ]]; then
            matched="$key"; break 2
          fi
        done
      done
      if [[ -z "$matched" ]]; then
        case "$n" in
          *EUR*) matched="E31" ;;
          *GBP*) matched="G33" ;;
        esac
      fi
      if [[ -z "$matched" ]]; then
        echo "Unknown app '$token'. Use E31, G33, EUR, GBP, or all." >&2
        exit 2
      fi
      if [[ ! " ${out[*]-} " =~ " ${matched} " ]]; then
        out+=("$matched")
      fi
    done
  done
  if [[ ${#out[@]} -eq 0 ]]; then
    echo "No apps selected." >&2
    exit 2
  fi
  printf '%s\n' "${out[@]}"
}

lookup_row() {
  local want="$1" row key
  for row in "${CATALOG[@]}"; do
    key="${row%%|*}"
    if [[ "$key" == "$want" ]]; then
      echo "$row"
      return 0
    fi
  done
  return 1
}

normalize_action() {
  local a
  a="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
  case "$a" in
    start|stop|restart|status) echo "$a" ;;
    help|-h|--help) echo "help" ;;
    *)
      echo "Unknown action '$1'. Use start|stop|restart|status." >&2
      exit 2
      ;;
  esac
}

ACTION="$(normalize_action "$ACTION")"

if [[ "$ACTION" == "help" ]]; then
  cat <<EOF
Usage: $(basename "$0") <start|stop|restart|status> [E31|G33|EUR|GBP|all ...] [--timeout SECONDS]

Desks:
  E31 / EUR  → EdgeMinerEURUSDM5  http://127.0.0.1:8811
  G33 / GBP  → EdgeMinerGBPUSDM5  http://127.0.0.1:8831

Examples:
  $(basename "$0") status
  $(basename "$0") start
  $(basename "$0") restart EUR
  $(basename "$0") stop all
EOF
  exit 0
fi

# Map to Title-case expected by run_app_linux.sh
case "$ACTION" in
  start) RUN_ACTION="Start" ;;
  stop) RUN_ACTION="Stop" ;;
  restart) RUN_ACTION="Restart" ;;
  status) RUN_ACTION="Status" ;;
esac

mapfile -t KEYS < <(resolve_keys "${REQUESTED[@]}")
overall_rc=0

for key in "${KEYS[@]}"; do
  row="$(lookup_row "$key")"
  IFS='|' read -r _ folder port _ <<<"$row"
  runner="$ROOT/$folder/scripts/run_app_linux.sh"
  if [[ ! -x "$runner" && -f "$runner" ]]; then
    chmod +x "$runner" || true
  fi
  if [[ ! -f "$runner" ]]; then
    echo "Missing runner: $runner" >&2
    overall_rc=1
    continue
  fi
  echo ""
  echo "==== ${key} (${folder}) port ${port} — ${RUN_ACTION} ===="
  if ! "$runner" "$RUN_ACTION" --port "$port" --timeout "$TIMEOUT_SECONDS"; then
    # Status returns 1 when stopped — still print, don't abort siblings
    if [[ "$RUN_ACTION" != "Status" ]]; then
      overall_rc=1
    else
      overall_rc=1
    fi
  fi
done

echo ""
if [[ "$RUN_ACTION" == "Status" ]]; then
  if [[ $overall_rc -eq 0 ]]; then
    echo "All selected apps RUNNING."
  else
    echo "One or more selected apps STOPPED."
  fi
else
  echo "Done."
fi
exit "$overall_rc"

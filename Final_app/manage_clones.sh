#!/usr/bin/env bash
# Manage Streamlit apps for Final_app desks (EUR/GBP × M15/M5) on Linux.
#
#   ./manage_clones.sh start
#   ./manage_clones.sh stop
#   ./manage_clones.sh restart
#   ./manage_clones.sh status
#   ./manage_clones.sh restart F1
#   ./manage_clones.sh status M15
#   ./manage_clones.sh start EUR          # both EUR M15 + EUR M5
#   ./manage_clones.sh stop all
#
# DeployEA is Windows-only (manage_clones.ps1 / .cmd).
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
  REQUESTED=(F1 F2 F3 F4)
fi

# key|folder|port|aliases(comma)
CATALOG=(
  "F1|EdgeMinerEURUSDM15|8511|M15F1,EURM15,M15EUR,E15"
  "F2|EdgeMinerGBPUSDM15|8521|M15F2,GBPM15,M15GBP,G15"
  "F3|EdgeMinerEURUSDM5|8531|M5F3,EURM5,M5EUR,E5"
  "F4|EdgeMinerGBPUSDM5|8541|M5F4,GBPM5,M5GBP,G5"
)

norm() {
  echo "$1" | tr '[:lower:]' '[:upper:]' | tr -cd 'A-Z0-9'
}

resolve_keys() {
  local out=() token n key folder port aliases a folder_n matched
  for raw in "$@"; do
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

      # Group shortcuts
      case "$n" in
        M15)
          for key in F1 F2; do
            if [[ ! " ${out[*]-} " =~ " ${key} " ]]; then out+=("$key"); fi
          done
          continue
          ;;
        M5)
          for key in F3 F4; do
            if [[ ! " ${out[*]-} " =~ " ${key} " ]]; then out+=("$key"); fi
          done
          continue
          ;;
        EUR|EURUSD)
          for key in F1 F3; do
            if [[ ! " ${out[*]-} " =~ " ${key} " ]]; then out+=("$key"); fi
          done
          continue
          ;;
        GBP|GBPUSD)
          for key in F2 F4; do
            if [[ ! " ${out[*]-} " =~ " ${key} " ]]; then out+=("$key"); fi
          done
          continue
          ;;
      esac

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
        echo "Unknown app '$token'. Use F1 F2 F3 F4 | M15 M5 | EUR GBP | all." >&2
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
    deployea|deploy)
      echo "DeployEA is Windows-only. Use manage_clones.ps1 DeployEA or manage_clones.cmd DeployEA" >&2
      exit 2
      ;;
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
Usage: $(basename "$0") <start|stop|restart|status> [F1|F2|F3|F4|M15|M5|EUR|GBP|all ...] [--timeout SECONDS]

Desks (Final_app):
  F1 / M15F1 / EURM15  → EdgeMinerEURUSDM15  http://127.0.0.1:8511
  F2 / M15F2 / GBPM15  → EdgeMinerGBPUSDM15  http://127.0.0.1:8521
  F3 / M5F3  / EURM5   → EdgeMinerEURUSDM5   http://127.0.0.1:8531
  F4 / M5F4  / GBPM5   → EdgeMinerGBPUSDM5   http://127.0.0.1:8541

Groups:
  M15 → F1 F2 | M5 → F3 F4 | EUR → F1 F3 | GBP → F2 F4 | all → four desks

Examples:
  $(basename "$0") status
  $(basename "$0") start
  $(basename "$0") restart F3
  $(basename "$0") stop M15
  $(basename "$0") start EUR

Windows DeployEA: .\\manage_clones.ps1 DeployEA   (or manage_clones.cmd)
EOF
  exit 0
fi

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
    overall_rc=1
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

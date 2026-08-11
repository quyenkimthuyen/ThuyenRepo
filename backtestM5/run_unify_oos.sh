#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python}"
echo "==== EUR unify OOS ===="
"$PY" "$ROOT/EdgeMinerEURUSDM5/scripts/unify_oos_compare.py" "$@"
echo "==== GBP unify OOS ===="
"$PY" "$ROOT/EdgeMinerGBPUSDM5/scripts/unify_oos_compare.py" "$@"
echo "Done."

#!/usr/bin/env bash
# Unify OOS + re-score Trade Models on both M15 desks (2026-01-01 → 2026-08-07).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python}"

echo "==== EUR M15 unify OOS ===="
"$PY" "$ROOT/EdgeMinerEURUSDM15/scripts/unify_oos_compare.py" "$@"
echo "==== GBP M15 unify OOS ===="
"$PY" "$ROOT/EdgeMinerGBPUSDM15/scripts/unify_oos_compare.py" "$@"
echo "Done. See */results/research/m15_oos_unified/"

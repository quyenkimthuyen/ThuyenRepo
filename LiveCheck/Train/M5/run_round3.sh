#!/usr/bin/env bash
# Run Round-3 ensemble + monthly stability on EUR then GBP.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python}"

echo "==== EUR Round-3 ===="
"$PY" "$ROOT/EdgeMinerEURUSDM5/scripts/round3_ensemble_monthly.py" "$@"
echo "==== GBP Round-3 ===="
"$PY" "$ROOT/EdgeMinerGBPUSDM5/scripts/round3_ensemble_monthly.py" "$@"
echo "Done. See results/research/m5_round3_ensemble/ on each desk."

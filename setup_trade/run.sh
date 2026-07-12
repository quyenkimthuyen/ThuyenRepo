#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f data/market/eurusd_h1.csv ]]; then
  echo "Fetching EURUSD H1 data..."
  python3 scripts/fetch_data.py
fi

echo "Setup Trade → http://127.0.0.1:8767"
exec python3 -m uvicorn backend.api.app:app --host 0.0.0.0 --port 8767 --reload

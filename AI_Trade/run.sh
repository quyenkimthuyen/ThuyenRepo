#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f data/eurusd_h1.csv ]]; then
  echo "Fetching EURUSD H1 data..."
  python3 scripts/fetch_data.py
fi

echo "Starting AI Trade Lab at http://127.0.0.1:8766"
exec python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8766 --reload

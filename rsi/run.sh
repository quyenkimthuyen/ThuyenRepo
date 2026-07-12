#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

DATA_LINK="data/EURUSD_H1.json"
FOREX_DATA="../Forex/data/defaults/EURUSD_H1.json"

if [[ ! -f "$DATA_LINK" && -f "$FOREX_DATA" ]]; then
  ln -sf "$FOREX_DATA" "$DATA_LINK"
  echo "Linked $DATA_LINK → $FOREX_DATA"
fi

if [[ ! -f "$DATA_LINK" ]]; then
  echo "Missing EURUSD H1 data. Run: cd ../Forex && python3 scripts/fetch-default-data.py"
  exit 1
fi

if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies…"
  pip install -q -r requirements.txt
fi

PORT="${PORT:-8777}"
echo "RSI Zone Analyzer → http://127.0.0.1:${PORT}"
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" --reload

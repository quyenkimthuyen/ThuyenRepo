#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
exec .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port "${E2E_BACKEND_PORT:-18765}"

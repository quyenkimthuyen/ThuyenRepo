#!/usr/bin/env bash
# Chạy toàn bộ automated tests
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0

echo "=== PronounceLab Test Suite ==="
echo ""

# Backend
echo ">> Backend (pytest)"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt
else
  .venv/bin/pip install -q -r requirements-dev.txt 2>/dev/null || true
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARN: ffmpeg not found — some tests may skip"
fi

if ! .venv/bin/pytest tests/ -v --tb=short; then
  FAILED=1
fi

echo ""

# Frontend
echo ">> Frontend (node --test)"
cd "$ROOT/frontend"
if ! node --test tests/*.test.mjs; then
  FAILED=1
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "=== ALL TESTS PASSED ==="
  exit 0
else
  echo "=== SOME TESTS FAILED ==="
  exit 1
fi

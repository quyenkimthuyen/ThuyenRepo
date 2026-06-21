#!/usr/bin/env bash
# Chạy toàn bộ automated tests
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
RUN_E2E="${RUN_E2E:-1}"

echo "=== PronounceLab Test Suite ==="
echo ""

# Backend unit tests
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

# Frontend unit tests
echo ">> Frontend unit (node --test)"
cd "$ROOT/frontend"
if ! node --test tests/*.test.mjs; then
  FAILED=1
fi

echo ""

# Integration frontend ↔ backend
echo ">> Integration (frontend → backend HTTP)"
if ! node --test tests/integration/*.test.mjs; then
  FAILED=1
fi

echo ""

# E2E Playwright (Chrome + Edge)
if [ "$RUN_E2E" = "1" ]; then
  echo ">> E2E (Playwright — Chrome & Edge)"
  cd "$ROOT/frontend"

  if [ ! -d node_modules/@playwright/test ]; then
    echo "    Installing npm dev dependencies..."
    npm install --no-audit --no-fund
  fi

  chmod +x "$ROOT/scripts/start_test_backend.sh"

  echo "    Installing Chromium for Playwright..."
  npx playwright install chromium --with-deps 2>/dev/null || npx playwright install chromium || true

  if ! npx playwright test --project=chromium; then
    FAILED=1
  fi

  if npx playwright install msedge 2>/dev/null; then
    echo "    Running Edge E2E..."
    if ! npx playwright test --project=msedge; then
      FAILED=1
    fi
  else
    echo "WARN: Microsoft Edge chưa cài — bỏ qua E2E Edge (chạy: npx playwright install msedge)"
  fi
else
  echo ">> E2E skipped (RUN_E2E=0)"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "=== ALL TESTS PASSED ==="
  exit 0
else
  echo "=== SOME TESTS FAILED ==="
  exit 1
fi

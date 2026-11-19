#!/usr/bin/env bash
# Run under Git Bash or WSL on Windows.
#
# Prerequisites:
#   uv run --with playwright python -c "from playwright.sync_api import sync_playwright"
#   uv run playwright install chromium  (downloads ~130 MB)
#   Optional: vhs (https://github.com/charmbracelet/vhs) for GIF recording
#   Optional: asciinema + agg (https://github.com/asciinema/agg) as fallback
#
# Usage:
#   bash scripts/record_demo.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo "Cleaning up background processes…"
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

wait_for_port() {
  local port=$1
  local desc=${2:-"port $port"}
  echo "Waiting for $desc…"
  for i in $(seq 30); do
    if nc -z localhost "$port" 2>/dev/null; then
      echo "  $desc ready."
      return 0
    fi
    # curl fallback if nc is unavailable
    if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
      echo "  $desc ready (via curl)."
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $desc did not become available within 30 s" >&2
  exit 1
}

check_playwright() {
  if ! cd "$REPO_ROOT/backend" && uv run python -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
    echo "ERROR: playwright is not installed in the backend venv." >&2
    echo "  Run: cd backend && uv sync && uv run playwright install chromium" >&2
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# 1. Populate the DB with demo traces
# ---------------------------------------------------------------------------
echo "=== Step 1: populating demo traces ==="
cd "$REPO_ROOT"
just demo

# ---------------------------------------------------------------------------
# 2. Start the FastAPI backend
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 2: starting backend ==="
cd "$REPO_ROOT/backend"
uv run uvicorn app.main:app --port 8000 &
BACKEND_PID=$!
wait_for_port 8000 "FastAPI backend"

# ---------------------------------------------------------------------------
# 3. Start the Next.js frontend
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 3: starting frontend ==="
cd "$REPO_ROOT/frontend"
pnpm dev &
FRONTEND_PID=$!
wait_for_port 3000 "Next.js frontend"

# ---------------------------------------------------------------------------
# 4. Capture screenshot via Playwright
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 4: capturing screenshot ==="
check_playwright
cd "$REPO_ROOT/backend"
uv run python "$REPO_ROOT/scripts/screenshot.py"
echo "  Saved: docs/screenshot.png"

# ---------------------------------------------------------------------------
# 5. Record GIF (vhs preferred, asciinema+ffmpeg fallback)
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 5: recording demo GIF ==="
cd "$REPO_ROOT"

if command -v vhs >/dev/null 2>&1; then
  echo "  Using vhs…"
  vhs scripts/demo.tape
  echo "  Saved: docs/demo.gif"
elif command -v asciinema >/dev/null 2>&1 && command -v agg >/dev/null 2>&1; then
  # agg (https://github.com/asciinema/agg) converts .cast → GIF natively.
  # ffmpeg cannot read asciinema .cast files — it is not a media stream.
  echo "  vhs not found — using asciinema + agg…"
  CAST_FILE=$(mktemp /tmp/demo-XXXX.cast)
  asciinema rec --overwrite --command "bash -c 'echo \"just demo\" && sleep 1 && echo \"# Open http://localhost:3000\" && sleep 2'" "$CAST_FILE"
  agg --cols 120 --rows 30 "$CAST_FILE" docs/demo.gif
  echo "  Saved: docs/demo.gif"
else
  echo "  WARNING: neither vhs nor asciinema+agg found — keeping placeholder docs/demo.gif"
fi

echo ""
echo "=== Done ==="
echo "  docs/screenshot.png  — waterfall timeline screenshot"
echo "  docs/demo.gif        — terminal recording (placeholder if tools missing)"

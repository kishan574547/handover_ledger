#!/usr/bin/env bash
# scripts/dev.sh - Development server startup for Linux / macOS
set -e

PORT=${1:-8000}
HOST=${HOST:-0.0.0.0}
STABLE=${STABLE:-0}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Detect if port is occupied
if command -v lsof >/dev/null 2>&1; then
    PID=$(lsof -ti tcp:"$PORT" || true)
    if [ -n "$PID" ]; then
        echo "WARNING: Port $PORT is occupied by PID(s): $PID"
        echo "Please terminate the process before starting: kill -9 $PID"
        exit 1
    fi
elif command -v netstat >/dev/null 2>&1; then
    if netstat -tuln | grep -q ":$PORT "; then
        echo "WARNING: Port $PORT is currently occupied."
        exit 1
    fi
fi

if [ "$STABLE" = "1" ]; then
    echo "==> Starting HandoverLedger Backend in STABLE mode (no reload) on http://localhost:$PORT..."
    python -m uvicorn backend.main:app --host "$HOST" --port "$PORT"
else
    echo "==> Starting HandoverLedger Backend in DEV mode (auto-reload backend/ only) on http://localhost:$PORT..."
    python -m uvicorn backend.main:app --host "$HOST" --port "$PORT" \
        --reload \
        --reload-dir backend \
        --reload-exclude "data" \
        --reload-exclude "*.db*" \
        --reload-exclude "*.sqlite*" \
        --reload-exclude "*.log*" \
        --reload-exclude "uploads"
fi


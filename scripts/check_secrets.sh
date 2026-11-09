#!/usr/bin/env bash
# check_secrets.sh - Check repository for exposed secrets and staged .env files

set -euo pipefail

echo "==> Checking for staged .env files..."
staged_envs=$(git diff --cached --name-only | grep -E "(^|/)\.env($|\..*)" | grep -v "\.env\.example" || true)

if [ -n "$staged_envs" ]; then
    echo "ERROR: Attempting to commit .env file(s):"
    echo "$staged_envs"
    exit 1
fi

echo "==> Checking for secret patterns in tracked & staged files (excluding backend/demo_data)..."

# Patterns to detect: AIza..., ghp_..., sk-..., password=...
# We exclude backend/demo_data, scripts/check_secrets.*, node_modules, .git
FAILED=0

# Check git-tracked files
FILES=$(git ls-files | grep -v "^backend/demo_data/" | grep -v "^scripts/check_secrets\." | grep -v "\.env\.example$" || true)

for pattern in "AIza[0-9A-Za-z_\\-]{15,}" "ghp_[0-9A-Za-z]{15,}" "sk-[0-9A-Za-z]{15,}" "password\s*=\s*['\"][^'\"]+['\"]"; do
    if [ -n "$FILES" ]; then
        MATCHES=$(grep -EIn "$pattern" $FILES 2>/dev/null || true)
        if [ -n "$MATCHES" ]; then
            echo "ERROR: Suspicious pattern '$pattern' found outside backend/demo_data:"
            echo "$MATCHES"
            FAILED=1
        fi
    fi
done

if [ $FAILED -ne 0 ]; then
    echo "Secret check FAILED! Please remove sensitive tokens."
    exit 1
fi

echo "==> Secret check PASSED. No secrets found."
exit 0


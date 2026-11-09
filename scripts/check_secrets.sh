#!/usr/bin/env bash
# check_secrets.sh - Check repository and full git history for exposed secrets
# Guarantees that real secrets are NEVER printed to stdout or committed.

set -euo pipefail

echo "======================================================"
echo " HandoverLedger Full Secrets & History Scanner"
echo "======================================================"

FAILED=0

# 1. Check for staged .env files
echo "==> 1. Checking for staged .env files..."
staged_envs=$(git diff --cached --name-only | grep -E "(^|/)\.env($|\..*)" | grep -v "\.env\.example" || true)

if [ -n "$staged_envs" ]; then
    echo "ERROR: Attempting to commit staged .env file(s):"
    echo "$staged_envs"
    FAILED=1
else
    echo "    OK: No staged .env files."
fi

# 2. Check full git history for any committed .env files
echo "==> 2. Checking full git history for committed .env files..."
history_envs=$(git log --all --name-only --format="COMMIT:%H" | grep -E "(^|/)\.env($|\..*)" | grep -v "\.env\.example" || true)

if [ -n "$history_envs" ]; then
    echo "ERROR: Found committed .env file(s) in git history:"
    echo "$history_envs"
    FAILED=1
else
    echo "    OK: No .env files in git history."
fi

# 3. Check tracked files in working directory
echo "==> 3. Checking tracked files in working directory..."
TRACKED_FILES=$(git ls-files | grep -v "^backend/demo_data/" \
                             | grep -v "^backend/tests/" \
                             | grep -v "^scripts/check_secrets\." \
                             | grep -v "^backend/sanitizer\.py" \
                             | grep -v "^backend/gemini_client\.py" \
                             | grep -v "^frontend/src/utils/sanitize\.ts" \
                             | grep -v "\.env\.example$" || true)

PATTERNS=(
    "AIza[0-9A-Za-z_\-]{35}"
    "ghp_[0-9A-Za-z]{20,}"
    "github_pat_[0-9A-Za-z_]{20,}"
    "sk-[a-zA-Z0-9_\-]{20,}"
    "postgres(ql)?:\/\/[^\s:@\/]+:[^\s@\/]+@"
)

for pattern in "${PATTERNS[@]}"; do
    if [ -n "$TRACKED_FILES" ]; then
        MATCH_FILES=$(grep -EInl "$pattern" $TRACKED_FILES 2>/dev/null || true)
        if [ -n "$MATCH_FILES" ]; then
            echo "ERROR: Forbidden secret pattern detected in tracked file(s)!"
            echo "Pattern: $pattern"
            echo "Files:"
            for f in $MATCH_FILES; do
                echo "  - $f [MATCH DETECTED - CONTENT REDACTED]"
            done
            FAILED=1
        fi
    fi
done

if [ $FAILED -eq 0 ]; then
    echo "    OK: No secrets found in tracked files."
fi

# 4. Check full git history across all commits and branches
echo "==> 4. Scanning full git history across all commits and branches..."
EXCLUDES=(
    ":(exclude)backend/demo_data"
    ":(exclude)backend/tests"
    ":(exclude)scripts/check_secrets.sh"
    ":(exclude)scripts/check_secrets.ps1"
    ":(exclude)backend/sanitizer.py"
    ":(exclude)backend/gemini_client.py"
    ":(exclude)frontend/src/utils/sanitize.ts"
    ":(exclude)*.env.example"
)

for pattern in "${PATTERNS[@]}"; do
    MATCHING_COMMITS=$(git log --all --format="%H %s" -G"$pattern" -- "${EXCLUDES[@]}" 2>/dev/null || true)
    
    if [ -n "$MATCHING_COMMITS" ]; then
        echo "ERROR: Secret pattern '$pattern' was detected in git commit history!"
        echo "Matching commits (content redacted for security):"
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            echo "  - $line"
        done <<< "$MATCHING_COMMITS"
        FAILED=1
    fi
done

echo "------------------------------------------------------"
if [ $FAILED -ne 0 ]; then
    echo "Result: Secret check FAILED! Please sanitize identified commits/files."
    exit 1
fi

echo "Result: Secret check PASSED! Full git history is clean."
exit 0

# check_secrets.ps1 - PowerShell script to check repository & git history for secrets
# Guarantees that real secrets are NEVER printed to stdout or committed.

$failed = $false

Write-Host "======================================================"
Write-Host " HandoverLedger Full Secrets & History Scanner"
Write-Host "======================================================"

# 1. Staged .env files
Write-Host "==> 1. Checking for staged .env files..."
$staged = git diff --cached --name-only
$badEnvs = $staged | Where-Object { $_ -match '(^|/)\.env($|\..*)' -and $_ -notmatch '\.env\.example$' }
if ($badEnvs) {
    Write-Error "ERROR: Attempting to commit .env file(s): $($badEnvs -join ', ')"
    $failed = $true
} else {
    Write-Host "    OK: No staged .env files."
}

# 2. History .env files
Write-Host "==> 2. Checking full git history for committed .env files..."
$historyEnvs = git log --all --name-only --format="COMMIT:%H" | Where-Object { $_ -match '(^|/)\.env($|\..*)' -and $_ -notmatch '\.env\.example$' }
if ($historyEnvs) {
    Write-Error "ERROR: Found committed .env file(s) in git history: $($historyEnvs -join ', ')"
    $failed = $true
} else {
    Write-Host "    OK: No .env files in git history."
}

# 3. Tracked files in working directory
Write-Host "==> 3. Checking tracked files in working directory..."
$tracked = git ls-files | Where-Object { 
    $_ -notlike 'backend/demo_data/*' -and 
    $_ -notlike 'backend/tests/*' -and 
    $_ -notlike 'scripts/check_secrets.*' -and 
    $_ -notlike 'scripts/verify_*' -and 
    $_ -notlike 'backend/sanitizer.py' -and 
    $_ -notlike 'backend/gemini_client.py' -and 
    $_ -notlike 'frontend/src/utils/sanitize.ts' -and 
    $_ -notlike '*.env.example' 
}

$patterns = @(
    'AIza[0-9A-Za-z_\-]{35}',
    'ghp_[0-9A-Za-z]{20,}',
    'github_pat_[0-9A-Za-z_]{20,}',
    'sk-[a-zA-Z0-9_\-]{20,}',
    'postgres(ql)?:\/\/[^\s:@\/]+:[^\s@\/]+@'
)

foreach ($file in $tracked) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        foreach ($pat in $patterns) {
            if ($content -match $pat) {
                Write-Host "ERROR: Secret pattern '$pat' found in $file [MATCH DETECTED - CONTENT REDACTED]" -ForegroundColor Red
                $failed = $true
            }
        }
    }
}

if (-not $failed) {
    Write-Host "    OK: No secrets found in tracked files."
}

# 4. Check full git history
Write-Host "==> 4. Scanning full git history across all commits and branches..."
$excludes = @(
    ':(exclude)backend/demo_data',
    ':(exclude)backend/tests',
    ':(exclude)scripts/check_secrets.sh',
    ':(exclude)scripts/check_secrets.ps1',
    ':(exclude)scripts/verify_non_demo_run.py',
    ':(exclude)backend/sanitizer.py',
    ':(exclude)backend/gemini_client.py',
    ':(exclude)frontend/src/utils/sanitize.ts',
    ':(exclude)*.env.example'
)

foreach ($pat in $patterns) {
    $commits = git log --all --format="%H %s" -G"$pat" -- $excludes
    if ($commits) {
        Write-Host "ERROR: Secret pattern '$pat' detected in git commit history! Commits (redacted):" -ForegroundColor Red
        $commits | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
        $failed = $true
    }
}

Write-Host "------------------------------------------------------"
if ($failed) {
    Write-Error "Result: Secret check FAILED! Please sanitize identified commits/files."
    exit 1
}

Write-Host "Result: Secret check PASSED! Full git history is clean." -ForegroundColor Green
exit 0

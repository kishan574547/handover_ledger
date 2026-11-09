# check_secrets.ps1 - PowerShell script to check for exposed secrets and staged .env files

Write-Host "==> Checking for staged .env files..."
$staged = git diff --cached --name-only
$badEnvs = $staged | Where-Object { $_ -match '(^|/)\.env($|\..*)' -and $_ -notmatch '\.env\.example$' }

if ($badEnvs) {
    Write-Error "ERROR: Attempting to commit .env file(s): $($badEnvs -join ', ')"
    exit 1
}

Write-Host "==> Checking for secret patterns in tracked files (excluding backend/demo_data)..."
$tracked = git ls-files | Where-Object { 
    $_ -notlike 'backend/demo_data/*' -and 
    $_ -notlike 'scripts/check_secrets.*' -and 
    $_ -notlike '*.env.example' 
}

$patterns = @(
    'AIza[0-9A-Za-z_\-]{15,}',
    'ghp_[0-9A-Za-z]{15,}',
    'sk-[0-9A-Za-z]{15,}',
    'password\s*=\s*[''"][^''"]+[''"]'
)

$failed = $false
foreach ($file in $tracked) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        foreach ($pat in $patterns) {
            if ($content -match $pat) {
                Write-Error "ERROR: Pattern '$pat' found in $file"
                $failed = $true
            }
        }
    }
}

if ($failed) {
    Write-Error "Secret check FAILED! Please remove sensitive tokens."
    exit 1
}

Write-Host "==> Secret check PASSED. No secrets found."
exit 0

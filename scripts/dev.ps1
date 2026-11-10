# scripts/dev.ps1 - Development server startup for Windows
param (
    [int]$Port = 8000,
    [string]$HostAddress = "0.0.0.0",
    [switch]$Stable = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==> Checking if port $Port is occupied..." -ForegroundColor Cyan
try {
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        Write-Warning "Port $Port is currently occupied by process(es): $($pids -join ', ')."
        Write-Host "Please close the existing process or terminate it using: Stop-Process -Id $($pids -join ', ') -Force" -ForegroundColor Yellow
        exit 1
    }
} catch {
    # If Get-NetTCPConnection fails or is restricted, proceed gracefully
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

# Ensure python is available
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not found in PATH."
    exit 1
}

if ($Stable) {
    Write-Host "==> Starting HandoverLedger Backend in STABLE mode (no reload) on http://localhost:$Port..." -ForegroundColor Green
    python -m uvicorn backend.main:app --host $HostAddress --port $Port
} else {
    Write-Host "==> Starting HandoverLedger Backend in DEV mode (auto-reload backend/ only) on http://localhost:$Port..." -ForegroundColor Green
    python -m uvicorn backend.main:app --host $HostAddress --port $Port --reload --reload-dir backend --reload-exclude "data" --reload-exclude "*.db*" --reload-exclude "*.sqlite*" --reload-exclude "*.log*" --reload-exclude "uploads"
}


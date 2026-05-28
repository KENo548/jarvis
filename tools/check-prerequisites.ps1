# =============================================================================
# JARVIS Host Prerequisites Check
# =============================================================================
# Verifies Node.js 20+, Python 3.11+, and Docker Desktop are installed.
# Run: powershell -ExecutionPolicy Bypass -File tools/check-prerequisites.ps1
# =============================================================================

$ErrorActionPreference = "Continue"
$allPassed = $true

Write-Host "=== JARVIS Prerequisites Check ===" -ForegroundColor Cyan
Write-Host ""

# --- Node.js ---
Write-Host "[1/3] Checking Node.js..." -ForegroundColor Yellow
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    $nodeVersion = & node --version 2>&1
    $nodeMajor = [int]($nodeVersion -replace 'v','' -split '\.' | Select-Object -First 1)
    if ($nodeMajor -ge 20) {
        Write-Host "  PASS: Node.js $nodeVersion (>= 20 required)" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: Node.js $nodeVersion found, but 20+ required" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "  FAIL: Node.js not found. Install from https://nodejs.org" -ForegroundColor Red
    $allPassed = $false
}

# --- Python ---
Write-Host "[2/3] Checking Python..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
if ($pythonCmd) {
    $pythonVersion = & python --version 2>&1
    $pythonParts = ($pythonVersion -split ' ' | Select-Object -Last 1) -split '\.'
    $pythonMajor = [int]$pythonParts[0]
    $pythonMinor = [int]$pythonParts[1]
    if ($pythonMajor -eq 3 -and $pythonMinor -ge 11) {
        Write-Host "  PASS: $pythonVersion (>= 3.11 required)" -ForegroundColor Green
    } elseif ($pythonMajor -gt 3) {
        Write-Host "  PASS: $pythonVersion (>= 3.11 required)" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: $pythonVersion found, but 3.11+ required" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "  FAIL: Python not found. Install from https://python.org" -ForegroundColor Red
    $allPassed = $false
}

# --- Docker ---
Write-Host "[3/3] Checking Docker..." -ForegroundColor Yellow
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    $dockerVersion = & docker --version 2>&1
    Write-Host "  PASS: $dockerVersion" -ForegroundColor Green

    # Check if Docker daemon is running
    $dockerInfo = & docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PASS: Docker daemon is running" -ForegroundColor Green
    } else {
        Write-Host "  WARN: Docker installed but daemon not running. Start Docker Desktop." -ForegroundColor Yellow
    }
} else {
    Write-Host "  FAIL: Docker not found. Install Docker Desktop from https://docker.com" -ForegroundColor Red
    $allPassed = $false
}

# --- Summary ---
Write-Host ""
if ($allPassed) {
    Write-Host "=== All prerequisites met ===" -ForegroundColor Green
} else {
    Write-Host "=== Some prerequisites missing ===" -ForegroundColor Red
    Write-Host "Install the missing tools above, then re-run this script." -ForegroundColor Yellow
    exit 1
}

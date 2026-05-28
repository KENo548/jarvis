# =============================================================================
# JARVIS Secrets Setup — Free-tier secrets management via OS keyring
# =============================================================================
# Installs the keyring library and stores initial placeholder secrets.
# Uses Windows Credential Locker / macOS Keychain / Linux Secret Service.
# No subscription, no third-party service required.
#
# Run: powershell -ExecutionPolicy Bypass -File tools/setup-secrets.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=== JARVIS Secrets Setup (Free-Tier) ===" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Ensure keyring is installed ---
Write-Host "[1/3] Checking keyring library..." -ForegroundColor Yellow
$keyringCheck = python -c "import keyring; print('OK')" 2>&1
if ($keyringCheck -ne "OK") {
    Write-Host "  Installing keyring..." -ForegroundColor Yellow
    python -m pip install keyring -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to install keyring. Run: python -m pip install keyring" -ForegroundColor Red
        exit 1
    }
    Write-Host "  keyring installed." -ForegroundColor Green
} else {
    Write-Host "  keyring already installed." -ForegroundColor Green
}

# --- Step 2: Check which backend is active ---
Write-Host "`n[2/3] Checking keyring backend..." -ForegroundColor Yellow
$backendInfo = python -c "import keyring; print(type(keyring.get_keyring()).__name__)" 2>&1
Write-Host "  Active backend: $backendInfo" -ForegroundColor Green

# --- Step 3: Store placeholder secrets ---
Write-Host "`n[3/3] Storing initial secret placeholders..." -ForegroundColor Yellow
$secretsDir = Join-Path (Split-Path $PSScriptRoot -Parent) "security"

function Set-JarvisSecret {
    param($Service, $Key, $DefaultValue)
    $existing = python -c "import keyring; v=keyring.get_password('jarvis/$Service','$Key'); print(v or '')" 2>&1
    if ($existing) {
        Write-Host "  $Service/$Key already set (not overwriting)" -ForegroundColor Green
    } else {
        python -c "import keyring; keyring.set_password('jarvis/$Service','$Key','$DefaultValue')"
        Write-Host "  $Service/$Key = (placeholder — replace with real value)" -ForegroundColor Yellow
    }
}

Set-JarvisSecret "api" "anthropic_key" "TO_BE_SET"
Set-JarvisSecret "api" "github_token" "TO_BE_SET"
Set-JarvisSecret "monitoring" "grafana_password" "TO_BE_SET"
Set-JarvisSecret "database" "neo4j_password" "jarvis-neo4j"

Write-Host "`n=== Secrets Setup Complete ===" -ForegroundColor Cyan
Write-Host "Secrets are stored in your OS credential store:" -ForegroundColor Green
Write-Host "  Windows: Windows Credential Locker" -ForegroundColor White
Write-Host "  macOS:   Keychain" -ForegroundColor White
Write-Host "  Linux:   Secret Service (GNOME Keyring)" -ForegroundColor White
Write-Host ""
Write-Host "To set a real value:" -ForegroundColor Yellow
Write-Host "  python tools/secrets_client.py set api anthropic_key YOUR_KEY" -ForegroundColor White
Write-Host ""
Write-Host "To retrieve:" -ForegroundColor Yellow
Write-Host "  python tools/secrets_client.py get api anthropic_key" -ForegroundColor White

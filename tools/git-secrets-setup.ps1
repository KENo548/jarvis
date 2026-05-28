# =============================================================================
# JARVIS Git Secrets Setup - PowerShell version
# =============================================================================
# Configures git-secrets hooks across all repos to prevent accidental
# commits of API keys, passwords, and secrets.
#
# Uses gitleaks as the primary scanner (cross-platform, works on Windows).
# =============================================================================

Write-Host "[Git Secrets Setup] Installing gitleaks..." -ForegroundColor Yellow

# Check if gitleaks is installed
$gitleaksPath = Get-Command "gitleaks" -ErrorAction SilentlyContinue
if (-not $gitleaksPath) {
    Write-Host "  gitleaks not found. Installing via winget..." -ForegroundColor Yellow
    try {
        winget install gitleaks --silent 2>$null
        Write-Host "  [OK] gitleaks installed" -ForegroundColor Green
    } catch {
        Write-Host "  [INFO] Could not auto-install gitleaks." -ForegroundColor Yellow
        Write-Host "  [INFO] Install manually:" -ForegroundColor Yellow
        Write-Host "  1. Download from: https://github.com/gitleaks/gitleaks/releases" -ForegroundColor Yellow
        Write-Host "  2. Add gitleaks.exe to your PATH" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [OK] gitleaks already installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "[Git Secrets Setup] Installing git hooks..." -ForegroundColor Yellow

$repoDir = Join-Path -Path $PSScriptRoot -ChildPath "..\github-repos"

# Install pre-commit hook for the main project
$projectDir = Resolve-Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$hooksDir = Join-Path -Path $projectDir -ChildPath ".git\hooks"

if (Test-Path -LiteralPath (Join-Path -Path $projectDir -ChildPath ".git")) {
    $hookContent = @'
#!/usr/bin/env bash
# JARVIS gitleaks pre-commit hook
gitleaks detect --source . --verbose --no-git 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: gitleaks detected secrets in staged changes."
    echo "Remove or replace secrets before committing."
    exit 1
fi
'@
    $hookPath = Join-Path -Path $hooksDir -ChildPath "pre-commit"
    if (-not (Test-Path -LiteralPath $hookPath)) {
        Set-Content -LiteralPath $hookPath -Value $hookContent
        Write-Host "  [OK] pre-commit hook installed in project" -ForegroundColor Green
    } else {
        Write-Host "  [OK] pre-commit hook already exists" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[Git Secrets Setup] Complete!" -ForegroundColor Cyan
Write-Host "  Secrets will now be scanned before every commit." -ForegroundColor Cyan

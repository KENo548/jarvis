# JARVIS Sync — Git-Aware Helper (Windows)
# Usage: .\scripts\sync.ps1 [pull|push|status]
#
# This is NOT file synchronization.
# It uses Git as the sync layer between PC and Oracle.

param(
    [string]$Mode = "status"
)

$ErrorActionPreference = "Stop"
$JarvisDir = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent

Set-Location $JarvisDir

function Check-Uncommitted {
    $changes = git diff --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Uncommitted changes in working tree" -ForegroundColor Yellow
        git diff --stat
        return $false
    }
    $staged = git diff --cached --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Staged but uncommitted changes" -ForegroundColor Yellow
        git diff --cached --stat
        return $false
    }
    return $true
}

switch ($Mode) {
    "status" {
        Write-Host "=== JARVIS Git Status ===" -ForegroundColor Cyan
        git status
        Write-Host ""
        Write-Host "=== Remote Status ===" -ForegroundColor Cyan
        git fetch --dry-run 2>&1
    }
    "pull" {
        Write-Host "=== JARVIS Git Pull ===" -ForegroundColor Cyan
        if (-not (Check-Uncommitted)) {
            Write-Host "ABORT: Commit or stash changes before pulling" -ForegroundColor Red
            exit 1
        }
        git fetch
        git status
        Write-Host ""
        Write-Host "Ready to pull. Run: git pull" -ForegroundColor Green
    }
    "push" {
        Write-Host "=== JARVIS Git Push ===" -ForegroundColor Cyan
        if (-not (Check-Uncommitted)) {
            Write-Host "ABORT: Commit changes before pushing" -ForegroundColor Red
            exit 1
        }
        git status
        Write-Host ""
        Write-Host "Ready to push. Run: git push" -ForegroundColor Green
    }
    default {
        Write-Host "Usage: .\scripts\sync.ps1 [pull|push|status]"
        exit 1
    }
}

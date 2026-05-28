# =============================================================================
# JARVIS Daily Health Check
# =============================================================================
# Run this daily to verify the ecosystem is healthy.
# Add to Task Scheduler for automatic daily runs.
#
# Usage:  powershell -ExecutionPolicy Bypass -File daily-health-check.ps1
# =============================================================================

param(
    [string]$LogDir = "..\logs"
)

$logFile = Join-Path -Path $PSScriptRoot -ChildPath "$LogDir\health-check.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  JARVIS Daily Health Check - $timestamp" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$issues = 0
$checks = 0

# === Check 1: SQLite Database ===
$checks++
$dbPath = Join-Path -Path $PSScriptRoot -ChildPath "..\memory\sqlite\jarvis.db"
if (Test-Path -LiteralPath $dbPath) {
    try {
        $conn = New-Object System.Data.SQLite.SQLiteConnection
        $conn.ConnectionString = "Data Source=$dbPath"
        $conn.Open()

        # Check system status
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT value FROM system_control WHERE key = 'kill_switch'"
        $killSwitch = $cmd.ExecuteScalar()
        if ($killSwitch -eq "true") {
            Write-Host "[WARN] Kill switch is ACTIVE. Reset with: python tools/reset-kill-switch.py" -ForegroundColor Yellow
            $issues++
        } else {
            Write-Host "[OK] Kill switch is inactive" -ForegroundColor Green
        }

        # Check pending approvals
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT COUNT(*) FROM approval_queue WHERE status = 'pending'"
        $pending = $cmd.ExecuteScalar()
        if ($pending -gt 0) {
            Write-Host "[INFO] $pending pending approvals in queue" -ForegroundColor Cyan
        } else {
            Write-Host "[OK] No pending approvals" -ForegroundColor Green
        }

        $conn.Close()
    } catch {
        Write-Host "[FAIL] Database check failed: $_" -ForegroundColor Red
        $issues++
    }
} else {
    Write-Host "[FAIL] Database not found at $dbPath" -ForegroundColor Red
    $issues++
}

# === Check 2: Docker Services ===
$checks++
try {
    $dockerPs = docker ps --format "{{.Names}}" 2>$null
    if ($dockerPs) {
        $expected = @("jarvis-chroma", "jarvis-n8n", "jarvis-prometheus", "jarvis-grafana", "jarvis-loki", "jarvis-vault", "jarvis-temporal")
        foreach ($svc in $expected) {
            if ($dockerPs -contains $svc) {
                Write-Host "[OK] Docker: $svc is running" -ForegroundColor Green
            } else {
                Write-Host "[INFO] Docker: $svc is not running (may be intentional)" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "[INFO] Docker services not running" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] Docker not available" -ForegroundColor Yellow
}

# === Check 3: Disk Space ===
$checks++
try {
    $drive = (Get-Location).Drive.Root
    $disk = Get-PSDrive -Name $drive[0]
    $freeGB = [math]::Round($disk.Free / 1GB, 1)
    $totalGB = [math]::Round(($disk.Free + $disk.Used) / 1GB, 1)
    $pctFree = [math]::Round(($disk.Free / ($disk.Free + $disk.Used)) * 100, 1)

    if ($pctFree -lt 10) {
        Write-Host "[WARN] Disk space: $freeGB GB free ($pctFree%) - LOW" -ForegroundColor Yellow
        $issues++
    } else {
        Write-Host "[OK] Disk space: $freeGB GB free ($pctFree% of $totalGB GB)" -ForegroundColor Green
    }
} catch {
    Write-Host "[INFO] Could not check disk space" -ForegroundColor Yellow
}

# === Check 4: Vault API Health ===
$checks++
try {
    $vaultResp = Invoke-RestMethod -Uri "http://localhost:18201/v1/sys/health" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($vaultResp.initialized -and -not $vaultResp.sealed) {
        Write-Host "[OK] Vault is initialized and unsealed" -ForegroundColor Green
    } elseif ($vaultResp.initialized -and $vaultResp.sealed) {
        Write-Host "[WARN] Vault is initialized but SEALED - run unseal steps" -ForegroundColor Yellow
        $issues++
    } else {
        Write-Host "[INFO] Vault is not initialized" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] Vault is not responding (may be intentional)" -ForegroundColor Yellow
}

# === Check 5: Log Directory ===
$checks++
$logDir = Join-Path -Path $PSScriptRoot -ChildPath "..\logs"
if (Test-Path -LiteralPath $logDir) {
    $logSize = (Get-ChildItem -LiteralPath $logDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $logSizeMB = [math]::Round($logSize / 1MB, 1)
    if ($logSizeMB -gt 500) {
        Write-Host "[WARN] Log size: $logSizeMB MB - consider log rotation" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Log size: $logSizeMB MB" -ForegroundColor Green
    }
} else {
    Write-Host "[INFO] Log directory not found" -ForegroundColor Yellow
}

# === Check 6: Gitleaks Pre-Commit Hook ===
$checks++
$gitHook = Join-Path -Path $PSScriptRoot -ChildPath "..\.git\hooks\pre-commit"
if (Test-Path -LiteralPath $gitHook) {
    $hookContent = Get-Content -LiteralPath $gitHook -Raw
    if ($hookContent -match "gitleaks") {
        Write-Host "[OK] Gitleaks pre-commit hook is installed" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Pre-commit hook exists but does not mention gitleaks" -ForegroundColor Yellow
        $issues++
    }
} else {
    Write-Host "[WARN] No gitleaks pre-commit hook - commits will NOT be scanned for secrets" -ForegroundColor Yellow
    Write-Host "       Run: .\tools\git-secrets-setup.ps1" -ForegroundColor Yellow
    $issues++
}

# === Check 7: Secrets in Plaintext ===
$checks++
$vaultKeys = Join-Path -Path $PSScriptRoot -ChildPath "..\infrastructure\secrets\vault-keys.txt"
if (Test-Path -LiteralPath $vaultKeys) {
    Write-Host "[WARN] Vault root token is stored in plaintext at infrastructure\secrets\vault-keys.txt" -ForegroundColor Yellow
    Write-Host "       Copy this to Bitwarden/1Password, then delete the file." -ForegroundColor Yellow
    Write-Host "       File is gitignored, but still visible to anyone with file access." -ForegroundColor Yellow
    $issues++
} else {
    Write-Host "[OK] No plaintext vault keys file found" -ForegroundColor Green
}

$envFile = Join-Path -Path $PSScriptRoot -ChildPath "..\infrastructure\.env"
if (Test-Path -LiteralPath $envFile) {
    $envContent = Get-Content -LiteralPath $envFile
    $placeholderKeys = $envContent | Select-String -Pattern "your-key-here|your-token-here|your-secret"
    if ($placeholderKeys) {
        Write-Host "[WARN] .env still contains placeholder values - replace with real secrets" -ForegroundColor Yellow
        $issues++
    } else {
        Write-Host "[OK] .env has no placeholder values" -ForegroundColor Green
    }
}

# === Check 8: Tailscale Detection ===
$checks++
$tailscale = Get-Command "tailscale" -ErrorAction SilentlyContinue
if ($tailscale) {
    $tsStatus = & tailscale status 2>&1 | Out-String
    if ($tsStatus -match "Connected") {
        Write-Host "[OK] Tailscale is connected" -ForegroundColor Green
    } elseif ($tsStatus -match "Logged out|Stopped") {
        Write-Host "[INFO] Tailscale is installed but not connected" -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Tailscale is installed - run 'tailscale up' to connect" -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] Tailscale is not installed (optional - only needed for multi-machine setup)" -ForegroundColor Cyan
}

# === Summary ===
Write-Host ""
if ($issues -eq 0) {
    Write-Host "[OK] All checks passed" -ForegroundColor Green
} else {
    Write-Host "[WARN] $issues issue(s) found out of $checks checks" -ForegroundColor Yellow
}
Write-Host ""

# Log to file
$logDir = Resolve-Path (Join-Path -Path $PSScriptRoot -ChildPath "..\logs") -ErrorAction SilentlyContinue
if (-not $logDir) {
    $logDir = New-Item -ItemType Directory -Path (Join-Path -Path $PSScriptRoot -ChildPath "..\logs") -Force
}
$logEntry = "$timestamp | health-check | issues=$issues | checks=$checks"
Add-Content -LiteralPath (Join-Path -Path $logDir -ChildPath "health-check.log") -Value $logEntry

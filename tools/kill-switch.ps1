# =============================================================================
# JARVIS Emergency Kill Switch — PowerShell
# =============================================================================
# Stops all agents, queued actions, and running processes immediately.
# Call this if an agent is misbehaving or if you need to halt all AI activity.
#
# Usage:  powershell -ExecutionPolicy Bypass -File kill-switch.ps1
# =============================================================================

Write-Host "============================================" -ForegroundColor Red
Write-Host "   JARVIS EMERGENCY KILL SWITCH ACTIVATED" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

# 1. Write a kill signal to the SQLite database
$dbPath = Join-Path -Path $PSScriptRoot -ChildPath "..\memory\sqlite\jarvis.db"
if (Test-Path -LiteralPath $dbPath) {
    try {
        $conn = New-Object System.Data.SQLite.SQLiteConnection
        $conn.ConnectionString = "Data Source=$dbPath"
        $conn.Open()
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "CREATE TABLE IF NOT EXISTS system_control (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
        $cmd.ExecuteNonQuery() | Out-Null

        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "INSERT OR REPLACE INTO system_control (key, value, updated_at) VALUES ('kill_switch', 'true', datetime('now'))"
        $cmd.ExecuteNonQuery() | Out-Null

        # Reject all pending approval queue items
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "UPDATE approval_queue SET status = 'rejected', rejection_reason = 'kill_switch_activated' WHERE status = 'pending'"
        $count = $cmd.ExecuteNonQuery()

        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "INSERT INTO approval_history (timestamp, agent_id, action_type, action_detail, risk_level, status, rejection_reason, approved_at) SELECT datetime('now'), agent_id, action_type, action_detail || ' (KILL SWITCH)', risk_level, 'rejected', 'kill_switch', datetime('now') FROM approval_queue WHERE status = 'rejected' AND id NOT IN (SELECT id FROM approval_history)"


        $conn.Close()
        Write-Host "[OK] Kill switch signal written to database. $count pending actions rejected." -ForegroundColor Yellow
    } catch {
        Write-Host "[WARN] Could not write to database: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Database not found at $dbPath. Will still stop running processes." -ForegroundColor Yellow
}

# 2. Kill any running agent processes
$agentPatterns = @("python.*approval-queue", "node.*mcp-", "python.*agent")
$stopped = 0
foreach ($pattern in $agentPatterns) {
    $processes = Get-Process | Where-Object { $_.CommandLine -match $pattern } 2>$null
    foreach ($proc in $processes) {
        try {
            $proc.Kill()
            Write-Host "[OK] Killed process $($proc.Id) ($($proc.ProcessName))" -ForegroundColor Yellow
            $stopped++
        } catch {
            Write-Host "[WARN] Could not kill process $($proc.Id): $_" -ForegroundColor Yellow
        }
    }
}

# 3. Write audit log entry
$logPath = Join-Path -Path $PSScriptRoot -ChildPath "..\logs\audit.log"
$logDir = Split-Path -Parent $logPath
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$entry = "$timestamp | kill-switch | HUMAN | kill_switch_triggered | Emergency kill switch activated by human | critical"
Add-Content -LiteralPath $logPath -Value $entry

Write-Host ""
Write-Host "[OK] Kill switch audit entry written." -ForegroundColor Yellow
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "   KILL SWITCH COMPLETE" -ForegroundColor Green
Write-Host "   $stopped process(es) stopped" -ForegroundColor Green
Write-Host "   All pending actions rejected" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "To re-enable agents, run: python tools/reset-kill-switch.py" -ForegroundColor Cyan

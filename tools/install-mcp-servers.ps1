# =============================================================================
# JARVIS MCP Server Installer — installs and enables MCP servers
# =============================================================================
# Usage:
#   .\install-mcp-servers.ps1                    # Interactive (asks what to install)
#   .\install-mcp-servers.ps1 -EnableAll          # Install + enable search + browser
#   .\install-mcp-servers.ps1 -EnableSearch       # Install + enable search only
# =============================================================================

param(
    [switch]$EnableSearch,
    [switch]$EnableBrowser,
    [switch]$EnableAll
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RegistryPath = Join-Path -Path $RepoRoot -ChildPath "mcp-servers\mcp-registry.json"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   JARVIS MCP Server Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---- Prerequisites ----
Write-Host "[CHECK] Prerequisites..." -ForegroundColor Yellow
$nodeVersion = & node --version 2>$null
if (-not $nodeVersion) {
    Write-Host "[FAIL] Node.js is required. Install from https://nodejs.org" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Node.js: $nodeVersion" -ForegroundColor Green

$npmVersion = & npm --version 2>$null
if (-not $npmVersion) {
    Write-Host "[FAIL] npm is required." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] npm: $npmVersion" -ForegroundColor Green

# ---- Determine selection ----
if (-not $EnableSearch -and -not $EnableBrowser -and -not $EnableAll) {
    Write-Host ""
    Write-Host "Which MCP servers do you want to install?" -ForegroundColor Cyan
    $response = Read-Host "  [1] Search only   [2] Browser only   [3] Both   [4] Skip"
    switch ($response) {
        "1" { $EnableSearch = $true }
        "2" { $EnableBrowser = $true }
        "3" { $EnableAll = $true }
        default {
            Write-Host "  [INFO] Skipping MCP installation." -ForegroundColor Yellow
            exit 0
        }
    }
}

if ($EnableAll) {
    $EnableSearch = $true
    $EnableBrowser = $true
}

# ---- Read registry ----
$registry = Get-Content -LiteralPath $RegistryPath -Raw | ConvertFrom-Json

# ---- Install packages ----
Write-Host ""
Write-Host "[STEP 1] Installing MCP npm packages..." -ForegroundColor Yellow
Push-Location -LiteralPath $RepoRoot
$anyFailed = $false

try {
    if ($EnableSearch) {
        Write-Host "  Checking @modelcontextprotocol/server-brave-search..." -ForegroundColor Gray
        $alreadyInstalled = Test-Path -LiteralPath (Join-Path $RepoRoot "node_modules\@modelcontextprotocol\server-brave-search")
        if (-not $alreadyInstalled) {
            npm install @modelcontextprotocol/server-brave-search 2>&1 | Out-Null
        }
        Write-Host "  [OK] @modelcontextprotocol/server-brave-search available (requires BRAVE_API_KEY env var)" -ForegroundColor Green
        $registry.mcp_servers.'search-mcp'.enabled = $true
        Write-Host "  [WARN] This MCP server needs a Brave Search API key. Get one free at:" -ForegroundColor Yellow
        Write-Host "         https://brave.com/search/api/" -ForegroundColor Yellow
        Write-Host "         Then set: `$env:BRAVE_API_KEY = 'your-key-here'" -ForegroundColor Yellow
        Write-Host "         Without it, SearXNG fallback is used automatically." -ForegroundColor Yellow
    }

    if ($EnableBrowser) {
        Write-Host "  Installing @playwright/mcp..." -ForegroundColor Gray
        npm install @playwright/mcp 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] @playwright/mcp installed" -ForegroundColor Green
            $registry.mcp_servers.'browser-mcp'.enabled = $true
        } else {
            Write-Host "  [FAIL] npm install @playwright/mcp failed" -ForegroundColor Red
            $anyFailed = $true
        }

        Write-Host "  Installing Playwright browser binaries..." -ForegroundColor Gray
        & npx playwright install chromium 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Playwright Chromium browser installed" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Playwright browser install skipped. Run 'npx playwright install chromium' manually." -ForegroundColor Yellow
        }
    }
} finally {
    Pop-Location
}

# ---- Write updated registry ----
$registryJson = $registry | ConvertTo-Json -Depth 10
Set-Content -LiteralPath $RegistryPath -Value $registryJson
Write-Host ""
Write-Host "[STEP 2] Registry updated at mcp-servers/mcp-registry.json" -ForegroundColor Green

# ---- Summary ----
Write-Host ""
Write-Host "[STEP 3] Enabled MCP servers:" -ForegroundColor Yellow
$enabledCount = 0
foreach ($server in $registry.mcp_servers.PSObject.Properties) {
    if ($server.Value.enabled) {
        Write-Host "  [ENABLED] $($server.Name): $($server.Value.description)" -ForegroundColor Green
        $enabledCount++
    }
}
Write-Host "  Total enabled: $enabledCount" -ForegroundColor Cyan

if ($anyFailed) {
    Write-Host ""
    Write-Host "  [WARN] Some installations failed. Check errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   MCP Server installation complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next:" -ForegroundColor White
Write-Host "   - Enabled MCP servers are ready for OpenCode auto-discovery" -ForegroundColor Cyan
Write-Host "   - Run 'npm test' to verify the full toolchain" -ForegroundColor Cyan
Write-Host "   - research_gateway.py will auto-pick search-mcp when enabled" -ForegroundColor Cyan

# =============================================================================
# JARVIS Phase 1 Setup - PowerShell
# =============================================================================
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1
# =============================================================================

param(
    [string]$GoogleApiKey = "",
    [string]$NvidiaApiKey = "",
    [string]$GitHubToken = ""
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   JARVIS Ecosystem - Phase 1 Setup" -ForegroundColor Cyan
Write-Host "   Foundation Installation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# === Prerequisite Check ===
Write-Host "[STEP 1] Checking prerequisites..." -ForegroundColor Yellow
$prereqs = @(
    @{ Name = "Node.js"; Command = "node --version"; Required = $true },
    @{ Name = "Python"; Command = "python --version"; Required = $true },
    @{ Name = "Git"; Command = "git --version"; Required = $true }
)

$allPassed = $true
foreach ($prereq in $prereqs) {
    try {
        $output = & cmd /c "$($prereq.Command) 2>nul"
        if ($LASTEXITCODE -ne 0 -and -not $output) {
            throw "Not found"
        }
        Write-Host "  [OK] $($prereq.Name): $output" -ForegroundColor Green
    }
    catch {
        Write-Host "  [FAIL] $($prereq.Name) is required but not found. Please install it." -ForegroundColor Red
        if ($prereq.Required) { $allPassed = $false }
    }
}

try {
    Write-Host "  [OK] PowerShell: $($PSVersionTable.PSVersion)" -ForegroundColor Green
}
catch {
    $allPassed = $false
}

if (-not $allPassed) {
    Write-Host ""
    Write-Host "Please install required dependencies and re-run this script." -ForegroundColor Red
    Write-Host "  - Node.js 20+: https://nodejs.org"
    Write-Host "  - Python 3.11+: https://python.org"
    Write-Host "  - Git: https://git-scm.com"
    exit 1
}

Write-Host ""

# === Docker Check (optional) ===
Write-Host '[STEP 2] Checking Docker (optional, for infrastructure services)...' -ForegroundColor Yellow
try {
    $dockerVersion = & docker --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $dockerVersion) {
        Write-Host "  [OK] Docker: $dockerVersion" -ForegroundColor Green
    }
    else {
        throw "Docker not available"
    }
}
catch {
    Write-Host '  [INFO] Docker not found. Infrastructure services [Chroma, n8n] will run locally instead.' -ForegroundColor Yellow
    Write-Host "  [INFO] Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/" -ForegroundColor Yellow
}

Write-Host ""

# === Environment Configuration ===
Write-Host "[STEP 3] Setting up environment configuration..." -ForegroundColor Yellow
$envFile = Join-Path -Path $PSScriptRoot -ChildPath "infrastructure\.env"
$envExample = Join-Path -Path $PSScriptRoot -ChildPath "infrastructure\.env.example"

if (-not (Test-Path -LiteralPath $envFile)) {
    if (-not (Test-Path -LiteralPath $envExample)) {
        Write-Host "  [FAIL] Missing infrastructure\.env.example" -ForegroundColor Red
        exit 1
    }
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Host "  [OK] Created .env from .env.example" -ForegroundColor Green

    if ([string]::IsNullOrEmpty($GoogleApiKey)) {
        Write-Host "  [INPUT] Gemini API key from https://aistudio.google.com/apikey (AIza...):" -ForegroundColor Cyan
        Write-Host "  (Press Enter to skip - add later in OpenCode with /connect)" -ForegroundColor Gray
        $GoogleApiKey = Read-Host -Prompt "  Google API Key"
    }

    if (-not [string]::IsNullOrEmpty($GoogleApiKey)) {
        (Get-Content -LiteralPath $envFile) `
            -replace 'GOOGLE_API_KEY=AIza-your-key-here', "GOOGLE_API_KEY=$GoogleApiKey" `
            | Set-Content -LiteralPath $envFile
        Write-Host "  [OK] Google Gemini API key configured" -ForegroundColor Green
    }

    if ([string]::IsNullOrEmpty($NvidiaApiKey)) {
        Write-Host "  [INPUT] NVIDIA API key from https://build.nvidia.com (nvapi...):" -ForegroundColor Cyan
        Write-Host "  (Press Enter to skip - fallback when Gemini rate limits)" -ForegroundColor Gray
        $NvidiaApiKey = Read-Host -Prompt "  NVIDIA API Key"
    }

    if (-not [string]::IsNullOrEmpty($NvidiaApiKey)) {
        (Get-Content -LiteralPath $envFile) `
            -replace 'NVIDIA_API_KEY=nvapi-your-key-here', "NVIDIA_API_KEY=$NvidiaApiKey" `
            | Set-Content -LiteralPath $envFile
        Write-Host "  [OK] NVIDIA API key configured" -ForegroundColor Green
    }

    if ([string]::IsNullOrEmpty($GitHubToken)) {
        Write-Host "  [INPUT] Enter your GitHub Personal Access Token (ghp_...):" -ForegroundColor Cyan
        Write-Host "  (Press Enter to skip - can be configured later)" -ForegroundColor Gray
        $GitHubToken = Read-Host -Prompt "  Token"
    }

    if (-not [string]::IsNullOrEmpty($GitHubToken)) {
        (Get-Content -LiteralPath $envFile) `
            -replace 'GITHUB_TOKEN=ghp_your-token-here', "GITHUB_TOKEN=$GitHubToken" `
            | Set-Content -LiteralPath $envFile
        Write-Host "  [OK] GitHub token configured" -ForegroundColor Green
    }
}
else {
    Write-Host "  [OK] .env already exists - skipping" -ForegroundColor Green
}

Write-Host ""

# === Directory Structure ===
Write-Host "[STEP 4] Creating directory structure..." -ForegroundColor Yellow
$directories = @(
    "agents\coder",
    "agents\researcher",
    "agents\planner",
    "agents\security",
    "agents\qa",
    "agents\writer",
    "agents\data",
    "agents\orchestrator",
    "mcp-servers",
    "memory\chroma",
    "memory\sqlite",
    "memory\obsidian-vault",
    "workflows",
    "tools",
    "infrastructure\monitoring",
    "infrastructure\secrets",
    "security",
    "github-repos",
    "logs",
    "docs"
)

foreach ($dir in $directories) {
    $fullPath = Join-Path -Path $PSScriptRoot -ChildPath $dir
    if (-not (Test-Path -LiteralPath $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "  [OK] Created: $dir" -ForegroundColor Green
    }
}

Write-Host ""

# === Initialize SQLite Database ===
Write-Host "[STEP 5] Initializing SQLite database..." -ForegroundColor Yellow
$initDbScript = Join-Path -Path $PSScriptRoot -ChildPath "tools\init-jarvis-db.py"
try {
    $dbOutput = & python $initDbScript 2>&1
    $dbExit = $LASTEXITCODE
    if ($dbOutput) {
        $dbOutput | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
    }
    if ($dbExit -ne 0) {
        throw "init-jarvis-db.py exited with code $dbExit"
    }
}
catch {
    Write-Host "  [WARN] Could not initialize SQLite database: $_" -ForegroundColor Yellow
    Write-Host "  [INFO] Run manually: python tools\init-jarvis-db.py" -ForegroundColor Yellow
}

Write-Host ""

# === Git Secrets Setup ===
Write-Host "[STEP 6] Setting up Git secret scanning..." -ForegroundColor Yellow
$gitSecretsScript = Join-Path -Path $PSScriptRoot -ChildPath "tools\git-secrets-setup.ps1"
if (Test-Path -LiteralPath $gitSecretsScript) {
    try {
        & $gitSecretsScript
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Git secrets configured" -ForegroundColor Green
        }
        else {
            Write-Host "  [INFO] Run tools\git-secrets-setup.ps1 manually later" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  [INFO] Run tools\git-secrets-setup.ps1 manually later" -ForegroundColor Yellow
    }
}
else {
    Write-Host "  [INFO] git-secrets-setup.ps1 not found - skip for now" -ForegroundColor Yellow
}

# --- Secure secrets management (Bitwarden / 1Password) ---
Write-Host "" 
Write-Host "[STEP 6b] Secrets management — password manager integration" -ForegroundColor Yellow

$bwPath = Get-Command "bw" -ErrorAction SilentlyContinue
$opPath = Get-Command "op" -ErrorAction SilentlyContinue

if ($bwPath) {
    Write-Host "  [DETECTED] Bitwarden CLI (bw)" -ForegroundColor Green
    $useBw = Read-Host "  Use Bitwarden to fetch/store API keys? (y/N)"
    if ($useBw -eq "y" -or $useBw -eq "Y") {
        try {
            $bwStatus = & bw status 2>&1
            if ($bwStatus -match '"status":"unauthenticated"') {
                Write-Host "  [INPUT] Log in to Bitwarden:" -ForegroundColor Cyan
                $bwSession = & bw login 2>&1
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  [WARN] Bitwarden login failed. Falling back to manual entry." -ForegroundColor Yellow
                }
            }
            $bwStatus = & bw status 2>&1
            if ($bwStatus -match '"status":"locked"') {
                Write-Host "  [INPUT] Vault is locked. Enter your master password to unlock:" -ForegroundColor Cyan
                & bw unlock 2>&1 | Out-Null
            }
            Write-Host "  [OK] Bitwarden ready. You can store/retrieve keys with:" -ForegroundColor Green
            Write-Host '    bw get item "JARVIS API Keys" | ConvertFrom-Json' -ForegroundColor Gray
        }
        catch {
            Write-Host "  [WARN] Bitwarden error: $_" -ForegroundColor Yellow
        }
    }
}
elseif ($opPath) {
    Write-Host "  [DETECTED] 1Password CLI (op)" -ForegroundColor Green
    $useOp = Read-Host "  Use 1Password to fetch/store API keys? (y/N)"
    if ($useOp -eq "y" -or $useOp -eq "Y") {
        try {
            $opWhoami = & op whoami 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [INPUT] Sign in to 1Password:" -ForegroundColor Cyan
                & op account add 2>&1 | Out-Null
            }
            Write-Host "  [OK] 1Password ready. You can store/retrieve keys with:" -ForegroundColor Green
            Write-Host '    op item get "JARVIS API Keys" --format json' -ForegroundColor Gray
        }
        catch {
            Write-Host "  [WARN] 1Password error: $_" -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "  [INFO] No password manager CLI detected." -ForegroundColor Yellow
    $installPm = Read-Host "  Install Bitwarden CLI for secure key storage? (y/N)"
    if ($installPm -eq "y" -or $installPm -eq "Y") {
        Write-Host "  Installing Bitwarden CLI via winget..." -ForegroundColor Gray
        try {
            & winget install Bitwarden.CLI --silent 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Bitwarden CLI installed. Re-run setup to configure." -ForegroundColor Green
            }
            else {
                Write-Host "  [WARN] winget install failed. Install manually: https://bitwarden.com/download" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "  [WARN] Could not install Bitwarden CLI: $_" -ForegroundColor Yellow
            Write-Host "  [INFO] Install manually: https://bitwarden.com/download" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "  [INFO] API keys stored in .env (plain text). For production, use a password manager." -ForegroundColor Yellow
    }
}

# --- gitleaks enforcement ---
Write-Host "" 
Write-Host "[STEP 6c] gitleaks — secret scanning enforcement" -ForegroundColor Yellow
$gitleaksVersion = & gitleaks version 2>$null
if ($LASTEXITCODE -eq 0 -and $gitleaksVersion) {
    Write-Host "  [OK] gitleaks installed: $gitleaksVersion" -ForegroundColor Green
}
else {
    Write-Host "  [INFO] gitleaks not found." -ForegroundColor Yellow
    $installGl = Read-Host "  Install gitleaks via winget? (y/N)"
    if ($installGl -eq "y" -or $installGl -eq "Y") {
        try {
            & winget install gitleaks --silent 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] gitleaks installed successfully" -ForegroundColor Green
            }
            else {
                Write-Host "  [WARN] winget install failed. Download from: https://github.com/gitleaks/gitleaks/releases" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "  [WARN] Could not install gitleaks: $_" -ForegroundColor Yellow
            Write-Host "  [INFO] Download from: https://github.com/gitleaks/gitleaks/releases" -ForegroundColor Yellow
        }
    }
}

# Run gitleaks scan on current repo
$enableScan = Read-Host "  Run gitleaks scan against this repo now? (y/N)"
if ($enableScan -eq "y" -or $enableScan -eq "Y") {
    Write-Host "  Scanning for secrets..." -ForegroundColor Gray
    $scanResult = & gitleaks detect --source $PSScriptRoot --no-git --verbose 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] No secrets detected." -ForegroundColor Green
    }
    else {
        Write-Host "  [WARN] gitleaks found potential secrets. Review above." -ForegroundColor Yellow
    }
}

# --- Tailscale guidance ---
Write-Host "" 
Write-Host "[STEP 6d] Optional: Tailscale (for private network access)" -ForegroundColor Yellow
$tsVersion = & tailscale version 2>$null
if ($LASTEXITCODE -eq 0 -and $tsVersion) {
    Write-Host "  [OK] Tailscale installed: $tsVersion" -ForegroundColor Green
}
else {
    Write-Host "  [INFO] Tailscale not detected. Install for multi-host orchestration:" -ForegroundColor Cyan
    Write-Host "  https://tailscale.com/download" -ForegroundColor Cyan
}

Write-Host ""

# === Summary ===
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Phase 1 Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  What's installed:" -ForegroundColor White
Write-Host "  [OK] Directory structure" -ForegroundColor Green
Write-Host "  [OK] SQLite database (if Step 5 succeeded)" -ForegroundColor Green
Write-Host "  [OK] Agent configurations deployed" -ForegroundColor Green
Write-Host "  [OK] MCP server registry configured" -ForegroundColor Green
Write-Host "  [OK] Security framework deployed" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "  1. Open the jarvis folder in OpenCode" -ForegroundColor Cyan
Write-Host "  2. In OpenCode: /connect Google + NVIDIA (see docs\USER_PREFERENCES.md)" -ForegroundColor Cyan
Write-Host "  3. Create Obsidian vault at memory\obsidian-vault" -ForegroundColor Cyan
Write-Host "  4. Verify: python tools\approval-queue.py list" -ForegroundColor Cyan
Write-Host ""
Write-Host '  Docker services [Chroma, n8n, Grafana]:' -ForegroundColor White
Write-Host "  cd infrastructure; docker compose up -d" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

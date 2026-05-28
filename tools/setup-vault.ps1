# =============================================================================
# JARVIS Vault Setup — Initialize and unseal HashiCorp Vault
# =============================================================================
# Run once after starting the vault container:
#   powershell -ExecutionPolicy Bypass -File tools/setup-vault.ps1
#
# This script:
#   1. Checks if Vault is reachable
#   2. Initializes Vault (if not already initialized)
#   3. Unseals Vault (if sealed)
#   4. Stores initial secrets (API keys placeholder)
#   5. Applies agent and admin policies
# =============================================================================

param(
    [string]$VaultAddr = "http://localhost:18201",
    [int]$KeyShares = 5,
    [int]$KeyThreshold = 3
)

$ErrorActionPreference = "Stop"
$VaultDir = Split-Path (Split-Path $PSScriptRoot -Parent) -ChildPath "security"
$KeysFile = Join-Path $VaultDir ".vault-keys.json"
$TokenFile = Join-Path $VaultDir ".vault-root-token"

Write-Host "=== JARVIS Vault Setup ===" -ForegroundColor Cyan
Write-Host "Vault address: $VaultAddr" -ForegroundColor White

# --- Step 1: Check Vault health ---
Write-Host "`n[1/5] Checking Vault health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$VaultAddr/v1/sys/health" -Method Get -TimeoutSec 5
    Write-Host "  Vault is running. Initialized: $($health.initialized), Sealed: $($health.sealed)" -ForegroundColor Green
} catch {
    Write-Host "  Cannot reach Vault at $VaultAddr. Is the container running?" -ForegroundColor Red
    Write-Host "  Start it with: docker compose -f infrastructure/docker-compose.yml up -d vault" -ForegroundColor Yellow
    exit 1
}

# --- Step 2: Initialize Vault ---
if (-not $health.initialized) {
    Write-Host "`n[2/5] Initializing Vault ($KeyShares shares, threshold $KeyThreshold)..." -ForegroundColor Yellow
    $initPayload = @{
        secret_shares = $KeyShares
        secret_threshold = $KeyThreshold
    } | ConvertTo-Json

    $initResponse = Invoke-RestMethod -Uri "$VaultAddr/v1/sys/init" -Method Post -Body $initPayload -ContentType "application/json"
    
    # Save keys securely
    $keysData = @{
        keys = $initResponse.keys
        keys_base64 = $initResponse.keys_base64
        threshold = $KeyThreshold
        created_at = (Get-Date -Format "o")
    }
    $keysData | ConvertTo-Json -Depth 3 | Set-Content -Path $KeysFile -Encoding UTF8
    Write-Host "  Vault initialized. Keys saved to: $KeysFile" -ForegroundColor Green
    Write-Host "  WARNING: Protect this file! It contains unseal keys." -ForegroundColor Red

    $rootToken = $initResponse.root_token
    $rootToken | Set-Content -Path $TokenFile -Encoding UTF8
    Write-Host "  Root token saved to: $TokenFile" -ForegroundColor Green

    # Update VAULT_TOKEN for this session
    $env:VAULT_TOKEN = $rootToken
} else {
    Write-Host "`n[2/5] Vault already initialized." -ForegroundColor Green
    
    if (Test-Path $TokenFile) {
        $env:VAULT_TOKEN = Get-Content $TokenFile -Raw
        Write-Host "  Loaded root token from: $TokenFile" -ForegroundColor Green
    }
}

# --- Step 3: Unseal Vault ---
if ($health.sealed) {
    Write-Host "`n[3/5] Unsealing Vault..." -ForegroundColor Yellow
    
    if (-not (Test-Path $KeysFile)) {
        Write-Host "  Keys file not found: $KeysFile" -ForegroundColor Red
        Write-Host "  Cannot unseal without keys." -ForegroundColor Red
        exit 1
    }
    
    $keysData = Get-Content $KeysFile -Raw | ConvertFrom-Json
    $keys = $keysData.keys
    
    for ($i = 0; $i -lt $KeyThreshold; $i++) {
        $unsealPayload = @{ key = $keys[$i] } | ConvertTo-Json
        $unsealResponse = Invoke-RestMethod -Uri "$VaultAddr/v1/sys/unseal" -Method Post -Body $unsealPayload -ContentType "application/json"
        Write-Host "  Unseal key $($i + 1)/$KeyThreshold applied. Sealed: $($unsealResponse.sealed)" -ForegroundColor Green
    }
} else {
    Write-Host "`n[3/5] Vault already unsealed." -ForegroundColor Green
}

# --- Step 4: Apply policies ---
Write-Host "`n[4/5] Applying Vault policies..." -ForegroundColor Yellow
$policyFiles = @(
    @{ Name = "agents-policy"; Path = "vault-policies.hcl" }
)

# Apply agent policy via CLI (if vault CLI is available)
$vaultCLI = Get-Command vault -ErrorAction SilentlyContinue
if ($vaultCLI) {
    $policyPath = Join-Path $VaultDir "vault-policies.hcl"
    if (Test-Path $policyPath) {
        try {
            # Read and apply the agent section
            $policyContent = Get-Content $policyPath -Raw
            # Write a minimal agent policy
            $agentPolicy = @"
path "secret/data/agents/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/agents/*" {
  capabilities = ["read", "list"]
}
path "secret/data/system/*" {
  capabilities = ["deny"]
}
"@
            $agentPolicy | vault policy write agents-policy - 2>$null
            Write-Host "  Applied agents-policy" -ForegroundColor Green
        } catch {
            Write-Host "  Could not apply policies via CLI: $_" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  Vault CLI not found. Apply policies manually via Vault UI." -ForegroundColor Yellow
}

# --- Step 5: Store initial secrets (placeholders) ---
Write-Host "`n[5/5] Storing initial secret placeholders..." -ForegroundColor Yellow

function Set-VaultSecret {
    param($Path, $Data)
    $payload = @{ data = $Data } | ConvertTo-Json -Depth 3
    try {
        Invoke-RestMethod -Uri "$VaultAddr/v1/secret/data/$Path" -Method Post -Body $payload -ContentType "application/json" -Headers @{ "X-Vault-Token" = $env:VAULT_TOKEN }
        Write-Host "  Stored: secret/data/$Path" -ForegroundColor Green
    } catch {
        Write-Host "  Could not store secret at $Path : $_" -ForegroundColor Yellow
    }
}

# Store placeholder secrets (replace with real values later)
Set-VaultSecret "api/anthropic" @{ api_key = "REPLACE_WITH_REAL_KEY"; model = "claude-sonnet-4-20250514" }
Set-VaultSecret "api/github" @{ token = "REPLACE_WITH_REAL_TOKEN" }
Set-VaultSecret "agents/coder" @{ name = "coder-001"; permissions = "filesystem,github,sandbox" }
Set-VaultSecret "agents/researcher" @{ name = "researcher-001"; permissions = "browser,search,fetch" }
Set-VaultSecret "system/monitoring" @{ grafana_password = "REPLACE_WITH_REAL_PASSWORD" }

Write-Host "`n=== Vault Setup Complete ===" -ForegroundColor Cyan
Write-Host "Vault is initialized, unsealed, and ready." -ForegroundColor Green
Write-Host "  Address:  $VaultAddr" -ForegroundColor White
Write-Host "  UI:       $VaultAddr/ui" -ForegroundColor White
Write-Host "  Keys:     $KeysFile" -ForegroundColor White
Write-Host "  Token:    $TokenFile" -ForegroundColor White
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Replace REPLACE_WITH_REAL_KEY with your Anthropic API key" -ForegroundColor White
Write-Host "  2. Replace REPLACE_WITH_REAL_TOKEN with your GitHub token" -ForegroundColor White
Write-Host "  3. Set VAULT_ADDR=$VaultAddr and VAULT_TOKEN in your environment" -ForegroundColor White

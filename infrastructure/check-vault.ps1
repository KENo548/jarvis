param(
    [string]$ComposePath = ".",
    [string]$VaultAddr = "http://127.0.0.1:8201"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "[check-vault] $msg" -ForegroundColor Cyan
}

function Fail($msg) {
    Write-Host "[check-vault] FAIL: $msg" -ForegroundColor Red
    exit 1
}

Write-Step "Using compose path: $ComposePath"
Set-Location $ComposePath

Write-Step "Checking docker daemon"
$null = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail "Docker daemon is not reachable. Start Docker Desktop first."
}

Write-Step "Ensuring Vault container is up"
docker compose up -d vault | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fail "Could not start Vault container."
}

Write-Step "Reading container status"
$psOutput = docker compose ps vault
if ($LASTEXITCODE -ne 0) {
    Fail "Failed to read compose status."
}

$psOutput | Write-Host

$psText = ($psOutput -join "`n")

if ($psText -notmatch "jarvis-vault\b") {
    Fail "Vault container not found in compose output."
}
if ($psText -notmatch "Up\b") {
    Fail "Vault container is not running."
}

Write-Step "Waiting for Vault to be ready at $VaultAddr"
$retries = 15
$statusJson = $null
for ($i = 0; $i -lt $retries; $i++) {
    $result = docker compose exec -T vault sh -lc "export VAULT_ADDR=$VaultAddr; vault status -format=json" 2>&1
    $ec = $LASTEXITCODE
    if ($ec -eq 0 -or $ec -eq 2) {
        $statusJson = $result
        break
    }
    Start-Sleep 2
}
if ($null -eq $statusJson) {
    Fail "Vault did not become ready within $($retries * 2) seconds."
}

$status = $statusJson | ConvertFrom-Json
Write-Host ("[check-vault] Initialized={0} Sealed={1} Version={2}" -f $status.initialized, $status.sealed, $status.version)

if (-not $status.initialized) {
    Fail "Vault is not initialized."
}
if ($status.sealed) {
    Fail "Vault is sealed."
}

Write-Step "Performing KV read/write test"
$putOut = docker compose exec -T vault sh -lc "export VAULT_ADDR=$VaultAddr; vault kv put secret/jarvis/health-check key=ok >/dev/null 2>&1"
if ($LASTEXITCODE -ne 0) {
    Fail "KV write test failed."
}

$getOut = docker compose exec -T vault sh -lc "export VAULT_ADDR=$VaultAddr; vault kv get -field=key secret/jarvis/health-check"
if ($LASTEXITCODE -ne 0) {
    Fail "KV read test failed."
}

$getOut = $getOut.Trim()
if ($getOut -ne "ok") {
    Fail "KV read returned unexpected value: '$getOut'"
}

Write-Step "Cleaning up test secret"
docker compose exec -T vault sh -lc "export VAULT_ADDR=$VaultAddr; vault kv metadata delete secret/jarvis/health-check >/dev/null 2>&1" | Out-Null
docker compose exec -T vault sh -lc "export VAULT_ADDR=$VaultAddr; vault kv destroy -versions=1 secret/jarvis/health-check >/dev/null 2>&1" | Out-Null

Write-Host "[check-vault] PASS: Vault is unsealed, initialized, and KV read/write succeeded." -ForegroundColor Green

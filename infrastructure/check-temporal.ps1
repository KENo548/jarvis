param(
    [string]$ComposePath = ".",
    [string]$Profile = "temporal"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "[check-temporal] $msg" -ForegroundColor Cyan
}

function Fail($msg) {
    Write-Host "[check-temporal] FAIL: $msg" -ForegroundColor Red
    exit 1
}

Write-Step "Using compose path: $ComposePath"
Set-Location $ComposePath

Write-Step "Checking docker daemon"
$null = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail "Docker daemon is not reachable. Start Docker Desktop first."
}

Write-Step "Ensuring Temporal stack is up"
docker compose --profile $Profile up -d temporal-postgresql temporal temporal-ui | Out-Null
if ($LASTEXITCODE -ne 0) {
    Fail "Could not start Temporal services."
}

Write-Step "Reading container status"
$psOutput = docker compose --profile $Profile ps temporal temporal-postgresql temporal-ui
if ($LASTEXITCODE -ne 0) {
    Fail "Failed to read compose status."
}

$psOutput | Write-Host

$psText = ($psOutput -join "`n")

if ($psText -notmatch "jarvis-temporal\b") {
    Fail "Temporal container not found in compose output."
}
if ($psText -notmatch "jarvis-temporal-db\b") {
    Fail "Temporal PostgreSQL container not found in compose output."
}
if ($psText -notmatch "jarvis-temporal-ui\b") {
    Fail "Temporal UI container not found in compose output."
}
if ($psText -notmatch "jarvis-temporal-db.*healthy") {
    Fail "Temporal PostgreSQL is not healthy yet."
}

Write-Step "Checking Temporal Web UI at http://localhost:8233"
$headers = curl.exe -sS -D - http://localhost:8233 -o NUL
if ($LASTEXITCODE -ne 0) {
    Fail "Temporal Web UI is not responding on :8233"
}

$headersText = ($headers -join "`n")

if ($headersText -notmatch "HTTP/1\.[01]\s+200") {
    Fail "Temporal Web UI did not return HTTP 200."
}

Write-Step "Checking cluster health"
$health = docker compose exec temporal sh -lc "tctl --address temporal:7233 cluster health"
if ($LASTEXITCODE -ne 0) {
    Fail "Temporal cluster health command failed."
}

$health | Write-Host
if ($health -notmatch "SERVING") {
    Fail "Temporal cluster is not SERVING."
}

Write-Host "[check-temporal] PASS: Temporal UI and cluster health are good." -ForegroundColor Green

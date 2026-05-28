# =============================================================================
# JARVIS Ollama Setup — Installs and configures local LLM + embedding backend
# =============================================================================
# Run once: powershell -ExecutionPolicy Bypass -File tools/setup-ollama.ps1
# =============================================================================

param(
    [string]$OllamaHost = "http://localhost:11434",
    [string]$EmbeddingModel = "nomic-embed-text",
    [string]$LLMModel = "llama3.2"
)

$ErrorActionPreference = "Stop"

Write-Host "=== JARVIS Ollama Setup ===" -ForegroundColor Cyan

# --- Step 1: Check if Ollama is installed ---
Write-Host "`n[1/4] Checking Ollama installation..." -ForegroundColor Yellow
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaPath) {
    Write-Host "  Ollama not found. Installing via winget..." -ForegroundColor Red
    try {
        winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        Write-Host "  Ollama installed successfully." -ForegroundColor Green
    } catch {
        Write-Host "  Failed to install Ollama. Please install manually from https://ollama.com" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Ollama found at: $($ollamaPath.Source)" -ForegroundColor Green
}

# --- Step 2: Start Ollama service ---
Write-Host "`n[2/4] Starting Ollama service..." -ForegroundColor Yellow
$ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Write-Host "  Starting Ollama serve..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Verify connection
try {
    $response = Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get -TimeoutSec 5
    Write-Host "  Ollama is running. Existing models: $($response.models.Count)" -ForegroundColor Green
} catch {
    Write-Host "  Ollama not responding at $OllamaHost. Waiting..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    try {
        $response = Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get -TimeoutSec 10
        Write-Host "  Ollama is now running." -ForegroundColor Green
    } catch {
        Write-Host "  Failed to connect to Ollama. Check if the service is running." -ForegroundColor Red
        exit 1
    }
}

# --- Step 3: Pull embedding model ---
Write-Host "`n[3/4] Pulling embedding model: $EmbeddingModel..." -ForegroundColor Yellow
$existingModels = (Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get).models | ForEach-Object { $_.name }
if ($existingModels -contains $EmbeddingModel) {
    Write-Host "  Model $EmbeddingModel already present." -ForegroundColor Green
} else {
    Write-Host "  Pulling $EmbeddingModel (this may take a minute)..." -ForegroundColor Yellow
    ollama pull $EmbeddingModel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to pull $EmbeddingModel" -ForegroundColor Red
        exit 1
    }
    Write-Host "  $EmbeddingModel pulled successfully." -ForegroundColor Green
}

# --- Step 4: Pull LLM model ---
Write-Host "`n[4/4] Pulling LLM model: $LLMModel..." -ForegroundColor Yellow
if ($existingModels -contains $LLMModel) {
    Write-Host "  Model $LLMModel already present." -ForegroundColor Green
} else {
    Write-Host "  Pulling $LLMModel (this may take a few minutes)..." -ForegroundColor Yellow
    ollama pull $LLMModel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to pull $LLMModel" -ForegroundColor Red
        exit 1
    }
    Write-Host "  $LLMModel pulled successfully." -ForegroundColor Green
}

# --- Verify embedding works ---
Write-Host "`n=== Verifying embedding backend ===" -ForegroundColor Cyan
$testPayload = @{ model = $EmbeddingModel; prompt = "JARVIS health check" } | ConvertTo-Json
try {
    $embedResponse = Invoke-RestMethod -Uri "$OllamaHost/api/embeddings" -Method Post -Body $testPayload -ContentType "application/json" -TimeoutSec 10
    $vectorSize = $embedResponse.embedding.Count
    Write-Host "  Embedding vector size: $vectorSize" -ForegroundColor Green
    Write-Host "  nomic-embed-text is working!" -ForegroundColor Green
} catch {
    Write-Host "  Embedding test failed: $_" -ForegroundColor Red
    exit 1
}

# --- Write .env snippet ---
Write-Host "`n=== Configuration ===" -ForegroundColor Cyan
$envSnippet = @"
# JARVIS Ollama Configuration (add to .env or environment)
OLLAMA_HOST=$OllamaHost
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=$EmbeddingModel
CHROMA_ENABLE=true
"@
Write-Host $envSnippet -ForegroundColor White

$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) "infrastructure/.env"
$envDir = Split-Path $envFile -Parent
if (-not (Test-Path $envDir)) { New-Item -ItemType Directory -Path $envDir -Force | Out-Null }
Add-Content -Path $envFile -Value "`n# Ollama Configuration`nOLLAMA_HOST=$OllamaHost`nEMBEDDING_PROVIDER=ollama`nEMBEDDING_MODEL=$EmbeddingModel`nCHROMA_ENABLE=true" -ErrorAction SilentlyContinue
Write-Host "  Updated $envFile" -ForegroundColor Green

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Ollama is running with:" -ForegroundColor Green
Write-Host "  - Embedding: $EmbeddingModel (vector size: 768)" -ForegroundColor White
Write-Host "  - LLM: $LLMModel" -ForegroundColor White
Write-Host "  - Endpoint: $OllamaHost" -ForegroundColor White

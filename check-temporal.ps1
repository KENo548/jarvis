$ErrorActionPreference = "Stop"

$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "infrastructure\check-temporal.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Temporal check script not found at: $scriptPath"
    exit 1
}

& $scriptPath -ComposePath (Join-Path -Path $PSScriptRoot -ChildPath "infrastructure")
exit $LASTEXITCODE

# Capability Registry Search — find skill by trigger keyword (PowerShell)
# Usage: .\capability_registry_search.ps1 <keyword>

param(
    [Parameter(Mandatory=$true)]
    [string]$Keyword
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JarvisDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$ConfigPath = Join-Path $JarvisDir "config\capabilities.json"

# Read and search
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$keywordLower = $Keyword.ToLower()
$matches = @()

foreach ($cap in $config.capabilities) {
    $triggers = $cap.triggers | ForEach-Object { $_.ToLower() }
    if ($triggers -contains $keywordLower) {
        $matches += $cap
    } else {
        foreach ($t in $triggers) {
            if ($t -like "*$keywordLower*") {
                $matches += $cap
                break
            }
        }
    }
}

if ($matches.Count -gt 0) {
    foreach ($m in $matches) {
        Write-Output "$($m.id): $($m.name) -> skill: $($m.skill)"
    }
    exit 0
} else {
    Write-Error "No capability found for: $Keyword"
    exit 1
}

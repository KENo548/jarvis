# Tool Registry Search — find tool by trigger keyword (PowerShell)
# Usage: .\tool_registry_search.ps1 <keyword>

param(
    [Parameter(Mandatory=$true)]
    [string]$Keyword
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JarvisDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$ConfigPath = Join-Path $JarvisDir "config\tools.json"

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$keywordLower = $Keyword.ToLower()
$matches = @()

foreach ($tool in $config.tools) {
    $searchable = @($tool.id, $tool.label, $tool.purpose) + ($tool.agents) + ($tool.cli_commands)
    $match = $false
    foreach ($field in $searchable) {
        if ($null -ne $field -and $field.ToLower().Contains($keywordLower)) {
            $match = $true
            break
        }
    }
    if ($match) {
        $matches += $tool
    }
}

if ($matches.Count -gt 0) {
    foreach ($m in $matches) {
        $platforms = ($m.platforms) -join ", "
        $agents = ($m.agents) -join ", "
        Write-Output "$($m.id): $($m.label) [platforms: $platforms] [agents: $agents] [type: $($m.type)]"
    }
    exit 0
} else {
    Write-Error "No tool found for: $Keyword"
    exit 1
}

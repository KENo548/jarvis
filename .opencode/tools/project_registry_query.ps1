# Project Registry Query — resolve project name to path (PowerShell)
# Usage: .\project_registry_query.ps1 <project-name> [platform]
#
# Reads config/projects.json and outputs the resolved path.
# Platform defaults to current OS detection.

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    [string]$Platform = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JarvisDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$ConfigPath = Join-Path $JarvisDir "config\projects.json"

# Auto-detect platform
if (-not $Platform) {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $Platform = "windows"
    } else {
        $Platform = "linux"
    }
}

# Read and resolve
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

foreach ($project in $config.projects) {
    if ($project.name -eq $ProjectName) {
        $paths = $project.paths
        $path = $paths.$Platform
        if (-not $path) {
            $path = $paths.windows
        }
        if (-not $path) {
            $path = $paths.linux
        }
        if ($path) {
            Write-Output $path
            exit 0
        } else {
            Write-Error "No path found for platform: $Platform"
            exit 1
        }
    }
}

Write-Error "Project not found: $ProjectName"
exit 1

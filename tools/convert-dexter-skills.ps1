#
# Convert Dexter (Autonomous Finance Researcher) skills into OpenCode skills.
#
# This script:
# - Reads all SKILL.md under dexter-main/src/skills
# - Copies them to jarvis/dexter-skills/<skill>/SKILL.md
# - Keeps frontmatter (name + description) as-is
# - Generates a manifest at jarvis/dexter-skills/manifest.md
#
param(
    [string]$SourceRoot = "C:\Users\Admin\Documents\agency-agents-main\Autonomous Finance Researcher\dexter-main\src\skills",
    [string]$DestRoot = "C:\Users\Admin\Documents\agency-agents-main\jarvis\dexter-skills"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DestRoot)) {
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
}

$skills = Get-ChildItem -Path $SourceRoot -Recurse -Filter 'SKILL.md'
$manifest = @()
$errors = @()
$count = 0

foreach ($file in $skills) {
    $skillName = Split-Path $file.DirectoryName -Leaf
    $destDir = Join-Path $DestRoot $skillName
    $destFile = Join-Path $destDir 'SKILL.md'

    try {
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Copy-Item -Path $file.FullName -Destination $destFile -Force
        $count++
        $manifest += "| $count | $skillName | OK |"
    } catch {
        $errors += "| $($file.FullName) | $($_.Exception.Message) |"
    }
}

$manifestFile = Join-Path $DestRoot 'manifest.md'
$manifestBody = @(
    '# Dexter Skills to OpenCode Skills Manifest',
    '',
    "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Source: $SourceRoot",
    "Destination: $DestRoot",
    '',
    '## Summary',
    '',
    "- Total skills found: $($skills.Count)",
    "- Converted skills: $count",
    "- Errors: $($errors.Count)",
    '',
    '## Converted Skills',
    '',
    '| # | Skill Name | Status |',
    '|---|-----------|--------|'
)

$manifestBody += $manifest

if ($errors.Count -gt 0) {
    $manifestBody += '', '## Errors', '', '| File | Error |', '|------|-------|'
    $manifestBody += $errors
}

$manifestBody -join "`r`n" | Out-File -FilePath $manifestFile -Encoding utf8 -Force

Write-Host "Converted: $count"
Write-Host "Manifest: $manifestFile"

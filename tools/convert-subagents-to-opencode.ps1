#
# Convert awesome-claude-code-subagents into OpenCode agent definitions.
#
# This script:
# - Reads all *.md under categories/
# - Extracts YAML frontmatter fields (name, description, tools, model)
# - Writes OpenCode agents into jarvis/.opencode/agents/awesome-claude/
# - Generates a manifest at jarvis/.opencode/agents/awesome-claude/manifest.md
#
param(
    [string]$SourceRoot = "C:\Users\Admin\Documents\agency-agents-main\awesome-claude-code-subagents-main",
    [string]$DestRoot = "C:\Users\Admin\Documents\agency-agents-main\jarvis\.opencode\agents\awesome-claude"
)

$ErrorActionPreference = "Stop"

function Get-YamlFrontmatter {
    param([string[]]$Lines)
    $inFront = $false
    $frontLines = @()
    $bodyStart = 0
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($i -eq 0 -and $Lines[$i] -eq '---') {
            $inFront = $true
            continue
        }
        if ($inFront -and $Lines[$i] -eq '---') {
            $bodyStart = $i + 1
            break
        }
        if ($inFront) {
            $frontLines += $Lines[$i]
        }
    }
    return @{
        Frontmatter = $frontLines
        BodyStart   = $bodyStart
        HasFront    = $inFront -or $frontLines.Count -gt 0
    }
}

function Parse-Frontmatter {
    param([string[]]$FrontLines)
    $data = @{}
    $descriptionLines = @()
    $inDescription = $false
    $descriptionKey = $false

    foreach ($line in $FrontLines) {
        if ($line -match '^description:\s*\|') {
            $inDescription = $true
            $descriptionKey = $true
            continue
        }
        if ($inDescription) {
            if ($line -match '^\s{2,}') {
                $descriptionLines += $line.TrimStart()
                continue
            } else {
                $inDescription = $false
            }
        }

        if ($line -match '^name:\s*(.+)$') {
            $data['name'] = $matches[1].Trim()
            continue
        }
        if ($line -match '^description:\s*(.+)$') {
            $data['description'] = $matches[1].Trim().Trim('"')
            continue
        }
        if ($line -match '^tools:\s*(.+)$') {
            $data['tools'] = $matches[1].Trim()
            continue
        }
        if ($line -match '^model:\s*(.+)$') {
            $data['model'] = $matches[1].Trim()
            continue
        }
    }

    if ($descriptionKey -and $descriptionLines.Count -gt 0) {
        $data['description'] = ($descriptionLines -join ' ')
    }

    return $data
}

function Map-Tools {
    param([string]$Tools)
    if (-not $Tools) { return $null }

    $map = @{
        'Read' = 'Read'
        'Write' = 'Write'
        'Edit' = 'Edit'
        'Glob' = 'Glob'
        'Grep' = 'Grep'
        'Bash' = 'Bash'
        'WebFetch' = 'WebFetch'
        'WebSearch' = 'WebFetch'
        'AskUserQuestion' = 'AskUserQuestion'
    }

    $out = @()
    $parts = $Tools -split ','
    foreach ($p in $parts) {
        $tool = $p.Trim()
        if ($map.ContainsKey($tool)) {
            $mapped = $map[$tool]
            if (-not $out.Contains($mapped)) {
                $out += $mapped
            }
        }
    }
    if ($out.Count -eq 0) { return $null }
    return ($out -join ', ')
}

if (-not (Test-Path $DestRoot)) {
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
}

$files = Get-ChildItem -Path (Join-Path $SourceRoot 'categories') -Recurse -Filter '*.md' | Where-Object {
    $_.Name -ne 'README.md'
}

$manifest = @()
$errors = @()
$count = 0

foreach ($file in $files) {
    try {
        $rawLines = Get-Content -Path $file.FullName -Raw
        $lines = $rawLines -split "`r`n|`n"

        $fmInfo = Get-YamlFrontmatter -Lines $lines
        if (-not $fmInfo.HasFront) { continue }

        $front = Parse-Frontmatter -FrontLines $fmInfo.Frontmatter
        if (-not $front.ContainsKey('name')) { continue }

        $name = $front['name']
        $desc = $front['description']
        $tools = Map-Tools -Tools $front['tools']

        $bodyLines = $lines[$fmInfo.BodyStart..($lines.Count - 1)]
        $body = ($bodyLines -join "`r`n").Trim()

        $out = @('---')
        $out += "name: $name"
        if ($desc) { $out += "description: $desc" }
        $out += 'mode: subagent'
        if ($tools) { $out += "tools: $tools" }
        $out += '---'
        $out += ''
        $out += $body

        $destFile = Join-Path $DestRoot ("$name.md")
        $out -join "`r`n" | Out-File -FilePath $destFile -Encoding utf8 -Force

        $count++
        $manifest += "| $count | $name | OK |"
    } catch {
        $errors += "| $($file.FullName) | $($_.Exception.Message) |"
    }
}

$manifestFile = Join-Path $DestRoot 'manifest.md'
$manifestBody = @(
    '# Awesome Claude Subagents to OpenCode Agents Manifest',
    '',
    "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Source: $SourceRoot",
    "Destination: $DestRoot",
    '',
    '## Summary',
    '',
    "- Total files scanned: $($files.Count)",
    "- Converted agents: $count",
    "- Errors: $($errors.Count)",
    '',
    '## Converted Agents',
    '',
    '| # | Agent Name | Status |',
    '|---|------------|--------|'
)

$manifestBody += $manifest

if ($errors.Count -gt 0) {
    $manifestBody += '', '## Errors', '', '| File | Error |', '|------|-------|'
    $manifestBody += $errors
}

$manifestBody -join "`r`n" | Out-File -FilePath $manifestFile -Encoding utf8 -Force

Write-Host "Converted: $count"
Write-Host "Manifest: $manifestFile"

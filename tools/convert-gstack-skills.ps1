<#
.SYNOPSIS
  Convert all GStack SKILL.md files from OpenClaude format to OpenCode-compatible format.

.DESCRIPTION
  Reads each SKILL.md from gstack-main/gstack-main/<skill>/SKILL.md, converts
  OpenClaude-specific syntax to OpenCode equivalents, and writes the result to
  jarvis/gstack-skills/<skill>/SKILL.md.

  Conversions performed:
  1. Frontmatter: strip preamble-tier, version, benefits-from, triggers, allowed-tools, gbrain
     (keep only name + description — OpenCode host config uses allowlist mode)
  2. Path rewrites: ~/.claude/ → ~/.config/opencode/ , .claude/ → .opencode/
  3. Claude CLI references → opencode CLI
  4. MODEL_OVERLAY: claude → MODEL_OVERLAY: opencode
  5. mcp__conductor__ → mcp__opencode__
  6. SPAWNED_SESSION references (OpenClaw) updated to OpenCode equivalents
  7. Model-Specific Behavioral Patch updated for opencode

.PARAMETER SourceRoot
  Path to the gstack-main root directory (containing all skill dirs with SKILL.md)

.PARAMETER DestRoot
  Path where converted skills will be written (jarvis/gstack-skills)

.PARAMETER OpenCodeConfigBackup
  If true, also copy opencode.ts to the dest root for reference

.EXAMPLE
  .\convert-gstack-skills.ps1
  Converts all skills using default paths.
#>

param(
    [string]$SourceRoot = "C:\Users\Admin\Documents\agency-agents-main\gstack-main\gstack-main",
    [string]$DestRoot = "C:\Users\Admin\Documents\agency-agents-main\jarvis\gstack-skills",
    [string]$OpenCodeConfigPath = "C:\Users\Admin\Documents\agency-agents-main\gstack-main\gstack-main\hosts\opencode.ts",
    [switch]$OpenCodeConfigBackup = $true
)

$ErrorActionPreference = "Stop"

# ---- Utility: YAML frontmatter parsing (simple line-by-line) ----
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

function Convert-Frontmatter {
    param([string[]]$FrontLines)
    # Fields to KEEP (name and description are allowlisted by opencode.ts)
    # We still output a clean minimal frontmatter
    $keep = @{}
    $descriptionLines = @()
    $inDescription = $false
    $descriptionKey = $false

    foreach ($line in $FrontLines) {
        # Track multi-line description (YAML | block scalars)
        if ($line -match '^description:\s*\|') {
            $inDescription = $true
            $descriptionKey = $true
            $keep['name'] = $null  # placeholder, will set from name line
            continue
        }
        if ($inDescription) {
            if ($line -match '^\s{2,}') {
                # continuation of description block
                $descriptionLines += $line.TrimStart()
                continue
            } else {
                $inDescription = $false
                # This line is a new key, re-process it below
            }
        }

        if ($line -match '^name:\s*(.+)$') {
            $keep['name'] = $matches[1].Trim()
            continue
        }
        if ($line -match '^description:\s*(.+)$') {
            # Single-line description
            $keep['description'] = $matches[1].Trim()
            continue
        }
        # Check if this line continues a previous description (indented)
        if ($line -match '^\s{2,}' -and $keep.ContainsKey('description') -and $keep['description']) {
            $keep['description'] += " " + $line.Trim()
            continue
        }
    }

    # Build output YAML frontmatter
    $outLines = @('---')
    if ($keep.ContainsKey('name') -and $keep['name']) {
        $outLines += "name: $($keep['name'])"
    }
    if ($descriptionKey -and $descriptionLines.Count -gt 0) {
        $outLines += "description: |"
        foreach ($dl in $descriptionLines) {
            $outLines += "  $dl"
        }
    } elseif ($keep.ContainsKey('description') -and $keep['description']) {
        $outLines += "description: $($keep['description'])"
    }
    $outLines += '---'
    return $outLines
}

# ---- Utility: Content transformations ----
function Convert-Content {
    param([string[]]$Lines, [string]$SkillName)

    $result = @()

    # Skip the AUTO-GENERATED comment (lines 1-2 after frontmatter usually)
    # We'll keep them but update
    foreach ($line in $Lines) {
        $newLine = $line

        # Path rewrites (must be done before general claude rewrites)
        $newLine = $newLine -replace '~\/\.claude\/skills\/gstack', '~/.config/opencode/skills/gstack'
        $newLine = $newLine -replace '~\/\.claude\/', '~/.config/opencode/'
        $newLine = $newLine -replace '~\/\.claude\.json', '~/.config/opencode.json'
        $newLine = $newLine -replace '(?<!~)\/\.claude\/skills\/gstack', '/.opencode/skills/gstack'
        $newLine = $newLine -replace '(?<!~)\/\.claude\/skills', '/.opencode/skills'
        $newLine = $newLine -replace '(?<!~)\/\.claude\/', '/.opencode/'
        $newLine = $newLine -replace '\.claude\/skills\/gstack', '.opencode/skills/gstack'
        $newLine = $newLine -replace '\.claude\/skills', '.opencode/skills'
        $newLine = $newLine -replace '(?<!\.config\/)\.claude\/', '.opencode/'

        # Model overlay
        $newLine = $newLine -replace 'MODEL_OVERLAY:\s*claude', 'MODEL_OVERLAY: opencode'

        # OpenClaw → OpenCode references
        $newLine = $newLine -replace 'OpenClaw', 'OpenCode'
        $newLine = $newLine -replace 'OPENCLAW_SESSION', 'OPENCODE_SESSION'

        # mcp conductor → opencode
        $newLine = $newLine -replace 'mcp__conductor__', 'mcp__opencode__'

        # Skill invocation paths in prose (e.g., "read ~/.claude/skills/gstack/office-hours/SKILL.md")
        $newLine = $newLine -replace '~\/\.claude\/skills\/gstack\/([\w-]+)\/SKILL\.md', '~/.config/opencode/skills/gstack/$1/SKILL.md'

        # Update model-specific behavioral patch section title
        $newLine = $newLine -replace '## Model-Specific Behavioral Patch \(claude\)', '## Model-Specific Behavioral Patch (opencode)'

        # CLAUDE.md references stay as-is (both OpenClaude and OpenCode use CLAUDE.md)

        # Remove OpenClaude-specific frontmatter fields in prose references
        # (things like "preamble-tier" references in instructions)
        # These are rare; just let them pass through natural text
        $result += $newLine
    }

    return $result
}

# ---- Main ----

Write-Host "=== GStack → OpenCode Skill Converter ===" -ForegroundColor Cyan
Write-Host "Source: $SourceRoot"
Write-Host "Dest:   $DestRoot"
Write-Host ""

# Ensure destination root exists
if (-not (Test-Path $DestRoot)) {
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
    Write-Host "Created destination directory: $DestRoot" -ForegroundColor Green
}

# Get all skill directories
$skillDirs = Get-ChildItem -Directory -Path $SourceRoot | Where-Object {
    Test-Path (Join-Path $_.FullName "SKILL.md")
} | Sort-Object Name

$converted = 0
$errors = @()
$manifest = @()

foreach ($dir in $skillDirs) {
    $skillName = $dir.Name
    $srcFile = Join-Path $dir.FullName "SKILL.md"
    $destDir = Join-Path $DestRoot $skillName
    $destFile = Join-Path $destDir "SKILL.md"

    Write-Host "[$($converted+1)/$($skillDirs.Count)] Converting: $skillName" -ForegroundColor Yellow

    try {
        # Read source file
        $rawLines = Get-Content -Path $srcFile -Raw
        $lines = $rawLines -split "`r`n|`n"

        # Parse frontmatter
        $fmInfo = Get-YamlFrontmatter -Lines $lines

        # Convert frontmatter
        if ($fmInfo.HasFront -and $fmInfo.Frontmatter.Count -gt 0) {
            $newFront = Convert-Frontmatter -FrontLines $fmInfo.Frontmatter
        } else {
            $newFront = @('---', "name: $skillName", '---')
        }

        # Convert body content
        $bodyLines = $lines[$fmInfo.BodyStart..($lines.Count - 1)]
        $convertedBody = Convert-Content -Lines $bodyLines -SkillName $skillName

        # Combine
        $outputLines = $newFront + $convertedBody

        # Ensure dest dir exists
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        # Write output
        $outputLines -join "`r`n" | Out-File -FilePath $destFile -Encoding utf8 -Force

        $converted++
        $manifest += @{
            Skill    = $skillName
            Source   = $srcFile
            Dest     = $destFile
            Status   = "OK"
        }

        Write-Host "  -> Written to $destFile" -ForegroundColor Green

    } catch {
        $errors += @{
            Skill = $skillName
            Error = $_.Exception.Message
        }
        Write-Host "  ERROR: $_" -ForegroundColor Red
    }
}

# ---- Write manifest ----
$manifestFile = Join-Path $DestRoot "manifest.md"
$manifestBody = @(
    "# GStack → OpenCode Skills Manifest",
    "",
    "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Source: $SourceRoot",
    "Destination: $DestRoot",
    "",
    "## Summary",
    "",
    "- Total skills found: $($skillDirs.Count)",
    "- Successfully converted: $converted",
    "- Errors: $($errors.Count)",
    "",
    "## Converted Skills",
    "",
    "| # | Skill Name | Status |",
    "|---|-----------|--------|"
)

$i = 0
foreach ($m in $manifest) {
    $i++
    $manifestBody += "| $i | $($m.Skill) | OK |"
}

if ($errors.Count -gt 0) {
    $manifestBody += "",
    "## Errors",
    "",
    "| Skill | Error |",
    "|-------|-------|"
    foreach ($e in $errors) {
        $manifestBody += "| $($e.Skill) | $($e.Error) |"
    }
}

$manifestBody -join "`r`n" | Out-File -FilePath $manifestFile -Encoding utf8 -Force
Write-Host ""
Write-Host "Manifest written: $manifestFile" -ForegroundColor Cyan

# ---- Copy opencode.ts for reference ----
if ($OpenCodeConfigBackup -and (Test-Path $OpenCodeConfigPath)) {
    $backupFile = Join-Path $DestRoot "opencode-backup.ts"
    Copy-Item -Path $OpenCodeConfigPath -Destination $backupFile -Force
    Write-Host "OpenCode config backed up: $backupFile" -ForegroundColor Cyan
}

# ---- Summary ----
Write-Host ""
Write-Host "=== Conversion Complete ===" -ForegroundColor Cyan
Write-Host "  Skills found:    $($skillDirs.Count)"
Write-Host "  Converted:       $converted"
Write-Host "  Errors:          $($errors.Count)"
if ($errors.Count -gt 0) {
    Write-Host "  (check manifest for error details)" -ForegroundColor Yellow
}

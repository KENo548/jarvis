# Tools Health Check — verify JARVIS toolchain is available and valid (PowerShell)
# Usage: .\tools_health.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JarvisDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$RegistryPath = Join-Path $JarvisDir "config\tools.json"

if (!(Test-Path $RegistryPath)) {
    Write-Error "Registry not found: $RegistryPath"
    exit 1
}

$reg = Get-Content $RegistryPath -Raw | ConvertFrom-Json

$scriptsDir = Join-Path $JarvisDir ".opencode\tools"
$BinDir = Join-Path $JarvisDir "node_modules\.bin"

$failed = 0

foreach ($tool in $reg.tools) {
    $label = "$($tool.id) ($($tool.label))"
    $bin = $tool.id

    # Special cases for bin name
    if ($tool.id -eq "playwright") { $bin = "playwright-cli" }
    if ($tool.id -eq "context7") { $bin = "ctx7" }

    $exe = Join-Path $BinDir "$bin.cmd"
    if (!(Test-Path $exe)) {
        Write-Warning "$label : not found at $exe - run: npm ci"
        $failed++
        continue
    }

    try {
        $minVer = $tool.verification.min_version
        $out = & cmd /c "`"$exe`" --version 2>&1" | Out-String
        if ($out -match '\d+\.\d+\.\d+') {
            $ver = $Matches[0]
            if ([version]$ver -ge [version]$minVer) {
                Write-Output ("{0} : OK (v{1})" -f $label, $ver)
            } else {
                Write-Warning "$label : version $ver below minimum $minVer"
                $failed++
            }
        } else {
            Write-Warning "$label : could not parse version from output"
            $failed++
        }
    } catch {
        Write-Warning "$label : check failed - $($_.Exception.Message)"
        $failed++
    }
}

if ($failed -gt 0) {
    Write-Warning "$failed tool(s) failed health check"
    exit 1
}

Write-Output "All tools healthy."
exit 0

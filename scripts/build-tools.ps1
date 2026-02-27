# =============================================================================
# ForensicStack — Build forensic tool Docker images (Windows PowerShell)
#
# Run this ONCE after cloning, before submitting any analysis jobs.
#
# Usage:
#   .\scripts\build-tools.ps1
#
# Build a single tool:
#   .\scripts\build-tools.ps1 -Tool exiftool
# =============================================================================
param(
    [string]$Tool = "all"
)

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginsDir = Join-Path $ScriptDir "..\backend\forensicstack\plugins\external"

function Build-Image {
    param([string]$Name, [string]$Tag, [string]$Dir)
    Write-Host "[build-tools] Building $Tag ..." -ForegroundColor Yellow
    docker build -t $Tag $Dir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[build-tools] $Tag - FAILED" -ForegroundColor Red
        exit 1
    }
    Write-Host "[build-tools] $Tag - OK" -ForegroundColor Green
}

if ($Tool -eq "all" -or $Tool -eq "ileapp") {
    Build-Image "iLEAPP"      "forensicstack/ileapp:0.1"     (Join-Path $PluginsDir "ileapp")
}

if ($Tool -eq "all" -or $Tool -eq "aleapp") {
    Build-Image "ALEAPP"      "forensicstack/aleapp:0.1"     (Join-Path $PluginsDir "aleapp")
}

if ($Tool -eq "all" -or $Tool -eq "exiftool") {
    Build-Image "ExifTool"    "forensicstack/exiftool:0.1"   (Join-Path $PluginsDir "exiftool")
}

if ($Tool -eq "all" -or $Tool -eq "volatility") {
    Build-Image "Volatility3" "forensicstack/volatility:0.1" (Join-Path $PluginsDir "volatility")
}

Write-Host ""
Write-Host "All forensic tool images are ready." -ForegroundColor Green
Write-Host "Verify with:  docker images | Select-String forensicstack"

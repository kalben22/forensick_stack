# =============================================================================
# ForensicStack — Install EZ Tools on the Windows host (run ONCE)
#
# Uses Eric Zimmerman's official Get-ZimmermanTools.ps1 script to download
# and install all tools to C:\EZTools (or the path set in EZTOOLS_DIR).
#
# Source: https://github.com/EricZimmerman/Get-ZimmermanTools
#
# Usage:
#   .\scripts\install-eztools.ps1
#
# Custom install directory:
#   $env:EZTOOLS_DIR = "D:\Forensics\EZTools"
#   .\scripts\install-eztools.ps1
#
# Requirements: PowerShell 5.1+, internet access
# =============================================================================
$ErrorActionPreference = "Stop"

$InstallDir    = if ($env:EZTOOLS_DIR) { $env:EZTOOLS_DIR } else { "C:\EZTools" }
$GetToolsUrl   = "https://raw.githubusercontent.com/EricZimmerman/Get-ZimmermanTools/master/Get-ZimmermanTools.ps1"
$GetToolsLocal = Join-Path $env:TEMP "Get-ZimmermanTools.ps1"

Write-Host "[ForensicStack] Installing EZ Tools to '$InstallDir'..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Download Eric Zimmerman's official installer script
Write-Host "[ForensicStack] Fetching Get-ZimmermanTools.ps1 from GitHub..."
Invoke-WebRequest -Uri $GetToolsUrl -OutFile $GetToolsLocal -UseBasicParsing

# Run the official script: net6 tools (compatible with all modern Windows)
Write-Host "[ForensicStack] Downloading EZ Tools (net6, this may take a few minutes)..."
& powershell -ExecutionPolicy Bypass -File $GetToolsLocal `
    -Dest $InstallDir `
    -NetVersion 6

Remove-Item $GetToolsLocal -ErrorAction SilentlyContinue

# Sanity check
$ExeCount = (Get-ChildItem -Path $InstallDir -Filter "*.exe" -Recurse -ErrorAction SilentlyContinue).Count
Write-Host ""
Write-Host "[ForensicStack] Done. $ExeCount executables installed in '$InstallDir'." -ForegroundColor Green
Write-Host ""
Write-Host "ForensicStack will look for EZ Tools in '$InstallDir' by default."
Write-Host "To use a different path, set the EZTOOLS_DIR environment variable:"
Write-Host "  [System.Environment]::SetEnvironmentVariable('EZTOOLS_DIR', 'D:\MyTools\EZTools', 'Machine')"

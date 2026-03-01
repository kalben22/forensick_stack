# =============================================================================
# ForensicStack — Install EZ Tools on the Windows host (run ONCE)
#
# Downloads Eric Zimmerman's forensic tools from Backblaze and extracts
# them to C:\EZTools (or the path set in EZTOOLS_DIR env var).
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

$InstallDir = if ($env:EZTOOLS_DIR) { $env:EZTOOLS_DIR } else { "C:\EZTools" }
$Url        = "https://f001.backblazeb2.com/file/EricZimmermanTools/net6/All_6.zip"
$ZipPath    = Join-Path $InstallDir "All_6.zip"

Write-Host "[ForensicStack] Installing EZ Tools to '$InstallDir'..." -ForegroundColor Cyan

# Create directory if needed
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Download
Write-Host "[ForensicStack] Downloading EZ Tools (~200 MB)..."
Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
Write-Host "[ForensicStack] Download complete."

# Extract
Write-Host "[ForensicStack] Extracting..."
Expand-Archive -Path $ZipPath -DestinationPath $InstallDir -Force
Remove-Item $ZipPath

# Quick sanity check
$ExeCount = (Get-ChildItem -Path $InstallDir -Filter "*.exe" -Recurse).Count
Write-Host ""
Write-Host "[ForensicStack] Done. $ExeCount executables installed in '$InstallDir'." -ForegroundColor Green
Write-Host ""
Write-Host "ForensicStack will look for EZ Tools in '$InstallDir' by default."
Write-Host "To use a different path, set the EZTOOLS_DIR environment variable:"
Write-Host "  [System.Environment]::SetEnvironmentVariable('EZTOOLS_DIR', 'D:\MyTools\EZTools', 'Machine')"

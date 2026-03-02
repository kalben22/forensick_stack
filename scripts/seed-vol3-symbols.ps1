# =============================================================================
# ForensicStack - Seed Volatility3 Windows symbol tables into Docker volume
#
# Downloads the official windows.zip from the Volatility Foundation and
# extracts it into the named Docker volume forensicstack_vol3_symbols.
# Run this ONCE after building the Volatility3 Docker image.
#
# Usage (from repo root):
#   .\scripts\seed-vol3-symbols.ps1
#
# Requirements: Docker Desktop running (Linux container mode)
# =============================================================================
$ErrorActionPreference = "Stop"

$Url    = "https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip"
$Volume = "forensicstack_vol3_symbols"
$ZipPath    = Join-Path $env:TEMP "forensicstack-vol3-windows.zip"
$ExtractDir = Join-Path $env:TEMP "forensicstack-vol3-extract"

Write-Host ""
Write-Host "[ForensicStack] Seeding Volatility3 Windows symbol tables"
Write-Host "  Source : $Url"
Write-Host "  Volume : $Volume"
Write-Host ""

# ── Step 1: Download ─────────────────────────────────────────────────────────
Write-Host "[1/3] Downloading windows.zip (~300-400 MB compressed)..."
Write-Host "      This may take several minutes depending on your connection."

# Use Start-BitsTransfer (native Windows, supports resume, shows progress)
try {
    Import-Module BitsTransfer -ErrorAction Stop
    Start-BitsTransfer -Source $Url -Destination $ZipPath -Description "Volatility3 symbols" -DisplayName "ForensicStack"
} catch {
    # Fallback: curl.exe (available on Windows 10 1803+)
    Write-Host "      (BitsTransfer unavailable, using curl.exe...)"
    & curl.exe -L --progress-bar -o $ZipPath $Url
    if ($LASTEXITCODE -ne 0) { throw "Download failed (exit $LASTEXITCODE)" }
}

$sizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "      Downloaded: $sizeMB MB"

# ── Step 2: Extract ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/3] Extracting symbols..."

if (Test-Path $ExtractDir) { Remove-Item $ExtractDir -Recurse -Force }
New-Item -ItemType Directory -Path $ExtractDir | Out-Null

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $ExtractDir)

$WinDir = Join-Path $ExtractDir "windows"
if (-not (Test-Path $WinDir)) {
    throw "Extraction failed: 'windows/' directory not found in zip"
}

$count = (Get-ChildItem $WinDir -Recurse -File).Count
Write-Host "      $count ISF files extracted."

# ── Step 3: Copy into Docker volume ─────────────────────────────────────────
Write-Host ""
Write-Host "[3/3] Copying into Docker volume '$Volume'..."

$SrcPath = $WinDir.Replace("\", "/")
docker run --rm `
    -v "${Volume}:/target" `
    -v "${SrcPath}:/source:ro" `
    alpine sh -c "mkdir -p /target/symbols/windows && cp -r /source/. /target/symbols/windows/"

if ($LASTEXITCODE -ne 0) { throw "docker cp failed (exit $LASTEXITCODE)" }

$installed = docker run --rm -v "${Volume}:/vol" alpine sh -c "find /vol/symbols/windows -name '*.json.xz' | wc -l" 2>$null
Write-Host "      $installed ISF files now in volume."

# ── Cleanup ──────────────────────────────────────────────────────────────────
Remove-Item $ZipPath    -Force -ErrorAction SilentlyContinue
Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[ForensicStack] Done! Symbols ready in volume '$Volume'."
Write-Host "                Re-run Volatility3 analysis — no rebuild needed."

# =============================================================================
# ForensicStack - Seed Volatility3 Windows symbol tables (run ONCE)
#
# Two-phase download to avoid connection resets on slow/restricted networks:
#   Phase 1 - blobless clone: only tree/commit metadata (~5-20 MB)
#   Phase 2 - checkout: only blobs for the 4 NT kernel PDB dirs (~200-400 MB)
#
# Usage (from repo root or scripts\ folder):
#   .\scripts\seed-vol3-symbols.ps1
#
# Requirements: git, Docker Desktop running
# =============================================================================
$ErrorActionPreference = "Stop"

$Repo   = "https://github.com/Abyss-W4tcher/volatility3-symbols.git"
$Volume = "forensicstack_vol3_symbols"

Write-Host "[ForensicStack] Phase 1/2 - Downloading repo metadata (no blobs yet)..."
Write-Host "               This is fast (~5-20 MB)"

$TmpDir = Join-Path $env:TEMP ("vol3-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $TmpDir | Out-Null

try {
    Push-Location $TmpDir

    # Increase git http buffer to survive large packs on slow connections
    git config --global http.postBuffer 524288000
    git config --global http.lowSpeedLimit 1000
    git config --global http.lowSpeedTime 300

    # Phase 1: blobless clone (metadata only - fast)
    git clone --depth 1 --filter=blob:none --no-checkout $Repo .
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }

    # Configure sparse checkout BEFORE checkout so only the 4 PDB dirs are fetched
    git sparse-checkout init --cone
    git sparse-checkout set `
        windows/ntkrnlmp.pdb `
        windows/ntkrpamp.pdb `
        windows/ntoskrnl.pdb `
        windows/ntkrnlpa.pdb
    if ($LASTEXITCODE -ne 0) { throw "git sparse-checkout set failed" }

    Write-Host ""
    Write-Host "[ForensicStack] Phase 2/2 - Downloading symbol blobs (~200-400 MB)..."
    Write-Host "               Only the 4 NT kernel PDB directories"

    # Checkout triggers blob download for the sparse paths only
    git checkout HEAD
    if ($LASTEXITCODE -ne 0) { throw "git checkout HEAD failed" }

    Pop-Location

    # Verify the windows/ directory was populated
    $WinDir = Join-Path $TmpDir "windows"
    if (-not (Test-Path $WinDir)) {
        throw "windows/ directory not found after checkout - sparse checkout did not populate files"
    }

    $SrcPath = $WinDir.Replace("\", "/")

    Write-Host ""
    Write-Host "[ForensicStack] Copying symbols into Docker volume '$Volume'..."
    docker run --rm `
        -v "${Volume}:/target" `
        -v "${SrcPath}:/source:ro" `
        alpine sh -c "mkdir -p /target/symbols/windows && cp -r /source/. /target/symbols/windows/"
    if ($LASTEXITCODE -ne 0) { throw "docker run (copy) failed" }

    Write-Host ""
    Write-Host "[ForensicStack] Done! Symbols stored in volume '$Volume'."
    Write-Host "                Volatility3 will find them at /root/.cache/volatility3/symbols/windows/"

} catch {
    Write-Host "[ForensicStack] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    if (Test-Path $TmpDir) {
        Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
    }
}

# =============================================================================
# ForensicStack - Seed Volatility3 Windows symbol tables (run ONCE)
#
# Phase 1: git fetch --filter=blob:none  =>  metadata only (~900 KB, fast)
# Phase 2: git checkout FETCH_HEAD -- <paths>  =>  blobs only for 4 PDB dirs
#
# Usage (from repo root or scripts\ folder):
#   .\scripts\seed-vol3-symbols.ps1
#
# Requirements: git, Docker Desktop running
# =============================================================================
$ErrorActionPreference = "Stop"

$Repo   = "https://github.com/Abyss-W4tcher/volatility3-symbols.git"
$Volume = "forensicstack_vol3_symbols"

Write-Host "[ForensicStack] Phase 1/2 - Fetching repo metadata (~900 KB)..."

$TmpDir = Join-Path $env:TEMP ("vol3-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $TmpDir | Out-Null

try {
    Push-Location $TmpDir

    git config --global http.postBuffer 524288000
    git config --global http.lowSpeedLimit 1000
    git config --global http.lowSpeedTime 300

    # Initialize bare repo and fetch metadata only (no blobs)
    git init .
    git remote add origin $Repo
    git fetch --depth 1 --filter=blob:none origin master
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }

    Write-Host ""
    Write-Host "[ForensicStack] Phase 2/2 - Downloading symbol blobs for 4 NT kernel PDB dirs..."

    # Directly checkout specific paths from FETCH_HEAD
    # This forces git to fetch the blobs for those exact paths only
    git checkout FETCH_HEAD -- `
        windows/ntkrnlmp.pdb `
        windows/ntkrpamp.pdb `
        windows/ntoskrnl.pdb `
        windows/ntkrnlpa.pdb
    if ($LASTEXITCODE -ne 0) { throw "git checkout (paths) failed" }

    Pop-Location

    $WinDir = Join-Path $TmpDir "windows"
    if (-not (Test-Path $WinDir)) {
        throw "windows/ was not created - checkout did not populate files"
    }

    $count = (Get-ChildItem $WinDir -Recurse -File).Count
    Write-Host "  $count symbol files downloaded."

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

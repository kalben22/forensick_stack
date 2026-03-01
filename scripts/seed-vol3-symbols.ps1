# =============================================================================
# ForensicStack - Seed Volatility3 Windows symbol tables (run ONCE)
#
# Downloads the 4 NT kernel PDB directories from the community symbols repo
# on the Windows HOST (no Docker network dependency), then copies them into
# the named Docker volume forensicstack_vol3_symbols.
#
# Usage (from repo root or scripts\ folder):
#   .\scripts\seed-vol3-symbols.ps1
#
# Requirements: git, Docker Desktop running
# =============================================================================
$ErrorActionPreference = "Stop"

$Repo   = "https://github.com/Abyss-W4tcher/volatility3-symbols.git"
$Volume = "forensicstack_vol3_symbols"

Write-Host "[ForensicStack] Downloading Volatility3 NT kernel symbols onto the host..."
Write-Host "               (ntkrnlmp, ntkrpamp, ntoskrnl, ntkrnlpa - Win7/8/10/11 32+64-bit)"

$TmpDir = Join-Path $env:TEMP ("vol3-symbols-" + [System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $TmpDir | Out-Null

try {
    Push-Location $TmpDir

    git clone --depth 1 --sparse $Repo .
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }

    git sparse-checkout set `
        windows/ntkrnlmp.pdb `
        windows/ntkrpamp.pdb `
        windows/ntoskrnl.pdb `
        windows/ntkrnlpa.pdb
    if ($LASTEXITCODE -ne 0) { throw "git sparse-checkout failed" }

    Pop-Location

    # Convert backslashes to forward slashes for Docker volume mount
    $SrcPath = (Join-Path $TmpDir "windows").Replace("\", "/")

    Write-Host "[ForensicStack] Copying symbols into Docker volume '$Volume'..."
    docker run --rm `
        -v "${Volume}:/target" `
        -v "${SrcPath}:/source:ro" `
        alpine sh -c "mkdir -p /target/symbols/windows && cp -r /source/. /target/symbols/windows/"
    if ($LASTEXITCODE -ne 0) { throw "docker run (copy) failed" }

    Write-Host ""
    Write-Host "[ForensicStack] Done! Symbols stored in volume '$Volume'."
    Write-Host "                Volatility3 containers find them at /root/.cache/volatility3/symbols/windows/"

} catch {
    Write-Host "[ForensicStack] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    if (Test-Path $TmpDir) {
        Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
    }
}

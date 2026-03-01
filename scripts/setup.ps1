# =============================================================================
# ForensicStack — Automated Setup Script (Windows / PowerShell)
# =============================================================================
# Usage (run from repo root, as Administrator if docker requires it):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Info    { param($msg) Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Success { param($msg) Write-Host "[setup] OK  $msg" -ForegroundColor Green }
function Warn    { param($msg) Write-Host "[setup] !!  $msg" -ForegroundColor Yellow }
function Fail    { param($msg) Write-Host "[setup] ERR $msg" -ForegroundColor Red; exit 1 }
function Step    { param($msg) Write-Host "`n== $msg ==" -ForegroundColor White }

function Require {
    param($tool)
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Fail "Required tool not found: $tool — install it first (see README)."
    }
    Success "$tool is available"
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# =============================================================================
Step "1/8 — Prerequisites check"
# =============================================================================

Require "docker"
Require "python"
Require "node"
Require "npm"
Require "git"

$PythonVersion = (python --version 2>&1) -replace "Python ", ""
$NodeVersion   = (node --version) -replace "v", ""
Info "Python $PythonVersion | Node $NodeVersion"

$PyMajor, $PyMinor = $PythonVersion -split "\." | Select-Object -First 2
if ([int]$PyMajor -lt 3 -or ([int]$PyMajor -eq 3 -and [int]$PyMinor -lt 11)) {
    Fail "Python 3.11+ required (found $PythonVersion)"
}

$NodeMajor = ($NodeVersion -split "\.")[0]
if ([int]$NodeMajor -lt 18) {
    Fail "Node.js 18+ required (found $NodeVersion)"
}

# =============================================================================
Step "2/8 — Backend — environment file"
# =============================================================================

if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    # Auto-generate SECRET_KEY
    $Secret = python -c "import secrets; print(secrets.token_hex(32))"
    (Get-Content "backend\.env") -replace "replace_with_64_char_hex_secret", $Secret |
        Set-Content "backend\.env"
    Success "backend\.env created with a fresh SECRET_KEY"
    Warn "Review backend\.env and change the default passwords before exposing this to a network."
} else {
    Success "backend\.env already exists — skipping"
}

# =============================================================================
Step "3/8 — Frontend — environment file"
# =============================================================================

if (-not (Test-Path "web\.env.local")) {
    Copy-Item "web\.env.local.example" "web\.env.local"
    Success "web\.env.local created"
} else {
    Success "web\.env.local already exists — skipping"
}

# =============================================================================
Step "4/8 — Docker infrastructure (postgres, redis, minio, chromadb)"
# =============================================================================

Info "Starting infrastructure containers..."
docker compose -f backend/docker-compose.yml up -d postgres redis minio chromadb

Info "Waiting for services to become healthy (up to 60 s)..."
$Timeout = 60
$Elapsed = 0
while ($true) {
    $Running = docker compose -f backend/docker-compose.yml ps --quiet 2>$null
    if ($Running) {
        Success "Infrastructure containers are running"
        break
    }
    if ($Elapsed -ge $Timeout) {
        Warn "Timeout waiting for containers — check with: docker compose -f backend/docker-compose.yml ps"
        break
    }
    Start-Sleep -Seconds 3
    $Elapsed += 3
    Info "  Still waiting... ($($Elapsed)s)"
}

# =============================================================================
Step "5/8 — Forensic tool Docker images"
# =============================================================================

$Images = @(
    "forensicstack/ileapp:0.1",
    "forensicstack/aleapp:0.1",
    "forensicstack/exiftool:0.1",
    "forensicstack/volatility:0.1"
)

$AllExist = $true
foreach ($img in $Images) {
    $exists = docker image inspect $img 2>$null
    if ($LASTEXITCODE -ne 0) { $AllExist = $false; break }
}

if ($AllExist) {
    Success "All forensic tool images already built — skipping"
} else {
    Info "Building forensic tool images (first build may take 5-15 minutes)..."
    & "$PSScriptRoot\build-tools.ps1"
}

# =============================================================================
Step "6/8 — Backend — Python virtual environment"
# =============================================================================

if (-not (Test-Path "backend\venv")) {
    Info "Creating virtual environment..."
    python -m venv backend\venv
    Success "venv created at backend\venv"
} else {
    Success "backend\venv already exists — skipping creation"
}

Info "Installing Python dependencies..."
& "backend\venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& "backend\venv\Scripts\pip.exe" install --quiet -r backend\requirements.txt
Success "Python dependencies installed"

# =============================================================================
Step "7/8 — Frontend — Node dependencies"
# =============================================================================

Info "Installing frontend dependencies with 'npm ci' (reproducible install)..."
Set-Location web
npm ci --silent
if ($LASTEXITCODE -ne 0) { Fail "npm ci failed. Check the error above." }
Set-Location $RepoRoot
Success "Frontend dependencies installed"

# =============================================================================
Step "8/8 — Done!"
# =============================================================================

Write-Host ""
Write-Host "ForensicStack is ready." -ForegroundColor Green
Write-Host ""
Write-Host "  Start the API (terminal 1):" -ForegroundColor White
Write-Host "    cd backend" -ForegroundColor Cyan
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "    uvicorn forensicstack.api.main:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Start the worker (terminal 2):" -ForegroundColor White
Write-Host "    cd backend" -ForegroundColor Cyan
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "    python -m forensicstack.worker" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Start the frontend (terminal 3):" -ForegroundColor White
Write-Host "    cd web" -ForegroundColor Cyan
Write-Host "    npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Create your first account:" -ForegroundColor White
Write-Host '    Invoke-RestMethod -Method Post http://localhost:8001/auth/register `' -ForegroundColor Cyan
Write-Host '      -ContentType "application/json" `' -ForegroundColor Cyan
Write-Host '      -Body ''{"username":"analyst","password":"YourStrongPassword!"}''' -ForegroundColor Cyan
Write-Host ""
Write-Host "  Open:  http://localhost:3000" -ForegroundColor White
Write-Host "  Docs:  http://localhost:8001/docs" -ForegroundColor White
Write-Host ""
Write-Host "!! Never run 'npm audit fix --force' — it upgrades major versions and breaks the build." -ForegroundColor Yellow
Write-Host ""

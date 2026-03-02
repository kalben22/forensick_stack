# =============================================================================
# ForensicStack — Master setup script (Windows)
#
# Runs ONCE after cloning to prepare every component:
#   1. Docker images for Linux-container tools (iLEAPP, aLEAPP, ExifTool, Volatility3)
#   2. Volatility3 Windows symbol tables (seeded into a named Docker volume)
#   3. EZ Tools installed on the Windows host via Eric Zimmerman's official script
#
# Usage (from repo root):
#   .\setup.ps1
#
# Skip individual steps with flags:
#   .\setup.ps1 -SkipDockerImages
#   .\setup.ps1 -SkipVolatilitySymbols
#   .\setup.ps1 -SkipEZTools
#
# Requirements: Docker Desktop (Linux containers mode), git, PowerShell 5.1+
# =============================================================================
param(
    [switch]$SkipDockerImages,
    [switch]$SkipVolatilitySymbols,
    [switch]$SkipEZTools
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step  { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "    [!!] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "    [FAIL] $msg" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "Docker not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop"
}
$null = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Docker daemon is not running. Start Docker Desktop first."
}
Write-OK "Docker is running"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Fail "git not found. Install from https://git-scm.com/"
}
Write-OK "git is available"

# ---------------------------------------------------------------------------
# Step 1 — Build Docker images (Linux container tools)
# ---------------------------------------------------------------------------
if (-not $SkipDockerImages) {
    Write-Step "Building Docker images for Linux-container tools"
    & "$ScriptDir\scripts\build-tools.ps1" -Tool ileapp
    & "$ScriptDir\scripts\build-tools.ps1" -Tool aleapp
    & "$ScriptDir\scripts\build-tools.ps1" -Tool exiftool
    & "$ScriptDir\scripts\build-tools.ps1" -Tool volatility
    Write-OK "All Docker images built"
} else {
    Write-Warn "Skipping Docker image builds (-SkipDockerImages)"
}

# ---------------------------------------------------------------------------
# Step 2 — Seed Volatility3 Windows symbol tables
# ---------------------------------------------------------------------------
if (-not $SkipVolatilitySymbols) {
    Write-Step "Seeding Volatility3 symbol tables (one-time download ~200-400 MB)"
    & "$ScriptDir\scripts\seed-vol3-symbols.ps1"
    Write-OK "Volatility3 symbols ready"
} else {
    Write-Warn "Skipping Volatility3 symbols (-SkipVolatilitySymbols)"
}

# ---------------------------------------------------------------------------
# Step 3 — Install EZ Tools on the Windows host
# ---------------------------------------------------------------------------
if (-not $SkipEZTools) {
    Write-Step "Installing EZ Tools on the Windows host"
    & "$ScriptDir\scripts\install-eztools.ps1"
    Write-OK "EZ Tools ready"
} else {
    Write-Warn "Skipping EZ Tools installation (-SkipEZTools)"
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ForensicStack setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy .env.example to .env and fill in your secrets"
Write-Host "  2. docker compose up -d"
Write-Host "  3. Open http://localhost:3000"
Write-Host ""

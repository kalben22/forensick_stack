# =============================================================================
# run-auto-worker.ps1 - start the autonomous triage worker on the host (Windows)
# =============================================================================
# The /api/v1/analyze pipeline queues jobs on a Redis Stream that is consumed by
# forensicstack.stream_worker (NOT the legacy forensicstack.worker). This script
# runs that consumer natively against the compose stack's exposed Redis.
#
# Why native rather than in-compose on Windows: the hardened worker container
# needs HOST_WORKSPACE_ROOT pointed at the daemon-visible backing path of the
# tmp_jobs volume, which is awkward under Docker Desktop. Run on the host and the
# job workspace is a real host path Docker Desktop can bind-mount directly.
#
# Prereqs: `make up` (or docker compose up) is running, tool images are built
# (`make build-tools`), and Docker Desktop is sharing this drive.
#
# Usage:  ./scripts/run-auto-worker.ps1 [-Concurrency 2]
# =============================================================================
param(
    [int]$Concurrency = 2
)

$ErrorActionPreference = "Stop"
$root      = Split-Path -Parent $PSScriptRoot
$backend   = Join-Path $root "backend"
$envFile   = Join-Path $backend ".env"

if (-not (Test-Path $envFile)) {
    Write-Error "backend/.env not found - run scripts/setup first."
    exit 1
}

# Pull only the keys we need from backend/.env (KEY=VALUE, ignore comments).
$cfg = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)\s*$') { $cfg[$Matches[1]] = $Matches[2] }
}

# Redis is published to the host by docker-compose. Talk to it on localhost, not
# the compose-internal "redis" hostname.
$env:REDIS_HOST     = "127.0.0.1"
$env:REDIS_PORT     = if ($cfg.ContainsKey("REDIS_PORT")) { $cfg["REDIS_PORT"] } else { "6379" }
$env:REDIS_PASSWORD = $cfg["REDIS_PASSWORD"]

# Job workspaces live under backend/tmp_jobs/work; results under backend/tmp_jobs/results.
# Running natively, the worker path IS the daemon path, so no translation needed.
$workspace = Join-Path $backend "tmp_jobs\work"
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
$env:FORENSICSTACK_WORKSPACE = $workspace
# HOST_WORKSPACE_ROOT intentionally unset: native run, paths already match.

# Prefer the project venv's interpreter so deps resolve without activation.
$py = Join-Path $backend "forensic\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "[auto-worker] Redis  : $($env:REDIS_HOST):$($env:REDIS_PORT)"
Write-Host "[auto-worker] Workdir: $workspace"
Write-Host "[auto-worker] Consuming /analyze jobs (concurrency=$Concurrency). Ctrl-C to stop."

Push-Location $backend
try {
    & $py -u -m forensicstack.stream_worker --concurrency $Concurrency
} finally {
    Pop-Location
}

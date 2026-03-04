#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Automated Setup Script (Linux / macOS)
# =============================================================================
# Usage: chmod +x scripts/setup.sh && ./scripts/setup.sh
# Run from the repository root.
# =============================================================================

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[setup]${RESET} $*"; }
success() { echo -e "${GREEN}[setup] ✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}[setup] ⚠${RESET} $*"; }
error()   { echo -e "${RED}[setup] ✗${RESET} $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}══ $* ══${RESET}"; }

# ── Helpers ───────────────────────────────────────────────────────────────────
require() {
  if ! command -v "$1" &>/dev/null; then
    error "Required tool not found: $1 — install it first (see README)."
  fi
  success "$1 found: $(command -v "$1")"
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# =============================================================================
step "1/8 — Prerequisites check"
# =============================================================================

require docker
require python3
require node
require npm
require git

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
NODE_VERSION=$(node --version | tr -d 'v')
info "Python $PYTHON_VERSION | Node $NODE_VERSION"

# Validate Python >= 3.11
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 11 ]]; then
  error "Python 3.11+ required (found $PYTHON_VERSION)"
fi

# Validate Node >= 18
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
if [[ "$NODE_MAJOR" -lt 18 ]]; then
  error "Node.js 18+ required (found $NODE_VERSION)"
fi

# =============================================================================
step "2/8 — Backend — environment file"
# =============================================================================

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  # Auto-generate SECRET_KEY
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/replace_with_64_char_hex_secret/$SECRET/" backend/.env
  success "backend/.env created with a fresh SECRET_KEY"
  warn "Review backend/.env and change the default passwords before exposing this to a network."
else
  success "backend/.env already exists — skipping"
fi

# =============================================================================
step "3/8 — Frontend — environment file"
# =============================================================================

if [[ ! -f web/.env.local ]]; then
  cp web/.env.local.example web/.env.local
  success "web/.env.local created"
else
  success "web/.env.local already exists — skipping"
fi

# =============================================================================
step "4/8 — Docker infrastructure (postgres, redis, minio, chromadb)"
# =============================================================================

info "Starting infrastructure containers..."
docker compose -f backend/docker-compose.yml up -d postgres redis minio chromadb

info "Waiting for services to become healthy (up to 60 s)..."
TIMEOUT=60
ELAPSED=0
while true; do
  UNHEALTHY=$(docker compose -f backend/docker-compose.yml ps --format json 2>/dev/null \
    | python3 -c "
import sys, json
lines = sys.stdin.read().strip().splitlines()
count = 0
for line in lines:
    try:
        svc = json.loads(line)
        state = svc.get('Health', svc.get('State', ''))
        if state not in ('healthy', 'running', ''):
            count += 1
    except Exception:
        pass
print(count)
" 2>/dev/null || echo "0")

  if [[ "$UNHEALTHY" == "0" ]]; then
    success "All infrastructure containers are running"
    break
  fi
  if [[ "$ELAPSED" -ge "$TIMEOUT" ]]; then
    warn "Some containers may still be starting — check with: docker compose -f backend/docker-compose.yml ps"
    break
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  info "  Still waiting... (${ELAPSED}s)"
done

# =============================================================================
step "5/8 — Forensic tool Docker images + Volatility3 symbol cache"
# =============================================================================

IMAGES=("forensicstack/ileapp:0.1" "forensicstack/aleapp:0.1" "forensicstack/exiftool:0.1" "forensicstack/volatility:0.1")
ALL_EXIST=true
for img in "${IMAGES[@]}"; do
  if ! docker image inspect "$img" &>/dev/null; then
    ALL_EXIST=false
    break
  fi
done

if $ALL_EXIST; then
  success "All forensic tool images already built — skipping"
else
  info "Building forensic tool images (first build may take 5–15 minutes)..."
  chmod +x scripts/build-tools.sh
  bash scripts/build-tools.sh
fi

# ── Volatility3 symbol cache ────────────────────────────────────────────────────
# Check whether the named volume already has ISF symbol files.
# If yes: skip the ~350 MB download.  If no: seed it automatically.
VOL_COUNT=$(docker run --rm \
  -v forensicstack_vol3_symbols:/vol alpine \
  sh -c "find /vol/symbols/windows -name '*.json.xz' 2>/dev/null | wc -l" \
  2>/dev/null || echo "0")
VOL_COUNT="${VOL_COUNT//[^0-9]/}"   # strip whitespace / newlines

if [[ "${VOL_COUNT:-0}" -gt 100 ]]; then
  success "Volatility3 symbol cache already populated (${VOL_COUNT} ISF files) — skipping"
else
  info "Seeding Volatility3 symbol cache (~350 MB, one-time download)..."
  info "This pre-populates the cache volume so memory analysis works offline."
  chmod +x scripts/seed-vol3-symbols.sh
  bash scripts/seed-vol3-symbols.sh
fi

# =============================================================================
step "6/8 — Backend — Python virtual environment"
# =============================================================================

if [[ ! -d backend/venv ]]; then
  info "Creating virtual environment..."
  python3 -m venv backend/venv
  success "venv created at backend/venv"
else
  success "backend/venv already exists — skipping creation"
fi

info "Installing Python dependencies..."
backend/venv/bin/pip install --quiet --upgrade pip
backend/venv/bin/pip install --quiet -r backend/requirements.txt
success "Python dependencies installed"

# =============================================================================
step "7/8 — Frontend — Node dependencies"
# =============================================================================

info "Installing frontend dependencies with 'npm ci' (reproducible install)..."
cd web
npm ci --silent
cd "$REPO_ROOT"
success "Frontend dependencies installed"

# =============================================================================
step "8/8 — Done!"
# =============================================================================

echo ""
echo -e "${GREEN}${BOLD}ForensicStack is ready.${RESET}"
echo ""
echo -e "  ${BOLD}Start the API (terminal 1):${RESET}"
echo -e "  ${CYAN}cd backend && source venv/bin/activate${RESET}"
echo -e "  ${CYAN}uvicorn forensicstack.api.main:app --host 0.0.0.0 --port 8001 --reload${RESET}"
echo ""
echo -e "  ${BOLD}Start the worker (terminal 2):${RESET}"
echo -e "  ${CYAN}cd backend && source venv/bin/activate && python -m forensicstack.worker${RESET}"
echo ""
echo -e "  ${BOLD}Start the frontend (terminal 3):${RESET}"
echo -e "  ${CYAN}cd web && npm run dev${RESET}"
echo ""
echo -e "  ${BOLD}Create your first account:${RESET}"
echo -e "  ${CYAN}curl -X POST http://localhost:8001/auth/register \\${RESET}"
echo -e "  ${CYAN}  -H 'Content-Type: application/json' \\${RESET}"
echo -e "  ${CYAN}  -d '{\"username\":\"analyst\",\"password\":\"YourStrongPassword!\"}'${RESET}"
echo ""
echo -e "  ${BOLD}Open:${RESET}  http://localhost:3000"
echo -e "  ${BOLD}Docs:${RESET}  http://localhost:8001/docs"
echo ""
echo -e "${YELLOW}⚠  Never run 'npm audit fix --force' — it upgrades major versions and breaks the build.${RESET}"
echo ""

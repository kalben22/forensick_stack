#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Master setup script (Linux / macOS)
#
# Runs ONCE after cloning to prepare every component:
#   1. Docker images for Linux-container tools (iLEAPP, aLEAPP, ExifTool, Volatility3)
#   2. Volatility3 Windows symbol tables (seeded into a named Docker volume)
#
# Note: EZ Tools are Windows-only — run setup.ps1 on a Windows host for that.
#
# Usage (from repo root):
#   chmod +x setup.sh && ./setup.sh
#
# Skip individual steps:
#   ./setup.sh --skip-docker-images
#   ./setup.sh --skip-volatility-symbols
#
# Requirements: Docker, git, bash
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SKIP_DOCKER=0
SKIP_SYMBOLS=0

for arg in "$@"; do
    case $arg in
        --skip-docker-images)    SKIP_DOCKER=1 ;;
        --skip-volatility-symbols) SKIP_SYMBOLS=1 ;;
    esac
done

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step()  { echo -e "\n${CYAN}==> $1${NC}"; }
ok()    { echo -e "    ${GREEN}[OK] $1${NC}"; }
warn()  { echo -e "    ${YELLOW}[!!] $1${NC}"; }
fail()  { echo -e "    ${RED}[FAIL] $1${NC}"; exit 1; }

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
step "Checking prerequisites"

command -v docker &>/dev/null || fail "Docker not found. Install from https://www.docker.com"
docker info &>/dev/null      || fail "Docker daemon is not running. Start Docker first."
ok "Docker is running"

command -v git &>/dev/null   || fail "git not found."
ok "git is available"

# ---------------------------------------------------------------------------
# Step 1 — Build Docker images
# ---------------------------------------------------------------------------
if [[ $SKIP_DOCKER -eq 0 ]]; then
    step "Building Docker images for Linux-container tools"
    bash "$SCRIPT_DIR/scripts/build-tools.sh" ileapp
    bash "$SCRIPT_DIR/scripts/build-tools.sh" aleapp
    bash "$SCRIPT_DIR/scripts/build-tools.sh" exiftool
    bash "$SCRIPT_DIR/scripts/build-tools.sh" volatility
    ok "All Docker images built"
else
    warn "Skipping Docker image builds (--skip-docker-images)"
fi

# ---------------------------------------------------------------------------
# Step 2 — Seed Volatility3 Windows symbol tables
# ---------------------------------------------------------------------------
if [[ $SKIP_SYMBOLS -eq 0 ]]; then
    step "Seeding Volatility3 symbol tables (one-time download ~200-400 MB)"
    bash "$SCRIPT_DIR/scripts/seed-vol3-symbols.sh"
    ok "Volatility3 symbols ready"
else
    warn "Skipping Volatility3 symbols (--skip-volatility-symbols)"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  ForensicStack setup complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and fill in your secrets"
echo "  2. docker compose up -d"
echo "  3. Open http://localhost:3000"
echo ""
echo -e "${YELLOW}Note: EZ Tools (Windows forensics) require a Windows host.${NC}"
echo -e "${YELLOW}      Run .\\setup.ps1 on Windows to install them.${NC}"
echo ""

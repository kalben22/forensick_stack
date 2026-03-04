#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Build forensic tool Docker images
#
# Run this ONCE after cloning, before submitting any analysis jobs.
# Each image wraps a forensic tool in an isolated container that the
# ForensicStack worker will spin up on demand.
#
# Usage:
#   chmod +x scripts/build-tools.sh
#   ./scripts/build-tools.sh
#
# Build a single tool:
#   ./scripts/build-tools.sh exiftool
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGINS_DIR="$SCRIPT_DIR/../backend/forensicstack/plugins/external"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

build_image() {
    local name="$1"
    local tag="$2"
    local dir="$3"

    echo -e "${YELLOW}[build-tools] Building $tag ...${NC}"
    if docker build -t "$tag" "$dir"; then
        echo -e "${GREEN}[build-tools] $tag — OK${NC}"
    else
        echo -e "${RED}[build-tools] $tag — FAILED${NC}"
        exit 1
    fi
}

# Allow building a single tool: ./build-tools.sh exiftool
FILTER="${1:-all}"

if [[ "$FILTER" == "all" || "$FILTER" == "ileapp" ]]; then
    build_image "iLEAPP"      "forensicstack/ileapp:0.1"      "$PLUGINS_DIR/ileapp"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "aleapp" ]]; then
    build_image "ALEAPP"      "forensicstack/aleapp:0.1"      "$PLUGINS_DIR/aleapp"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "exiftool" ]]; then
    build_image "ExifTool"    "forensicstack/exiftool:0.1"    "$PLUGINS_DIR/exiftool"
fi

if [[ "$FILTER" == "all" || "$FILTER" == "volatility" ]]; then
    build_image "Volatility3" "forensicstack/volatility:0.1"  "$PLUGINS_DIR/volatility"
    echo ""
    echo -e "${GREEN}[build-tools] Volatility3 image built with common Windows kernel symbols baked in.${NC}"
    echo -e "${YELLOW}[build-tools] ⚠  For extended offline coverage (uncommon kernel versions),${NC}"
    echo -e "${YELLOW}[build-tools]    pre-populate the symbol cache volume by running ONCE:${NC}"
    echo -e "${GREEN}               ./scripts/seed-vol3-symbols.sh          (Linux / Mac)${NC}"
    echo -e "${GREEN}               .\\scripts\\seed-vol3-symbols.ps1         (Windows PowerShell)${NC}"
    echo -e "${YELLOW}[build-tools]    (the setup script does this automatically on first install)${NC}"
    echo ""
fi

if [[ "$FILTER" == "all" || "$FILTER" == "eztools" ]]; then
    echo ""
    echo -e "${YELLOW}[build-tools] EZ Tools run natively on the Windows host — no Docker image needed.${NC}"
    echo -e "${YELLOW}[build-tools] Install EZ Tools once on the Windows host with:${NC}"
    echo -e "${GREEN}               .\\scripts\\install-eztools.ps1${NC}"
    echo ""
fi

echo ""
echo -e "${GREEN}All forensic tool images are ready.${NC}"
echo "Verify with:  docker images | grep forensicstack"

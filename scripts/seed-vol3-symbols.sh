#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Seed Volatility3 Windows symbol cache (run ONCE per machine)
#
# Downloads the official Windows ISF symbol tables from the Volatility
# Foundation and stores them in the named Docker volume
# forensicstack_vol3_symbols so Volatility3 containers can analyse uncommon
# kernel versions without needing an internet connection at analysis time.
#
# Note: common Windows kernel symbols are already baked into the Docker image
# at build time. This script pre-populates the CACHE VOLUME as a supplement,
# ensuring offline analysis and faster first-run results for all kernel versions.
#
# Usage:
#   chmod +x scripts/seed-vol3-symbols.sh && ./scripts/seed-vol3-symbols.sh
#
# Requirements: wget or curl, unzip, docker
# =============================================================================
set -euo pipefail

URL="https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip"
VOLUME="forensicstack_vol3_symbols"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RESET='\033[0m'

echo -e "${CYAN}[vol3-symbols]${RESET} Seeding Volatility3 Windows symbol cache"
echo -e "${CYAN}[vol3-symbols]${RESET}   Source : $URL"
echo -e "${CYAN}[vol3-symbols]${RESET}   Volume : $VOLUME"
echo ""

# ── 1. Download ───────────────────────────────────────────────────────────────
echo -e "${CYAN}[1/3]${RESET} Downloading windows.zip (~350 MB compressed)..."
echo       "      This may take several minutes depending on your connection."

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

if command -v wget &>/dev/null; then
    wget -q --show-progress -O "$TMP/windows.zip" "$URL"
elif command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$TMP/windows.zip" "$URL"
else
    echo "ERROR: wget or curl is required to download symbols." >&2
    exit 1
fi

SIZE_MB=$(du -m "$TMP/windows.zip" | cut -f1)
echo "      Downloaded: ${SIZE_MB} MB"

# ── 2. Extract ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[2/3]${RESET} Extracting symbols..."
unzip -q "$TMP/windows.zip" -d "$TMP/"

if [[ ! -d "$TMP/windows" ]]; then
    echo "ERROR: Extraction failed — 'windows/' directory not found in zip." >&2
    exit 1
fi

COUNT=$(find "$TMP/windows" -name '*.json.xz' | wc -l)
echo "      ${COUNT} ISF files extracted."

# ── 3. Copy into Docker volume ─────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[3/3]${RESET} Copying into Docker volume '${VOLUME}'..."
docker run --rm \
    -v "${VOLUME}:/target" \
    -v "${TMP}/windows:/source:ro" \
    alpine sh -c "mkdir -p /target/symbols/windows && cp -r /source/. /target/symbols/windows/"

INSTALLED=$(docker run --rm -v "${VOLUME}:/vol" alpine \
    sh -c "find /vol/symbols/windows -name '*.json.xz' 2>/dev/null | wc -l")

echo ""
echo -e "${GREEN}[vol3-symbols] Done! ${INSTALLED} ISF files in volume '${VOLUME}'.${RESET}"
echo    "               Volatility3 analysis will now work offline for all common Windows kernels."

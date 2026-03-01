#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Seed Volatility3 Windows symbol tables (run ONCE)
#
# Downloads the 4 NT kernel PDB directories from the community symbols repo
# directly on the HOST (no Docker network dependency), then copies them into
# the named Docker volume forensicstack_vol3_symbols.
#
# Usage:
#   chmod +x scripts/seed-vol3-symbols.sh
#   ./scripts/seed-vol3-symbols.sh
#
# Requirements: git, docker
# =============================================================================
set -euo pipefail

REPO="https://github.com/Abyss-W4tcher/volatility3-symbols.git"
VOLUME="forensicstack_vol3_symbols"

echo "[ForensicStack] Downloading Volatility3 NT kernel symbols onto the host..."
echo "               (ntkrnlmp, ntkrpamp, ntoskrnl, ntkrnlpa — covers Win7-11 32/64-bit)"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

git clone --depth 1 --sparse "$REPO" "$TMP"
cd "$TMP"
git sparse-checkout set \
    windows/ntkrnlmp.pdb \
    windows/ntkrpamp.pdb \
    windows/ntoskrnl.pdb \
    windows/ntkrnlpa.pdb

echo "[ForensicStack] Copying symbols into Docker volume '$VOLUME'..."
docker run --rm \
    -v "${VOLUME}:/target" \
    -v "${TMP}/windows:/source:ro" \
    alpine sh -c "mkdir -p /target/symbols/windows && cp -r /source/. /target/symbols/windows/"

echo ""
echo "[ForensicStack] Done! Symbols are stored in volume '$VOLUME'."
echo "                Volatility3 containers will find them at:"
echo "                /root/.cache/volatility3/symbols/windows/"

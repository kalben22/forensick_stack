#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Volatility3 container entrypoint
#
# Mounts:
#   /data    (ro) — directory containing the memory image
#   /output  (rw) — results will be written here as JSON files
#
# Environment:
#   JOB_ID            — used to prefix output filenames (set by DockerExecutor)
#   VOLATILITY_PLUGIN — specific plugin to run (default: windows.pslist)
#
# First-run behaviour:
#   If NT kernel ISF symbols are missing from the volume cache, they are
#   downloaded automatically via git partial clone (--filter=blob:none +
#   --sparse).  The named Docker volume forensicstack_vol3_symbols persists
#   them for all subsequent runs.
#
# Why git clone (not git init + fetch):
#   git clone --filter=blob:none sets up the "partialclonefilter" in
#   .git/config, enabling lazy blob fetching when git sparse-checkout set
#   checks out the requested paths.  git init + git fetch does NOT configure
#   this, so git checkout silently fails to retrieve blobs.
# =============================================================================
set -euo pipefail

INPUT_DIR="/data"
OUTPUT_DIR="/output"
JOB_ID="${JOB_ID:-default}"
VOL="/app/volatility3/vol.py"
SYMBOLS_DIR="/root/.cache/volatility3/symbols/windows"

# ---------------------------------------------------------------------------
# Auto-seed symbols on first run
# ---------------------------------------------------------------------------
if [ ! -d "${SYMBOLS_DIR}/ntkrnlmp.pdb" ] && [ ! -d "${SYMBOLS_DIR}/ntkrpamp.pdb" ]; then
    echo "[volatility] First run: no symbol tables found."
    echo "[volatility] Downloading NT kernel ISF symbols — this is a one-time step."
    echo "[volatility] Symbols will be persisted in the Docker volume for future runs."

    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT

    # Phase 1: shallow partial clone — metadata only (~900 KB), no blobs yet.
    # --sparse starts the repo in cone mode (only root-level entries).
    # --filter=blob:none + git clone (not git init) sets partialclonefilter
    # so that phase 2 can do lazy blob fetches.
    echo "[volatility] Phase 1/2 — cloning metadata (~900 KB)..."
    git clone \
        --depth=1 \
        --filter=blob:none \
        --sparse \
        https://github.com/Abyss-W4tcher/volatility3-symbols.git \
        "$TMP"

    cd "$TMP"

    # Phase 2: set sparse checkout patterns and check out.
    # git sparse-checkout set triggers a working-tree update; because the
    # partial clone filter is active, git fetches only the blobs for the
    # 4 requested PDB directories (~200-400 MB total).
    echo "[volatility] Phase 2/2 — downloading 4 NT kernel PDB directories..."
    git sparse-checkout set \
        windows/ntkrnlmp.pdb \
        windows/ntkrpamp.pdb \
        windows/ntoskrnl.pdb \
        windows/ntkrnlpa.pdb

    if [ -d windows ]; then
        mkdir -p "${SYMBOLS_DIR}"
        cp -r windows/. "${SYMBOLS_DIR}/"
        echo "[volatility] Symbols cached at ${SYMBOLS_DIR}"
    else
        echo "[volatility] WARNING: symbol download did not produce windows/ directory."
        echo "[volatility]   Fallback: run the host seed script to populate the volume:"
        echo "[volatility]     Windows: .\\scripts\\seed-vol3-symbols.ps1"
        echo "[volatility]     Linux:   ./scripts/seed-vol3-symbols.sh"
    fi
fi

# ---------------------------------------------------------------------------
# Find the input file
# ---------------------------------------------------------------------------
INPUT_FILE=$(find "$INPUT_DIR" -maxdepth 2 -type f | head -1)

if [[ -z "$INPUT_FILE" ]]; then
    echo "[volatility] ERROR: No input file found in $INPUT_DIR"
    exit 1
fi

echo "[volatility] Input : $INPUT_FILE"
echo "[volatility] Job   : $JOB_ID"

# ---------------------------------------------------------------------------
# Run the requested plugin
# ---------------------------------------------------------------------------
PLUGIN="${VOLATILITY_PLUGIN:-windows.pslist}"
safe_name="${PLUGIN//./_}"
outfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.json"
logfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.log"

echo "[volatility] Running: $PLUGIN"
python "$VOL" -f "$INPUT_FILE" --renderer json "$PLUGIN" \
    > "$outfile" 2>"$logfile" || true

# Always surface stderr so docker logs / the worker can see what went wrong
if [[ -s "$logfile" ]]; then
    echo "[volatility] --- stderr ---"
    cat "$logfile"
    echo "[volatility] --- end stderr ---"
fi

echo "[volatility] Done — result in $outfile"

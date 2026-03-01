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
#   If the NT kernel ISF symbol tables are absent from the volume cache
#   (/root/.cache/volatility3/symbols/windows), they are downloaded
#   automatically before analysis.  The named Docker volume
#   forensicstack_vol3_symbols persists them for all subsequent runs.
# =============================================================================
set -euo pipefail

INPUT_DIR="/data"
OUTPUT_DIR="/output"
JOB_ID="${JOB_ID:-default}"
VOL="/app/volatility3/vol.py"
SYMBOLS_DIR="/root/.cache/volatility3/symbols/windows"

# ---------------------------------------------------------------------------
# Auto-seed symbols on first run
# The container has --network bridge so it can reach GitHub.
# Two-phase download:
#   1. git fetch --filter=blob:none  =>  metadata only  (~900 KB)
#   2. git read-tree + git checkout -- <paths>  =>  blobs for 4 PDB dirs only
# ---------------------------------------------------------------------------
if [ ! -d "${SYMBOLS_DIR}/ntkrnlmp.pdb" ] && [ ! -d "${SYMBOLS_DIR}/ntkrpamp.pdb" ]; then
    echo "[volatility] First run: no symbol tables found."
    echo "[volatility] Downloading NT kernel ISF symbols (~200-400 MB) — this is a one-time step."
    echo "[volatility] Symbols will be cached in the volume for all future runs."

    TMP=$(mktemp -d)
    cd "$TMP"

    git init .
    git remote add origin https://github.com/Abyss-W4tcher/volatility3-symbols.git

    echo "[volatility] Phase 1/2 — fetching metadata..."
    git fetch --depth 1 --filter=blob:none origin master

    echo "[volatility] Phase 2/2 — downloading symbol blobs..."
    git read-tree FETCH_HEAD
    git checkout -- \
        windows/ntkrnlmp.pdb \
        windows/ntkrpamp.pdb \
        windows/ntoskrnl.pdb \
        windows/ntkrnlpa.pdb 2>&1 || true

    if [ -d windows ]; then
        mkdir -p "${SYMBOLS_DIR}"
        cp -r windows/. "${SYMBOLS_DIR}/"
        echo "[volatility] Symbols cached at ${SYMBOLS_DIR}"
    else
        echo "[volatility] WARNING: symbol download did not produce windows/ — analysis may fail."
    fi

    cd / && rm -rf "$TMP"
fi

# ---------------------------------------------------------------------------
# Find the input file
# ---------------------------------------------------------------------------
INPUT_FILE=$(find "$INPUT_DIR" -maxdepth 2 -type f | head -1)

if [[ -z "$INPUT_FILE" ]]; then
    echo "[volatility] ERROR: No input file found in $INPUT_DIR"
    exit 1
fi

echo "[volatility] Input: $INPUT_FILE"
echo "[volatility] Job: $JOB_ID"

# Read plugin from env var — default to windows.pslist if not set
PLUGIN="${VOLATILITY_PLUGIN:-windows.pslist}"
safe_name="${PLUGIN//./_}"
outfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.json"
logfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.log"

echo "[volatility] Running: $PLUGIN"
python "$VOL" -f "$INPUT_FILE" --renderer json "$PLUGIN" \
    > "$outfile" 2>"$logfile" || true

# Print captured errors so docker logs / worker can see them
if [[ -s "$logfile" ]]; then
    echo "[volatility] Stderr output:"
    cat "$logfile"
fi

echo "[volatility] Done — result in $outfile"

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
# Symbol tables:
#   Downloaded automatically on first run from the official Volatility
#   Foundation CDN (windows.zip, ~300-400 MB).  The named Docker volume
#   forensicstack_vol3_symbols persists them for all subsequent runs.
# =============================================================================
set -euo pipefail

INPUT_DIR="/data"
OUTPUT_DIR="/output"
JOB_ID="${JOB_ID:-default}"
SYMBOLS_BASE="/root/.cache/volatility3/symbols"
SYMBOLS_DIR="${SYMBOLS_BASE}/windows"

# ---------------------------------------------------------------------------
# Auto-seed symbols on first run
# ---------------------------------------------------------------------------
if [ ! -d "${SYMBOLS_DIR}/ntkrnlmp.pdb" ] && [ ! -d "${SYMBOLS_DIR}/ntkrpamp.pdb" ]; then
    echo "[volatility] First run: no symbol tables found."
    echo "[volatility] Downloading Windows ISF symbols from Volatility Foundation..."
    echo "[volatility] This is a one-time step (~300-400 MB). Symbols will be"
    echo "[volatility] persisted in the Docker volume for all future runs."

    mkdir -p "${SYMBOLS_BASE}"

    wget -q --show-progress \
        "https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip" \
        -O /tmp/windows.zip

    echo "[volatility] Extracting symbols..."
    unzip -q /tmp/windows.zip -d "${SYMBOLS_BASE}"
    rm -f /tmp/windows.zip

    COUNT=$(find "${SYMBOLS_DIR}" -name '*.json.xz' 2>/dev/null | wc -l)
    echo "[volatility] Symbols ready: ${COUNT} ISF files installed at ${SYMBOLS_DIR}"
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
vol -f "$INPUT_FILE" --renderer json "$PLUGIN" \
    > "$outfile" 2>"$logfile" || true

# Always surface stderr so docker logs / the worker can see what went wrong
if [[ -s "$logfile" ]]; then
    echo "[volatility] --- stderr ---"
    cat "$logfile"
    echo "[volatility] --- end stderr ---"
fi

echo "[volatility] Done — result in $outfile"

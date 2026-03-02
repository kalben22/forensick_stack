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
# Symbol tables are baked into the image at build time — no runtime download,
# no Docker volume needed.  Rebuild the image to get updated symbols.
# =============================================================================
set -euo pipefail

INPUT_DIR="/data"
OUTPUT_DIR="/output"
JOB_ID="${JOB_ID:-default}"

# ---------------------------------------------------------------------------
# Find the input file
# ---------------------------------------------------------------------------
INPUT_FILE=$(find "$INPUT_DIR" -maxdepth 2 -type f | head -1)

if [[ -z "$INPUT_FILE" ]]; then
    echo "[volatility] ERROR: No input file found in $INPUT_DIR"
    exit 1
fi

echo "[volatility] Input  : $INPUT_FILE"
echo "[volatility] Job    : $JOB_ID"

# ---------------------------------------------------------------------------
# Run the requested plugin
# ---------------------------------------------------------------------------
PLUGIN="${VOLATILITY_PLUGIN:-windows.pslist}"
safe_name="${PLUGIN//./_}"
outfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.json"
logfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.log"

echo "[volatility] Plugin : $PLUGIN"
vol -f "$INPUT_FILE" --renderer json "$PLUGIN" \
    > "$outfile" 2>"$logfile" || true

# Always surface stderr so docker logs / the worker can see what went wrong
if [[ -s "$logfile" ]]; then
    echo "[volatility] --- stderr ---"
    cat "$logfile"
    echo "[volatility] --- end stderr ---"
fi

echo "[volatility] Done — result in $outfile"

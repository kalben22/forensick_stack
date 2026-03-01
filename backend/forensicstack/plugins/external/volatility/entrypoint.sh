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
# =============================================================================
set -euo pipefail

INPUT_DIR="/data"
OUTPUT_DIR="/output"
JOB_ID="${JOB_ID:-default}"
VOL="/app/volatility3/vol.py"

# Find the first file inside /data (memory image)
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

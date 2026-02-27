#!/usr/bin/env bash
# =============================================================================
# ForensicStack — Volatility3 container entrypoint
#
# Mounts:
#   /data    (ro) — directory containing the memory image
#   /output  (rw) — results will be written here as JSON files
#
# Environment:
#   JOB_ID   — used to prefix output filenames (set by DockerExecutor)
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

# Standard plugin set — run each and capture JSON output.
# Failures are tolerated (|| true) so a single plugin error does not abort.
PLUGINS=(
    "windows.pslist"
    "windows.cmdline"
    "windows.netscan"
    "windows.dlllist"
    "windows.malfind"
)

for plugin in "${PLUGINS[@]}"; do
    safe_name="${plugin//./_}"
    outfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.json"
    echo "[volatility] Running: $plugin"
    python "$VOL" -f "$INPUT_FILE" --renderer json "$plugin" \
        > "$outfile" 2>/dev/null || true
done

echo "[volatility] Done — results in $OUTPUT_DIR"

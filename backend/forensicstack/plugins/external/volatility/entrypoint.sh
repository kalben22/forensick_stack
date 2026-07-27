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
# Symbol tables are baked into the image at build time.  When a dump requires
# additional PDB files (uncommon kernel version), Volatility downloads them
# from Microsoft Symbol Server and caches them in /root/.cache/volatility3
# (mapped to the named Docker volume forensicstack_vol3_symbols).
# A single retry is performed if the first run produces no output — this covers
# the case where the first-ever symbol download times out or is interrupted.
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Ensure identifier.cache is populated (named volume may shadow baked copy)
# ---------------------------------------------------------------------------
CACHE_FILE="/root/.cache/volatility3/identifier.cache"
BAKED_COPY="/app/identifier.cache.baked"

_cache_entries() {
    python3 -c "
import sqlite3, os
db = '$CACHE_FILE'
if not os.path.exists(db):
    print(0)
else:
    try:
        print(sqlite3.connect(db).execute('SELECT COUNT(*) FROM cache').fetchone()[0])
    except Exception:
        print(0)
" 2>/dev/null || echo 0
}

if [[ -f "$BAKED_COPY" ]]; then
    entries=$(_cache_entries)
    if [[ "$entries" -lt 100 ]]; then
        echo "[volatility] identifier.cache empty ($entries entries) — restoring baked copy..."
        mkdir -p "$(dirname "$CACHE_FILE")"
        cp "$BAKED_COPY" "$CACHE_FILE"
        echo "[volatility] identifier.cache restored"
    else
        echo "[volatility] identifier.cache OK ($entries entries)"
    fi
fi

# INPUT_PATH / OUTPUT_PATH are injected by DockerExecutor:
#   - DooD mode  : absolute paths inside the shared /app volume
#   - Native mode: /data and /output (bind mount targets)
INPUT_DIR="${INPUT_PATH:-/data}"
OUTPUT_DIR="${OUTPUT_PATH:-/output}"
JOB_ID="${JOB_ID:-default}"

# ---------------------------------------------------------------------------
# Find the input file
# ---------------------------------------------------------------------------
# Prefer INPUT_FILENAME when available (deterministic, avoids `find` ordering).
if [[ -n "${INPUT_FILENAME:-}" && -f "$INPUT_DIR/$INPUT_FILENAME" ]]; then
    INPUT_FILE="$INPUT_DIR/$INPUT_FILENAME"
else
    INPUT_FILE=$(find "$INPUT_DIR" -maxdepth 2 -type f | head -1)
fi

if [[ -z "$INPUT_FILE" ]]; then
    echo "[volatility] ERROR: No input file found in $INPUT_DIR"
    exit 1
fi

echo "[volatility] Input  : $INPUT_FILE"
echo "[volatility] Job    : $JOB_ID"

# ---------------------------------------------------------------------------
# Run the requested plugin (with one automatic retry on empty output)
# ---------------------------------------------------------------------------
PLUGIN="${VOLATILITY_PLUGIN:-windows.pslist}"
safe_name="${PLUGIN//./_}"
outfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.json"
logfile="${OUTPUT_DIR}/${JOB_ID}_${safe_name}.log"

echo "[volatility] Plugin : $PLUGIN"

run_vol() {
    vol -f "$INPUT_FILE" --renderer json "$PLUGIN" \
        > "$outfile" 2>"$logfile" || true
}

run_vol

# If the output file is empty (0 bytes), the run likely failed due to a
# first-run symbol download issue.  Retry once after a short delay so the
# cached PDB/ISF file from the first attempt is available.
if [[ ! -s "$outfile" ]]; then
    echo "[volatility] Output empty on first attempt — retrying in 5 s..."
    rm -f "$outfile"
    sleep 5
    run_vol
fi

# Always surface stderr so docker logs / the worker can see diagnostics
if [[ -s "$logfile" ]]; then
    echo "[volatility] --- stderr ---"
    cat "$logfile"
    echo "[volatility] --- end stderr ---"
fi

echo "[volatility] Done — result in $outfile"

#!/usr/bin/env bash
set -e

# INPUT_PATH / OUTPUT_PATH injected by DockerExecutor
INPUT="${INPUT_PATH:-/data}"
OUTPUT="${OUTPUT_PATH:-/output}"
JOB_ID="${JOB_ID:-default}"

OUTFILE="${OUTPUT}/${JOB_ID}_raw.json"

echo "[entrypoint] Running ExifTool"

LOGFILE="${OUTPUT}/${JOB_ID}_raw.log"
exiftool -json -charset UTF8 -r "$INPUT" > "$OUTFILE" 2>"$LOGFILE" || true

if [[ -s "$LOGFILE" ]]; then
    echo "[exiftool] Stderr output:"
    cat "$LOGFILE"
fi

echo "[entrypoint] Done"
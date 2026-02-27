#!/usr/bin/env bash
set -e

INPUT="/data"
OUTPUT="/output"
JOB_ID="${JOB_ID:-default}"

OUTFILE="${OUTPUT}/${JOB_ID}_raw.json"

echo "[entrypoint] Running ExifTool"

exiftool -json -charset UTF8 -r "$INPUT" > "$OUTFILE" 2>/dev/null || true

echo "[entrypoint] Done"
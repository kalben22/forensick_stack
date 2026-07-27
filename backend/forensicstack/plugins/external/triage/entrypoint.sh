#!/bin/sh
# Contract: read $INPUT_PATH, write to $OUTPUT_PATH, propagate the exit code.
#
# Note the absence of a trailing `|| true`. The exiftool and volatility
# entrypoints both ended their tool invocation with `|| true`, so the container
# always exited 0 and the executor's exit-code check could never fire — a
# crashed tool was indistinguishable from one that found nothing.
set -eu

: "${INPUT_PATH:?INPUT_PATH is not set}"
: "${OUTPUT_PATH:=/output}"

if [ ! -f "$INPUT_PATH" ]; then
    echo "entrypoint: input file not found: $INPUT_PATH" >&2
    exit 2
fi

exec python3 /opt/triage/triage_scan.py

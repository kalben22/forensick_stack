#!/bin/bash

# INPUT_PATH / OUTPUT_PATH injected by DockerExecutor
INPUT="${INPUT_PATH:-/data}"
OUTPUT="${OUTPUT_PATH:-/output}"
SCRIPT="/app/iLEAPP/ileapp.py"

TYPE="${ILEAPP_TYPE:-fs}"

echo "[entrypoint] running: python $SCRIPT -t $TYPE -i $INPUT -o $OUTPUT"

python "$SCRIPT" -t "$TYPE" -i "$INPUT" -o "$OUTPUT"
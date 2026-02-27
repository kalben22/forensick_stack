#!/bin/bash

INPUT="/data"
OUTPUT="/output"
SCRIPT="/app/iLEAPP/ileapp.py"

TYPE="${ILEAPP_TYPE:-fs}"

echo "[entrypoint] running: python $SCRIPT -t $TYPE -i $INPUT -o $OUTPUT"

python "$SCRIPT" -t "$TYPE" -i "$INPUT" -o "$OUTPUT"
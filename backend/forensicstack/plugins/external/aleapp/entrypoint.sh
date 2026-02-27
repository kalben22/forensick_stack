#!/bin/bash

INPUT="/data"
OUTPUT="/output"
SCRIPT="/app/ALEAPP/aleapp.py"

TYPE="${ALEAPP_TYPE:-fs}"

echo "[entrypoint] running: python $SCRIPT -t $TYPE -i $INPUT -o $OUTPUT"

python "$SCRIPT" -t "$TYPE" -i "$INPUT" -o "$OUTPUT"
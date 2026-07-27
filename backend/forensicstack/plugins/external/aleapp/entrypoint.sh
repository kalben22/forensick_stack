#!/bin/bash

# INPUT_PATH / OUTPUT_PATH injected by DockerExecutor
INPUT="${INPUT_PATH:-/data}"
OUTPUT="${OUTPUT_PATH:-/output}"
SCRIPT="/opt/ALEAPP/aleapp.py"

TYPE="${ALEAPP_TYPE:-fs}"
FILENAME="${INPUT_FILENAME:-}"
EXT="${FILENAME##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')

if [[ "$EXT_LOWER" == "dd" || "$EXT_LOWER" == "img" || "$EXT_LOWER" == "e01" ]]; then
    # Locate the actual file
    if [ -f "$INPUT" ]; then
        IMG_FILE="$INPUT"
    else
        IMG_FILE="$INPUT/$FILENAME"
    fi

    EXTRACT_DIR="$OUTPUT/_extracted_fs"
    mkdir -p "$EXTRACT_DIR"

    echo "[entrypoint] Disk image detected — extracting filesystem with tsk_recover..."

    # Try direct extraction (single-partition image)
    tsk_recover -e "$IMG_FILE" "$EXTRACT_DIR" 2>/tmp/tsk_err
    TSK_RC=$?

    if [ $TSK_RC -ne 0 ]; then
        # Partitioned disk image: find the largest Linux/Android partition by offset
        OFFSET=$(mmls "$IMG_FILE" 2>/dev/null \
            | awk '/[0-9]/{print $3, $6}' \
            | sort -k2 -rn \
            | head -1 \
            | awk '{print $1}')

        if [ -n "$OFFSET" ]; then
            echo "[entrypoint] Partitioned image — using offset $OFFSET"
            tsk_recover -e -o "$OFFSET" "$IMG_FILE" "$EXTRACT_DIR"
        else
            echo "[entrypoint] tsk_recover failed and no partition found:" >&2
            cat /tmp/tsk_err >&2
            exit 1
        fi
    fi

    echo "[entrypoint] Extraction done — running: python $SCRIPT -t fs -i $EXTRACT_DIR -o $OUTPUT"
    python "$SCRIPT" -t fs -i "$EXTRACT_DIR" -o "$OUTPUT"
    RC=$?

    # Clean up extracted filesystem to free space
    rm -rf "$EXTRACT_DIR"
    exit $RC
else
    echo "[entrypoint] running: python $SCRIPT -t $TYPE -i $INPUT -o $OUTPUT"
    python "$SCRIPT" -t "$TYPE" -i "$INPUT" -o "$OUTPUT"
fi

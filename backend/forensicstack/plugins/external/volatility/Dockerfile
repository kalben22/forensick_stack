FROM python:3.11-slim

WORKDIR /app

# Build tools for yara-python (C extension); wget + unzip for symbol tables
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Volatility3 from PyPI (stable release)
RUN pip install --no-cache-dir volatility3 pefile yara-python

# ── Bake Windows ISF symbol tables into the Volatility3 PACKAGE directory ───
# Symbols go into the Python package dir (not /root/.cache) so they are never
# hidden when a Docker volume is mounted at /root/.cache/volatility3 for
# caching dynamically-downloaded PDBs.  Docker layer cache means this
# 300-400 MB download only happens ONCE per machine.
RUN VOL3_SYM_DIR=$(python3 -c "import volatility3, os; print(os.path.join(os.path.dirname(volatility3.__file__), 'symbols'))") && \
    mkdir -p "$VOL3_SYM_DIR" && \
    wget -q --show-progress \
        "https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip" \
        -O /tmp/windows.zip && \
    unzip -q /tmp/windows.zip -d "$VOL3_SYM_DIR/" && \
    rm /tmp/windows.zip && \
    echo "Symbols baked in: $(find $VOL3_SYM_DIR/windows -name '*.json.xz' | wc -l) ISF files at $VOL3_SYM_DIR"

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
# Strip Windows CRLF line endings in case the file was checked out on Windows
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

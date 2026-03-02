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

# ── Bake Windows ISF symbol tables into the image at build time ─────────────
# Docker layer cache means this 300-400 MB download only happens ONCE per
# machine, even if you rebuild the image later (as long as this RUN line
# doesn't change).  No runtime download, no Docker volume needed for symbols.
RUN mkdir -p /root/.cache/volatility3/symbols && \
    wget -q --show-progress \
        "https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip" \
        -O /tmp/windows.zip && \
    unzip -q /tmp/windows.zip -d /root/.cache/volatility3/symbols/ && \
    rm /tmp/windows.zip && \
    echo "Symbols baked in: $(find /root/.cache/volatility3/symbols/windows -name '*.json.xz' | wc -l) ISF files"

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
# Strip Windows CRLF line endings in case the file was checked out on Windows
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

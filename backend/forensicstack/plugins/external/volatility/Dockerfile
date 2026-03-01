FROM python:3.11-slim

WORKDIR /app

# System deps: git to clone vol3, plus build tools for some extensions
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Clone Volatility3 (pinned to latest stable tag)
RUN git clone --depth 1 https://github.com/volatilityfoundation/volatility3.git /app/volatility3

WORKDIR /app/volatility3

# Install Volatility3 and its Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pefile yara-python

# ---------------------------------------------------------------------------
# Symbol tables are NOT baked into this image (network is unreliable at
# build time in many Docker Desktop / CI environments).
#
# Run  scripts/seed-vol3-symbols.ps1  (Windows)
#  or  scripts/seed-vol3-symbols.sh   (Linux / Mac)
# ONCE after building this image.  The script downloads the NT kernel ISF
# files on the HOST and copies them into the named Docker volume
# forensicstack_vol3_symbols, which is mounted at /root/.cache/volatility3
# inside every analysis container.  Symbols persist between runs.
# ---------------------------------------------------------------------------

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
# Strip Windows CRLF line endings in case the file was checked out on Windows
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

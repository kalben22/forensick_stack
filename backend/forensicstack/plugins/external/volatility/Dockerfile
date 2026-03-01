FROM python:3.11-slim

WORKDIR /app

# System deps: git to clone vol3 + community symbols, build tools for Python extensions
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
# Pre-bake community Windows ISF symbol tables so the image is self-contained.
#
# Abyss-W4tcher/volatility3-symbols mirrors the official ISF server with
# thousands of Windows builds (Win7 32/64-bit, Win8/10/11, Server 2008-2022).
# Symbols are copied into Volatility3's built-in symbols directory so they
# are found immediately with no network access at analysis time.
#
# Directory structure expected by Volatility 3:
#   volatility3/symbols/windows/<PDB_name>/<GUID>/<PDB_name>.<GUID>.<age>.json.xz
#
# The sparse checkout fetches only the windows/ subtree, which keeps the
# image size reasonable (no Linux/macOS symbols included).
# ---------------------------------------------------------------------------
RUN git clone --no-checkout --depth 1 --filter=blob:none \
        https://github.com/Abyss-W4tcher/volatility3-symbols.git /tmp/vol3-symbols \
    && cd /tmp/vol3-symbols \
    && git sparse-checkout init --cone \
    && git sparse-checkout set windows \
    && git checkout \
    && cp -r windows/. /app/volatility3/volatility3/symbols/windows/ \
    && rm -rf /tmp/vol3-symbols

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
# Strip Windows CRLF line endings in case the file was checked out on Windows
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

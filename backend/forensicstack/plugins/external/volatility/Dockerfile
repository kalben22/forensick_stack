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
# Pre-bake NT kernel ISF symbol tables (Windows 7/8/10/11, 32-bit and 64-bit).
#
# ALL ForensicStack plugins (pslist, cmdline, netscan, dlllist, malfind) only
# need the NT kernel PDB to build the kernel symbol table. We fetch ONLY the
# 4 relevant PDB directories from the community repo — not the entire windows/
# subtree — so the build stays fast (minutes instead of hours):
#
#   ntkrnlmp.pdb  → Win7-11 64-bit  (and 32-bit non-PAE, multiprocessor)
#   ntkrpamp.pdb  → Win7/8 32-bit PAE  (most common 32-bit kernel)
#   ntoskrnl.pdb  → Win7/8 32-bit non-PAE / uniprocessor
#   ntkrnlpa.pdb  → Win7 32-bit PAE uniprocessor
#
# Directory structure expected by Volatility 3:
#   volatility3/symbols/windows/<PDB_name>/<GUID>/<PDB_name>.<GUID>.<age>.json.xz
# ---------------------------------------------------------------------------
RUN git clone --depth 1 --sparse \
        https://github.com/Abyss-W4tcher/volatility3-symbols.git /tmp/vol3-symbols \
    && cd /tmp/vol3-symbols \
    && git sparse-checkout set \
        windows/ntkrnlmp.pdb \
        windows/ntkrpamp.pdb \
        windows/ntoskrnl.pdb \
        windows/ntkrnlpa.pdb \
    && cp -r windows/. /app/volatility3/volatility3/symbols/windows/ \
    && rm -rf /tmp/vol3-symbols

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
# Strip Windows CRLF line endings in case the file was checked out on Windows
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

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

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

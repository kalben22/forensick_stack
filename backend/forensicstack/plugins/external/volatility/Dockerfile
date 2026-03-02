FROM python:3.11-slim

WORKDIR /app

# Build tools for yara-python (C extension); wget+unzip for symbol download
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Volatility3 from PyPI — stable release, no git clone needed
RUN pip install --no-cache-dir volatility3 pefile yara-python

# Create output directory
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
# Strip Windows CRLF line endings in case the file was checked out on Windows
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

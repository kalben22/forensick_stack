FROM python:3.11-slim

WORKDIR /app

# 🔧 INSTALLER LES OUTILS DE BUILD (CRITIQUE!)
RUN apt-get update && apt-get install -y \
    git \
    unzip \
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    libffi-dev \
    libssl-dev \
    liblzma-dev \
    libbz2-dev \
    liblz4-dev \
    libzstd-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Cloner iLEAPP
RUN git clone --depth 1 https://github.com/abrignoni/iLEAPP.git

WORKDIR /app/iLEAPP

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Dossier de sortie
RUN mkdir -p /output

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
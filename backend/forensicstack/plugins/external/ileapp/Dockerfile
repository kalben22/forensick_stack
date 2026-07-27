FROM python:3.11-slim


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
    sleuthkit \
    && rm -rf /var/lib/apt/lists/*

# Cloner iLEAPP
# Install under /opt so --volumes-from /app mount does not shadow it
RUN git clone --depth 1 https://github.com/abrignoni/iLEAPP.git /opt/iLEAPP

WORKDIR /opt/iLEAPP

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Dossier de sortie
RUN mkdir -p /output

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
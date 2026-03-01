FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# exiftool (libimage-exiftool-perl) + petits utilitaires
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libimage-exiftool-perl \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# create output dir
RUN mkdir -p /output && chmod 0777 /output

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

# run as non-root user
RUN useradd -m -u 1000 analyst || true
USER analyst

ENTRYPOINT ["/entrypoint.sh"]
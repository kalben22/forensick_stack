FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Default command: run the API server.
# The worker service overrides this via 'command:' in docker-compose.yml.
CMD ["uvicorn", "forensicstack.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
Write-Host "Building ForensicStack..."
docker compose build

Write-Host "Starting services..."
docker compose up -d

Write-Host "ForensicStack is running at:"
Write-Host "http://localhost:8000"
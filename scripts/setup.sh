#!/bin/bash

echo "Building ForensicStack..."
docker compose build

echo "Starting services..."
docker compose up -d

echo "ForensicStack is running at:"
echo "http://localhost:8000"
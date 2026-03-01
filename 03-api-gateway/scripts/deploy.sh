#!/bin/bash
# Deployment script for API Gateway
# File: 03-api-gateway/scripts/deploy.sh
# Build Host: Windows 11 console
# Target Host: Raspberry Pi

set -e

echo "=========================================="
echo "Deploying Lucid API Gateway"
echo "=========================================="

# Navigate to project directory
cd "$(dirname "$0")/.."

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    echo "Copy .env.example to .env and configure it first"
    exit 1
fi

# Validate required environment variables
required_vars=("JWT_SECRET_KEY" "MONGO_PASSWORD" "REDIS_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env"
        exit 1
    fi
done

echo "Environment variables validated"
echo ""

# Create necessary directories
echo "Creating required directories..."
mkdir -p logs certs database

# Generate SSL certificates if not present
if [ ! -f "certs/api-gateway.crt" ]; then
    echo "Generating SSL certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout certs/api-gateway.key \
        -out certs/api-gateway.crt -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Lucid/CN=api.lucid-blockchain.org"
    echo "SSL certificates generated"
fi

echo ""
echo "Starting services with Docker Compose..."
docker-compose up -d

# Wait for health check
echo ""
echo "Waiting for service to be healthy..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -f http://localhost:8080/api/v1/meta/health > /dev/null 2>&1; then
        echo "Service is healthy!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo ""
    echo "Error: Service failed to become healthy"
    echo "Showing logs:"
    docker-compose logs api-gateway
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo "API Gateway is available at:"
echo "  HTTP:  http://localhost:8080"
echo "  HTTPS: https://localhost:8081"
echo ""
echo "Health check: curl http://localhost:8080/api/v1/meta/health"
echo "View logs: docker-compose logs -f api-gateway"
echo ""


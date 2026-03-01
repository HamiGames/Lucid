# TRON Payment System API - Distroless Deployment

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-DEPLOY-06B |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document provides comprehensive deployment configurations for the TRON Payment System API using distroless containers. It covers Docker Compose integration, volume management, environment configuration, health checks, and network isolation according to SPEC-1B-v2 requirements.

### Key Principles

- **Distroless Integration**: Seamless deployment of minimal containers
- **Volume Management**: Read-only secrets, writable logs/tmp
- **Network Isolation**: Wallet plane separation via Beta sidecar
- **Health Monitoring**: HTTP-based health checks without shell access
- **Resource Management**: Appropriate limits and reservations

---

## Docker Compose Integration

### Complete Service Definition

```yaml
# docker-compose.yml - TRON Payment Service
version: '3.8'

services:
  # ==============================================================================
  # TRON Payment Service - Distroless Container
  # ==============================================================================
  tron-payment-service:
    image: pickme/lucid:tron-payment-service:latest
    container_name: tron-payment-service
    hostname: tron-payment-service
    
    # Network configuration - Wallet plane isolation
    networks:
      - wallet_plane
      - tor_network
    
    # Environment variables
    environment:
      # Service configuration
      - LUCID_ENV=production
      - SERVICE_NAME=tron-payment-service
      - SERVICE_PORT=8090
      
      # TRON network configuration
      - TRON_NETWORK=mainnet
      - TRON_NODE_URL=https://api.trongrid.io
      - TRON_PRIVATE_KEY_FILE=/run/secrets/tron_private_key
      
      # Database configuration
      - MONGO_URL=mongodb://lucid:lucid@mongo:27017/lucid_payments
      - MONGO_DATABASE=lucid_payments
      
      # API Gateway configuration
      - API_GATEWAY_URL=http://api-gateway:8080
      - INTERNAL_AUTH_SECRET_FILE=/run/secrets/internal_auth_secret
      
      # Tor proxy configuration
      - TOR_PROXY=socks5://tor-proxy:9050
      - TOR_ONLY=true
      
      # Circuit breaker configuration
      - CIRCUIT_BREAKER_DAILY_LIMIT=10000
      - CIRCUIT_BREAKER_HOURLY_LIMIT=1000
      - CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
      
      # Logging configuration
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      
      # Health check configuration
      - HEALTH_CHECK_INTERVAL=30
      - HEALTH_CHECK_TIMEOUT=10
    
    # Volume mounts
    volumes:
      # Secrets (read-only)
      - type: bind
        source: ./configs/secrets
        target: /run/secrets
        read_only: true
      
      # Logs (writable)
      - type: bind
        source: ./logs/tron-payment
        target: /app/logs
      
      # Temporary files (writable)
      - type: bind
        source: ./tmp/tron-payment
        target: /app/tmp
      
      # Configuration files (read-only)
      - type: bind
        source: ./configs/tron-payment
        target: /app/configs
        read_only: true
    
    # Port configuration (internal only)
    expose:
      - "8090"
    
    # Health check configuration
    healthcheck:
      test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # Restart policy
    restart: unless-stopped
    
    # Resource limits and reservations
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
    
    # Dependencies
    depends_on:
      mongo:
        condition: service_healthy
      tor-proxy:
        condition: service_healthy
      beta-sidecar:
        condition: service_healthy
    
    # Security configuration
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /app/tmp:noexec,nosuid,size=50m

  # ==============================================================================
  # Beta Sidecar - Service Isolation
  # ==============================================================================
  beta-sidecar:
    image: pickme/lucid:beta-sidecar:latest
    container_name: tron-payment-beta-sidecar
    hostname: tron-payment-beta-sidecar
    
    networks:
      - wallet_plane
      - ops_plane
    
    environment:
      - SERVICE_NAME=tron-payment-service
      - SERVICE_PORT=8090
      - PLANE=wallet
      - ACL_POLICY_FILE=/app/configs/wallet_plane.acl
      - LOG_LEVEL=INFO
    
    volumes:
      - type: bind
        source: ./configs/beta-sidecar
        target: /app/configs
        read_only: true
    
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.1'
        reservations:
          memory: 128M
          cpus: '0.05'

  # ==============================================================================
  # MongoDB - Payment Database
  # ==============================================================================
  mongo:
    image: mongo:7.0
    container_name: lucid-mongo-payments
    hostname: lucid-mongo-payments
    
    networks:
      - wallet_plane
      - chain_plane
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=lucid
      - MONGO_INITDB_DATABASE=lucid_payments
    
    volumes:
      - mongo_payments_data:/data/db
      - type: bind
        source: ./scripts/database/init_payment_collections.js
        target: /docker-entrypoint-initdb.d/init_payments.js
        read_only: true
    
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
    
    healthcheck:
      test: ["CMD-SHELL", "mongosh --eval 'db.runCommand({ping: 1})' --quiet"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  # ==============================================================================
  # Tor Proxy - Network Isolation
  # ==============================================================================
  tor-proxy:
    image: alpine:3.18
    container_name: lucid-tor-payment
    hostname: lucid-tor-payment
    
    networks:
      - tor_network
    
    volumes:
      - type: bind
        source: ./configs/tor/torrc.payment
        target: /etc/tor/torrc
        read_only: true
    
    expose:
      - "9050"  # SOCKS proxy
      - "9051"  # Control port
    
    command: ["sh", "-c", "apk add --no-cache tor curl && tor -f /etc/tor/torrc"]
    
    healthcheck:
      test: ["CMD-SHELL", "curl -f --socks5 localhost:9050 http://httpbin.org/ip"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.1'
        reservations:
          memory: 64M
          cpus: '0.05'

# ==============================================================================
# Networks - Plane Isolation
# ==============================================================================
networks:
  # Wallet plane - Payment services only
  wallet_plane:
    name: lucid_wallet_plane
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.30.0.0/16
          gateway: 172.30.0.1
  
  # Ops plane - API Gateway access
  ops_plane:
    name: lucid_ops_plane
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
  
  # Chain plane - Blockchain services
  chain_plane:
    name: lucid_chain_plane
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.25.0.0/16
          gateway: 172.25.0.1
  
  # Tor network - External access
  tor_network:
    name: lucid_tor_network
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.35.0.0/16
          gateway: 172.35.0.1

# ==============================================================================
# Volumes - Data Persistence
# ==============================================================================
volumes:
  # MongoDB data volume
  mongo_payments_data:
    name: lucid_mongo_payments_data
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/mongo_payments
```

---

## Volume Mounting Strategies

### Read-Only Secrets Configuration

```yaml
# Secrets volume configuration
volumes:
  - type: bind
    source: ./configs/secrets
    target: /run/secrets
    read_only: true
    bind:
      propagation: rprivate

# Secrets directory structure
configs/secrets/
├── tron_private_key          # TRON wallet private key
├── internal_auth_secret      # Service-to-service auth
├── mongo_password           # Database password
└── api_keys/                # External API keys
    ├── tron_grid_api_key
    └── monitoring_api_key
```

### Writable Directories

```yaml
# Logs directory (writable)
volumes:
  - type: bind
    source: ./logs/tron-payment
    target: /app/logs
    bind:
      propagation: rshared

# Temporary files (writable)
volumes:
  - type: bind
    source: ./tmp/tron-payment
    target: /app/tmp
    bind:
      propagation: rshared
```

### Configuration Files

```yaml
# Configuration files (read-only)
volumes:
  - type: bind
    source: ./configs/tron-payment
    target: /app/configs
    read_only: true
    bind:
      propagation: rprivate

# Configuration directory structure
configs/tron-payment/
├── app_config.yaml          # Application configuration
├── tron_config.yaml         # TRON network configuration
├── circuit_breaker.yaml     # Circuit breaker settings
└── logging.yaml             # Logging configuration
```

---

## Environment Variable Configuration

### Service Configuration

```yaml
environment:
  # Core service settings
  - LUCID_ENV=production
  - SERVICE_NAME=tron-payment-service
  - SERVICE_PORT=8090
  - PYTHONUNBUFFERED=1
  - PYTHONDONTWRITEBYTECODE=1
  - PYTHONPATH=/app
```

### TRON Network Configuration

```yaml
environment:
  # TRON network settings
  - TRON_NETWORK=mainnet
  - TRON_NODE_URL=https://api.trongrid.io
  - TRON_PRIVATE_KEY_FILE=/run/secrets/tron_private_key
  - TRON_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
  - TRON_CONFIRMATIONS_REQUIRED=19
  - TRON_TIMEOUT_SECONDS=30
```

### Database Configuration

```yaml
environment:
  # MongoDB settings
  - MONGO_URL=mongodb://lucid:lucid@mongo:27017/lucid_payments
  - MONGO_DATABASE=lucid_payments
  - MONGO_CONNECTION_TIMEOUT=30
  - MONGO_SERVER_SELECTION_TIMEOUT=30
  - MONGO_MAX_POOL_SIZE=10
```

### Security Configuration

```yaml
environment:
  # Security settings
  - INTERNAL_AUTH_SECRET_FILE=/run/secrets/internal_auth_secret
  - JWT_ALGORITHM=HS256
  - JWT_EXPIRATION_HOURS=24
  - ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
  - TOR_ONLY=true
  - TOR_PROXY=socks5://tor-proxy:9050
```

### Circuit Breaker Configuration

```yaml
environment:
  # Circuit breaker settings
  - CIRCUIT_BREAKER_DAILY_LIMIT=10000
  - CIRCUIT_BREAKER_HOURLY_LIMIT=1000
  - CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
  - CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300
  - CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=3
```

---

## Health Check Implementations

### HTTP-Based Health Checks

```yaml
# Primary health check
healthcheck:
  test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()\""]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Alternative health check using curl (if available)
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8090/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Custom Health Check Script

```python
# health_check.py - Custom health check implementation
import urllib.request
import json
import sys

def check_health():
    try:
        # Check main health endpoint
        response = urllib.request.urlopen('http://localhost:8090/health', timeout=5)
        health_data = json.loads(response.read().decode())
        
        # Verify service status
        if health_data.get('status') != 'healthy':
            return False
        
        # Check individual components
        checks = health_data.get('checks', {})
        for component, status in checks.items():
            if status.get('status') != 'healthy':
                return False
        
        return True
        
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)
```

### Health Check Configuration

```yaml
# Environment variables for health checks
environment:
  - HEALTH_CHECK_INTERVAL=30
  - HEALTH_CHECK_TIMEOUT=10
  - HEALTH_CHECK_RETRIES=3
  - HEALTH_CHECK_START_PERIOD=40
```

---

## Network Configuration

### Wallet Plane Isolation

```yaml
networks:
  wallet_plane:
    name: lucid_wallet_plane
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.30.0.0/16
          gateway: 172.30.0.1
    driver_opts:
      com.docker.network.bridge.name: lucid-wallet-br
```

### Cross-Plane Communication

```yaml
# Beta sidecar network configuration
beta-sidecar:
  networks:
    - wallet_plane  # Access to payment service
    - ops_plane     # Access to API gateway
```

### Tor Network Integration

```yaml
# Tor proxy network configuration
tor-proxy:
  networks:
    - tor_network
  expose:
    - "9050"  # SOCKS proxy
    - "9051"  # Control port
```

---

## Resource Limits and Reservations

### CPU and Memory Configuration

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
    reservations:
      memory: 512M
      cpus: '0.25'
```

### Resource Monitoring

```yaml
# Resource monitoring labels
labels:
  - "com.lucid.resource.limits.memory=1G"
  - "com.lucid.resource.limits.cpu=0.5"
  - "com.lucid.resource.reservations.memory=512M"
  - "com.lucid.resource.reservations.cpu=0.25"
```

### Resource Validation

```bash
#!/bin/bash
# validate-resources.sh

echo "Validating resource configuration..."

# Check memory limits
docker stats tron-payment-service --no-stream --format "table {{.MemUsage}}"

# Check CPU usage
docker stats tron-payment-service --no-stream --format "table {{.CPUPerc}}"

# Check disk usage
docker exec tron-payment-service du -sh /app/logs /app/tmp

echo "Resource validation complete"
```

---

## Restart Policies

### Restart Configuration

```yaml
restart: unless-stopped

deploy:
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
    window: 120s
```

### Restart Validation

```bash
#!/bin/bash
# test-restart.sh

echo "Testing restart policy..."

# Stop the service
docker-compose stop tron-payment-service

# Wait for restart
sleep 10

# Check if service restarted
if docker-compose ps tron-payment-service | grep -q "Up"; then
    echo "✅ Service restarted successfully"
else
    echo "❌ Service failed to restart"
    exit 1
fi
```

---

## Dependencies and Startup Order

### Service Dependencies

```yaml
depends_on:
  mongo:
    condition: service_healthy
  tor-proxy:
    condition: service_healthy
  beta-sidecar:
    condition: service_healthy
```

### Startup Order Validation

```bash
#!/bin/bash
# validate-startup-order.sh

echo "Validating startup order..."

# Start services in dependency order
docker-compose up -d mongo
sleep 10

docker-compose up -d tor-proxy
sleep 5

docker-compose up -d beta-sidecar
sleep 5

docker-compose up -d tron-payment-service
sleep 10

# Check all services are running
docker-compose ps

echo "Startup order validation complete"
```

---

## Deployment Commands

### Development Deployment

```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f tron-payment-service

# Execute commands in container
docker-compose exec tron-payment-service python3 -c "import sys; print(sys.version)"
```

### Production Deployment

```bash
# Pull latest images
docker-compose pull

# Deploy with zero downtime
docker-compose up -d --no-deps tron-payment-service

# Verify deployment
docker-compose ps
docker-compose logs --tail=100 tron-payment-service
```

### Health Check Validation

```bash
# Check service health
curl -f http://localhost:8090/health

# Check metrics endpoint
curl -f http://localhost:8090/metrics

# Validate circuit breaker status
curl -f http://localhost:8090/stats | jq '.circuit_breaker_status'
```

---

## References

- [06a_DISTROLESS_DOCKERFILE.md](06a_DISTROLESS_DOCKERFILE.md) - Container build configuration
- [07_SECURITY_COMPLIANCE.md](07_SECURITY_COMPLIANCE.md) - Security implementation
- [Docker Compose Documentation](https://docs.docker.com/compose/) - Official Docker Compose guide
- [SPEC-1B-v2-DISTROLESS.md](../../../docs/build-docs/Build_guide_docs/SPEC-1B-v2-DISTROLESS.md) - Architecture requirements

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12

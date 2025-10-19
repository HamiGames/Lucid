#!/bin/bash
# scripts/config/generate-all-env.sh
# Generate all environment configuration files with real values

set -e

echo "Generating environment configuration files..."

# Create configs directory if it doesn't exist
mkdir -p configs/environment

# Generate secure passwords and keys
MONGODB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
ELASTICSEARCH_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
TOR_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Generate .env.pi-build
cat > configs/environment/.env.pi-build << EOF
# Build Host Configuration
BUILD_HOST=windows11
BUILD_USER=surba
BUILD_DIR=C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2\Lucid

# Target Host Configuration  
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production
PI_ARCH=arm64
PI_PLATFORM=linux/arm64

# Network Configuration
LUCID_NETWORK=lucid-pi-network
NETWORK_SUBNET=172.20.0.0/16
TRON_ISOLATED_NETWORK=lucid-tron-isolated
TRON_SUBNET=172.21.0.0/16

# Docker Registry
DOCKER_REGISTRY=ghcr.io/hamigames/lucid
DOCKER_TAG=latest
EOF

# Generate .env.foundation
cat > configs/environment/.env.foundation << EOF
# Database Configuration
MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@192.168.0.75:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://:${REDIS_PASSWORD}@192.168.0.75:6379/0
ELASTICSEARCH_URL=http://192.168.0.75:9200

# Database Passwords
MONGODB_PASSWORD=${MONGODB_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}

# Security Keys
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
TOR_CONTROL_PASSWORD=${TOR_PASSWORD}

# Service Ports
AUTH_SERVICE_PORT=8089
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_PORT=9200

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
EOF

# Generate .env.core
cat > configs/environment/.env.core << EOF
# API Gateway Configuration
API_GATEWAY_PORT=8080
API_GATEWAY_HOST=0.0.0.0
RATE_LIMIT_FREE=100
RATE_LIMIT_PREMIUM=1000
RATE_LIMIT_ENTERPRISE=10000

# Blockchain Core Configuration
BLOCKCHAIN_CORE_PORT=8084
BLOCKCHAIN_CORE_HOST=0.0.0.0
BLOCK_TIME_SECONDS=10
CONSENSUS_THRESHOLD=0.67
BLOCK_SIZE_LIMIT=1048576

# Service Mesh Configuration
SERVICE_MESH_CONTROLLER_PORT=8081
CONSUL_PORT=8500
ENVOY_ADMIN_PORT=9901

# Network Configuration
LUCID_NETWORK=lucid-pi-network
SERVICE_DISCOVERY_ENABLED=true
MTLS_ENABLED=true

# Performance Configuration
MAX_CONNECTIONS=1000
CONNECTION_TIMEOUT=30
REQUEST_TIMEOUT=60
EOF

# Generate .env.application
cat > configs/environment/.env.application << EOF
# Session Management Configuration
SESSION_API_PORT=8087
SESSION_PIPELINE_PORT=8088
SESSION_RECORDER_PORT=8089
CHUNK_PROCESSOR_PORT=8090
SESSION_STORAGE_PORT=8091

# Session Processing Configuration
CHUNK_SIZE_MB=10
COMPRESSION_LEVEL=6
ENCRYPTION_ALGO=AES-256-GCM
MERKLE_HASH_ALGO=SHA256
MAX_CHUNK_SIZE=10485760
PROCESSING_THREADS=4

# RDP Services Configuration
RDP_SERVER_MANAGER_PORT=8092
XRDP_INTEGRATION_PORT=8093
SESSION_CONTROLLER_PORT=8094
RESOURCE_MONITOR_PORT=8095

# RDP Configuration
XRDP_PORT=3389
XRDP_HOST=0.0.0.0
MAX_RDP_SESSIONS=10
SESSION_TIMEOUT=3600

# Node Management Configuration
NODE_MANAGEMENT_PORT=8096
POOT_CALCULATION_INTERVAL_SEC=300
PAYOUT_THRESHOLD_USDT=10.0
POOL_MAX_NODES=100
NODE_REGISTRATION_TIMEOUT=30
EOF

# Generate .env.support
cat > configs/environment/.env.support << EOF
# Admin Interface Configuration
ADMIN_INTERFACE_PORT=8083
ADMIN_INTERFACE_HOST=0.0.0.0
ADMIN_DASHBOARD_ENABLED=true
METRICS_COLLECTION_ENABLED=true

# TRON Payment Configuration (Isolated)
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
TRON_TESTNET_API=https://api.shasta.trongrid.io
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
TRX_STAKING_MIN_AMOUNT=100
PAYOUT_MIN_THRESHOLD=10

# TRON Service Ports (Isolated Network)
TRON_CLIENT_PORT=8097
PAYOUT_ROUTER_PORT=8098
WALLET_MANAGER_PORT=8099
USDT_MANAGER_PORT=8100
TRX_STAKING_PORT=8101
PAYMENT_GATEWAY_PORT=8102

# Security Configuration
TRON_WALLET_ENCRYPTION_KEY=SecureTronWalletKey123456789
TRON_API_KEY=your_trongrid_api_key_here
TRON_PRIVATE_KEY=your_tron_private_key_here
EOF

# Generate .env.gui
cat > configs/environment/.env.gui << EOF
# API Endpoints (from backend .env files)
API_GATEWAY_URL=http://192.168.0.75:8080
BLOCKCHAIN_CORE_URL=http://192.168.0.75:8084
AUTH_SERVICE_URL=http://192.168.0.75:8089
SESSION_API_URL=http://192.168.0.75:8087
NODE_MANAGEMENT_URL=http://192.168.0.75:8096
ADMIN_INTERFACE_URL=http://192.168.0.75:8083

# Tor Configuration
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_ENABLED=true
TOR_AUTO_START=true

# GUI Configuration
ELECTRON_GUI_VERSION=1.0.0
GUI_THEME=dark
GUI_LANGUAGE=en
GUI_UPDATE_CHECK=true

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
LEDGER_SUPPORT=true
TREZOR_SUPPORT=true
KEEPKEY_SUPPORT=true
EOF

echo "Environment configuration files generated successfully!"
echo "Generated files:"
echo "- configs/environment/.env.pi-build"
echo "- configs/environment/.env.foundation"
echo "- configs/environment/.env.core"
echo "- configs/environment/.env.application"
echo "- configs/environment/.env.support"
echo "- configs/environment/.env.gui"
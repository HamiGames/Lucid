# Fixed Build Commands - Resolved Dependency Issues

## Issues Fixed:
1. **Authentication**: `tronapi>=3.2.0` → `tronapi>=3.1.6` (latest available)
2. **Encryptor**: Removed non-existent `python-hsm>=0.9.0` package

## Build Commands (Fixed):

### Layer 1: Session Pipeline
```powershell
# Session Chunker (already working)
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/core/Dockerfile.chunker -t pickme/lucid:session-chunker --push .

# Session Encryptor (FIXED)
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/encryption/Dockerfile.encryptor -t pickme/lucid:session-encryptor --push .

# Merkle Builder
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/core/Dockerfile.merkle_builder -t pickme/lucid:merkle-builder --push .

# Session Orchestrator
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/core/Dockerfile.orchestrator -t pickme/lucid:session-orchestrator --push .
```

### Layer 1: Authentication
```powershell
# Authentication Service (FIXED)
docker buildx build --platform linux/arm64,linux/amd64 -f auth/Dockerfile.authentication -t pickme/lucid:authentication --push .
```

### Core Support Services
```powershell
# Server Tools
docker buildx build --platform linux/arm64,linux/amd64 -f common/server-tools/Dockerfile -t pickme/lucid:server-tools --push common/server-tools

# Tunnel Tools
docker buildx build --platform linux/arm64,linux/amd64 -f 02-network-security/tunnels/Dockerfile -t pickme/lucid:tunnel-tools --push 02-network-security/tunnels

# Tor Proxy
docker buildx build --platform linux/arm64,linux/amd64 -f 02-network-security/tor/Dockerfile -t pickme/lucid:tor-proxy --push 02-network-security/tor
```

### API Gateway Services
```powershell
# API Gateway
docker buildx build --platform linux/arm64,linux/amd64 -f 03-api-gateway/gateway/Dockerfile.gateway -t pickme/lucid:api-gateway --push 03-api-gateway/gateway

# API Server
docker buildx build --platform linux/arm64,linux/amd64 -f 03-api-gateway/api/Dockerfile.api -t pickme/lucid:api-server --push 03-api-gateway/api
```

### Open API Services
```powershell
# OpenAPI Gateway
docker buildx build --platform linux/arm64,linux/amd64 -f open-api/gateway/Dockerfile.gateway -t pickme/lucid:openapi-gateway --push open-api/gateway

# OpenAPI Server
docker buildx build --platform linux/arm64,linux/amd64 -f open-api/api/Dockerfile.api -t pickme/lucid:openapi-server --push open-api/api
```

### Blockchain Services
```powershell
# Blockchain API
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/api/Dockerfile -t pickme/lucid:blockchain-api --push 04-blockchain-core/api

# Blockchain Governance
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/governance/Dockerfile -t pickme/lucid:blockchain-governance --push 04-blockchain-core/governance

# Blockchain Sessions Data
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/sessions-data/Dockerfile -t pickme/lucid:blockchain-sessions-data --push 04-blockchain-core/sessions-data

# Blockchain VM
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/vm/Dockerfile -t pickme/lucid:blockchain-vm --push 04-blockchain-core/vm

# Blockchain Ledger
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/ledger/Dockerfile -t pickme/lucid:blockchain-ledger --push 04-blockchain-core/ledger

# Legacy Blockchain API
docker buildx build --platform linux/arm64,linux/amd64 -f blockchain/api/Dockerfile -t pickme/lucid:blockchain-api-legacy --push blockchain/api
```

## Quick Test Commands:

```powershell
# Test the fixed authentication service
docker buildx build --platform linux/arm64,linux/amd64 -f auth/Dockerfile.authentication -t pickme/lucid:authentication --push .

# Test the fixed encryptor service  
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/encryption/Dockerfile.encryptor -t pickme/lucid:session-encryptor --push .
```

## Or use the PowerShell script:
```powershell
.\build-and-push-distroless.ps1
```

All dependency issues have been resolved!

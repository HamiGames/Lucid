# Step 21: Validate TRON Containers

## Overview

This step validates 6 distroless TRON containers built and deployed to isolated network (lucid-network-isolated: 172.21.0.0/16), ensuring proper container security labels and complete service isolation.

## Priority: CRITICAL

## Files to Review

### TRON Container Dockerfiles
- `payment-systems/tron/Dockerfile.tron-client`
- `payment-systems/tron/Dockerfile.payout-router`
- `payment-systems/tron/Dockerfile.wallet-manager`
- `payment-systems/tron/Dockerfile.usdt-manager`
- `payment-systems/tron/Dockerfile.trx-staking`
- `payment-systems/tron/Dockerfile.payment-gateway`

### TRON Container Configuration
- `payment-systems/tron/docker-compose.yml`
- `payment-systems/tron/.env.tron`
- `payment-systems/tron/requirements.txt`

## Actions Required

### 1. Verify 6 Distroless TRON Containers Built

**Check for:**
- All 6 TRON containers built successfully
- Distroless base images used
- Minimal attack surface
- Security-optimized containers

**Validation Commands:**
```bash
# Check all TRON Dockerfiles exist
ls -la payment-systems/tron/Dockerfile.*

# Verify distroless base images
grep "FROM.*distroless" payment-systems/tron/Dockerfile.*

# Check container builds
docker images | grep tron
```

### 2. Check Deployment to Isolated Network

**Check for:**
- Deployment to lucid-network-isolated (172.21.0.0/16)
- No deployment to main network (lucid-dev)
- Proper network isolation
- TRON services isolated from blockchain core

**Validation Commands:**
```bash
# Check isolated network configuration
grep -r "lucid-network-isolated" payment-systems/tron/docker-compose.yml

# Verify network subnet
grep "172.21.0.0/16" payment-systems/tron/docker-compose.yml

# Check for main network references
grep "lucid-dev" payment-systems/tron/docker-compose.yml
# Should return no results
```

### 3. Validate Container Security Labels

**Check for:**
- Wallet plane security labels
- Payment-only isolation labels
- Proper security annotations
- Container security policies

**Validation Commands:**
```bash
# Check security labels
grep "lucid.plane=wallet" payment-systems/tron/docker-compose.yml
grep "lucid.isolation=payment-only" payment-systems/tron/docker-compose.yml

# Verify security annotations
grep "lucid.security" payment-systems/tron/docker-compose.yml
```

### 4. Ensure Ports 8091-8096 Properly Mapped

**Check for:**
- TRON client: 8091
- Payout router: 8092
- Wallet manager: 8093
- USDT manager: 8094
- TRX staking: 8095
- Payment gateway: 8096

**Validation Commands:**
```bash
# Check port mappings
grep "8091:8091" payment-systems/tron/docker-compose.yml
grep "8092:8092" payment-systems/tron/docker-compose.yml
grep "8093:8093" payment-systems/tron/docker-compose.yml
grep "8094:8094" payment-systems/tron/docker-compose.yml
grep "8095:8095" payment-systems/tron/docker-compose.yml
grep "8096:8096" payment-systems/tron/docker-compose.yml
```

### 5. Verify Service Isolation from Blockchain Core

**Critical Check:**
- No blockchain core dependencies
- Independent TRON service network
- Isolated data storage
- No cross-service communication with blockchain

**Validation Commands:**
```bash
# Check for blockchain references
grep -r "blockchain" payment-systems/tron/docker-compose.yml
# Should return no results

# Verify network isolation
grep "lucid-dev" payment-systems/tron/docker-compose.yml
# Should return no results

# Check for shared volumes
grep "shared" payment-systems/tron/docker-compose.yml
# Should return no results
```

### 6. Test Container Health Checks

**Check for:**
- Health check endpoints configured
- Container health monitoring
- Service availability checks
- Automatic restart policies

**Validation Commands:**
```bash
# Check health check configuration
grep "healthcheck" payment-systems/tron/docker-compose.yml

# Test container health
docker-compose -f payment-systems/tron/docker-compose.yml ps

# Verify health check endpoints
curl -f http://localhost:8091/health
curl -f http://localhost:8092/health
curl -f http://localhost:8093/health
curl -f http://localhost:8094/health
curl -f http://localhost:8095/health
curl -f http://localhost:8096/health
```

## Container Build and Deployment

### Build TRON Containers
```bash
# Build all TRON containers
docker-compose -f payment-systems/tron/docker-compose.yml build

# Verify container builds
docker images | grep tron
```

### Deploy to Isolated Network
```bash
# Create isolated network
docker network create --driver bridge --subnet=172.21.0.0/16 --gateway=172.21.0.1 lucid-network-isolated

# Deploy TRON services
docker-compose -f payment-systems/tron/docker-compose.yml up -d

# Verify deployment
docker ps | grep tron
docker network inspect lucid-network-isolated
```

## Security Validation

### Container Security Checks
```bash
# Check container security labels
docker inspect tron-client | grep -i security

# Verify non-root user
docker run --rm tron-client id

# Check for security vulnerabilities
docker run --rm tron-client /bin/sh -c "apk info" 2>/dev/null || echo "Distroless image - no package manager"
```

### Network Security Validation
```bash
# Verify network isolation
docker network inspect lucid-network-isolated | grep tron

# Check for main network references
docker network ls | grep lucid-dev
# Should not show TRON services on main network

# Verify port isolation
netstat -tlnp | grep 809
```

## Service Functionality Testing

### Test TRON Services
```bash
# Test TRON client
curl -X GET http://localhost:8091/health
curl -X GET http://localhost:8091/network/status

# Test payout router
curl -X GET http://localhost:8092/health
curl -X GET http://localhost:8092/payouts/status

# Test wallet manager
curl -X GET http://localhost:8093/health
curl -X GET http://localhost:8093/wallets/list

# Test USDT manager
curl -X GET http://localhost:8094/health
curl -X GET http://localhost:8094/usdt/balance/test

# Test TRX staking
curl -X GET http://localhost:8095/health
curl -X GET http://localhost:8095/staking/stats

# Test payment gateway
curl -X GET http://localhost:8096/health
curl -X GET http://localhost:8096/payments/status
```

## Success Criteria

- ✅ 6 distroless TRON containers built successfully
- ✅ Deployed to isolated network (lucid-network-isolated: 172.21.0.0/16)
- ✅ Container security labels properly configured
- ✅ Ports 8091-8096 properly mapped
- ✅ Service isolation from blockchain core verified
- ✅ Container health checks functional

## Risk Mitigation

- Backup TRON container configuration
- Test TRON services in isolated environment
- Verify network isolation before deployment
- Ensure TRON service independence

## Rollback Procedures

If issues are found:
1. Stop TRON containers
2. Remove isolated network
3. Restore from backup configuration
4. Re-verify TRON service isolation

## Next Steps

After successful completion:
- Proceed to Step 22: Final TRON Isolation Verification
- Update TRON container documentation
- Generate compliance report for TRON containers

# Distroless Deployment Plan for Lucid Project

## Overview

Deploy distroless base infrastructure followed by Lucid services (foundation, core, application, support) on Raspberry Pi 5, using pre-built distroless images from Docker Hub (pickme namespace), with proper network configuration and secure environment variable management.

## Prerequisites

- Raspberry Pi 5 accessible at 192.168.0.75
- SSH access: `ssh pickme@192.168.0.75`
- Project root: `/mnt/myssd/Lucid/Lucid`
- Docker and Docker Compose installed on Pi
- Pre-built distroless images available on Docker Hub (pickme/lucid-*)

## Phase A: Network Infrastructure Setup

### Step A1: Create Primary Networks (from network-configs.md)

Create the three main networks required by Lucid services:

**Commands to run on Pi console:**

```bash
# Create Main Network (Foundation + Core + Application + Blockchain)
docker network create lucid-pi-network \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --gateway 172.20.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=main" \
  --label "lucid.subnet=172.20.0.0/16"

# Create TRON Isolated Network (Payment Services)
docker network create lucid-tron-isolated \
  --driver bridge \
  --subnet 172.21.0.0/16 \
  --gateway 172.21.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=tron-isolated" \
  --label "lucid.subnet=172.21.0.0/16"

# Create GUI Network (Electron GUI Services)
docker network create lucid-gui-network \
  --driver bridge \
  --subnet 172.22.0.0/16 \
  --gateway 172.22.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=gui" \
  --label "lucid.subnet=172.22.0.0/16"
```

**Or use existing script:**

```bash
cd /mnt/myssd/Lucid/Lucid
bash scripts/deployment/create-pi-networks.sh
```

### Step A2: Create Additional Distroless Networks

Create dedicated networks for distroless-specific services and testing:

**Commands to run on Pi console:**

```bash
# Create Distroless Production Network (for distroless-specific infrastructure)
docker network create lucid-distroless-production \
  --driver bridge \
  --subnet 172.23.0.0/16 \
  --gateway 172.23.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=distroless-production" \
  --label "lucid.subnet=172.23.0.0/16"

# Create Distroless Development Network (for dev/testing)
docker network create lucid-distroless-dev \
  --driver bridge \
  --subnet 172.24.0.0/16 \
  --gateway 172.24.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=distroless-dev" \
  --label "lucid.subnet=172.24.0.0/16"

# Create Multi-Stage Build Network (for build processes)
docker network create lucid-multi-stage-network \
  --driver bridge \
  --subnet 172.25.0.0/16 \
  --gateway 172.25.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=multi-stage" \
  --label "lucid.subnet=172.25.0.0/16"
```

### Step A3: Verify Networks

```bash
# Verify all networks created
docker network ls | grep lucid

# Expected output:
# lucid-pi-network (172.20.0.0/16)
# lucid-tron-isolated (172.21.0.0/16)
# lucid-gui-network (172.22.0.0/16)
# lucid-distroless-production (172.23.0.0/16)
# lucid-distroless-dev (172.24.0.0/16)
# lucid-multi-stage-network (172.25.0.0/16)

# Inspect network details
docker network inspect lucid-pi-network | grep -E "Subnet|Gateway"
```

## Phase B: Environment Configuration

### Step B1: Generate Secure Environment Files

Generate secure .env files with real cryptographic values:

```bash
cd /mnt/myssd/Lucid/Lucid
export PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"

# Generate all .env files
bash scripts/config/generate-all-env-complete.sh
```

This creates:

- `configs/environment/.env.foundation` - Phase 1 secrets (MongoDB, Redis, JWT, etc.)
- `configs/environment/.env.core` - Phase 2 secrets
- `configs/environment/.env.application` - Phase 3 secrets
- `configs/environment/.env.support` - Phase 4 secrets
- `configs/environment/.env.gui` - GUI integration secrets
- `configs/environment/.env.secure` - Master backup (chmod 600)

### Step B2: Create Distroless-Specific Environment File

Create `configs/environment/.env.distroless` by merging foundation .env with distroless-specific overrides:

```bash
cd /mnt/myssd/Lucid/Lucid

# Copy base from production.env template
cp configs/docker/distroless/production.env configs/environment/.env.distroless

# Then manually edit to replace hardcoded passwords with secure values
# Key variables to update from .env.foundation:
# - MONGODB_PASSWORD (from .env.foundation)
# - REDIS_PASSWORD (from .env.foundation)
# - JWT_SECRET (from .env.foundation)
# - ENCRYPTION_KEY (from .env.foundation)
# - TOR_CONTROL_PASSWORD (from .env.foundation)

# Or use sed to inject values programmatically:
source configs/environment/.env.foundation

sed -i "s|mongodb://lucid:lucid@|mongodb://lucid:${MONGODB_PASSWORD}@|g" configs/environment/.env.distroless
sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|g" configs/environment/.env.distroless
sed -i "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|g" configs/environment/.env.distroless
```

### Step B3: Verify Environment Files

```bash
# Check files exist
ls -la configs/environment/.env.*

# Verify no placeholders
grep -r "_PLACEHOLDER" configs/environment/ && echo "ERROR: Placeholders found!" || echo "OK: No placeholders"

# Verify no weak passwords
grep -E "PASSWORD=lucid$" configs/environment/.env.* && echo "ERROR: Weak password!" || echo "OK: Secure passwords"

# Check secure file permissions
ls -la configs/environment/.env.secure | grep "^-rw-------" && echo "OK: Secure permissions" || chmod 600 configs/environment/.env.secure
```

## Phase C: Distroless Base Infrastructure Deployment

### Step C1: Deploy Distroless Base Runtime

Deploy the base distroless runtime environment using `distroless-runtime-config.yml`:

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-runtime-config.yml \
  up -d
```

**Services deployed:**

- `distroless-runtime` - Main ARM64 runtime on lucid-pi-network
- `minimal-runtime` - Minimal resource-constrained runtime
- `arm64-runtime` - ARM64-optimized runtime for Pi 5

### Step C2: Deploy Distroless Development Environment (Optional)

For development and testing:

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-development-config.yml \
  up -d
```

**Services deployed:**

- `dev-distroless` - Development environment with hot reload
- `dev-minimal` - Minimal dev configuration
- `dev-tools` - Development tools container

### Step C3: Deploy Distroless Security Configuration (Production Only)

For hardened production deployments:

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-security-config.yml \
  up -d
```

**Services deployed:**

- `secure-distroless` - Security-hardened distroless with AppArmor/Seccomp
- `minimal-secure` - Minimal security configuration
- `security-monitor` - Security monitoring for distroless containers

### Step C4: Verify Distroless Base Infrastructure

```bash
# Check running containers
docker ps | grep distroless

# Check health status
docker inspect distroless-runtime | grep -A 10 Health

# Test basic Python execution
docker exec distroless-runtime python -c "import sys; print(f'Python {sys.version}'); sys.exit(0)"

# Verify network connectivity
docker network inspect lucid-pi-network | grep distroless-runtime
```

## Phase D: Lucid Services Deployment (Using Pre-Built Distroless Images)

### Step D1: Deploy Phase 1 - Foundation Services

Deploy MongoDB, Redis, Elasticsearch, and Auth
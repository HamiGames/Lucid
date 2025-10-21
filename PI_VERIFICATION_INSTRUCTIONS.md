# Pi Console Verification Instructions

**Location:** Raspberry Pi 5 Console (pickme@192.168.0.75)  
**Working Directory:** `/mnt/myssd/Lucid/Lucid`  
**Date:** $(date)

## Prerequisites

1. SSH into the Pi console:
   ```bash
   ssh pickme@192.168.0.75
   ```

2. Navigate to project directory:
   ```bash
   cd /mnt/myssd/Lucid/Lucid
   ```

## Step-by-Step Verification Process

### Step 1: Make Verification Scripts Executable

```bash
cd /mnt/myssd/Lucid/Lucid
chmod +x scripts/verification/verify-pi-docker-setup.sh
chmod +x scripts/verification/pull-missing-images.sh
chmod +x scripts/config/generate-all-env.sh
```

### Step 2: Run Comprehensive Docker Setup Verification

This script will:
- Check all 30 required Docker images (base + all phases)
- Verify required networks (lucid-pi-network, lucid-tron-isolated)
- Verify buildx availability
- Check .env generation scripts and their paths
- Verify deployment scripts exist

```bash
bash scripts/verification/verify-pi-docker-setup.sh
```

**Expected Output:**
- Image status report (present vs missing)
- Network verification
- Buildx version confirmation
- Script path verification

### Step 3: Pull Missing Docker Images (if needed)

If Step 2 shows missing images, pull them:

```bash
bash scripts/verification/pull-missing-images.sh
```

This will pull all missing images from Docker Hub for linux/arm64 platform.

**Note:** Some images may not exist yet on Docker Hub if they haven't been built. These will fail to pull but that's expected.

### Step 4: Verify .env Files Generation

Check if .env files exist:

```bash
ls -la configs/environment/
```

If .env files are missing or contain placeholders, generate them:

```bash
bash scripts/config/generate-all-env.sh
```

This will generate:
- `.env.pi-build` - Raspberry Pi target configuration
- `.env.foundation` - Phase 1 database/auth configs
- `.env.core` - Phase 2 gateway/blockchain configs
- `.env.application` - Phase 3 session/RDP/node configs
- `.env.support` - Phase 4 admin/TRON configs
- `.env.gui` - Electron GUI integration configs

### Step 5: Verify No Placeholders in .env Files

```bash
grep -r '\${' configs/environment/
```

**Expected:** No output (zero placeholders found)

If placeholders are found, regenerate using Step 4.

## Quick Verification Commands (Individual Checks)

### Check Docker Status
```bash
sudo systemctl status docker
docker info
```

### Check Docker Networks
```bash
docker network ls
docker network inspect lucid-pi-network
docker network inspect lucid-tron-isolated
```

### Check Docker Images
```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
```

### Check Buildx
```bash
docker buildx version
docker buildx ls
```

### Check Disk Space
```bash
df -h /mnt/myssd
```

## Complete Image List (30 Total)

### Base Images (2)
- pickme/lucid-base:python-distroless-arm64
- pickme/lucid-base:java-distroless-arm64

### Phase 1: Foundation Services (4)
- pickme/lucid-mongodb:latest-arm64
- pickme/lucid-redis:latest-arm64
- pickme/lucid-elasticsearch:latest-arm64
- pickme/lucid-auth-service:latest-arm64

### Phase 2: Core Services (6)
- pickme/lucid-api-gateway:latest-arm64
- pickme/lucid-service-mesh-controller:latest-arm64
- pickme/lucid-blockchain-engine:latest-arm64
- pickme/lucid-session-anchoring:latest-arm64
- pickme/lucid-block-manager:latest-arm64
- pickme/lucid-data-chain:latest-arm64

### Phase 3: Application Services (10)
- pickme/lucid-session-pipeline:latest-arm64
- pickme/lucid-session-recorder:latest-arm64
- pickme/lucid-chunk-processor:latest-arm64
- pickme/lucid-session-storage:latest-arm64
- pickme/lucid-session-api:latest-arm64
- pickme/lucid-rdp-server-manager:latest-arm64
- pickme/lucid-xrdp-integration:latest-arm64
- pickme/lucid-session-controller:latest-arm64
- pickme/lucid-resource-monitor:latest-arm64
- pickme/lucid-node-management:latest-arm64

### Phase 4: Support Services (8)
- pickme/lucid-admin-interface:latest-arm64
- pickme/lucid-tron-client:latest-arm64
- pickme/lucid-payout-router:latest-arm64
- pickme/lucid-wallet-manager:latest-arm64
- pickme/lucid-usdt-manager:latest-arm64
- pickme/lucid-trx-staking:latest-arm64
- pickme/lucid-payment-gateway:latest-arm64

## Required Networks (2)

1. **lucid-pi-network** - Main application network
   - Driver: bridge
   - Subnet: 172.20.0.0/16
   
2. **lucid-tron-isolated** - TRON payment isolation network
   - Driver: bridge
   - Isolated from main network

## Troubleshooting

### If SSH passphrase is required
If SSH keeps asking for passphrase, you may need to add your key to the agent:
```bash
# On Windows (Git Bash)
eval $(ssh-agent)
ssh-add ~/.ssh/id_rsa
```

### If Docker is not running
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### If Networks are missing
Create them:
```bash
docker network create --driver bridge --subnet 172.20.0.0/16 lucid-pi-network
docker network create --driver bridge lucid-tron-isolated
```

### If buildx is not available
```bash
docker buildx create --use --name pi5-builder
```

## Verification Checklist

After running all steps, confirm:

- [ ] Docker daemon is running
- [ ] Buildx is available (v0.29.1 or later)
- [ ] Both networks exist (lucid-pi-network, lucid-tron-isolated)
- [ ] Base images are present (2 images)
- [ ] All 6 .env files exist in `configs/environment/`
- [ ] No placeholders (`${...}`) in .env files
- [ ] Deployment scripts exist in `scripts/deployment/`
- [ ] At least 20GB free disk space on `/mnt/myssd`

## Summary Report

After verification, the system should report:
- **Architecture:** aarch64 (ARM64)
- **Docker Version:** 28.2.2+
- **Compose Version:** 2.40.1+
- **Buildx Version:** 0.29.1+
- **Networks:** 2/2 present
- **Base Images:** 2/2 present (or ready to pull)

---

**Next Steps:** After verification, proceed with Phase 1 Foundation Services build.


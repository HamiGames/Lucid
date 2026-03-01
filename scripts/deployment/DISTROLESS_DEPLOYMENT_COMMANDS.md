# Distroless Deployment Commands for Raspberry Pi

This document provides the correct commands for deploying distroless containers from the Raspberry Pi console.

## Prerequisites

### 1. SSH to Raspberry Pi
```bash
ssh pickme@192.168.0.75
```

### 2. Navigate to Project Directory
```bash
cd /mnt/myssd/Lucid/Lucid
```

### 3. Set Project Root Environment Variable
```bash
export PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
```

## Required Images

Before deployment, ensure these distroless images are available:

```bash
# Check if images exist
docker images | grep pickme/lucid

# If images are missing, pull them:
docker pull pickme/lucid-base:latest-arm64
docker pull pickme/lucid-auth-service:latest-arm64
docker pull pickme/lucid-mongodb:latest-arm64
docker pull pickme/lucid-redis:latest-arm64
```

## Deployment Commands

### 1. Full Distroless Deployment (Recommended)
```bash
# Deploy all distroless infrastructure
bash scripts/deployment/deploy-distroless-complete.sh full
```

### 2. Runtime Deployment Only
```bash
# Deploy distroless runtime containers
bash scripts/deployment/deploy-distroless-pi.sh runtime
```

### 3. Development Deployment
```bash
# Deploy development distroless containers
bash scripts/deployment/deploy-distroless-pi.sh development
```

### 4. Security Deployment
```bash
# Deploy security-hardened distroless containers
bash scripts/deployment/deploy-distroless-pi.sh security
```

### 5. Test Deployment
```bash
# Deploy test distroless containers
bash scripts/deployment/deploy-distroless-pi.sh test
```

## Individual Configuration Deployments

### Runtime Configuration
```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-runtime-config.yml \
  up -d --remove-orphans
```

### Development Configuration
```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-development-config.yml \
  up -d --remove-orphans
```

### Security Configuration
```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-security-config.yml \
  up -d --remove-orphans
```

### Base Configuration
```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-config.yml \
  up -d --remove-orphans
```

## Verification Commands

### Check Container Status
```bash
# List all running containers
docker ps

# Check specific distroless containers
docker ps | grep distroless

# Check container health
docker inspect <container_name> | grep -A 5 Health
```

### Check Network Status
```bash
# List networks
docker network ls | grep lucid

# Inspect network
docker network inspect lucid-distroless-production
```

### Check Logs
```bash
# View container logs
docker logs <container_name>

# Follow logs in real-time
docker logs -f <container_name>
```

## Troubleshooting Commands

### Stop All Distroless Containers
```bash
# Stop all distroless containers
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-runtime-config.yml \
  down --remove-orphans

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-development-config.yml \
  down --remove-orphans

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-security-config.yml \
  down --remove-orphans
```

### Clean Up Resources
```bash
# Remove stopped containers
docker container prune -f

# Remove unused networks
docker network prune -f

# Remove unused volumes
docker volume prune -f
```

### Debug Container Issues
```bash
# Execute into container (if shell available)
docker exec -it <container_name> /bin/sh

# Check container environment
docker exec <container_name> env

# Check container processes
docker exec <container_name> ps aux
```

## Environment Variables

### Required Environment Files
- `configs/environment/.env.distroless` - Main distroless environment
- `configs/docker/distroless/distroless.env` - Distroless-specific settings

### Key Environment Variables
```bash
# Security
SECURITY_MODE=distroless
NO_NEW_PRIVILEGES=true
READ_ONLY=true

# User
USER_ID=65532
GROUP_ID=65532

# Network
NETWORK_NAME=lucid-distroless-production
SUBNET=172.23.0.0/16
GATEWAY=172.23.0.1
```

## Network Configuration

### Required Networks
- `lucid-distroless-production` (172.23.0.0/16)
- `lucid-distroless-dev` (172.24.0.0/16)
- `lucid-multi-stage-network` (172.25.0.0/16)

### Create Networks
```bash
# Create distroless networks
bash scripts/deployment/create-distroless-networks.sh
```

## Health Checks

### Test Container Health
```bash
# Test Python execution in distroless containers
docker exec <container_name> python -c "import sys; print('Python healthy'); sys.exit(0)"

# Test health check endpoint (if available)
curl http://localhost:<port>/health
```

### Monitor Container Health
```bash
# Watch container health status
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep distroless'
```

## Performance Monitoring

### Resource Usage
```bash
# Monitor resource usage
docker stats

# Check specific container resources
docker stats <container_name>
```

### Log Analysis
```bash
# Analyze container logs
docker logs <container_name> 2>&1 | grep ERROR
docker logs <container_name> 2>&1 | grep WARNING
```

## Security Verification

### Check Security Labels
```bash
# Inspect container security labels
docker inspect <container_name> | grep -A 10 Labels
```

### Verify Non-root Execution
```bash
# Check user ID in container
docker exec <container_name> id
```

### Check Read-only Filesystem
```bash
# Test write permissions (should fail)
docker exec <container_name> touch /test-write
```

## Backup and Recovery

### Backup Container Data
```bash
# Backup volumes
docker run --rm -v lucid-distroless-production-data:/data -v $(pwd):/backup alpine tar czf /backup/distroless-data-backup.tar.gz -C /data .
```

### Restore Container Data
```bash
# Restore volumes
docker run --rm -v lucid-distroless-production-data:/data -v $(pwd):/backup alpine tar xzf /backup/distroless-data-backup.tar.gz -C /data
```

## Maintenance Commands

### Update Images
```bash
# Pull latest images
docker pull pickme/lucid-base:latest-arm64
docker pull pickme/lucid-auth-service:latest-arm64

# Restart containers with new images
docker-compose -f configs/docker/distroless/distroless-runtime-config.yml up -d --force-recreate
```

### Clean Up Old Images
```bash
# Remove unused images
docker image prune -a -f

# Remove specific old images
docker rmi pickme/lucid-base:old-tag
```

## Support and Debugging

### Get Help
```bash
# Show script help
bash scripts/deployment/deploy-distroless-pi.sh --help

# Show Docker Compose help
docker-compose --help
```

### Common Issues
1. **Image not found**: Pull required images first
2. **Network not found**: Create networks first
3. **Permission denied**: Check Docker permissions
4. **Container won't start**: Check logs for errors

### Log Locations
- Container logs: `docker logs <container_name>`
- System logs: `/var/log/docker.log`
- Application logs: Inside container `/app/logs/`

---

**Note**: All commands must be run from the Raspberry Pi console (`pickme@192.168.0.75`) in the project directory (`/mnt/myssd/Lucid/Lucid`).

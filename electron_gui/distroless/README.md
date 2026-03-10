# Lucid Electron-GUI Distroless Package Documentation
# Target Platform: Raspberry Pi (linux/arm64)
# Network: lucid-pi-network (172.20.0.0/16)
# Date: 2025-01-24

## Overview

This package contains distroless Docker images for the 3 Lucid Electron-GUI profiles:
- **Admin**: Full access to all services
- **User**: Restricted access for regular users
- **Node Operator**: Node-specific access for operators

## Package Structure

```
electron-gui/distroless/
├── Dockerfile.admin          # Admin distroless image
├── Dockerfile.user           # User distroless image
├── Dockerfile.node           # Node Operator distroless image
├── docker-compose.electron-gui.yml  # Docker Compose configuration
├── build-distroless.sh       # Build script
└── README.md                 # This documentation
```

## Network Integration

All packages integrate with the `lucid-pi-network` (172.20.0.0/16) as defined in `network-configs.md`:

- **Admin GUI**: 172.20.0.100:3000
- **User GUI**: 172.20.0.101:3001
- **Node GUI**: 172.20.0.102:3002

## Service Configuration

Each package uses its respective configuration file:

- **Admin**: `configs/api-services.conf` (full access)
- **User**: `configs/api-services-user.conf` (restricted)
- **Node**: `configs/api-services-node.conf` (node-specific)

## Building the Packages

### Prerequisites

1. Docker installed and running
2. Node.js 18+ for building
3. Access to the `pickme` registry

### Build All Packages

```bash
# From the electron-gui directory
./distroless/build-distroless.sh
```

### Build Individual Packages

```bash
# Admin package
docker build --platform linux/arm64 -f distroless/Dockerfile.admin -t pickme/lucid-electron-gui-admin:latest-arm64 .

# User package
docker build --platform linux/arm64 -f distroless/Dockerfile.user -t pickme/lucid-electron-gui-user:latest-arm64 .

# Node Operator package
docker build --platform linux/arm64 -f distroless/Dockerfile.node -t pickme/lucid-electron-gui-node:latest-arm64 .
```

## Deployment

### 1. Create Network

```bash
docker network create lucid-pi-network \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --gateway 172.20.0.1 \
  --attachable
```

### 2. Deploy with Docker Compose

```bash
# Deploy all services
docker-compose -f distroless/docker-compose.electron-gui.yml up -d

# Check status
docker-compose -f distroless/docker-compose.electron-gui.yml ps
```

### 3. Individual Service Deployment

```bash
# Deploy Admin GUI only
docker-compose -f distroless/docker-compose.electron-gui.yml up -d lucid-electron-gui-admin

# Deploy User GUI only
docker-compose -f distroless/docker-compose.electron-gui.yml up -d lucid-electron-gui-user

# Deploy Node GUI only
docker-compose -f distroless/docker-compose.electron-gui.yml up -d lucid-electron-gui-node
```

## Service Access

### Admin GUI (172.20.0.100:3000)
- **Access Level**: Full
- **Services**: All 27 Lucid services
- **Use Case**: System administration, debugging, monitoring

### User GUI (172.20.0.101:3001)
- **Access Level**: Restricted
- **Services**: API Gateway, Auth, Blockchain (read-only), Session API, Wallet (own), Payment Gateway (user payments)
- **Use Case**: Regular user operations

### Node Operator GUI (172.20.0.102:3002)
- **Access Level**: Node-specific
- **Services**: API Gateway, Auth, Node Management (own node), Blockchain (read-only), TRON Client (read-only), Payout Router (read-only), Wallet (earnings), Payment Gateway (withdrawals)
- **Use Case**: Node operator management and earnings monitoring

## Health Checks

All services include health checks:

```bash
# Check Admin GUI health
curl http://172.20.0.100:3000/health

# Check User GUI health
curl http://172.20.0.101:3001/health

# Check Node GUI health
curl http://172.20.0.102:3002/health
```

## Monitoring

### View Logs

```bash
# Admin GUI logs
docker logs lucid-electron-gui-admin

# User GUI logs
docker logs lucid-electron-gui-user

# Node GUI logs
docker logs lucid-electron-gui-node
```

### Monitor Resources

```bash
# Check resource usage
docker stats lucid-electron-gui-admin lucid-electron-gui-user lucid-electron-gui-node
```

## Security Features

### Distroless Benefits
- Minimal attack surface
- No shell or package manager
- Reduced image size
- Enhanced security

### Access Control
- Role-based service access
- JWT authentication
- Rate limiting per profile
- Network isolation

### Configuration Security
- Environment-specific configs
- Restricted service endpoints
- Explicit access controls

## Troubleshooting

### Common Issues

1. **Network Connectivity**
   ```bash
   # Check network
   docker network inspect lucid-pi-network
   
   # Test connectivity
   docker exec lucid-electron-gui-admin ping 172.20.0.10
   ```

2. **Service Startup**
   ```bash
   # Check service status
   docker-compose -f distroless/docker-compose.electron-gui.yml ps
   
   # View startup logs
   docker-compose -f distroless/docker-compose.electron-gui.yml logs
   ```

3. **Configuration Issues**
   ```bash
   # Verify config files
   docker exec lucid-electron-gui-admin cat /app/configs/api-services.conf
   ```

### Performance Optimization

1. **Resource Limits**
   ```yaml
   # Add to docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: '0.5'
   ```

2. **Health Check Tuning**
   ```yaml
   # Adjust health check intervals
   healthcheck:
     interval: 60s
     timeout: 15s
     retries: 5
   ```

## Integration with Main Services

The Electron-GUI packages connect to the main Lucid services via the `lucid-pi-network`:

- **API Gateway**: 172.20.0.10:8080
- **Auth Service**: 172.20.0.14:8089
- **Blockchain Engine**: 172.20.0.15:8084
- **Session API**: 172.20.0.20:8087
- **Node Management**: 172.20.0.25:8095
- **Admin Interface**: 172.20.0.26:8083
- **TRON Client**: 172.20.0.27:8091
- **Wallet Manager**: 172.20.0.29:8093
- **Payment Gateway**: 172.20.0.32:8097

## Maintenance

### Updates

```bash
# Rebuild and redeploy
./distroless/build-distroless.sh
docker-compose -f distroless/docker-compose.electron-gui.yml up -d --force-recreate
```

### Backup

```bash
# Backup volumes
docker run --rm -v electron-gui-admin-data:/data -v $(pwd):/backup alpine tar czf /backup/admin-data-backup.tar.gz -C /data .
```

## Support

For issues or questions:
1. Check logs: `docker logs <container-name>`
2. Verify network: `docker network inspect lucid-pi-network`
3. Test connectivity: `docker exec <container> ping <target-ip>`
4. Review configuration files in `/app/configs/`

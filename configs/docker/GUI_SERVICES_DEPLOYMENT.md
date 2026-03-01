# Docker Compose GUI Integration - Services Added

**Date:** 2025-01-25  
**File:** `configs/docker/docker-compose.gui-integration.yml`  
**Status:** Updated with three Electron GUI distroless services

---

## Services Added

### 1. Admin Interface
- **Container Name:** `lucid-admin-interface`
- **Image:** `pickme/lucid-admin-interface:latest-arm64`
- **Port:** `8120` (HTTPS: `8100`)
- **Profile:** `admin`
- **Health Check:** Port 8120

### 2. User Interface
- **Container Name:** `lucid-user-interface`
- **Image:** `pickme/lucid-user-interface:latest-arm64`
- **Port:** `3001`
- **Profile:** `user`
- **Health Check:** Port 3001

### 3. Node Operator Interface
- **Container Name:** `lucid-node-interface`
- **Image:** `pickme/lucid-node-interface:latest-arm64`
- **Port:** `3002`
- **Profile:** `node_operator`
- **Health Check:** Port 3002

---

## Configuration Details

All three services include:

- **Distroless Runtime:** Optimized for ARM64 (Raspberry Pi)
- **Environment Files:** Same as existing GUI services
  - `.env.secrets`
  - `.env.core`
  - `.env.application`
  - `.env.foundation`
  - `.env.gui`

- **Networks:** Connected to both:
  - `lucid-pi-network` (main cluster)
  - `lucid-gui-network` (GUI-specific, 172.22.0.0/16)

- **API Bridge Integration:** Each service connects to `lucid-gui-api-bridge:8097`

- **Volumes:** Dedicated logs and data directories for each service

- **Health Checks:** 30-second interval, 10-second timeout, 40-second start period

- **Security:**
  - Non-root user: `65532:65532`
  - Read-only filesystem
  - Security options: `no-new-privileges:true`
  - Minimal capabilities: only `NET_BIND_SERVICE`
  - Drop all other capabilities

- **Labels:** Standard Lucid labels for monitoring and orchestration:
  - `com.lucid.phase=gui`
  - `com.lucid.cluster=gui-integration`
  - Profile-specific service label

---

## Deployment Commands

### Start Single Service

```bash
# Admin interface only
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  up -d admin-interface

# User interface only
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  up -d user-interface

# Node operator interface only
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  up -d node-interface
```

### Start All GUI Services

```bash
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d
```

### Check Service Status

```bash
docker-compose -f configs/docker/docker-compose.gui-integration.yml ps

# Specific service
docker logs lucid-admin-interface
docker logs lucid-user-interface
docker logs lucid-node-interface
```

### Health Check

```bash
# Admin interface
curl -f http://127.0.0.1:8120/health

# User interface
curl -f http://127.0.0.1:3001/health

# Node operator interface
curl -f http://127.0.0.1:3002/health
```

---

## Service Dependencies

All three services depend on:
- `gui-api-bridge` (must be healthy before starting)

### Start Order

1. Core infrastructure (api-gateway, auth-service, etc.)
2. GUI backend services (gui-api-bridge)
3. GUI interfaces (admin, user, node)

```bash
# Automatic with docker-compose depends_on
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d
```

---

## Networking

### Port Mapping

| Service | Container Port | Host Port | Protocol |
|---------|-----------------|-----------|----------|
| Admin Interface | 8120 | 8120 | HTTP |
| Admin Interface (HTTPS) | 8100 | 8100 | HTTPS |
| User Interface | 3001 | 3001 | HTTP |
| Node Operator Interface | 3002 | 3002 | HTTP |

### Internal Communication

All services communicate via `lucid-gui-network` (172.22.0.0/16):
- DNS resolution uses container names
- Secure inter-service communication
- Isolated from main `lucid-pi-network`

---

## Data Persistence

Each service has dedicated volumes:

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/logs/<service>:/app/logs
  - /mnt/myssd/Lucid/Lucid/data/<service>:/app/data
```

Services:
- `admin-interface`
- `user-interface`
- `node-interface`

---

## Environment Variables

### Common to All Services

```yaml
NODE_ENV=production
ELECTRON_GUI_PROFILE=<profile>
ELECTRON_GUI_NETWORK=lucid-pi-network
ELECTRON_GUI_API_BASE_URL=http://lucid-gui-api-bridge:8097/api/v1
LOG_LEVEL=INFO
LUCID_ENV=production
```

### Service-Specific

**Admin Interface:**
- `ELECTRON_GUI_CONFIG_FILE=/app/configs/api-services.conf`
- `ADMIN_INTERFACE_HOST=0.0.0.0`
- `ADMIN_INTERFACE_PORT=8120`

**User Interface:**
- `ELECTRON_GUI_CONFIG_FILE=/app/configs/api-services-user.conf`

**Node Operator Interface:**
- `ELECTRON_GUI_CONFIG_FILE=/app/configs/api-services-node.conf`

---

## Next Steps

1. **Build Images:**
   ```bash
   cd /mnt/myssd/Lucid/Lucid
   bash electron-gui/distroless/build-distroless.sh
   ```

2. **Verify Images:**
   ```bash
   docker images | grep lucid-.*-interface
   ```

3. **Deploy Services:**
   ```bash
   docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d
   ```

4. **Monitor Health:**
   ```bash
   docker-compose -f configs/docker/docker-compose.gui-integration.yml ps
   ```

---

## File Reference

**Location:** `configs/docker/docker-compose.gui-integration.yml`  
**Lines:** 230-391 (new services)  
**Lines:** 1-229 (existing GUI backend services)  
**Lines:** 392-411 (networks configuration)

---

**Maintained By:** Lucid Development Team  
**Last Updated:** 2025-01-25  
**Status:** Ready for deployment

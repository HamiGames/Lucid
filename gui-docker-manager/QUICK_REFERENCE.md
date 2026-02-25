# GUI-DOCKER-MANAGER - QUICK REFERENCE

## 🎯 STATUS: COMPLETE ✅

All 8 recommendation phases successfully implemented.

---

## 📍 KEY FILES

### Configuration
- `configs/docker/docker-compose.gui-integration.yml` - Service dependencies added
- `configs/environment/.env.gui` - Shared GUI settings
- `configs/environment/.env.gui-docker-manager` - Service-specific config

### Services  
- `services/authentication_service.py` - JWT + RBAC
- `services/network_service.py` - Docker network ops
- `services/volume_service.py` - Docker volume ops

### Routers
- `routers/networks.py` - Network management (6 endpoints)
- `routers/volumes.py` - Volume management (5 endpoints)
- `routers/events.py` - WebSocket streaming
- `routers/containers.py` - Enhanced with pause/unpause/remove

### Models
- `models/responses.py` - Response models (8 types)
- `models/network.py` - Network data models (6 types)
- `models/volume.py` - Volume data models (7 types)

### Configuration
- `configs/services/gui-docker-manager-service-groups.yml`
- `configs/services/service-registry.json`
- `configs/services/permissions-matrix.json`
- `schemas/docker-events.schema.json`

---

## 🔌 QUICK ENDPOINT REFERENCE

### Container Operations
```
GET     /api/v1/containers
POST    /api/v1/containers/{id}/start
POST    /api/v1/containers/{id}/stop
POST    /api/v1/containers/{id}/pause        [NEW]
POST    /api/v1/containers/{id}/unpause      [NEW]
DELETE  /api/v1/containers/{id}              [NEW]
```

### Network Management [NEW]
```
GET     /api/v1/networks
POST    /api/v1/networks
DELETE  /api/v1/networks/{id}
POST    /api/v1/networks/{id}/connect
```

### Volume Management [NEW]
```
GET     /api/v1/volumes
POST    /api/v1/volumes
DELETE  /api/v1/volumes/{name}
```

### Event Streaming [NEW]
```
WebSocket /api/v1/events/ws
GET       /api/v1/events/subscribe
```

---

## 🔐 AUTHENTICATION

### Enable JWT Auth
1. Set `JWT_SECRET_KEY` in environment
2. Create token with role (user/developer/admin)
3. Include `Authorization: Bearer <token>` header

### Permissions
| Operation | USER | DEV | ADMIN |
|-----------|------|-----|-------|
| Read containers | ✅ | ✅ | ✅ |
| Manage containers | ❌ | ✅ | ✅ |
| Remove containers | ❌ | ❌ | ✅ |
| Manage networks | ❌ | ✅ | ✅ |
| Manage volumes | ❌ | ✅ | ✅ |
| Compose operations | ❌ | ❌ | ✅ |

---

## 🚀 DEPLOYMENT

### Prerequisites
- Docker with socket at `/var/run/docker.sock`
- lucid-mongodb healthy
- lucid-redis healthy
- api-gateway healthy
- JWT_SECRET_KEY set

### Quick Start
```bash
# Build
docker build -f gui-docker-manager/Dockerfile.gui-docker-manager -t gui-docker-manager .

# Deploy
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d gui-docker-manager

# Verify
curl http://localhost:8098/health
```

---

## 🧪 TESTING

### Health Check
```bash
curl http://localhost:8098/health
```

### List Containers
```bash
curl http://localhost:8098/api/v1/containers
```

### WebSocket Events
```javascript
ws = new WebSocket('ws://localhost:8098/api/v1/events/ws');
ws.send(JSON.stringify({
  container_names: [],
  event_types: ["start", "stop"]
}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## 📊 WHAT'S NEW

| Phase | Item | Details |
|-------|------|---------|
| 1 | Dependencies | Added explicit depends_on for mongo/redis/gateway |
| 2 | Auth | JWT + RBAC with 3 role levels |
| 3 | Endpoints | 15+ new endpoints (pause, unpause, remove, networks, volumes) |
| 4 | Events | Real-time WebSocket event streaming |
| 5 | Registry | Service groups, registry, permissions matrix |
| 6 | Models | 17 new Pydantic models for responses |
| 7 | Config | Environment variables and templates |
| 8 | Schema | JSON schema for Docker events |

---

## ⚠️ IMPORTANT NOTES

1. **Middleware Order**: Authentication is applied to all endpoints except excluded paths
2. **WebSocket**: Connect to `/api/v1/events/ws` directly (no /api/v1/events prefix in path)
3. **Dependencies**: Service won't start until all depends_on services are healthy
4. **Docker Socket**: Must be mounted read-only as per docker-compose config
5. **JWT Secret**: Critical for production - use secure value from secrets manager

---

## 📝 DOCUMENTATION

- `IMPLEMENTATION_COMPLETE.md` - Full details
- `DEPLOYMENT_SUMMARY.md` - Deployment checklist

---

## 🔗 RELATED SERVICES

| Service | Port | Purpose |
|---------|------|---------|
| lucid-mongodb | 27017 | Data storage |
| lucid-redis | 6379 | Caching |
| api-gateway | 8080 | API routing |
| gui-api-bridge | 8102 | GUI proxy |
| gui-docker-manager | 8098 | This service |

---

**Ready to Deploy** ✅ | Updated: 2026-02-25 | v1.0.0

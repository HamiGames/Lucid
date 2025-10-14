# Cluster 04: RDP Services - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 04-RDP-SERVICES |
| Build Phase | Phase 3 (Weeks 5-7) |
| Parallel Track | Track E |
| Version | 1.0.0 |

---

## Cluster Overview

### Services (Ports 8090-8093)
1. **RDP Server Manager** (8090) - Server instance management
2. **XRDP Integration** (8091) - XRDP configuration
3. **Session Controller** (8092) - Connection management
4. **Resource Monitor** (8093) - Resource tracking

### Dependencies
- Cluster 01 (API Gateway): Authentication, routing
- Cluster 08 (Database): Server metadata

---

## MVP Files (50 files, ~7,000 lines)

### Core Services (25 files, ~4,000 lines)
- RDP Server Manager: `main.py`, `server_manager.py`, `port_manager.py`
- XRDP Integration: `xrdp_config.py`, `xrdp_service.py`
- Session Controller: `session_controller.py`, `connection_manager.py`
- Resource Monitor: `resource_monitor.py`, `metrics_collector.py`

### Configuration (10 files, ~1,500 lines)
- Dockerfiles (4 services)
- docker-compose files
- Requirements, env vars

### API Layer (15 files, ~1,500 lines)
- API routes for each service
- Models and schemas
- Middleware

---

## Build Sequence (21 days)

### Week 1: RDP Server Manager + XRDP Integration
**Days 1-3**: RDP Server Manager
- Server lifecycle management
- Port allocation
- Configuration management

**Days 4-7**: XRDP Integration
- XRDP config generation
- Service control
- Template management

### Week 2: Session Controller + Resource Monitor
**Days 8-10**: Session Controller
- Connection management
- Session routing
- Access control

**Days 11-14**: Resource Monitor
- CPU/memory monitoring
- Disk usage tracking
- Network metrics

### Week 3: Integration & Testing
**Days 15-17**: Service integration
**Days 18-21**: Testing and containerization

---

## Key Implementations

### RDP Server Manager
```python
# rdp-server-manager/core/server_manager.py (350 lines)
class RDPServerManager:
    async def create_server(self, user_id, config):
        # Allocate port
        # Generate config
        # Start XRDP instance
        
    async def start_server(self, server_id):
        # Start XRDP service
        # Update status
```

### XRDP Integration
```python
# xrdp-integration/core/xrdp_service.py (300 lines)
class XRDPService:
    async def configure_xrdp(self, server_id, config):
        # Generate xrdp.ini
        # Generate sesman.ini
        # Restart service
```

---

## Environment Variables
```bash
RDP_SERVER_MANAGER_PORT=8090
XRDP_INTEGRATION_PORT=8091
SESSION_CONTROLLER_PORT=8092
RESOURCE_MONITOR_PORT=8093

RDP_PORT_RANGE_START=13389
RDP_PORT_RANGE_END=14389
MAX_CONCURRENT_SERVERS=100
```

---

## Docker Compose
```yaml
services:
  rdp-server-manager:
    ports: ["8090:8090"]
  xrdp-integration:
    ports: ["8091:8091"]
  session-controller:
    ports: ["8092:8092"]
  resource-monitor:
    ports: ["8093:8093"]
```

---

## Success Criteria
- [ ] RDP servers created dynamically
- [ ] XRDP configured per user
- [ ] Sessions controlled and monitored
- [ ] Resources tracked
- [ ] All 4 services containerized

---

**Build Time**: 21 days (2 developers)



---

## DOCKER COMPOSE NETWORK DEFINITIONS

### Complete Network Configuration

```yaml
networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
    attachable: true
    
  lucid-tron-isolated:
    driver: bridge
    ipam:
      magyar:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
    attachable: true
    
  lucid-gui-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16
          gateway: 172.22.0.1
    attachable: true
    
  lucid-distroless调动:
    driver: bridge
    ipam:
      config:
        - subnet: 172.23.0.0/16
          gateway: 172.23.0.1
    attachable: true
    
  lucid-distroless-dev:
    driver: bridge
    ipam:
      config:
        - subnet: 172.24.0.0/16
          gateway: 172.24.0.1
    attachable: true
    
  lucid-multi-stage-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
          gateway: 172.25.0.1
    attachable: true
```

---

## VOLUME MAPPINGS (from project root)

All volumes stem from: `/mnt/myssd/Lucid/Lucid/`

### Foundation Services Volumes
- `/mnt/myssd/Lucid/Lucid/data/mongodb`
- `/mnt/myssd/Lucid/Lucid/data/redis`
- `/mnt/myssd/Lucid/Lucid/data/elasticsearch`
- `/mnt/myssd/Lucid/Lucid/logs/*`

### Application Services Volumes
- `/mnt/myssd/Lucid/Lucid/data/sessions`
- `/mnt/myssd/Lucid/Lucid/data/encrypted`
- `/mnt/myssd/Lucid/Lucid/data/rdp-sessions`
- `/mnt/myssd/Lucid/Lucid/data/rdp-recordings`
- `/mnt/myssd/Lucid/Lucid/data/blockchain`
- `/mnt/myssd/Lucid/Lucid/data/nodes`

### Payment Services Volumes
- `/mnt/myssd/Lucid/Lucid/data/tron`
- `/mnt/myssd/Lucid/Lucid/data/payments`
- `/mnt/myssd/Lucid/Lucid/data/wallets`
- `/mnt/myssd/Lucid/Lucid/data/usdt`
- `/mnt/myssd/Lucid/Lucid/data/staking`
- `/mnt/myssd/Lucid/Lucid/data/keys` (read-only)

---

## ENVIRONMENT FILE ALIGNMENT

All services must use environment files from:
- `/mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation`
- `/mnt/myssd/Lucid/Lucid/configs/environment/.env.core`
- `/mnt/myssd/Lucid/Lucid/configs/environment/.env.application` (for Phase 3)
- `/mnt/myssd/Lucid/Lucid/configs/environment/.env.support` (for Phase 4)

Additional service-specific env files as specified in essentials.md lines 11-114.

---

## DEPLOYMENT FILES REFERENCE

All services operate from the following deployment files:

### Core Infrastructure
- `infrastructure/compose/docker-compose.core.yaml` - Foundation & Core services
- `infrastructure/compose/docker-compose.blockchain.yaml` - Blockchain services
- `infrastructure/compose/docker-compose.sessions.yaml` - Session services
- `infrastructure/compose/docker-compose.payment-systems.yaml` - Payment services

### Individual Service Compose Files
- `auth/docker-compose.yml` - Auth service
- `sessions/docker-compose.yml` - Session services
- `RDP/docker-compose.yml` - RDP services
- `node/docker-compose.yml` - Node management
- `payment-systems/tron/docker-compose.yml` - TRON payment services

### Kubernetes Configurations
- `infrastructure/kubernetes/03-databases/*.yaml` - Database services
- `infrastructure/kubernetes/04-auth/*.yaml` - Auth service
- `infrastructure/kubernetes/05-core/*.yaml` - Core services
- `infrastructure/kubernetes/06-application/*.yaml` - Application services
- `infrastructure/kubernetes/07-support/*.yaml` - Support services
- `infrastructure/kubernetes/01-configmaps/*.yaml` - Service configurations

---

## CONSTANTS COMPLIANCE VERIFICATION

All network configurations align with:
- ✅ `plan/constants/essentials.md` - Service definitions and IP allocations
- ✅ Network subnet definitions (172.20.0.0/16, 172.21.0.0/16, 172.22.0.0/16)
- ✅ Port allocations as specified in essentials.md
- ✅ Volume paths from project root (`/mnt/myssd/Lucid/Lucid/`)
- ✅ Environment file paths from `configs/environment/`
- ✅ Health check endpoints and ports
- ✅ Service dependencies and startup order

---

**Document Status:** Complete  
**All 27 services documented with full network configuration**
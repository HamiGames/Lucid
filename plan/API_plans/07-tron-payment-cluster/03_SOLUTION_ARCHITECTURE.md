# TRON Payment System API - Solution Architecture

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-ARCH-003 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

The TRON Payment System API implements a secure, isolated payment infrastructure for USDT-TRC20 payouts within the Lucid RDP ecosystem. This document defines the unified Python-based architecture that consolidates existing implementations and enforces strict service isolation according to SPEC-1B-v2 requirements.

### Key Principles

1. **Unified Implementation**: Single Python-based service using FastAPI
2. **Service Isolation**: Complete separation from blockchain core operations
3. **API Gateway Integration**: Centralized entry point with authentication
4. **Distroless Deployment**: Minimal attack surface containers
5. **Tor-Only Access**: All communication via .onion endpoints

---

## Three-Tier Architecture

### Plane Separation Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Ops Plane (Cluster A)                     │
│                                                               │
│  ┌─────────────────┐     ┌──────────────────┐              │
│  │  API Gateway    │────▶│  Authentication  │              │
│  │  (Port 8080)    │     │  & Authorization │              │
│  └────────┬────────┘     └──────────────────┘              │
└───────────┼──────────────────────────────────────────────────┘
            │
            │ Proxy Routes (JWT Validated)
            │
┌───────────▼──────────────────────────────────────────────────┐
│              Chain Plane (Cluster B)                          │
│                                                               │
│  ┌───────────────────────────────────────────────────┐      │
│  │       Blockchain Core (Port 8084)                 │      │
│  │       - Session anchoring (lucid_blocks)         │      │
│  │       - Merkle proof generation                   │      │
│  │       - PoOT consensus                            │      │
│  └───────────────────────────────────────────────────┘      │
└───────────────────────────────────────────────────────────────┘
            
            ║ STRICT ISOLATION ║
            
┌───────────────────────────────────────────────────────────────┐
│             Wallet Plane (Payment Tier)                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │    TRON Payment Service (Port 8090)                │    │
│  │                                                      │    │
│  │  ┌──────────────────┐  ┌───────────────────────┐  │    │
│  │  │ PayoutRouterV0   │  │  PayoutRouterKYC      │  │    │
│  │  │ (Non-KYC)        │  │  (KYC-gated)          │  │    │
│  │  └──────────────────┘  └───────────────────────┘  │    │
│  │                                                      │    │
│  │  ┌──────────────────┐  ┌───────────────────────┐  │    │
│  │  │ TronService      │  │  PayoutManager        │  │    │
│  │  │ (TronPy client)  │  │  (Orchestration)      │  │    │
│  │  └──────────────────┘  └───────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│                  TRON Network                                │
│            (USDT-TRC20 Mainnet/Shasta)                      │
└───────────────────────────────────────────────────────────────┘
```

### Service Boundaries

#### Blockchain Core (lucid_blocks)
- **Scope**: Session anchoring, consensus (PoOT), governance
- **Port**: 8084
- **Container**: `lucid-blocks-core`
- **Database**: `sessions`, `chunks`, `task_proofs`, `work_tally`
- **Prohibited**: NO payment operations

#### TRON Payment Service (Isolated)
- **Scope**: USDT-TRC20 payouts ONLY
- **Port**: 8090
- **Container**: `tron-payment-service`
- **Database**: `payouts` (isolated collection)
- **Prohibited**: NO blockchain operations, NO consensus, NO session anchoring

#### API Gateway
- **Scope**: Centralized entry point, authentication, rate limiting
- **Port**: 8080
- **Container**: `lucid-api-gateway`
- **Function**: Proxy requests to appropriate services

---

## Component Architecture

### Core Components

```python
# Unified Payment Service Architecture
class PaymentService:
    def __init__(self):
        self.tron_service = TronService()
        self.payout_manager = PayoutManager()
        self.router_v0 = PayoutRouterV0()
        self.router_kyc = PayoutRouterKYC()
        self.circuit_breaker = CircuitBreaker()
        self.audit_logger = AuditLogger()
```

### Service Dependencies

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│  Authentication  │───▶│  Rate Limiting  │
└─────────┬───────┘    └──────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Payment Service │───▶│   TronService    │───▶│  TRON Network   │
└─────────┬───────┘    └──────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ PayoutManager   │───▶│ Circuit Breaker  │───▶│   MongoDB       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## API Gateway Integration

### Proxy Routing Pattern

```python
# API Gateway Payment Proxy
@router.post("/api/payment/{path:path}")
async def proxy_payment(
    path: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy payment requests to TRON Payment Service
    
    Flow:
    1. Validate JWT token
    2. Check user permissions
    3. Apply rate limiting
    4. Add user context headers
    5. Proxy to payment service
    6. Return response
    """
    # Validate permissions
    if not await require_permissions(current_user, ["payment:create"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Add user context
    headers = {
        "X-User-ID": current_user.id,
        "X-User-Role": current_user.role,
        "X-Request-ID": generate_request_id()
    }
    
    # Proxy to payment service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYMENT_SERVICE_URL}/{path}",
            json=await request.json(),
            headers=headers
        )
    
    return response.json()
```

### Authentication Flow

```
Client Request
     │
     ▼
┌─────────────┐    JWT Token    ┌─────────────────┐
│ API Gateway │◄───────────────▶│  Auth Service   │
└─────┬───────┘                 └─────────────────┘
      │
      │ Validate & Extract User Context
      ▼
┌─────────────┐    User Headers ┌─────────────────┐
│ Payment     │◄────────────────│ API Gateway     │
│ Service     │                 │ (Proxy)         │
└─────────────┘                 └─────────────────┘
```

---

## Service Isolation Strategies

### Beta Sidecar Integration

```yaml
# Beta Sidecar Configuration
services:
  tron-payment-service:
    image: pickme/lucid:tron-payment-latest
    networks:
      - wallet_plane
    depends_on:
      - tron-payment-beta-sidecar

  tron-payment-beta-sidecar:
    image: pickme/lucid:beta-sidecar-latest
    networks:
      - wallet_plane
    environment:
      - SERVICE_NAME=tron-payment-service
      - SERVICE_PORT=8090
      - PLANE=wallet
      - ACL_POLICY=wallet_plane_policy
```

### Access Control Lists (ACLs)

```yaml
# Wallet Plane ACL Policy
rule "gateway_to_payment" {
  source_plane = "ops"
  source_service = "api-gateway"
  target_plane = "wallet"
  target_service = "tron-payment-service"
  allowed_endpoints = ["/payouts", "/payouts/*", "/health", "/metrics"]
  action = "allow"
}

rule "blockchain_to_payment_deny" {
  source_plane = "chain"
  target_plane = "wallet"
  action = "deny"
  reason = "SPEC-1B-v2: Blockchain Tier cannot access Payment Tier"
}

rule "payment_to_blockchain_deny" {
  source_plane = "wallet"
  target_plane = "chain"
  action = "deny"
  reason = "Payment Tier operates independently"
}
```

---

## Network Topology

### Tor-Only Access Configuration

```yaml
# Tor Hidden Service Configuration
services:
  tor-proxy:
    image: alpine-tor:latest
    volumes:
      - ./configs/tor/torrc:/etc/tor/torrc:ro
    environment:
      - HIDDEN_SERVICE_DIR=/var/lib/tor/hidden_service
    networks:
      - tor_network

  api-gateway:
    image: pickme/lucid:api-gateway-latest
    networks:
      - ops_plane
      - wallet_plane
      - tor_network
    ports:
      - "8080:8080"  # Accessible via Tor only
    depends_on:
      - tor-proxy

networks:
  ops_plane:
    driver: bridge
    internal: false  # Can access external via Tor
  
  wallet_plane:
    driver: bridge
    internal: true   # Fully isolated, no external access
  
  tor_network:
    driver: bridge
    internal: false  # Routes to Tor network
```

### Network Isolation Rules

1. **Ops Plane**: Can access external via Tor, can access other planes
2. **Chain Plane**: Internal only, no external access, no payment access
3. **Wallet Plane**: Internal only, can access external TRON via Tor
4. **Tor Network**: Routes all external communication

---

## Docker Compose Service Definitions

### Payment Service Configuration

```yaml
services:
  tron-payment-service:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile
      target: distroless
    image: pickme/lucid:tron-payment-service:latest
    container_name: tron-payment-service
    networks:
      - wallet_plane
    environment:
      - LUCID_ENV=production
      - SERVICE_NAME=tron-payment-service
      - PORT=8090
      - TRON_NETWORK=mainnet
      - MONGO_URL=mongodb://lucid:lucid@mongo:27017/lucid_payments
      - API_GATEWAY_URL=http://api-gateway:8080
      - TOR_PROXY=socks5://tor-proxy:9050
    volumes:
      - ./configs/secrets:/run/secrets:ro
    healthcheck:
      test: ["CMD-SHELL", "python3 -c \"import httpx; httpx.get('http://localhost:8090/health').raise_for_status()\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

### Database Isolation

```yaml
services:
  mongo:
    image: mongo:7.0
    container_name: lucid-mongo
    networks:
      - chain_plane
      - wallet_plane
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=lucid
    volumes:
      - mongo_data:/data/db
      - ./scripts/database/init_collections.js:/docker-entrypoint-initdb.d/init.js:ro
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]

volumes:
  mongo_data:
    driver: local
```

---

## Component Interaction Diagrams

### Payout Creation Flow

```
User Request
     │
     ▼
┌─────────────┐    JWT Validation    ┌─────────────────┐
│ API Gateway │◄────────────────────▶│  Auth Service   │
└─────┬───────┘                      └─────────────────┘
      │
      │ Proxy with User Context
      ▼
┌─────────────┐    Router Selection  ┌─────────────────┐
│ Payment     │◄────────────────────▶│ PayoutManager   │
│ Service     │                      └─────────────────┘
└─────┬───────┘
      │
      │ USDT Transfer
      ▼
┌─────────────┐    TRON Network     ┌─────────────────┐
│ TronService │◄───────────────────▶│ TRON Blockchain │
└─────────────┘                     └─────────────────┘
```

### Batch Processing Flow

```
Batch Request
     │
     ▼
┌─────────────┐    Validation      ┌─────────────────┐
│ PayoutManager│◄──────────────────▶│ Circuit Breaker │
└─────┬───────┘                    └─────────────────┘
      │
      │ Individual Payouts
      ▼
┌─────────────┐    Queue Management ┌─────────────────┐
│ Batch Queue │◄───────────────────▶│ Priority Queues │
└─────┬───────┘                    └─────────────────┘
      │
      │ Process by Batch Type
      ▼
┌─────────────┐    Status Updates   ┌─────────────────┐
│ TronService │◄───────────────────▶│   MongoDB       │
└─────────────┘                    └─────────────────┘
```

---

## SPEC-1B-v2 Compliance

### TRON Isolation Requirements

✅ **ALLOWED Operations:**
- USDT-TRC20 transfers via PayoutRouterV0/PRKYC
- Energy/bandwidth management (TRX staking)
- Monthly payout distribution
- Wallet integration for payouts

❌ **PROHIBITED Operations:**
- Session anchoring (use lucid_blocks)
- Consensus participation (use PoOT)
- Chunk storage (use lucid_blocks)
- Governance operations (use lucid_blocks)
- Any blockchain operations beyond payments

### Distroless Compliance

- **Base Image**: `gcr.io/distroless/python3-debian12:nonroot`
- **User**: Non-root user (UID 65532)
- **Filesystem**: Read-only root filesystem
- **Security**: No shell, no package managers
- **Health Checks**: HTTP-based (no shell commands)

### Service Separation

- **Container**: `tron-payment-service` (isolated)
- **Network**: Wallet plane only via Beta sidecar
- **Data**: Only `payouts` collection access
- **Communication**: Via API Gateway proxy only

---

## Implementation Roadmap

### Phase 1: Consolidation (Week 1)
1. Remove Node.js implementation
2. Consolidate Python codebase
3. Implement API Gateway integration
4. Configure Beta sidecar ACLs

### Phase 2: Security (Week 2)
1. Implement multi-layer authentication
2. Configure Tor-only access
3. Set up audit logging
4. Implement circuit breakers

### Phase 3: Operations (Week 3)
1. Deploy distroless containers
2. Configure monitoring/metrics
3. Set up health checks
4. Implement batch processing

### Phase 4: Validation (Week 4)
1. Security audit
2. Performance testing
3. Integration testing
4. Documentation review

---

## References

- [SPEC-1B-v2-DISTROLESS.md](../../../docs/build-docs/Build_guide_docs/SPEC-1B-v2-DISTROLESS.md) - Core architecture specification
- [02_PROBLEM_ANALYSIS.md](02_PROBLEM_ANALYSIS.md) - Detailed problem analysis
- [04_API_SPECIFICATIONS.md](04_API_SPECIFICATIONS.md) - API endpoint specifications
- [TRON Documentation](https://developers.tron.network/) - Official TRON developer docs
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - API framework reference

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12

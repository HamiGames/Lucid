# Lucid API Master Architecture

## Overview

This document defines the master API architecture for the Lucid blockchain system, establishing consistent naming conventions, service isolation principles, and architectural patterns across all service clusters.

## Core Architecture Principles

### 1. Consistent Naming Convention

**CRITICAL**: All documentation and code MUST use consistent naming:

- **On-Chain Blockchain System**: Always `lucid_blocks` (Python), `lucid-blocks` (containers)
- **TRON Payment System**: Always `tron-payment-service` (isolated container)
- **Service Naming**: `{cluster}-{service}` format (e.g., `api-gateway`, `session-recorder`)
- **Container Naming**: `lucid-{cluster}-{service}` format (e.g., `lucid-api-gateway`)

### 2. TRON Isolation Architecture

**CRITICAL**: TRON is STRICTLY a payment system and MUST be completely isolated from core blockchain operations.

**TRON ISOLATION RULES**:
- ✅ TRON handles: USDT-TRC20 transfers, payout routing, wallet integration, TRX staking
- ❌ TRON NEVER handles: session anchoring, consensus, chunk storage, governance, DHT/CRDT, work credits, leader selection
- ❌ TRON code MUST NOT appear in `blockchain/` directory
- ✅ TRON code ONLY in `payment-systems/tron-payment-service/` directory

### 3. Distroless Container Mandate

**MANDATORY**: All production containers MUST use distroless base images:

- **Base Images**: `gcr.io/distroless/python3-debian12` or `gcr.io/distroless/java17-debian12`
- **Multi-stage builds**: Required for all services
- **Security**: Minimal attack surface, no shell, no package managers
- **Size**: Optimized for minimal footprint

### 4. Service Plane Isolation

**Beta Sidecar Pattern**: Enforce strict service isolation:

- **Ops Plane**: Management and monitoring services
- **Chain Plane**: Core blockchain operations (`lucid_blocks`)
- **Wallet Plane**: Payment operations (TRON only)

## Service Cluster Architecture

### Cluster Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Cluster (A)                  │
│  Ports: 8080 (HTTP), 8081 (HTTPS)                          │
│  Services: Gateway, Router, Load Balancer                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Blockchain Core Cluster (B)                  │
│  Port: 8084                                                  │
│  Services: lucid_blocks, Consensus, Session Anchoring       │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Application Service Clusters                 │
│  Session Management, RDP Services, Node Management          │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Support Service Clusters                     │
│  Admin Interface, Storage, Authentication                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                TRON Payment Cluster (ISOLATED)              │
│  Port: 8085 (isolated)                                      │
│  Services: TRON Client, Payout Router, Wallet Manager       │
└─────────────────────────────────────────────────────────────┘
```

## API Design Standards

### 1. RESTful Design Principles

- **Resource-based URLs**: `/api/v1/sessions`, `/api/v1/blocks`
- **HTTP Methods**: GET, POST, PUT, PATCH, DELETE
- **Status Codes**: Standard HTTP status codes with Lucid-specific error extensions
- **Content Types**: `application/json` for all API communications

### 2. API Versioning

- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: Maintain for minimum 6 months
- **Deprecation Notice**: 3-month advance notice for breaking changes

### 3. Error Handling Standard

**Standard Error Response Schema**:
```json
{
  "error": {
    "code": "LUCID_ERR_XXXX",
    "message": "Human-readable error message",
    "details": {
      "field": "specific field error details",
      "constraint": "validation constraint violated"
    },
    "request_id": "req-uuid-here",
    "timestamp": "2025-01-10T19:08:00Z",
    "service": "api-gateway",
    "version": "v1"
  }
}
```

**Error Code Categories**:
- `LUCID_ERR_1XXX`: Validation errors
- `LUCID_ERR_2XXX`: Authentication/Authorization errors
- `LUCID_ERR_3XXX`: Rate limiting errors
- `LUCID_ERR_4XXX`: Business logic errors
- `LUCID_ERR_5XXX`: System errors

### 4. Rate Limiting Standards

**Tiered Rate Limiting**:
- **Public Endpoints**: 100 requests/minute per IP
- **Authenticated Endpoints**: 1000 requests/minute per token
- **Admin Endpoints**: 10000 requests/minute per admin token
- **Chunk Uploads**: 10 MB/second per session
- **Blockchain Queries**: 500 requests/minute per authenticated user

### 5. Data Transfer Limits

**API-Level Enforcement**:
- **Request Size**: Maximum 100MB per request
- **Session Size**: Maximum 100GB per session (enforced at API gateway)
- **Chunk Size**: Maximum 10MB per chunk
- **Response Streaming**: For responses > 1MB
- **Pagination**: Maximum 1000 items per page

## Security Architecture

### 1. Authentication Flow

```
┌─────────────┐    Magic Link    ┌─────────────┐    TOTP Code    ┌─────────────┐
│    User     │ ───────────────► │   Email     │ ──────────────► │   TOTP      │
│             │                  │  Service    │                 │  Generator  │
└─────────────┘                  └─────────────┘                 └─────────────┘
       │                                 │                              │
       │ JWT Token                       │                              │
       ▼                                 ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        JWT Token Service                                   │
│  - Access Token (15 min)                                                   │
│  - Refresh Token (7 days)                                                  │
│  - Hardware Wallet Integration                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Authorization Model

**Role-Based Access Control (RBAC)**:
- **User**: Basic session operations
- **Node Operator**: Node management, PoOT operations
- **Admin**: System management, blockchain operations
- **Super Admin**: Full system access, TRON payout management

### 3. Network Security

**Tor-Only Transport**:
- All external communication via `.onion` endpoints
- Internal service communication via Beta sidecar
- No direct internet access for production services

## Inter-Service Communication

### 1. Service Discovery

**Beta Sidecar Pattern**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: blockchain-core
spec:
  selector:
    app: blockchain-core
  ports:
  - port: 8084
    targetPort: 8084
```

### 2. Circuit Breaker Pattern

**Implementation**:
```python
from circuit_breaker import CircuitBreaker

@CircuitBreaker(failure_threshold=5, recovery_timeout=30)
async def call_blockchain_service(request):
    # Service call with automatic failure handling
    pass
```

### 3. Error Propagation

**Standard Error Chain**:
```
API Gateway → Service Cluster → Database/External
     ↓              ↓                    ↓
  Rate Limit    Business Logic      System Error
     ↓              ↓                    ↓
  LUCID_ERR_3XXX  LUCID_ERR_4XXX    LUCID_ERR_5XXX
```

## Monitoring and Observability

### 1. Health Check Standards

**Health Check Endpoint**: `/health`
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "1.0.0",
  "timestamp": "2025-01-10T19:08:00Z",
  "dependencies": {
    "blockchain-core": "healthy",
    "database": "healthy",
    "tron-payment": "healthy"
  }
}
```

### 2. Metrics Collection

**Key Metrics**:
- Request rate (requests/second)
- Response time (percentiles: 50th, 95th, 99th)
- Error rate (4xx, 5xx responses)
- Resource utilization (CPU, memory, disk)
- Business metrics (sessions created, blocks anchored)

### 3. Logging Standards

**Structured Logging**:
```json
{
  "timestamp": "2025-01-10T19:08:00Z",
  "level": "INFO",
  "service": "api-gateway",
  "request_id": "req-uuid-here",
  "user_id": "user-uuid",
  "action": "session_created",
  "duration_ms": 150,
  "status": "success"
}
```

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create master architecture document
- [ ] Establish naming conventions across codebase
- [ ] Document TRON isolation violations
- [ ] Create API error code registry

### Phase 2: Core Services (Week 2)
- [ ] API Gateway cluster documentation
- [ ] Blockchain Core cluster documentation
- [ ] TRON Payment cluster documentation (isolation focus)

### Phase 3: Application Services (Week 3)
- [ ] Session Management cluster documentation
- [ ] RDP Services cluster documentation
- [ ] Node Management cluster documentation

### Phase 4: Support Services (Week 4)
- [ ] Admin Interface cluster documentation
- [ ] Storage Database cluster documentation
- [ ] Authentication cluster documentation
- [ ] Cross-Cluster Integration documentation

### Phase 5: Implementation (Week 5)
- [ ] Create implementation checklists
- [ ] Priority matrix for API fixes
- [ ] Migration guides for breaking changes
- [ ] Testing strategy documentation

## Critical Issues to Address

### 1. Naming Inconsistencies (Priority: CRITICAL)

**Current Issues**:
- `blockchain-core` vs `blockchain_engine` vs `blockchain_api`
- `tron_client` vs `TronNodeSystem` vs `TronNodeClient`
- `SERVICE_NAME` variations across services

**Resolution**:
- Standardize all blockchain references to `lucid_blocks`
- Standardize all TRON references to `tron-payment-service`
- Implement automated naming validation in CI/CD

### 2. TRON Isolation Violations (Priority: CRITICAL)

**Current Issues**:
- TRON code in `blockchain/core/blockchain_engine.py`
- Payment logic mixed with consensus logic
- No clear service boundary enforcement

**Resolution**:
- Move all TRON code to dedicated `payment-systems/` directory
- Remove TRON dependencies from blockchain core
- Implement Beta sidecar ACLs for wallet plane isolation

### 3. Missing Rate Limiting (Priority: HIGH)

**Current Issues**:
- No rate limiting on any APIs
- Unlimited session creation
- Unlimited chunk uploads

**Resolution**:
- Implement tiered rate limiting at API gateway
- Add rate limiting middleware to all services
- Monitor and alert on rate limit violations

### 4. Data Transfer Limits Not Enforced (Priority: HIGH)

**Current Issues**:
- No API-level enforcement of data limits
- Chunk size limits not validated on upload
- No streaming for large responses

**Resolution**:
- Add request size validation middleware
- Implement streaming responses for large data
- Add progress tracking for large transfers

## Success Criteria

### Consistency
- [ ] All references use `lucid_blocks` for on-chain system
- [ ] TRON only referenced in payment system documentation
- [ ] Service names consistent across all documents
- [ ] Error codes follow LUCID_ERR_XXXX pattern

### Completeness
- [ ] All 47+ existing endpoints documented
- [ ] All identified missing APIs documented
- [ ] OpenAPI 3.0 specs for all clusters
- [ ] Rate limiting specified for all endpoints

### Compliance
- [ ] All containers specify distroless base images
- [ ] TRON isolation architecture documented
- [ ] Beta sidecar integration documented
- [ ] Tor-only transport enforced

### Implementability
- [ ] Complete code examples provided
- [ ] Docker compose configurations included
- [ ] Testing strategies defined
- [ ] Migration paths documented

## References

- [DISTROLESS Container Specification](../docs/architecture/DISTROLESS-CONTAINER-SPEC.md)
- [TRON Payment Isolation](../docs/architecture/TRON-PAYMENT-ISOLATION.md)
- [Lucid API Elements Summary](../docs/analysis/LUCID_API_ELEMENTS_COMPREHENSIVE_SUMMARY.md)
- [Complete Distroless Implementation](../Build_guide_docs/COMPLETE_DISTROLESS_IMPLEMENTATION_PROGRESS.md)

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

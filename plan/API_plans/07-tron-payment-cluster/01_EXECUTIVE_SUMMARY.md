# TRON Payment System API - Executive Summary

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-EXEC-001 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

The TRON Payment System API provides a secure, isolated payment infrastructure for USDT-TRC20 payouts within the Lucid RDP ecosystem. This system is architecturally separated from the core blockchain (On-System Data Chain) and operates exclusively for payment operations, adhering to SPEC-1B-v2 requirements.

### Key Objectives

1. **Payment Isolation**: TRON operations completely isolated from core blockchain
2. **Dual Router Support**: Non-KYC (PayoutRouterV0) and KYC-gated (PayoutRouterKYC) payment paths
3. **Distroless Deployment**: Minimal attack surface using `gcr.io/distroless/python3-debian12`
4. **Tor-Only Access**: All API traffic routed through Tor network (.onion services)
5. **API Gateway Integration**: Centralized entry point with authentication and rate limiting

---

## System Architecture

### Three-Tier Separation

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
            │ Proxy Routes
            │
┌───────────▼──────────────────────────────────────────────────┐
│              Chain Plane (Cluster B)                          │
│                                                               │
│  ┌───────────────────────────────────────────────────┐      │
│  │       Blockchain Core (Port 8084)                 │      │
│  │       - Session anchoring                         │      │
│  │       - Merkle proof generation                   │      │
│  │       - PoOT consensus                            │      │
│  └───────────────────────────────────────────────────┘      │
└───────────────────────────────────────────────────────────────┘
            
            ║ STRICT ISOLATION ║
            
┌───────────────────────────────────────────────────────────────┐
│             Wallet Plane (Payment Tier)                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │    TRON Payment System (Isolated)                   │    │
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

### Service Isolation Principles

1. **Blockchain Tier** (On-System Data Chain)
   - Session recording and anchoring
   - Merkle tree construction
   - PoOT consensus mechanism
   - **Does NOT handle payments**

2. **Payment Tier** (TRON - ISOLATED)
   - USDT-TRC20 payouts exclusively
   - No access to core blockchain operations
   - Operates via API Gateway proxy only
   - Distroless container deployment

3. **Ops Plane** (API Gateway)
   - Single entry point for all APIs
   - Authentication & authorization
   - Rate limiting & circuit breakers
   - Proxies requests to appropriate tier

---

## API Ecosystem

### Primary Endpoints

| Endpoint Pattern | Purpose | Authentication | Rate Limit |
|-----------------|---------|----------------|------------|
| `POST /api/payment/payouts` | Create new payout | JWT Required | 10/min |
| `GET /api/payment/payouts/{id}` | Get payout status | JWT Required | 60/min |
| `GET /api/payment/payouts` | List payouts | JWT Required | 30/min |
| `POST /api/payment/payouts/batch` | Batch payout creation | JWT Required | 5/min |
| `GET /api/payment/stats` | Payment statistics | JWT Required | 20/min |
| `GET /api/payment/health` | Health check | No Auth | 120/min |
| `GET /api/payment/metrics` | Prometheus metrics | Internal Only | N/A |

### Router Selection Logic

```python
def select_router(kyc_verified: bool, has_kyc_hash: bool, node_id: Optional[str]):
    if kyc_verified and has_kyc_hash and node_id:
        return PayoutRouterKYC  # KYC-gated, for node workers
    else:
        return PayoutRouterV0    # Non-KYC, for end-users
```

---

## Core Features

### 1. Dual Router Architecture

**PayoutRouterV0** (Non-KYC)
- Designed for end-user session payouts
- Lower transaction limits
- Faster processing (immediate batch type)
- No KYC verification required

**PayoutRouterKYC** (KYC-Gated)
- Designed for verified node workers
- Higher transaction limits
- Compliance signature required
- KYC hash verification

### 2. Batch Processing

| Batch Type | Processing Schedule | Use Case |
|------------|-------------------|----------|
| IMMEDIATE | Process immediately | High-priority payouts |
| HOURLY | Top of each hour | Regular node rewards |
| DAILY | End of day | Bulk distributions |
| WEEKLY | End of week | Governance rewards |

### 3. Circuit Breaker Protection

```
Daily Limit: $10,000 USDT
Hourly Limit: $1,000 USDT
Error Threshold: 50% failure rate
Automatic Reset: Daily at 00:00 UTC
```

### 4. Security Features

- **Tor-Only Network**: All traffic via .onion services
- **JWT Authentication**: Required for all payout endpoints
- **Role-Based Authorization**: Admin, Node Operator, End User
- **API Rate Limiting**: Per-endpoint throttling
- **Audit Logging**: All payment operations logged
- **Circuit Breakers**: Automatic failure protection
- **Retry Logic**: Max 3 retries with exponential backoff

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| API Framework | FastAPI | 0.104+ | High-performance async API |
| TRON Client | TronPy | 0.4+ | TRON blockchain interaction |
| Container Base | gcr.io/distroless/python3-debian12 | latest | Minimal attack surface |
| Database | MongoDB | 7.0+ | Payout tracking persistence |
| Network | Tor | 0.4.7+ | Anonymous network routing |
| Gateway | Nginx/FastAPI | latest | API Gateway proxy |
| Monitoring | Prometheus | 2.45+ | Metrics collection |

### Python Dependencies

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
tronpy>=0.4.0
httpx>=0.25.0
motor>=3.3.0  # Async MongoDB
```

---

## Deployment Model

### Container Strategy

1. **Multi-Stage Build**
   - Builder stage: `python:3.12-slim-bookworm`
   - Final stage: `gcr.io/distroless/python3-debian12:nonroot`

2. **Security Hardening**
   - Non-root user (`nonroot`)
   - Read-only filesystem
   - No shell access
   - Minimal syscalls

3. **Health Checks**
   - Liveness: `/api/payment/health`
   - Readiness: TRON network connectivity
   - Startup: 30-second grace period

### Raspberry Pi Deployment

```yaml
Target: Raspberry Pi 4/5 (4GB+ RAM)
Architecture: linux/arm64
Network: Tor-only via .onion service
Storage: 32GB+ SSD (for logs and payout records)
Orchestration: Docker Compose profiles
```

---

## Integration Points

### API Gateway Integration

```python
# API Gateway proxies payment requests
@app.post("/api/payment/{path:path}")
async def proxy_payment(path: str, request: Request):
    # Validate JWT
    # Check rate limits
    # Proxy to TRON Payment Service
    # Return response
```

### Blockchain Core Coordination

The payment system operates independently but coordinates with Blockchain Core for:
- Session completion events (triggers payouts)
- Work credit calculation (determines payout amounts)
- Node reputation scores (affects KYC eligibility)

**Important**: Blockchain Core NEVER directly calls TRON. All payment operations flow through the isolated Payment Tier.

---

## Governance & Compliance

### Monthly Payout Distribution (R-MUST-018)

```
Schedule: Last day of each month
Process:
1. Calculate work credits per session
2. Aggregate payouts by node/user
3. Apply daily/hourly limits
4. Route via appropriate router (V0 or KYC)
5. Process in batches
6. Monitor confirmations
7. Generate audit reports
```

### KYC Requirements

For PayoutRouterKYC access:
1. Node operator identity verification
2. Compliance signature from authority
3. Valid KYC hash (SHA-256)
4. Active node registration

---

## Performance Targets

| Metric | Target | Current Status |
|--------|--------|----------------|
| API Response Time (p50) | < 100ms | TBD |
| API Response Time (p99) | < 500ms | TBD |
| Payout Processing Time | < 60s | TBD |
| TRON Confirmation Time | ~3 minutes (19 blocks) | Network Dependent |
| Maximum Concurrent Payouts | 10 | Configurable |
| Daily Throughput | $10,000 USDT | Circuit Breaker Limit |
| Uptime SLA | 99.9% | Target |

---

## Risk Management

### Identified Risks

1. **TRON Network Congestion**
   - Mitigation: Energy staking, batch processing
   
2. **Private Key Compromise**
   - Mitigation: Hardware security modules, key rotation

3. **Circuit Breaker Failures**
   - Mitigation: Redundant limit checks, manual override

4. **API Rate Limit Bypass**
   - Mitigation: Multiple rate limiting layers, IP blocking

5. **Payment System Downtime**
   - Mitigation: Queue-based processing, retry logic, alerting

---

## Success Criteria

### Phase 1: MVP (Current)
- [ ] All 10 identified API problems documented
- [ ] Python-based TRON service implemented
- [ ] API Gateway integration complete
- [ ] Distroless containers deployed
- [ ] Basic health checks operational

### Phase 2: Production Ready
- [ ] Full OpenAPI 3.0 specification
- [ ] Comprehensive test coverage (>80%)
- [ ] Security audit passed
- [ ] Load testing validated
- [ ] Monitoring & alerting configured

### Phase 3: Scale & Optimize
- [ ] Auto-scaling implemented
- [ ] Performance targets achieved
- [ ] 99.9% uptime SLA met
- [ ] Advanced analytics dashboard
- [ ] Multi-region support (if needed)

---

## Quick Start Guide

### For Developers

1. Review [04_API_SPECIFICATIONS.md](04_API_SPECIFICATIONS.md) for endpoint details
2. Check [12_CODE_EXAMPLES.md](12_CODE_EXAMPLES.md) for implementation patterns
3. Use [05_OPENAPI_SPEC.yaml](05_OPENAPI_SPEC.yaml) for API contract

### For DevOps

1. Review [06_DISTROLESS_CONTAINERS.md](06_DISTROLESS_CONTAINERS.md) for build instructions
2. Check [09_DEPLOYMENT_PROCEDURES.md](09_DEPLOYMENT_PROCEDURES.md) for deployment steps
3. Configure using [13_CONFIGURATION_TEMPLATES.md](13_CONFIGURATION_TEMPLATES.md)

### For Security Team

1. Review [07_SECURITY_COMPLIANCE.md](07_SECURITY_COMPLIANCE.md) for security requirements
2. Validate using [14_IMPLEMENTATION_CHECKLIST.md](14_IMPLEMENTATION_CHECKLIST.md)
3. Test using [08_TESTING_STRATEGY.md](08_TESTING_STRATEGY.md)

---

## Next Steps

1. **Immediate Actions**
   - Complete all 14 documentation files
   - Validate against SPEC-1B-v2
   - Begin implementation following checklist

2. **Short-Term (1-2 weeks)**
   - Deploy MVP to test environment
   - Execute integration tests
   - Security review

3. **Medium-Term (1-2 months)**
   - Production deployment to Raspberry Pi
   - Performance optimization
   - Monitoring & alerting setup

4. **Long-Term (3-6 months)**
   - Scale testing
   - Advanced features (multi-sig, etc.)
   - Cross-chain support evaluation

---

## Glossary

| Term | Definition |
|------|------------|
| **Distroless** | Minimal container images without shell, package managers, or unnecessary binaries |
| **PayoutRouterV0** | Non-KYC payout router for end-user session rewards |
| **PayoutRouterKYC** | KYC-gated payout router for verified node operators |
| **USDT-TRC20** | Tether stablecoin on TRON network (TRC20 standard) |
| **PoOT** | Proof of Objective Trust - consensus mechanism for work credit calculation |
| **.onion** | Tor hidden service address format |
| **Circuit Breaker** | Automatic safety mechanism to prevent cascading failures |
| **Merkle Root** | Cryptographic hash of session chunk tree |

---

## References

- [SPEC-1B-v2-DISTROLESS.md](../../../docs/build-docs/Build_guide_docs/SPEC-1B-v2-DISTROLESS.md) - Core architecture specification
- [TR.plan.md](../tr.plan.md) - Original TRON payment system plan
- [TRON Documentation](https://developers.tron.network/) - Official TRON developer docs
- [TronPy Repository](https://github.com/andelf/tronpy) - Python TRON library
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - API framework reference

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12


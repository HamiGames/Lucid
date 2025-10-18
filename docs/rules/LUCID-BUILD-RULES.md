# LUCID BUILD RULES

## Overview

This document establishes mandatory build rules for the Lucid RDP project, ensuring consistent architecture, security, and operational practices across all components.

## Rule 1: Distroless Design Mandate

**ALL container builds MUST use distroless base images.**

### Rationale
- Minimize attack surface
- Reduce CVE exposure
- Eliminate shell-based attacks
- Optimize image size
- Improve security posture

### Compliance Requirements
- All Dockerfiles MUST use `gcr.io/distroless/*` as final stage
- Builder stages may use standard images (node:20-slim, python:3.12-slim)
- NO runtime shells (bash, sh) in production containers
- CI MUST verify distroless compliance before deployment

### Allowed Base Images
```dockerfile
# Node.js Services
FROM gcr.io/distroless/nodejs20-debian12

# Python Services  
FROM gcr.io/distroless/python3-debian12

# Static Binaries
FROM gcr.io/distroless/static-debian12
```

### Example Compliance Pattern
```dockerfile
# ✅ COMPLIANT: Multi-stage with distroless final stage
FROM node:20-slim AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production

FROM gcr.io/distroless/nodejs20-debian12
COPY --from=builder /build/node_modules /app/node_modules
COPY --chown=nonroot:nonroot src/ /app/
USER nonroot
WORKDIR /app
CMD ["index.js"]

# ❌ NON-COMPLIANT: Standard base image in final stage
FROM node:20-slim
# ... rest of Dockerfile
```

## Rule 2: TRON Payment System Isolation

**TRON is a PAYMENT SYSTEM ONLY - NOT a blockchain component.**

### Scope Definition

**✅ ALLOWED Operations:**
- USDT-TRC20 transfers via PayoutRouterV0/PRKYC
- Energy/bandwidth management (TRX staking)
- Monthly payout distribution
- Wallet integration for payouts
- Payout batch processing
- TRON transaction fee management

**❌ PROHIBITED Operations:**
- Session anchoring (use On-System Chain)
- Consensus participation (use PoOT on On-System Chain)
- Chunk storage (use On-System Chain)
- Governance operations (use On-System Chain)
- Any blockchain operations beyond payments
- DHT/CRDT participation
- Work credits calculation
- Leader selection participation

### Compliance Requirements
- TRON service MUST run in isolated container (`tron-payment-service`)
- TRON service MUST ONLY access wallet plane via Beta sidecar
- Code reviews MUST verify TRON isolation
- MongoDB `payouts` collection is ONLY TRON-related data store
- NO direct blockchain operations from TRON service

### Service Boundaries
```yaml
# ✅ COMPLIANT: TRON service configuration
services:
  tron-payment-service:
    image: gcr.io/distroless/nodejs20-debian12
    networks:
      - wallet_plane
    labels:
      - com.lucid.plane=wallet
      - com.lucid.service=tron-payment
    environment:
      - TRON_ONLY_PAYMENTS=true
    volumes:
      - tron_payouts_data:/data/payouts

# ❌ NON-COMPLIANT: TRON service with blockchain operations
services:
  tron-node-client:
    image: node:20-slim  # Non-distroless
    networks:
      - blockchain_plane  # Wrong plane
    labels:
      - com.lucid.service=blockchain  # Wrong service type
```

### Data Isolation
```javascript
// ✅ COMPLIANT: TRON service only accesses payout data
const payoutCollection = db.collection('payouts');

// ❌ NON-COMPLIANT: TRON service accessing blockchain data
const sessionsCollection = db.collection('sessions');
const chunksCollection = db.collection('chunks');
```

## Rule 3: Container Plane Isolation

**All services MUST operate within defined network planes with strict ACLs.**

### Plane Definitions
- **Ops Plane**: General service operations, admin UI, monitoring
- **Chain Plane**: On-System Chain operations, consensus, governance
- **Wallet Plane**: Payment operations (TRON), wallet management

### Compliance Requirements
- Services MUST be labeled with appropriate plane (`com.lucid.plane`)
- Beta sidecar MUST enforce ACLs between planes
- NO direct inter-plane communication without explicit allow-lists
- Wallet plane MUST deny-by-default except for approved pairs

### Example Configuration
```yaml
services:
  blockchain-core:
    labels:
      - com.lucid.plane=chain
      - com.lucid.service=blockchain-core
    networks:
      - chain_plane
  
  tron-payment-service:
    labels:
      - com.lucid.plane=wallet
      - com.lucid.service=tron-payment
    networks:
      - wallet_plane
  
  admin-ui:
    labels:
      - com.lucid.plane=ops
      - com.lucid.service=admin-ui
    networks:
      - ops_plane
```

## Rule 4: Build Stage Compliance

**All builds MUST follow Spec-4 clustered build stages (0-6).**

### Stage Definitions
- **Stage 0**: Base + Beta Sidecar
- **Stage 1**: Blockchain Group (On-System Chain)
- **Stage 2**: Sessions Group
- **Stage 3**: Node Systems Group
- **Stage 4**: Admin/Wallet Group (includes isolated TRON service)
- **Stage 5**: Observability Group
- **Stage 6**: Relay/Directory (optional)

### Compliance Requirements
- Health checks required for all services
- Rollout gates enforced between stages
- Staged deployment with health verification
- Rollback capability for each stage

### Example Stage Configuration
```yaml
# docker-compose.yml with profiles
services:
  blockchain-core:
    profiles: [blockchain, stage1]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  tron-payment-service:
    profiles: [admin, stage4]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Rule 5: Security Hardening Standards

**All containers MUST implement security hardening measures.**

### Mandatory Security Features
- **Read-only Root**: Mount root filesystem read-only where possible
- **Non-root User**: Use UID 65532 (nonroot user)
- **Minimal Syscalls**: Implement seccomp profiles
- **No Shells**: No bash, sh, or other shells in runtime
- **Resource Limits**: CPU and memory limits defined

### Example Security Configuration
```yaml
services:
  blockchain-core:
    security_opt:
      - seccomp:./seccomp-profile.json
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    user: "65532:65532"
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

## Rule 6: Image Supply Chain Security

**All images MUST meet supply chain security requirements.**

### Mandatory Requirements
- **Signature Verification**: All images must be signed
- **SBOM Generation**: Software Bill of Materials required
- **CVE Scanning**: No critical vulnerabilities allowed
- **Digest Pinning**: Use SHA256 digests, not tags
- **Attestation Verification**: Build attestations required

### Example Supply Chain Configuration
```yaml
# .github/workflows/build.yml
- name: Build and sign image
  run: |
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      --tag ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
      --push \
      --sbom=true \
      --provenance=true \
      .
    
    cosign sign --yes ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

## Enforcement & Compliance

### CI/CD Checks
- **Pre-commit Hooks**: Lint Dockerfiles for distroless compliance
- **Build Verification**: Verify distroless base images in CI
- **Security Scanning**: Trivy/CVE scanning on all images
- **Policy Gates**: Block deployment on rule violations

### Code Review Checklist
- [ ] Dockerfile uses distroless base image
- [ ] TRON service isolated to payment operations only
- [ ] Services labeled with correct plane
- [ ] Security hardening measures implemented
- [ ] Health checks defined
- [ ] Resource limits specified

### Deployment Gates
- **Distroless Compliance**: All images must use distroless bases
- **TRON Isolation**: TRON service must be isolated
- **Security Scan**: No critical CVEs allowed
- **Health Check**: All services must pass health checks
- **Resource Limits**: All services must have resource limits

### Compliance Monitoring
- **Runtime Verification**: Monitor container compliance at runtime
- **Audit Logs**: Log all rule violations
- **Alerting**: Alert on compliance violations
- **Reporting**: Regular compliance reports

## Violation Handling

### Severity Levels
- **Critical**: Distroless violation, TRON isolation breach
- **High**: Security hardening missing, plane isolation violation
- **Medium**: Missing health checks, resource limits not defined
- **Low**: Missing labels, documentation incomplete

### Response Actions
- **Critical/High**: Block deployment, require immediate fix
- **Medium**: Block deployment, fix required before next release
- **Low**: Warning, fix required in next sprint

### Escalation Process
1. **Automated Detection**: CI/CD pipeline detects violation
2. **Immediate Block**: Deployment blocked automatically
3. **Notification**: Team notified of violation
4. **Fix Required**: Developer must fix violation
5. **Re-verification**: CI/CD re-runs after fix
6. **Deployment**: Deployment proceeds after compliance

## Conclusion

These rules ensure consistent, secure, and maintainable architecture across the Lucid RDP platform. All team members must follow these rules without exception, and any violations must be addressed immediately to maintain system integrity and security.

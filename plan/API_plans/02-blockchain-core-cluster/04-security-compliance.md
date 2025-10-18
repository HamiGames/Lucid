# Blockchain Core Cluster - Security & Compliance

## Overview

Security architecture for the Lucid blockchain core cluster (lucid_blocks), focusing on TRON isolation, authentication, authorization, rate limiting, and audit logging. This document defines security controls for the on-chain blockchain system separate from payment operations.

## Security Architecture

### Service Isolation Principles

**TRON Isolation Enforcement:**
- Blockchain core services MUST NOT contain TRON payment logic
- All TRON operations isolated to payment-systems/tron-payment-service/
- Beta sidecar enforces wallet plane isolation via ACLs
- Clear service boundary enforcement between consensus and payment

**Network Security:**
- All communication via Tor .onion endpoints only
- No direct IP-based communication between services
- Beta sidecar proxy enforces network isolation
- TLS termination at Beta sidecar level

### Authentication & Authorization

**Service Authentication:**
```yaml
blockchain_core_auth:
  method: "service_token"
  token_type: "JWT"
  issuer: "lucid-auth-service"
  audience: "lucid-blocks"
  expiration: "1h"
  rotation_interval: "30m"
```

**API Authentication:**
```yaml
api_auth:
  public_endpoints:
    - "/api/v1/chain/info"
    - "/api/v1/chain/height"
    - "/api/v1/chain/status"
  
  authenticated_endpoints:
    - "/api/v1/wallet/*"
    - "/api/v1/contract/*"
    - "/api/v1/transaction/*"
  
  admin_endpoints:
    - "/api/v1/admin/*"
    - "/api/v1/system/*"
```

**Role-Based Access Control:**
```yaml
rbac_roles:
  public_user:
    permissions:
      - "read:chain_info"
      - "read:block_height"
      - "read:chain_status"
  
  authenticated_user:
    permissions:
      - "read:chain_info"
      - "read:block_height"
      - "read:chain_status"
      - "read:own_wallet"
      - "create:transaction"
      - "deploy:contract"
  
  admin_user:
    permissions:
      - "read:*"
      - "write:*"
      - "admin:system"
      - "admin:config"
```

## Rate Limiting Strategy

### Tiered Rate Limiting

**Public Endpoints (100 req/min per IP):**
- `/api/v1/chain/info`
- `/api/v1/chain/height`
- `/api/v1/chain/status`
- `/api/v1/block/*` (read operations)

**Authenticated Endpoints (1000 req/min per token):**
- `/api/v1/wallet/*`
- `/api/v1/contract/deploy`
- `/api/v1/transaction/create`
- `/api/v1/transaction/submit`

**Admin Endpoints (10000 req/min per admin token):**
- `/api/v1/admin/*`
- `/api/v1/system/*`
- `/api/v1/config/*`

### Rate Limiting Implementation

```python
# Rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],
    storage_uri="redis://redis:6379"
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Apply different limits based on endpoint and auth status
    if request.url.path.startswith("/api/v1/admin/"):
        rate_limit = "10000/minute"
    elif request.url.path.startswith("/api/v1/chain/"):
        rate_limit = "100/minute"
    else:
        rate_limit = "1000/minute"
    
    # Apply rate limiting logic
    return await call_next(request)
```

## Input Validation & Sanitization

### Request Validation

**Wallet Operations:**
```yaml
wallet_validation:
  address_format:
    pattern: "^[0-9a-fA-F]{40}$"
    min_length: 40
    max_length: 40
  
  private_key:
    pattern: "^[0-9a-fA-F]{64}$"
    min_length: 64
    max_length: 64
    encrypted: true
  
  amount:
    type: "decimal"
    min_value: "0"
    max_value: "1000000000000000000"
    precision: 18
```

**Contract Deployment:**
```yaml
contract_validation:
  bytecode:
    pattern: "^0x[0-9a-fA-F]+$"
    min_length: 2
    max_length: 100000
  
  abi:
    type: "json"
    schema: "contract_abi_schema.json"
  
  constructor_args:
    type: "array"
    max_items: 50
    item_type: "string"
```

**Transaction Validation:**
```yaml
transaction_validation:
  to_address:
    pattern: "^[0-9a-fA-F]{40}$"
    required: true
  
  from_address:
    pattern: "^[0-9a-fA-F]{40}$"
    required: true
  
  value:
    type: "decimal"
    min_value: "0"
    max_value: "1000000000000000000"
  
  gas_limit:
    type: "integer"
    min_value: 21000
    max_value: 10000000
  
  gas_price:
    type: "decimal"
    min_value: "1000000000"
    max_value: "1000000000000"
```

## Audit Logging

### Audit Log Schema

```yaml
audit_log_entry:
  timestamp: "ISO-8601"
  request_id: "UUID"
  user_id: "string"
  session_id: "string"
  service: "lucid-blocks"
  operation: "string"
  resource: "string"
  action: "string"
  result: "success|failure"
  ip_address: "string"
  user_agent: "string"
  request_body_hash: "SHA-256"
  response_code: "integer"
  error_message: "string"
  duration_ms: "integer"
```

### Logged Operations

**Wallet Operations:**
- Wallet creation
- Private key access
- Balance queries
- Transaction signing

**Contract Operations:**
- Contract deployment
- Contract interaction
- Contract state changes
- Contract destruction

**Transaction Operations:**
- Transaction creation
- Transaction signing
- Transaction submission
- Transaction confirmation

**Admin Operations:**
- System configuration changes
- User management
- Service restarts
- Backup operations

### Log Retention Policy

```yaml
log_retention:
  audit_logs:
    retention_period: "7 years"
    compression: "gzip"
    encryption: "AES-256"
    storage: "immutable"
  
  access_logs:
    retention_period: "1 year"
    compression: "gzip"
    storage: "readonly"
  
  error_logs:
    retention_period: "6 months"
    compression: "gzip"
    alerting: "enabled"
```

## Data Protection

### Encryption Standards

**Data at Rest:**
- Database encryption: AES-256
- File system encryption: LUKS
- Backup encryption: GPG
- Key management: HashiCorp Vault

**Data in Transit:**
- TLS 1.3 for all communications
- Perfect Forward Secrecy
- Certificate pinning
- HSTS headers

**Sensitive Data Handling:**
```yaml
sensitive_data:
  private_keys:
    encryption: "AES-256-GCM"
    key_rotation: "90 days"
    storage: "hardware_security_module"
  
  wallet_seeds:
    encryption: "AES-256-GCM"
    key_rotation: "90 days"
    storage: "hardware_security_module"
  
  user_credentials:
    hashing: "Argon2id"
    salt_length: 32
    iterations: 3
    memory: 65536
```

## Compliance Requirements

### Regulatory Compliance

**Data Privacy:**
- GDPR compliance for EU users
- CCPA compliance for California users
- Data minimization principles
- Right to deletion
- Data portability

**Financial Regulations:**
- AML (Anti-Money Laundering) compliance
- KYC (Know Your Customer) requirements
- Suspicious activity reporting
- Transaction monitoring

**Security Standards:**
- ISO 27001 compliance
- SOC 2 Type II certification
- PCI DSS for payment processing
- OWASP security guidelines

### Monitoring & Alerting

**Security Monitoring:**
```yaml
security_monitoring:
  failed_login_attempts:
    threshold: 5
    window: "15 minutes"
    action: "account_lockout"
  
  suspicious_transactions:
    threshold: "10000 USDT"
    window: "1 hour"
    action: "manual_review"
  
  rate_limit_violations:
    threshold: 100
    window: "1 minute"
    action: "ip_block"
  
  unauthorized_access:
    threshold: 1
    window: "immediate"
    action: "security_alert"
```

**Compliance Monitoring:**
- Data access logging
- User consent tracking
- Data retention compliance
- Audit trail integrity

## Incident Response

### Security Incident Classification

**Severity Levels:**
- **Critical (P1):** Data breach, system compromise
- **High (P2):** Authentication bypass, privilege escalation
- **Medium (P3):** Rate limiting bypass, unauthorized access
- **Low (P4):** Configuration drift, minor vulnerabilities

### Incident Response Procedures

**Detection & Analysis:**
1. Automated monitoring alerts
2. Manual security assessment
3. Threat intelligence correlation
4. Impact assessment

**Containment & Eradication:**
1. Immediate threat isolation
2. System quarantine
3. Vulnerability patching
4. Malware removal

**Recovery & Lessons Learned:**
1. System restoration
2. Security hardening
3. Process improvement
4. Documentation update

## Security Testing

### Automated Security Testing

**Static Application Security Testing (SAST):**
- Code analysis with SonarQube
- Dependency vulnerability scanning
- Secret detection
- License compliance

**Dynamic Application Security Testing (DAST):**
- OWASP ZAP scanning
- Penetration testing
- API security testing
- Infrastructure scanning

**Container Security:**
- Image vulnerability scanning
- Runtime security monitoring
- Network policy enforcement
- Resource isolation

### Manual Security Testing

**Penetration Testing:**
- Quarterly external assessments
- Annual red team exercises
- Bug bounty program
- Security code reviews

## Security Metrics

### Key Security Indicators

**Authentication Metrics:**
- Failed login attempts per hour
- Account lockout frequency
- Multi-factor authentication adoption
- Session timeout compliance

**Authorization Metrics:**
- Privilege escalation attempts
- Unauthorized access attempts
- Role-based access compliance
- Permission audit results

**Data Protection Metrics:**
- Encryption coverage percentage
- Key rotation compliance
- Data loss incidents
- Backup integrity checks

**Compliance Metrics:**
- Audit log completeness
- Data retention compliance
- Privacy request response time
- Regulatory reporting accuracy

## Security Configuration

### Security Headers

```yaml
security_headers:
  Strict-Transport-Security: "max-age=31536000; includeSubDomains"
  Content-Security-Policy: "default-src 'self'"
  X-Frame-Options: "DENY"
  X-Content-Type-Options: "nosniff"
  Referrer-Policy: "strict-origin-when-cross-origin"
  Permissions-Policy: "camera=(), microphone=(), geolocation=()"
```

### Network Security

```yaml
network_security:
  firewall_rules:
    - action: "ALLOW"
      source: "tor_network"
      destination: "blockchain_core"
      port: "8084"
    
    - action: "DENY"
      source: "0.0.0.0/0"
      destination: "blockchain_core"
      port: "8084"
  
  dns_security:
    - dns_over_tls: true
    - dns_over_https: true
    - dns_filtering: true
```

This security and compliance document ensures the blockchain core cluster maintains the highest security standards while enforcing TRON isolation and regulatory compliance requirements.

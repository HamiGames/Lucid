# TRON Payment System API - Security Compliance

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-SEC-007 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document defines the comprehensive security architecture for the TRON Payment System API, implementing multi-layer authentication, authorization, network isolation, and audit logging according to SPEC-1B-v2 requirements.

### Security Principles

- **Defense in Depth**: Multiple security layers
- **Least Privilege**: Minimal required permissions
- **Zero Trust**: Verify everything, trust nothing
- **Audit Everything**: Complete logging and monitoring
- **Isolation**: Strict service boundaries

---

## Multi-Layer Authentication Architecture

### Authentication Flow

```
Client Request
     │
     ▼
┌─────────────┐    JWT Validation    ┌─────────────────┐
│ API Gateway │◄────────────────────▶│  Auth Service   │
└─────┬───────┘                      └─────────────────┘
      │
      │ Extract User Context
      ▼
┌─────────────┐    User Headers      ┌─────────────────┐
│ Payment     │◄─────────────────────│ API Gateway     │
│ Service     │                      │ (Proxy)         │
└─────────────┘                      └─────────────────┘
      │
      │ Internal Validation
      ▼
┌─────────────┐    Service Token     ┌─────────────────┐
│ TRON        │◄────────────────────▶│  TRON Network   │
│ Service     │                      │ (External)      │
└─────────────┘                      └─────────────────┘
```

### JWT Authentication at API Gateway

```python
# API Gateway JWT Validation
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Validate JWT token and extract user information
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True}
        )
        
        # Extract user information
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Validate user permissions
        user = await get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def require_permissions(
    user: User,
    required_permissions: List[str]
) -> bool:
    """
    Check if user has required permissions
    """
    user_permissions = await get_user_permissions(user.id)
    
    for permission in required_permissions:
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}"
            )
    
    return True
```

### Internal Request Validation

```python
# Internal service validation via headers
from fastapi import Header, HTTPException
from typing import Optional

async def validate_internal_request(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
) -> InternalRequest:
    """
    Validate internal service-to-service request
    """
    # Validate internal token
    if not await validate_internal_token(x_internal_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token"
        )
    
    # Validate required headers
    if not all([x_user_id, x_user_role, x_request_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required headers"
        )
    
    return InternalRequest(
        user_id=x_user_id,
        user_role=x_user_role,
        request_id=x_request_id
    )
```

---

## Role-Based Authorization Matrix

### Role Definitions

| Role | Description | Payment Permissions |
|------|-------------|-------------------|
| `admin` | System administrator | All operations, override limits |
| `node_operator` | Node worker operator | KYC payouts, batch operations |
| `end_user` | Regular user | Non-KYC payouts, single operations |
| `service` | Internal service | Service-to-service operations |

### Permission Matrix

```python
# Permission definitions
PERMISSIONS = {
    "payment:create": {
        "end_user": ["PayoutRouterV0", "single"],
        "node_operator": ["PayoutRouterV0", "PayoutRouterKYC", "single", "batch"],
        "admin": ["all"]
    },
    "payment:read": {
        "end_user": ["own_payouts"],
        "node_operator": ["own_payouts", "node_payouts"],
        "admin": ["all_payouts"]
    },
    "payment:stats": {
        "node_operator": ["limited"],
        "admin": ["full"]
    },
    "payment:admin": {
        "admin": ["circuit_breaker", "limits", "monitoring"]
    }
}

class PermissionChecker:
    def __init__(self, user_role: str):
        self.user_role = user_role
    
    def has_permission(self, permission: str, resource: str = None) -> bool:
        """
        Check if user role has specific permission
        """
        role_permissions = PERMISSIONS.get(permission, {}).get(self.user_role, [])
        
        if "all" in role_permissions:
            return True
        
        if resource and resource in role_permissions:
            return True
        
        return False
```

### Authorization Implementation

```python
# Authorization decorator
from functools import wraps
from typing import List, Optional

def require_permissions(
    permissions: List[str],
    resource: Optional[str] = None
):
    """
    Decorator to require specific permissions
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from dependency injection
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions
            checker = PermissionChecker(current_user.role)
            for permission in permissions:
                if not checker.has_permission(permission, resource):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing permission: {permission}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
@router.post("/payouts")
@require_permissions(["payment:create"], "single")
async def create_payout(
    payout_request: PayoutRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create payout with permission checking
    """
    # Implementation here
    pass
```

---

## Tor-Only Network Enforcement

### Network Isolation Configuration

```python
# Tor-only network enforcement
import httpx
from urllib.parse import urlparse

class TorOnlyHTTPClient:
    """
    HTTP client that enforces Tor-only connections
    """
    def __init__(self, tor_proxy_url: str):
        self.tor_proxy_url = tor_proxy_url
        self.client = httpx.AsyncClient(
            proxies={
                "http://": tor_proxy_url,
                "https://": tor_proxy_url
            },
            timeout=30.0
        )
    
    async def get(self, url: str, **kwargs):
        """
        GET request through Tor only
        """
        await self._validate_tor_connection()
        return await self.client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        """
        POST request through Tor only
        """
        await self._validate_tor_connection()
        return await self.client.post(url, **kwargs)
    
    async def _validate_tor_connection(self):
        """
        Validate Tor connection is active
        """
        try:
            response = await self.client.get("http://httpbin.org/ip")
            ip_info = response.json()
            
            # Check if IP is different from direct connection
            if not self._is_tor_ip(ip_info.get("origin")):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Tor connection not available"
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Tor validation failed: {str(e)}"
            )
    
    def _is_tor_ip(self, ip: str) -> bool:
        """
        Check if IP appears to be from Tor network
        """
        # Simplified check - in production, use proper Tor IP detection
        return ip != "127.0.0.1" and ip != "localhost"
```

### Network Configuration

```yaml
# Docker Compose network isolation
services:
  tron-payment-service:
    networks:
      - wallet_plane  # Internal only
      - tor_network   # Tor access only
    
    environment:
      - TOR_ONLY=true
      - TOR_PROXY=socks5://tor-proxy:9050
      - ALLOW_DIRECT_CONNECTIONS=false

networks:
  wallet_plane:
    driver: bridge
    internal: true  # No external access
  
  tor_network:
    driver: bridge
    internal: false  # Routes to Tor network
```

---

## Audit Logging Specifications

### Audit Log Format

```python
# Audit log entry structure
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class AuditAction(str, Enum):
    PAYOUT_CREATE = "payout_create"
    PAYOUT_UPDATE = "payout_update"
    PAYOUT_READ = "payout_read"
    BATCH_CREATE = "batch_create"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_DENIED = "authorization_denied"

class AuditLogEntry(BaseModel):
    timestamp: datetime
    action: AuditAction
    user_id: Optional[str]
    user_role: Optional[str]
    request_id: str
    resource_id: Optional[str]
    success: bool
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]

class AuditLogger:
    def __init__(self, mongo_client):
        self.collection = mongo_client.audit_logs
    
    async def log_action(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        request_id: str = None,
        resource_id: Optional[str] = None,
        success: bool = True,
        details: Dict[str, Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Log audit event to MongoDB
        """
        log_entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            action=action,
            user_id=user_id,
            user_role=user_role,
            request_id=request_id,
            resource_id=resource_id,
            success=success,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        await self.collection.insert_one(log_entry.dict())
```

### Audit Log Implementation

```python
# Audit logging middleware
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, audit_logger: AuditLogger):
        super().__init__(app)
        self.audit_logger = audit_logger
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract user information
        user_id = request.headers.get("X-User-ID")
        user_role = request.headers.get("X-User-Role")
        
        # Process request
        response = await call_next(request)
        
        # Log request
        await self.audit_logger.log_action(
            action=AuditAction.PAYOUT_READ if request.method == "GET" else AuditAction.PAYOUT_CREATE,
            user_id=user_id,
            user_role=user_role,
            request_id=request_id,
            success=response.status_code < 400,
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent")
        )
        
        return response
```

---

## Circuit Breaker Security Limits

### Circuit Breaker Implementation

```python
# Circuit breaker with security limits
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Optional

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit open, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered

class SecurityLimits:
    def __init__(self):
        self.daily_limit_usdt = 10000.0
        self.hourly_limit_usdt = 1000.0
        self.failure_threshold = 5
        self.recovery_timeout = 300  # 5 minutes
        self.half_open_max_calls = 3

class CircuitBreaker:
    def __init__(self, limits: SecurityLimits):
        self.limits = limits
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.daily_usage = 0.0
        self.hourly_usage = 0.0
        self.last_reset_daily = datetime.utcnow()
        self.last_reset_hourly = datetime.utcnow()
    
    async def check_limits(self, amount_usdt: float) -> bool:
        """
        Check if request is within security limits
        """
        # Reset counters if needed
        await self._reset_counters_if_needed()
        
        # Check daily limit
        if self.daily_usage + amount_usdt > self.limits.daily_limit_usdt:
            await self._open_circuit("Daily limit exceeded")
            return False
        
        # Check hourly limit
        if self.hourly_usage + amount_usdt > self.limits.hourly_limit_usdt:
            await self._open_circuit("Hourly limit exceeded")
            return False
        
        return True
    
    async def record_success(self, amount_usdt: float):
        """
        Record successful operation
        """
        self.failure_count = 0
        self.daily_usage += amount_usdt
        self.hourly_usage += amount_usdt
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.limits.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.half_open_calls = 0
    
    async def record_failure(self):
        """
        Record failed operation
        """
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.limits.failure_threshold:
            await self._open_circuit("Failure threshold exceeded")
    
    async def _open_circuit(self, reason: str):
        """
        Open circuit breaker
        """
        self.state = CircuitBreakerState.OPEN
        self.last_failure_time = datetime.utcnow()
        
        # Log security event
        await self.audit_logger.log_action(
            action=AuditAction.CIRCUIT_BREAKER_OPEN,
            success=False,
            details={"reason": reason}
        )
    
    async def _reset_counters_if_needed(self):
        """
        Reset daily/hourly counters if needed
        """
        now = datetime.utcnow()
        
        # Reset daily counter
        if now.date() > self.last_reset_daily.date():
            self.daily_usage = 0.0
            self.last_reset_daily = now
        
        # Reset hourly counter
        if now.hour > self.last_reset_hourly.hour:
            self.hourly_usage = 0.0
            self.last_reset_hourly = now
```

---

## Secrets Management with SOPS

### SOPS Configuration

```yaml
# .sops.yaml - SOPS configuration
creation_rules:
  - path_regex: \.prod\.yaml$
    kms: 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'
    age: 'age1qyqt8thj5rnmc3as6l2x9q8w7z2c4v5b6n7m8k9l0p1q2r3s4t5u6v7w8x9y0z'
  
  - path_regex: \.staging\.yaml$
    age: 'age1qyqt8thj5rnmc3as6l2x9q8w7z2c4v5b6n7m8k9l0p1q2r3s4t5u6v7w8x9y0z'
  
  - path_regex: \.dev\.yaml$
    age: 'age1qyqt8thj5rnmc3as6l2x9q8w7z2c4v5b6n7m8k9l0p1q2r3s4t5u6v7w8x9y0z'
```

### Secrets Structure

```yaml
# configs/secrets/production.enc.yaml (SOPS encrypted)
tron_private_key: |
  -----BEGIN PRIVATE KEY-----
  MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKB
  # ... encrypted content ...
  -----END PRIVATE KEY-----

internal_auth_secret: "encrypted_secret_here"
mongo_password: "encrypted_password_here"
api_keys:
  tron_grid_api_key: "encrypted_api_key_here"
  monitoring_api_key: "encrypted_monitoring_key_here"

encryption_keys:
  jwt_secret: "encrypted_jwt_secret_here"
  data_encryption_key: "encrypted_data_key_here"
```

### Secrets Decryption

```python
# Secrets decryption utility
import sops
from pathlib import Path

class SecretsManager:
    def __init__(self, secrets_dir: str):
        self.secrets_dir = Path(secrets_dir)
    
    def load_secrets(self, environment: str) -> Dict[str, Any]:
        """
        Load and decrypt secrets for environment
        """
        secrets_file = self.secrets_dir / f"{environment}.enc.yaml"
        
        if not secrets_file.exists():
            raise FileNotFoundError(f"Secrets file not found: {secrets_file}")
        
        # Decrypt with SOPS
        decrypted = sops.load(str(secrets_file))
        return decrypted
    
    def get_secret(self, key: str, environment: str = "production") -> str:
        """
        Get specific secret value
        """
        secrets = self.load_secrets(environment)
        
        # Support nested keys with dot notation
        keys = key.split('.')
        value = secrets
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                raise KeyError(f"Secret not found: {key}")
        
        return value
```

---

## API Rate Limiting Implementation

### Rate Limiting Configuration

```python
# Rate limiting implementation
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.limits = {
            "POST /payouts": {"limit": 10, "window": 60},  # 10 per minute
            "GET /payouts": {"limit": 30, "window": 60},   # 30 per minute
            "POST /payouts/batch": {"limit": 5, "window": 60},  # 5 per minute
            "GET /stats": {"limit": 20, "window": 60},     # 20 per minute
            "GET /health": {"limit": 120, "window": 60},   # 120 per minute
        }
        self.requests = defaultdict(list)
    
    async def check_rate_limit(
        self,
        endpoint: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Check if request is within rate limits
        """
        # Get limit configuration
        limit_config = self.limits.get(endpoint)
        if not limit_config:
            return True  # No limit configured
        
        # Use user_id if available, otherwise use IP
        key = user_id or ip_address
        if not key:
            return False
        
        # Clean old requests
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=limit_config["window"])
        
        user_requests = self.requests[key]
        user_requests = [req_time for req_time in user_requests if req_time > window_start]
        
        # Check if limit exceeded
        if len(user_requests) >= limit_config["limit"]:
            return False
        
        # Record request
        user_requests.append(now)
        self.requests[key] = user_requests
        
        return True
```

---

## CORS Policy Configuration

### CORS Middleware Configuration

```python
# CORS configuration for API Gateway
from fastapi.middleware.cors import CORSMiddleware

# CORS configuration
ALLOWED_ORIGINS = [
    "https://lucid-rdp.onion",
    "https://gateway.onion",
    "https://admin.onion",
]

ALLOWED_METHODS = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "OPTIONS"
]

ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-User-ID",
    "X-User-Role",
    "X-Request-ID",
    "X-Internal-Token"
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=3600,  # Cache preflight for 1 hour
)
```

---

## Security Monitoring and Alerting

### Security Event Detection

```python
# Security monitoring
class SecurityMonitor:
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.suspicious_patterns = {
            "multiple_failed_auth": 5,  # 5 failed auth attempts
            "rate_limit_exceeded": 10,  # 10 rate limit violations
            "unusual_amount": 10000,    # Unusual payout amount
            "circuit_breaker_open": 1   # Circuit breaker activation
        }
    
    async def monitor_security_events(self):
        """
        Monitor for security events and trigger alerts
        """
        # Check for suspicious patterns
        await self._check_failed_authentication()
        await self._check_rate_limit_violations()
        await self._check_unusual_activities()
        await self._check_circuit_breaker_events()
    
    async def _check_failed_authentication(self):
        """
        Check for multiple failed authentication attempts
        """
        # Implementation for failed auth monitoring
        pass
    
    async def _check_rate_limit_violations(self):
        """
        Check for excessive rate limit violations
        """
        # Implementation for rate limit monitoring
        pass
    
    async def _check_unusual_activities(self):
        """
        Check for unusual payment patterns
        """
        # Implementation for unusual activity detection
        pass
    
    async def _check_circuit_breaker_events(self):
        """
        Check for circuit breaker activations
        """
        # Implementation for circuit breaker monitoring
        pass
```

---

## References

- [06b_DISTROLESS_DEPLOYMENT.md](06b_DISTROLESS_DEPLOYMENT.md) - Deployment security
- [08_TESTING_STRATEGY.md](08_TESTING_STRATEGY.md) - Security testing
- [SPEC-1B-v2-DISTROLESS.md](../../../docs/build-docs/Build_guide_docs/SPEC-1B-v2-DISTROLESS.md) - Architecture requirements
- [JWT Best Practices](https://tools.ietf.org/html/rfc7519) - JWT security guidelines
- [OWASP API Security](https://owasp.org/www-project-api-security/) - API security standards

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12

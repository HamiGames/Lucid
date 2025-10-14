# RDP Services Cluster - Security & Compliance

## Overview
This document outlines security measures, authentication mechanisms, authorization policies, and compliance requirements for the RDP Services Cluster.

## Authentication

### JWT Authentication

All API requests must include a valid JWT token in the Authorization header.

#### Token Structure

```json
{
  "user_id": "uuid-v4",
  "username": "string",
  "email": "string",
  "roles": ["user", "admin"],
  "permissions": ["rdp:read", "rdp:write", "rdp:admin"],
  "iat": 1234567890,
  "exp": 1234571490
}
```

#### Authentication Implementation

**File**: `shared/auth/authentication.py`

```python
from fastapi import Header, HTTPException, status
from typing import Dict, Optional
import jwt
from datetime import datetime

class JWTAuthenticator:
    """JWT token authentication"""
    
    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "LUCID_ERR_0101",
                        "message": "Token has expired"
                    }
                )
            
            return payload
            
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "LUCID_ERR_0102",
                    "message": "Invalid authentication token"
                }
            )
    
    async def authenticate_request(
        self, 
        authorization: str = Header(...)
    ) -> Dict:
        """Authenticate API request"""
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "LUCID_ERR_0103",
                    "message": "Invalid authorization header format"
                }
            )
        
        token = authorization.replace("Bearer ", "")
        return self.verify_token(token)
```

### Authentication Integration

**Service Integration Example**:

```python
from fastapi import Depends
from shared.auth.authentication import JWTAuthenticator
from .config import settings

authenticator = JWTAuthenticator(settings.JWT_SECRET)

async def get_current_user(
    user: Dict = Depends(authenticator.authenticate_request)
) -> Dict:
    """Get current authenticated user"""
    return user
```

## Authorization

### Role-Based Access Control (RBAC)

The RDP Services Cluster implements hierarchical RBAC with three primary roles:

#### Role Hierarchy

```
admin (full access)
  └── operator (manage servers and sessions)
      └── user (basic access)
```

#### Role Permissions

| Role | Permissions |
|------|-------------|
| **admin** | All operations, configuration management, user management |
| **operator** | Create/manage RDP servers, manage sessions, view resources |
| **user** | Create personal RDP servers, manage own sessions, view own resources |

### Permission Matrix

| Endpoint | User | Operator | Admin |
|----------|------|----------|-------|
| GET /rdp/servers | Own only | All | All |
| POST /rdp/servers | ✓ | ✓ | ✓ |
| PUT /rdp/servers/{id} | Own only | All | All |
| DELETE /rdp/servers/{id} | Own only | All | All |
| POST /rdp/servers/{id}/start | Own only | All | All |
| POST /rdp/servers/{id}/stop | Own only | All | All |
| GET /xrdp/config | ✗ | ✓ | ✓ |
| PUT /xrdp/config | ✗ | ✗ | ✓ |
| POST /xrdp/service/start | ✗ | ✗ | ✓ |
| POST /xrdp/service/stop | ✗ | ✗ | ✓ |
| GET /sessions | Own only | All | All |
| POST /sessions | ✓ | ✓ | ✓ |
| DELETE /sessions/{id} | Own only | All | All |
| GET /resources/usage | Own only | All | All |
| PUT /resources/limits | ✗ | ✗ | ✓ |

### Authorization Implementation

**File**: `shared/auth/authorization.py`

```python
from fastapi import HTTPException, status
from typing import List, Dict
from enum import Enum

class Role(str, Enum):
    USER = "user"
    OPERATOR = "operator"
    ADMIN = "admin"

class Permission(str, Enum):
    RDP_READ = "rdp:read"
    RDP_WRITE = "rdp:write"
    RDP_DELETE = "rdp:delete"
    RDP_ADMIN = "rdp:admin"
    XRDP_READ = "xrdp:read"
    XRDP_WRITE = "xrdp:write"
    XRDP_ADMIN = "xrdp:admin"
    SESSION_READ = "session:read"
    SESSION_WRITE = "session:write"
    SESSION_DELETE = "session:delete"
    RESOURCE_READ = "resource:read"
    RESOURCE_ADMIN = "resource:admin"

ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.RDP_READ, Permission.RDP_WRITE, Permission.RDP_DELETE, Permission.RDP_ADMIN,
        Permission.XRDP_READ, Permission.XRDP_WRITE, Permission.XRDP_ADMIN,
        Permission.SESSION_READ, Permission.SESSION_WRITE, Permission.SESSION_DELETE,
        Permission.RESOURCE_READ, Permission.RESOURCE_ADMIN,
    ],
    Role.OPERATOR: [
        Permission.RDP_READ, Permission.RDP_WRITE, Permission.RDP_DELETE,
        Permission.XRDP_READ,
        Permission.SESSION_READ, Permission.SESSION_WRITE, Permission.SESSION_DELETE,
        Permission.RESOURCE_READ,
    ],
    Role.USER: [
        Permission.RDP_READ, Permission.RDP_WRITE,
        Permission.SESSION_READ, Permission.SESSION_WRITE,
        Permission.RESOURCE_READ,
    ],
}

class Authorizer:
    """Authorization handler"""
    
    @staticmethod
    def get_user_permissions(user: Dict) -> List[Permission]:
        """Get all permissions for a user based on their roles"""
        permissions = set()
        
        for role_name in user.get("roles", []):
            try:
                role = Role(role_name)
                role_perms = ROLE_PERMISSIONS.get(role, [])
                permissions.update(role_perms)
            except ValueError:
                continue
        
        # Add explicit permissions
        for perm in user.get("permissions", []):
            try:
                permissions.add(Permission(perm))
            except ValueError:
                continue
        
        return list(permissions)
    
    @staticmethod
    def has_permission(user: Dict, required_permission: Permission) -> bool:
        """Check if user has a specific permission"""
        permissions = Authorizer.get_user_permissions(user)
        return required_permission in permissions
    
    @staticmethod
    def has_role(user: Dict, required_role: Role) -> bool:
        """Check if user has a specific role"""
        return required_role.value in user.get("roles", [])
    
    @staticmethod
    def require_permission(required_permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                current_user = kwargs.get("current_user")
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "code": "LUCID_ERR_0104",
                            "message": "Authentication required"
                        }
                    )
                
                if not Authorizer.has_permission(current_user, required_permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": "LUCID_ERR_0105",
                            "message": "Insufficient permissions"
                        }
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_role(required_role: Role):
        """Decorator to require specific role"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                current_user = kwargs.get("current_user")
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "code": "LUCID_ERR_0104",
                            "message": "Authentication required"
                        }
                    )
                
                if not Authorizer.has_role(current_user, required_role):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": "LUCID_ERR_0106",
                            "message": f"Role '{required_role.value}' required"
                        }
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
```

### Resource Ownership Validation

```python
async def verify_resource_ownership(
    resource: Dict,
    current_user: Dict
) -> bool:
    """Verify user owns the resource or has admin role"""
    
    # Admins can access all resources
    if Authorizer.has_role(current_user, Role.ADMIN):
        return True
    
    # Operators can access all resources
    if Authorizer.has_role(current_user, Role.OPERATOR):
        return True
    
    # Users can only access their own resources
    return resource.get("user_id") == current_user.get("user_id")
```

## Rate Limiting

### Rate Limit Configuration

Based on API specification (lines 1844-1873):

```python
RATE_LIMITS = {
    "rdp_server_operations": {
        "requests_per_minute": 100,
        "burst_size": 200,
        "endpoints": ["/api/v1/rdp/servers/*"],
    },
    "xrdp_operations": {
        "requests_per_minute": 50,
        "burst_size": 100,
        "endpoints": ["/api/v1/xrdp/*"],
    },
    "session_operations": {
        "requests_per_minute": 200,
        "burst_size": 400,
        "endpoints": ["/api/v1/sessions/*"],
    },
    "resource_monitoring": {
        "requests_per_minute": 300,
        "burst_size": 600,
        "endpoints": ["/api/v1/resources/*"],
    },
}
```

### Rate Limiter Implementation

**File**: `shared/middleware/rate_limiter.py`

```python
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from redis import asyncio as aioredis
from typing import Dict
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_url: str, rate_limits: Dict):
        super().__init__(app)
        self.redis = aioredis.from_url(redis_url)
        self.rate_limits = rate_limits
    
    def get_rate_limit_for_path(self, path: str) -> Dict:
        """Get rate limit configuration for path"""
        for limit_name, config in self.rate_limits.items():
            for endpoint_pattern in config["endpoints"]:
                if self._match_pattern(path, endpoint_pattern):
                    return config
        
        # Default rate limit
        return {
            "requests_per_minute": 100,
            "burst_size": 200,
        }
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Match path against pattern (supports wildcards)"""
        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])
        return path == pattern
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""
        
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get user identifier
        user_id = request.headers.get("X-User-ID", request.client.host)
        
        # Get rate limit config
        rate_config = self.get_rate_limit_for_path(request.url.path)
        requests_per_minute = rate_config["requests_per_minute"]
        burst_size = rate_config["burst_size"]
        
        # Redis key
        key = f"rate_limit:{user_id}:{request.url.path}"
        
        # Check rate limit
        current_time = int(time.time())
        window_start = current_time - 60  # 1 minute window
        
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in window
        request_count = await self.redis.zcard(key)
        
        if request_count >= burst_size:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "LUCID_ERR_0107",
                    "message": "Rate limit exceeded",
                    "retry_after": 60
                }
            )
        
        # Add current request
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, 60)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(burst_size - request_count - 1)
        response.headers["X-RateLimit-Reset"] = str(window_start + 60)
        
        return response
```

## Tor Transport Enforcement

### Tor-Only Communication

All external communications must go through Tor network.

**Configuration**: `config/tor.yaml`

```yaml
tor_config:
  enabled: true
  socks_proxy: "socks5h://tor-proxy:9050"
  control_port: 9051
  enforce_tor: true
  allowed_direct_connections:
    - "127.0.0.1"
    - "localhost"
    - "*.lucid.internal"
```

**Implementation**: `shared/transport/tor_client.py`

```python
import httpx
from typing import Optional

class TorHTTPClient:
    """HTTP client that enforces Tor transport"""
    
    def __init__(self, tor_proxy: str = "socks5h://tor-proxy:9050"):
        self.proxies = {
            "http://": tor_proxy,
            "https://": tor_proxy,
        }
        self.client = httpx.AsyncClient(
            proxies=self.proxies,
            timeout=30.0,
        )
    
    async def get(self, url: str, **kwargs):
        """HTTP GET through Tor"""
        return await self.client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        """HTTP POST through Tor"""
        return await self.client.post(url, **kwargs)
    
    async def close(self):
        """Close client connection"""
        await self.client.aclose()
```

## Session Security

### RDP Session Encryption

All RDP sessions must use TLS encryption.

**XRDP Security Configuration**:

```ini
[Security]
crypt_level=high
ssl_protocols=TLSv1.2, TLSv1.3
tls_ciphers=HIGH:!aNULL:!MD5
require_credentials=true
certificate=/etc/ssl/certs/xrdp.crt
key_file=/etc/ssl/private/xrdp.key
```

### Session Token Generation

```python
import secrets
from datetime import datetime, timedelta

def generate_session_token(user_id: str, server_id: str) -> Dict:
    """Generate secure session token"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user_id": user_id,
        "server_id": server_id,
    }
```

## Audit Logging

### Audit Log Structure

All security-relevant operations must be logged.

```json
{
  "timestamp": "2025-01-10T12:00:00Z",
  "event_type": "rdp_server_created",
  "actor": {
    "user_id": "uuid",
    "username": "string",
    "ip_address": "string"
  },
  "resource": {
    "type": "rdp_server",
    "id": "uuid",
    "name": "string"
  },
  "action": "create",
  "result": "success",
  "details": {
    "configuration": {},
    "resources": {}
  },
  "service": "rdp-server-manager"
}
```

### Audit Logger Implementation

**File**: `shared/logging/audit_logger.py`

```python
import logging
from typing import Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

class AuditLogger:
    """Audit logging for security events"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["audit_logs"]
        self.logger = logging.getLogger("audit")
    
    async def log_event(
        self,
        event_type: str,
        actor: Dict,
        resource: Dict,
        action: str,
        result: str,
        details: Optional[Dict] = None,
        service: str = "unknown"
    ):
        """Log audit event"""
        event = {
            "timestamp": datetime.utcnow(),
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "action": action,
            "result": result,
            "details": details or {},
            "service": service,
        }
        
        # Store in database
        await self.collection.insert_one(event)
        
        # Log to file
        self.logger.info(
            f"AUDIT: {event_type} - "
            f"actor={actor.get('user_id')} "
            f"resource={resource.get('type')}:{resource.get('id')} "
            f"action={action} result={result}"
        )
    
    async def log_authentication(self, user_id: str, result: str, ip_address: str):
        """Log authentication attempt"""
        await self.log_event(
            event_type="authentication",
            actor={"user_id": user_id, "ip_address": ip_address},
            resource={"type": "auth", "id": user_id},
            action="login",
            result=result,
            service="auth"
        )
    
    async def log_authorization_failure(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        required_permission: str
    ):
        """Log authorization failure"""
        await self.log_event(
            event_type="authorization_failure",
            actor={"user_id": user_id},
            resource={"type": resource_type, "id": resource_id},
            action="access",
            result="denied",
            details={"required_permission": required_permission},
            service="authorization"
        )
```

### Events to Audit

| Event | Priority |
|-------|----------|
| User authentication | High |
| Authorization failure | High |
| RDP server creation | Medium |
| RDP server deletion | High |
| Session creation | Medium |
| Session termination | Medium |
| XRDP configuration change | High |
| XRDP service start/stop | High |
| Resource limit exceeded | High |
| Configuration changes | High |

## Port Security

### Firewall Configuration

**File**: `scripts/firewall-setup.sh`

```bash
#!/bin/bash
# RDP Services Cluster Firewall Configuration

# Allow service ports
ufw allow 8090/tcp comment "RDP Server Manager"
ufw allow 8091/tcp comment "XRDP Integration"
ufw allow 8092/tcp comment "Session Controller"
ufw allow 8093/tcp comment "Resource Monitor"

# Allow RDP port range
ufw allow 33890:33999/tcp comment "Dynamic RDP Ports"

# Allow standard RDP
ufw allow 3389/tcp comment "Standard RDP"

# Allow Prometheus
ufw allow 9090/tcp comment "Prometheus Metrics"

# Deny all other incoming by default
ufw default deny incoming
ufw default allow outgoing

# Enable firewall
ufw --force enable
```

### Network Isolation

```yaml
# Network policy for RDP services
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rdp-services-network-policy
spec:
  podSelector:
    matchLabels:
      cluster: rdp-services
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8090
        - protocol: TCP
          port: 8091
        - protocol: TCP
          port: 8092
        - protocol: TCP
          port: 8093
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: mongodb
      ports:
        - protocol: TCP
          port: 27017
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
```

## Compliance

### Data Protection

1. **Encryption at Rest**: All MongoDB data encrypted
2. **Encryption in Transit**: TLS 1.2+ for all connections
3. **Data Retention**: Session data retained for 90 days, audit logs for 1 year
4. **Data Deletion**: Secure deletion of user data on request

### Security Standards

- **OWASP Top 10**: All vulnerabilities mitigated
- **CIS Benchmarks**: Container security compliance
- **ISO 27001**: Information security management
- **SOC 2**: Security controls compliance

### Regular Security Audits

1. **Quarterly penetration testing**
2. **Monthly dependency vulnerability scanning**
3. **Weekly container security scanning**
4. **Daily automated security checks**

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10


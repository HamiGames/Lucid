# 04. Security Compliance

## Overview

This document outlines the comprehensive security architecture for the Session Management Cluster, including authentication, authorization, data protection, network security, and compliance requirements.

## Authentication Architecture

### Multi-Layer Authentication

#### 1. API Gateway Authentication
```python
# sessions/core/security.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import redis

class AuthenticationService:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        # Store token in Redis for validation
        self.redis_client.setex(
            f"access_token:{encoded_jwt}",
            self.access_token_expire_minutes * 60,
            data["user_id"]
        )
        
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token in Redis
        self.redis_client.setex(
            f"refresh_token:{encoded_jwt}",
            self.refresh_token_expire_days * 24 * 60 * 60,
            data["user_id"]
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Verify token exists in Redis
            user_id = self.redis_client.get(f"access_token:{token}")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            return payload
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def revoke_token(self, token: str):
        """Revoke access token."""
        self.redis_client.delete(f"access_token:{token}")
    
    def revoke_user_tokens(self, user_id: str):
        """Revoke all tokens for a user."""
        # Get all tokens for user
        pattern = f"access_token:*"
        for key in self.redis_client.scan_iter(match=pattern):
            token = key.decode().split(":", 1)[1]
            payload = self.verify_token(token)
            if payload.get("user_id") == user_id:
                self.redis_client.delete(key)
```

#### 2. Internal Request Validation
```python
# sessions/api/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from typing import Optional

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> dict:
    """Get current authenticated user."""
    
    token = credentials.credentials
    
    # Verify token
    auth_service = AuthenticationService()
    payload = auth_service.verify_token(token)
    
    # Extract user information
    user_id = payload.get("user_id")
    user_roles = payload.get("roles", [])
    permissions = payload.get("permissions", [])
    
    # Add request context
    request.state.user_id = user_id
    request.state.user_roles = user_roles
    request.state.permissions = permissions
    
    return {
        "user_id": user_id,
        "roles": user_roles,
        "permissions": permissions
    }

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    request: Request = None
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise."""
    
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, request)
    except HTTPException:
        return None
```

### Role-Based Access Control (RBAC)

#### Role Definitions
```python
# sessions/core/rbac.py
from enum import Enum
from typing import List, Dict

class Role(str, Enum):
    ADMIN = "admin"
    SESSION_MANAGER = "session_manager"
    SESSION_OPERATOR = "session_operator"
    SESSION_VIEWER = "session_viewer"
    AUDITOR = "auditor"

class Permission(str, Enum):
    # Session permissions
    CREATE_SESSION = "sessions:create"
    READ_SESSION = "sessions:read"
    UPDATE_SESSION = "sessions:update"
    DELETE_SESSION = "sessions:delete"
    START_SESSION = "sessions:start"
    STOP_SESSION = "sessions:stop"
    PAUSE_SESSION = "sessions:pause"
    
    # Chunk permissions
    READ_CHUNK = "chunks:read"
    DOWNLOAD_CHUNK = "chunks:download"
    DELETE_CHUNK = "chunks:delete"
    
    # Pipeline permissions
    READ_PIPELINE = "pipeline:read"
    CONTROL_PIPELINE = "pipeline:control"
    
    # Statistics permissions
    READ_STATISTICS = "statistics:read"
    READ_SYSTEM_STATISTICS = "statistics:system"
    
    # Admin permissions
    MANAGE_USERS = "admin:users"
    MANAGE_SYSTEM = "admin:system"
    VIEW_AUDIT_LOGS = "admin:audit"

# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [
        Permission.CREATE_SESSION,
        Permission.READ_SESSION,
        Permission.UPDATE_SESSION,
        Permission.DELETE_SESSION,
        Permission.START_SESSION,
        Permission.STOP_SESSION,
        Permission.PAUSE_SESSION,
        Permission.READ_CHUNK,
        Permission.DOWNLOAD_CHUNK,
        Permission.DELETE_CHUNK,
        Permission.READ_PIPELINE,
        Permission.CONTROL_PIPELINE,
        Permission.READ_STATISTICS,
        Permission.READ_SYSTEM_STATISTICS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_SYSTEM,
        Permission.VIEW_AUDIT_LOGS
    ],
    Role.SESSION_MANAGER: [
        Permission.CREATE_SESSION,
        Permission.READ_SESSION,
        Permission.UPDATE_SESSION,
        Permission.DELETE_SESSION,
        Permission.START_SESSION,
        Permission.STOP_SESSION,
        Permission.PAUSE_SESSION,
        Permission.READ_CHUNK,
        Permission.DOWNLOAD_CHUNK,
        Permission.READ_PIPELINE,
        Permission.CONTROL_PIPELINE,
        Permission.READ_STATISTICS
    ],
    Role.SESSION_OPERATOR: [
        Permission.READ_SESSION,
        Permission.START_SESSION,
        Permission.STOP_SESSION,
        Permission.PAUSE_SESSION,
        Permission.READ_CHUNK,
        Permission.READ_PIPELINE,
        Permission.READ_STATISTICS
    ],
    Role.SESSION_VIEWER: [
        Permission.READ_SESSION,
        Permission.READ_CHUNK,
        Permission.READ_PIPELINE,
        Permission.READ_STATISTICS
    ],
    Role.AUDITOR: [
        Permission.READ_SESSION,
        Permission.READ_CHUNK,
        Permission.READ_STATISTICS,
        Permission.VIEW_AUDIT_LOGS
    ]
}

class RBACService:
    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS
    
    def has_permission(self, user_roles: List[str], required_permission: Permission) -> bool:
        """Check if user has required permission."""
        
        for role in user_roles:
            if role in self.role_permissions:
                if required_permission in self.role_permissions[role]:
                    return True
        
        return False
    
    def has_any_permission(self, user_roles: List[str], required_permissions: List[Permission]) -> bool:
        """Check if user has any of the required permissions."""
        
        for permission in required_permissions:
            if self.has_permission(user_roles, permission):
                return True
        
        return False
    
    def has_all_permissions(self, user_roles: List[str], required_permissions: List[Permission]) -> bool:
        """Check if user has all required permissions."""
        
        for permission in required_permissions:
            if not self.has_permission(user_roles, permission):
                return False
        
        return True

# Permission decorators
def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            rbac_service = RBACService()
            if not rbac_service.has_permission(current_user['roles'], permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission {permission.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[Permission]):
    """Decorator to require any of the specified permissions."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            rbac_service = RBACService()
            if not rbac_service.has_any_permission(current_user['roles'], permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of permissions {[p.value for p in permissions]} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### Permission Matrix
| Role | Create Session | Read Session | Update Session | Delete Session | Start/Stop Session | Read Chunks | Download Chunks | Control Pipeline | Read Statistics | Admin Functions |
|------|---------------|--------------|----------------|----------------|-------------------|-------------|-----------------|------------------|-----------------|-----------------|
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Session Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Session Operator | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Session Viewer | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Auditor | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ (Audit Logs) |

## Data Protection

### Encryption at Rest
```python
# sessions/core/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class EncryptionService:
    def __init__(self):
        self.key = self._derive_key()
        self.cipher = Fernet(self.key)
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from password."""
        password = settings.ENCRYPTION_PASSWORD.encode()
        salt = settings.ENCRYPTION_SALT.encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data."""
        return self.cipher.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data."""
        return self.cipher.decrypt(encrypted_data)
    
    def encrypt_file(self, input_path: str, output_path: str):
        """Encrypt file."""
        with open(input_path, 'rb') as infile:
            data = infile.read()
        
        encrypted_data = self.encrypt_data(data)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(encrypted_data)
    
    def decrypt_file(self, input_path: str, output_path: str):
        """Decrypt file."""
        with open(input_path, 'rb') as infile:
            encrypted_data = infile.read()
        
        data = self.decrypt_data(encrypted_data)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(data)
```

### Encryption in Transit
```python
# sessions/core/tls.py
import ssl
import certifi
from typing import Optional

class TLSService:
    def __init__(self):
        self.ssl_context = self._create_ssl_context()
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for secure connections."""
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(certifi.where())
        
        # Disable weak protocols
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        
        return context
    
    def create_secure_connection(self, host: str, port: int) -> ssl.SSLSocket:
        """Create secure connection to host."""
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        secure_sock = self.ssl_context.wrap_socket(sock, server_hostname=host)
        secure_sock.connect((host, port))
        
        return secure_sock
```

## Network Security

### Tor-Only Network Enforcement
```python
# sessions/core/network.py
import socket
from typing import List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TorNetworkService:
    def __init__(self):
        self.tor_proxy = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
        self.allowed_domains = [
            '.onion',
            'localhost',
            '127.0.0.1'
        ]
    
    def validate_tor_connection(self) -> bool:
        """Validate Tor connection."""
        try:
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=self.tor_proxy,
                timeout=10
            )
            
            # Check if IP is different from direct connection
            tor_ip = response.json().get('origin')
            
            # Verify IP is from Tor network
            return self._is_tor_ip(tor_ip)
            
        except Exception:
            return False
    
    def _is_tor_ip(self, ip: str) -> bool:
        """Check if IP is from Tor network."""
        # Tor exit node IP ranges (simplified check)
        tor_ranges = [
            '176.10.104.0/24',
            '176.10.107.0/24',
            '185.220.100.0/22',
            '185.220.101.0/24',
            '185.220.102.0/24',
            '185.220.103.0/24'
        ]
        
        # This is a simplified check - in production, use proper IP range checking
        return any(ip.startswith(range.split('/')[0][:-1]) for range in tor_ranges)
    
    def create_tor_session(self) -> requests.Session:
        """Create requests session with Tor proxy."""
        session = requests.Session()
        session.proxies.update(self.tor_proxy)
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def enforce_tor_only(self, url: str) -> bool:
        """Enforce Tor-only access to URL."""
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        
        if not hostname:
            return False
        
        # Check if hostname is allowed
        return any(hostname.endswith(domain) for domain in self.allowed_domains)
```

### Network Access Control Lists (ACLs)
```python
# sessions/core/acl.py
from typing import List, Dict, Set
from ipaddress import ip_network, ip_address
import redis

class NetworkACL:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.allowed_networks = set()
        self.blocked_networks = set()
        self.allowed_ips = set()
        self.blocked_ips = set()
        
        self._load_acl_rules()
    
    def _load_acl_rules(self):
        """Load ACL rules from configuration."""
        
        # Load allowed networks
        allowed_networks = settings.ALLOWED_NETWORKS.split(',')
        for network in allowed_networks:
            if network.strip():
                self.allowed_networks.add(ip_network(network.strip()))
        
        # Load blocked networks
        blocked_networks = settings.BLOCKED_NETWORKS.split(',')
        for network in blocked_networks:
            if network.strip():
                self.blocked_networks.add(ip_network(network.strip()))
        
        # Load allowed IPs
        allowed_ips = settings.ALLOWED_IPS.split(',')
        for ip in allowed_ips:
            if ip.strip():
                self.allowed_ips.add(ip_address(ip.strip()))
        
        # Load blocked IPs
        blocked_ips = settings.BLOCKED_IPS.split(',')
        for ip in blocked_ips:
            if ip.strip():
                self.blocked_ips.add(ip_address(ip.strip()))
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed."""
        
        try:
            ip_addr = ip_address(ip)
        except ValueError:
            return False
        
        # Check blocked IPs first
        if ip_addr in self.blocked_ips:
            return False
        
        # Check blocked networks
        for network in self.blocked_networks:
            if ip_addr in network:
                return False
        
        # Check allowed IPs
        if ip_addr in self.allowed_ips:
            return True
        
        # Check allowed networks
        for network in self.allowed_networks:
            if ip_addr in network:
                return True
        
        # Default deny
        return False
    
    def add_allowed_network(self, network: str):
        """Add allowed network."""
        self.allowed_networks.add(ip_network(network))
    
    def add_blocked_network(self, network: str):
        """Add blocked network."""
        self.blocked_networks.add(ip_network(network))
    
    def remove_allowed_network(self, network: str):
        """Remove allowed network."""
        self.allowed_networks.discard(ip_network(network))
    
    def remove_blocked_network(self, network: str):
        """Remove blocked network."""
        self.blocked_networks.discard(ip_network(network))
```

## Audit Logging

### Audit Log Specifications
```python
# sessions/core/audit.py
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import json
import uuid
from app.core.logging import get_logger

class AuditEventType(str, Enum):
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    SESSION_DELETED = "session_deleted"
    SESSION_STARTED = "session_started"
    SESSION_STOPPED = "session_stopped"
    SESSION_PAUSED = "session_paused"
    CHUNK_ACCESSED = "chunk_accessed"
    CHUNK_DOWNLOADED = "chunk_downloaded"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_STOPPED = "pipeline_stopped"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PERMISSION_DENIED = "permission_denied"
    CONFIGURATION_CHANGED = "configuration_changed"

class AuditLogger:
    def __init__(self):
        self.logger = get_logger("audit")
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log audit event."""
        
        audit_entry = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "error_message": error_message,
            "details": details or {}
        }
        
        # Log to structured logger
        self.logger.info(
            "Audit event",
            extra=audit_entry
        )
        
        # Store in database for compliance
        self._store_audit_entry(audit_entry)
    
    def _store_audit_entry(self, audit_entry: Dict[str, Any]):
        """Store audit entry in database."""
        from app.core.database import get_db
        
        db = next(get_db())
        
        # Store in audit_logs collection
        db.audit_logs.insert_one(audit_entry)
    
    def log_session_access(self, user_id: str, session_id: str, action: str, ip_address: str):
        """Log session access."""
        self.log_event(
            event_type=AuditEventType.SESSION_ACCESSED,
            user_id=user_id,
            resource_id=session_id,
            details={"action": action},
            ip_address=ip_address
        )
    
    def log_permission_denied(self, user_id: str, resource_id: str, required_permission: str, ip_address: str):
        """Log permission denied event."""
        self.log_event(
            event_type=AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            resource_id=resource_id,
            details={"required_permission": required_permission},
            ip_address=ip_address,
            success=False,
            error_message="Permission denied"
        )
    
    def log_configuration_change(self, user_id: str, config_type: str, old_value: Any, new_value: Any):
        """Log configuration change."""
        self.log_event(
            event_type=AuditEventType.CONFIGURATION_CHANGED,
            user_id=user_id,
            details={
                "config_type": config_type,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )

# Audit decorator
def audit_log(event_type: AuditEventType, resource_id_field: str = None):
    """Decorator to automatically log audit events."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request context
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            
            if not request or not current_user:
                return await func(*args, **kwargs)
            
            # Get resource ID
            resource_id = None
            if resource_id_field:
                resource_id = getattr(request, resource_id_field, None)
            
            # Get IP address
            ip_address = request.client.host
            if request.headers.get("X-Forwarded-For"):
                ip_address = request.headers.get("X-Forwarded-For").split(",")[0].strip()
            
            # Get user agent
            user_agent = request.headers.get("User-Agent")
            
            audit_logger = AuditLogger()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Log successful event
                audit_logger.log_event(
                    event_type=event_type,
                    user_id=current_user['user_id'],
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
                
                return result
                
            except Exception as e:
                # Log failed event
                audit_logger.log_event(
                    event_type=event_type,
                    user_id=current_user['user_id'],
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e)
                )
                
                raise
        
        return wrapper
    return decorator
```

## Rate Limiting

### API Rate Limiting Implementation
```python
# sessions/core/rate_limiting.py
import redis
from typing import Dict, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse

class RateLimiter:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.RATE_LIMIT_STORAGE_URL)
        self.default_limits = {
            "session_create": {"calls": 10, "period": 60},  # 10 per minute
            "session_read": {"calls": 100, "period": 60},   # 100 per minute
            "session_update": {"calls": 50, "period": 60},  # 50 per minute
            "session_delete": {"calls": 5, "period": 60},   # 5 per minute
            "chunk_download": {"calls": 1000, "period": 60}, # 1000 per minute
            "pipeline_control": {"calls": 20, "period": 60}, # 20 per minute
            "statistics": {"calls": 60, "period": 60},       # 60 per minute
        }
    
    def get_rate_limit_key(self, user_id: str, endpoint: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{user_id}:{endpoint}"
    
    def is_rate_limited(self, user_id: str, endpoint: str, custom_limit: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Check if user is rate limited."""
        
        limit_config = custom_limit or self.default_limits.get(endpoint, {"calls": 100, "period": 60})
        calls_limit = limit_config["calls"]
        period_seconds = limit_config["period"]
        
        key = self.get_rate_limit_key(user_id, endpoint)
        
        # Get current count
        current_count = self.redis_client.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)
        
        # Check if rate limited
        if current_count >= calls_limit:
            # Get TTL for rate limit window
            ttl = self.redis_client.ttl(key)
            
            return True, {
                "limit": calls_limit,
                "remaining": 0,
                "reset_time": datetime.utcnow() + timedelta(seconds=ttl),
                "retry_after": ttl
            }
        
        # Increment counter
        if current_count == 0:
            # Set initial expiration
            self.redis_client.setex(key, period_seconds, 1)
        else:
            # Increment existing counter
            self.redis_client.incr(key)
        
        return False, {
            "limit": calls_limit,
            "remaining": calls_limit - current_count - 1,
            "reset_time": datetime.utcnow() + timedelta(seconds=period_seconds),
            "retry_after": 0
        }
    
    def get_rate_limit_info(self, user_id: str, endpoint: str) -> Dict:
        """Get rate limit information for user."""
        
        limit_config = self.default_limits.get(endpoint, {"calls": 100, "period": 60})
        calls_limit = limit_config["calls"]
        period_seconds = limit_config["period"]
        
        key = self.get_rate_limit_key(user_id, endpoint)
        
        # Get current count
        current_count = self.redis_client.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)
        
        # Get TTL
        ttl = self.redis_client.ttl(key)
        if ttl == -1:
            ttl = period_seconds
        
        return {
            "limit": calls_limit,
            "remaining": max(0, calls_limit - current_count),
            "reset_time": datetime.utcnow() + timedelta(seconds=ttl),
            "retry_after": ttl if current_count >= calls_limit else 0
        }

# Rate limiting decorator
def rate_limit(calls: int = 100, period: int = 60):
    """Rate limiting decorator."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request context
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            
            if not request or not current_user:
                return await func(*args, **kwargs)
            
            # Get endpoint name
            endpoint = request.url.path.split('/')[-1]
            
            rate_limiter = RateLimiter()
            custom_limit = {"calls": calls, "period": period}
            
            is_limited, rate_info = rate_limiter.is_rate_limited(
                current_user['user_id'],
                endpoint,
                custom_limit
            )
            
            if is_limited:
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "LUCID_ERR_3010",
                            "message": "Rate limit exceeded",
                            "details": rate_info
                        }
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_info["limit"]),
                        "X-RateLimit-Remaining": str(rate_info["remaining"]),
                        "X-RateLimit-Reset": str(int(rate_info["reset_time"].timestamp())),
                        "Retry-After": str(rate_info["retry_after"])
                    }
                )
                return response
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset_time"].timestamp()))
            
            return response
        
        return wrapper
    return decorator
```

## CORS Policy Configuration

### CORS Configuration
```python
# sessions/api/cors.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def configure_cors(app: FastAPI):
    """Configure CORS policy."""
    
    # Allowed origins based on environment
    allowed_origins = settings.ALLOWED_ORIGINS
    
    # Add localhost for development
    if settings.DEBUG:
        allowed_origins.extend([
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "X-Request-ID",
            "X-User-ID",
            "X-User-Role"
        ],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Request-ID"
        ],
        max_age=86400  # 24 hours
    )
```

## Security Headers

### Security Headers Middleware
```python
# sessions/api/security_headers.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response
```

## Compliance Requirements

### Data Retention Policy
```python
# sessions/core/retention.py
from datetime import datetime, timedelta
from typing import List
import asyncio

class DataRetentionService:
    def __init__(self):
        self.retention_policies = {
            "sessions": 90,  # 90 days
            "chunks": 30,    # 30 days
            "audit_logs": 365,  # 1 year
            "statistics": 180,   # 6 months
        }
    
    async def cleanup_expired_data(self):
        """Clean up expired data based on retention policies."""
        
        for data_type, retention_days in self.retention_policies.items():
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            if data_type == "sessions":
                await self._cleanup_sessions(cutoff_date)
            elif data_type == "chunks":
                await self._cleanup_chunks(cutoff_date)
            elif data_type == "audit_logs":
                await self._cleanup_audit_logs(cutoff_date)
            elif data_type == "statistics":
                await self._cleanup_statistics(cutoff_date)
    
    async def _cleanup_sessions(self, cutoff_date: datetime):
        """Clean up expired sessions."""
        from app.core.database import get_db
        
        db = next(get_db())
        
        # Find expired sessions
        expired_sessions = db.sessions.find({
            "created_at": {"$lt": cutoff_date},
            "status": {"$in": ["completed", "failed", "deleted"]}
        })
        
        for session in expired_sessions:
            # Delete associated chunks
            await self._delete_session_chunks(session["session_id"])
            
            # Delete session files
            await self._delete_session_files(session["session_id"])
            
            # Delete session record
            db.sessions.delete_one({"_id": session["_id"]})
    
    async def _cleanup_chunks(self, cutoff_date: datetime):
        """Clean up expired chunks."""
        from app.core.database import get_db
        
        db = next(get_db())
        
        # Find expired chunks
        expired_chunks = db.chunks.find({
            "created_at": {"$lt": cutoff_date}
        })
        
        for chunk in expired_chunks:
            # Delete chunk file
            await self._delete_chunk_file(chunk["storage_path"])
            
            # Delete chunk record
            db.chunks.delete_one({"_id": chunk["_id"]})
    
    async def _cleanup_audit_logs(self, cutoff_date: datetime):
        """Clean up expired audit logs."""
        from app.core.database import get_db
        
        db = next(get_db())
        
        # Delete expired audit logs
        result = db.audit_logs.delete_many({
            "timestamp": {"$lt": cutoff_date.isoformat()}
        })
        
        print(f"Deleted {result.deleted_count} expired audit logs")
    
    async def _cleanup_statistics(self, cutoff_date: datetime):
        """Clean up expired statistics."""
        from app.core.database import get_db
        
        db = next(get_db())
        
        # Delete expired statistics
        result = db.statistics.delete_many({
            "timestamp": {"$lt": cutoff_date}
        })
        
        print(f"Deleted {result.deleted_count} expired statistics")
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX

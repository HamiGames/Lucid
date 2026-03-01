# API Gateway Cluster - Data Models

## Overview

This document defines the data models, validation rules, and MongoDB collections used by the API Gateway cluster. All models follow consistent naming conventions and enforce data integrity through validation schemas.

## Core Data Models

### User Model

**Collection**: `users`

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

class UserRole(str, Enum):
    USER = "user"
    NODE_OPERATOR = "node_operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class UserModel(BaseModel):
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    password_hash: str = Field(..., description="Bcrypt hashed password")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = Field(default=UserRole.USER)
    hardware_wallet_enabled: bool = Field(default=False)
    hardware_wallet_address: Optional[str] = Field(None, max_length=100)
    totp_secret: Optional[str] = Field(None, max_length=32)
    totp_enabled: bool = Field(default=False)
    email_verified: bool = Field(default=False)
    email_verification_token: Optional[str] = Field(None, max_length=100)
    password_reset_token: Optional[str] = Field(None, max_length=100)
    password_reset_expires: Optional[datetime] = Field(None)
    last_login: Optional[datetime] = Field(None)
    login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Username cannot be empty')
        return v.lower().strip()
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

# MongoDB Indexes
user_indexes = [
    {"email": 1},  # Unique index
    {"username": 1},  # Unique index
    {"user_id": 1},  # Unique index
    {"role": 1},
    {"created_at": 1},
    {"last_login": 1},
    {"email_verification_token": 1},  # Sparse index
    {"password_reset_token": 1},  # Sparse index
]
```

### Session Model

**Collection**: `sessions`

```python
class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SessionModel(BaseModel):
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="Owner user ID")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    duration: Optional[int] = Field(None, description="Duration in seconds")
    size_bytes: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    max_size_bytes: int = Field(default=107374182400, description="100GB limit")
    encryption_key: Optional[str] = Field(None, max_length=64)
    merkle_root: Optional[str] = Field(None, max_length=64)
    manifest_id: Optional[uuid.UUID] = Field(None)
    rdp_server_id: Optional[str] = Field(None, max_length=100)
    trust_policy_id: Optional[uuid.UUID] = Field(None)
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
    
    @validator('size_bytes')
    def validate_size_limit(cls, v, values):
        max_size = values.get('max_size_bytes', 107374182400)
        if v > max_size:
            raise ValueError(f'Session size {v} exceeds limit {max_size}')
        return v

# MongoDB Indexes
session_indexes = [
    {"session_id": 1},  # Unique index
    {"user_id": 1},
    {"status": 1},
    {"created_at": 1},
    {"updated_at": 1},
    {"started_at": 1},
    {"completed_at": 1},
    {"user_id": 1, "status": 1},  # Compound index
    {"user_id": 1, "created_at": -1},  # Compound index for user sessions
]
```

### Manifest Model

**Collection**: `manifests`

```python
class ManifestModel(BaseModel):
    manifest_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID = Field(..., description="Associated session ID")
    merkle_root: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$")
    chunk_count: int = Field(..., ge=1)
    total_size: int = Field(..., ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chunks: List['ChunkInfo'] = Field(default_factory=list)
    blockchain_anchored: bool = Field(default=False)
    blockchain_transaction_id: Optional[str] = Field(None, max_length=100)
    blockchain_block_height: Optional[int] = Field(None, ge=0)
    blockchain_timestamp: Optional[datetime] = Field(None)
    validation_status: str = Field(default="pending", regex="^(pending|valid|invalid)$")
    validation_errors: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

class ChunkInfo(BaseModel):
    chunk_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    index: int = Field(..., ge=0)
    size: int = Field(..., ge=1, le=10485760)  # Max 10MB per chunk
    hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    storage_path: Optional[str] = Field(None, max_length=500)
    encryption_key: Optional[str] = Field(None, max_length=64)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

# MongoDB Indexes
manifest_indexes = [
    {"manifest_id": 1},  # Unique index
    {"session_id": 1},  # Unique index
    {"merkle_root": 1},
    {"created_at": 1},
    {"blockchain_anchored": 1},
    {"blockchain_transaction_id": 1},  # Sparse index
    {"validation_status": 1},
    {"chunks.chunk_id": 1},  # Sparse index for chunk lookups
]
```

### Trust Policy Model

**Collection**: `trust_policies`

```python
class TrustRuleType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"

class TrustRule(BaseModel):
    rule_id: str = Field(..., min_length=1, max_length=100)
    type: TrustRuleType = Field(...)
    condition: str = Field(..., min_length=1, max_length=1000)
    action: str = Field(..., min_length=1, max_length=500)
    priority: int = Field(default=0, ge=0)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TrustPolicyModel(BaseModel):
    policy_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="Owner user ID")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rules: List[TrustRule] = Field(..., min_items=1)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
    
    @validator('rules')
    def validate_rules(cls, v):
        if not v:
            raise ValueError('Trust policy must have at least one rule')
        
        # Validate rule IDs are unique within policy
        rule_ids = [rule.rule_id for rule in v]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError('Rule IDs must be unique within a policy')
        
        return v

# MongoDB Indexes
trust_policy_indexes = [
    {"policy_id": 1},  # Unique index
    {"user_id": 1},
    {"enabled": 1},
    {"created_at": 1},
    {"updated_at": 1},
    {"user_id": 1, "enabled": 1},  # Compound index
]
```

### Wallet Model

**Collection**: `wallets`

```python
class WalletCurrency(str, Enum):
    USDT = "USDT"
    TRX = "TRX"

class WalletNetwork(str, Enum):
    TRON = "TRON"

class WalletModel(BaseModel):
    wallet_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="Owner user ID")
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., max_length=100, regex="^T[A-Za-z1-9]{33}$")
    balance: float = Field(default=0.0, ge=0.0)
    currency: WalletCurrency = Field(...)
    network: WalletNetwork = Field(default=WalletNetwork.TRON)
    private_key_encrypted: Optional[str] = Field(None, max_length=500)
    hardware_wallet: bool = Field(default=False)
    hardware_wallet_path: Optional[str] = Field(None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync: Optional[datetime] = Field(None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
    
    @validator('address')
    def validate_tron_address(cls, v):
        if not v or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        if not v.startswith('T'):
            raise ValueError('TRON address must start with T')
        return v

# MongoDB Indexes
wallet_indexes = [
    {"wallet_id": 1},  # Unique index
    {"user_id": 1},
    {"address": 1},  # Unique index
    {"currency": 1},
    {"network": 1},
    {"created_at": 1},
    {"user_id": 1, "currency": 1},  # Compound index
    {"user_id": 1, "network": 1},  # Compound index
]
```

### Authentication Token Model

**Collection**: `auth_tokens`

```python
class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    MAGIC_LINK = "magic_link"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"

class AuthTokenModel(BaseModel):
    token_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="Associated user ID")
    token_type: TokenType = Field(...)
    token_hash: str = Field(..., max_length=255, description="SHA256 hash of token")
    token_value: Optional[str] = Field(None, max_length=500, description="Encrypted token value")
    expires_at: datetime = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = Field(None)
    revoked: bool = Field(default=False)
    revoked_at: Optional[datetime] = Field(None)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

# MongoDB Indexes
auth_token_indexes = [
    {"token_id": 1},  # Unique index
    {"token_hash": 1},  # Unique index
    {"user_id": 1},
    {"token_type": 1},
    {"expires_at": 1},
    {"revoked": 1},
    {"created_at": 1},
    {"user_id": 1, "token_type": 1},  # Compound index
    {"expires_at": 1, "revoked": 1},  # Compound index for cleanup
]
```

### Rate Limit Model

**Collection**: `rate_limits`

```python
class RateLimitModel(BaseModel):
    limit_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    identifier: str = Field(..., max_length=200, description="IP, user_id, or token")
    identifier_type: str = Field(..., regex="^(ip|user|token)$")
    endpoint: str = Field(..., max_length=500)
    method: str = Field(..., regex="^(GET|POST|PUT|PATCH|DELETE)$")
    requests_count: int = Field(default=0, ge=0)
    window_start: datetime = Field(default_factory=datetime.utcnow)
    window_end: datetime = Field(...)
    limit: int = Field(..., ge=1)
    burst_limit: int = Field(..., ge=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }

# MongoDB Indexes
rate_limit_indexes = [
    {"limit_id": 1},  # Unique index
    {"identifier": 1, "endpoint": 1, "method": 1},  # Compound unique index
    {"window_end": 1},  # TTL index for cleanup
    {"identifier_type": 1},
    {"created_at": 1},
]
```

## Request/Response Models

### API Request Models

```python
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    hardware_wallet: bool = Field(default=False, description="Use hardware wallet authentication")
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

class VerifyRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    code: str = Field(..., min_length=6, max_length=6, regex="^[0-9]{6}$", description="6-digit TOTP code")
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('TOTP code must contain only digits')
        return v

class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=500, description="Valid refresh token")

class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128, description="Plain text password")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Username cannot be empty')
        return v.lower().strip()
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class SessionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    max_size_bytes: int = Field(default=107374182400, ge=1048576, le=107374182400, description="Max 100GB")
    trust_policy_id: Optional[uuid.UUID] = Field(None)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Session name cannot be empty')
        return v.strip()

class TrustPolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rules: List[TrustRule] = Field(..., min_items=1)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Policy name cannot be empty')
        return v.strip()
    
    @validator('rules')
    def validate_rules(cls, v):
        if not v:
            raise ValueError('Trust policy must have at least one rule')
        
        # Validate rule IDs are unique
        rule_ids = [rule.rule_id for rule in v]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError('Rule IDs must be unique')
        
        return v

class WalletCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    currency: WalletCurrency = Field(..., description="Wallet currency")
    network: WalletNetwork = Field(default=WalletNetwork.TRON)
    hardware_wallet: bool = Field(default=False)
    hardware_wallet_path: Optional[str] = Field(None, max_length=200)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Wallet name cannot be empty')
        return v.strip()
```

### API Response Models

```python
class ServiceInfo(BaseModel):
    service_name: str = Field(..., example="api-gateway")
    version: str = Field(..., example="1.0.0")
    build_date: datetime = Field(...)
    environment: str = Field(..., example="production")
    features: List[str] = Field(..., example=["authentication", "rate_limiting", "ssl_termination"])

class HealthStatus(BaseModel):
    status: str = Field(..., regex="^(healthy|unhealthy|degraded)$")
    timestamp: datetime = Field(...)
    service: str = Field(..., example="api-gateway")
    version: str = Field(..., example="1.0.0")
    dependencies: Dict[str, str] = Field(..., description="Dependency health status")
    uptime: int = Field(..., description="Uptime in seconds")
    response_time: float = Field(..., description="Average response time in milliseconds")

class AuthResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: 'UserResponse' = Field(...)

class UserResponse(BaseModel):
    user_id: uuid.UUID = Field(...)
    email: EmailStr = Field(...)
    username: str = Field(...)
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    role: UserRole = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    last_login: Optional[datetime] = Field(None)
    hardware_wallet_enabled: bool = Field(...)

class SessionResponse(BaseModel):
    session_id: uuid.UUID = Field(...)
    user_id: uuid.UUID = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    status: SessionStatus = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    duration: Optional[int] = Field(None, description="Duration in seconds")
    size_bytes: int = Field(...)
    chunk_count: int = Field(...)

class ErrorResponse(BaseModel):
    error: 'ErrorDetail' = Field(...)

class ErrorDetail(BaseModel):
    code: str = Field(..., example="LUCID_ERR_1001")
    message: str = Field(..., example="Invalid request data")
    details: Optional[Dict[str, Any]] = Field(None)
    request_id: uuid.UUID = Field(...)
    timestamp: datetime = Field(...)
    service: str = Field(..., example="api-gateway")
    version: str = Field(..., example="v1")

class PaginationInfo(BaseModel):
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)
```

## Validation Rules

### Field Validation

```python
# Email validation
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Username validation
USERNAME_PATTERN = r'^[a-zA-Z0-9_-]{3,50}$'

# Password validation
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGITS = True
PASSWORD_REQUIRE_SPECIAL = False

# UUID validation
UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'

# TRON address validation
TRON_ADDRESS_PATTERN = r'^T[A-Za-z1-9]{33}$'

# Hash validation (SHA256)
HASH_PATTERN = r'^[a-fA-F0-9]{64}$'

# TOTP code validation
TOTP_CODE_PATTERN = r'^[0-9]{6}$'
```

### Business Logic Validation

```python
# Session size limits
MAX_SESSION_SIZE_BYTES = 107374182400  # 100GB
MIN_SESSION_SIZE_BYTES = 1048576       # 1MB

# Chunk size limits
MAX_CHUNK_SIZE_BYTES = 10485760        # 10MB
MIN_CHUNK_SIZE_BYTES = 1024            # 1KB

# Rate limiting
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_BURST_MULTIPLIER = 2

# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAGIC_LINK_EXPIRE_MINUTES = 5

# User limits
MAX_SESSIONS_PER_USER = 100
MAX_WALLETS_PER_USER = 10
MAX_TRUST_POLICIES_PER_USER = 50

# Password requirements
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
```

## MongoDB Collection Configuration

### Collection Settings

```javascript
// users collection
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "email", "username", "password_hash", "role"],
      properties: {
        user_id: { bsonType: "binData", subType: "04" },
        email: { bsonType: "string", pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$" },
        username: { bsonType: "string", minLength: 3, maxLength: 50 },
        role: { enum: ["user", "node_operator", "admin", "super_admin"] }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// sessions collection
db.createCollection("sessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["session_id", "user_id", "name", "status"],
      properties: {
        session_id: { bsonType: "binData", subType: "04" },
        user_id: { bsonType: "binData", subType: "04" },
        name: { bsonType: "string", minLength: 1, maxLength: 255 },
        status: { enum: ["active", "completed", "failed", "cancelled"] },
        size_bytes: { bsonType: "int", minimum: 0, maximum: 107374182400 }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});
```

### Index Creation Script

```javascript
// Create all indexes for API Gateway collections
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.users.createIndex({ "role": 1 });
db.users.createIndex({ "created_at": 1 });
db.users.createIndex({ "last_login": 1 });

db.sessions.createIndex({ "session_id": 1 }, { unique: true });
db.sessions.createIndex({ "user_id": 1 });
db.sessions.createIndex({ "status": 1 });
db.sessions.createIndex({ "created_at": 1 });
db.sessions.createIndex({ "user_id": 1, "status": 1 });
db.sessions.createIndex({ "user_id": 1, "created_at": -1 });

db.manifests.createIndex({ "manifest_id": 1 }, { unique: true });
db.manifests.createIndex({ "session_id": 1 }, { unique: true });
db.manifests.createIndex({ "merkle_root": 1 });
db.manifests.createIndex({ "blockchain_anchored": 1 });
db.manifests.createIndex({ "validation_status": 1 });

db.trust_policies.createIndex({ "policy_id": 1 }, { unique: true });
db.trust_policies.createIndex({ "user_id": 1 });
db.trust_policies.createIndex({ "enabled": 1 });
db.trust_policies.createIndex({ "user_id": 1, "enabled": 1 });

db.wallets.createIndex({ "wallet_id": 1 }, { unique: true });
db.wallets.createIndex({ "user_id": 1 });
db.wallets.createIndex({ "address": 1 }, { unique: true });
db.wallets.createIndex({ "currency": 1 });
db.wallets.createIndex({ "user_id": 1, "currency": 1 });

db.auth_tokens.createIndex({ "token_id": 1 }, { unique: true });
db.auth_tokens.createIndex({ "token_hash": 1 }, { unique: true });
db.auth_tokens.createIndex({ "user_id": 1 });
db.auth_tokens.createIndex({ "token_type": 1 });
db.auth_tokens.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
db.auth_tokens.createIndex({ "expires_at": 1, "revoked": 1 });

db.rate_limits.createIndex({ "limit_id": 1 }, { unique: true });
db.rate_limits.createIndex({ "identifier": 1, "endpoint": 1, "method": 1 }, { unique: true });
db.rate_limits.createIndex({ "window_end": 1 }, { expireAfterSeconds: 0 });
```

## Data Migration Scripts

### User Migration

```python
async def migrate_users():
    """Migrate users from old schema to new schema"""
    async for user in db.users.find({}):
        # Add new fields with defaults
        update_data = {
            "hardware_wallet_enabled": False,
            "totp_enabled": False,
            "email_verified": False,
            "login_attempts": 0,
            "updated_at": datetime.utcnow()
        }
        
        # Update user document
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": update_data}
        )
```

### Session Migration

```python
async def migrate_sessions():
    """Migrate sessions from old schema to new schema"""
    async for session in db.sessions.find({}):
        # Add new fields with defaults
        update_data = {
            "max_size_bytes": 107374182400,  # 100GB default
            "chunk_count": 0,
            "size_bytes": 0,
            "metadata": {},
            "updated_at": datetime.utcnow()
        }
        
        # Update session document
        await db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": update_data}
        )
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

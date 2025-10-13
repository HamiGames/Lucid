# Storage Database Cluster - Data Models

## Overview

This document defines the data models, database schemas, collection structures, and validation rules used by the Storage Database Cluster. All models follow consistent naming conventions and enforce data integrity through comprehensive validation schemas.

## Core Database Collections

### MongoDB Collections Schema

#### Users Collection
**Collection**: `users`

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class UserRole(str, Enum):
    USER = "user"
    NODE_OPERATOR = "node_operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class UserModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
        allow_population_by_field_name = True
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Username cannot be empty')
        return v.lower().strip()
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

# MongoDB Indexes for Users
user_indexes = [
    {"user_id": 1},  # Unique index
    {"email": 1},    # Unique index
    {"username": 1}, # Unique index
    {"role": 1},
    {"created_at": 1},
    {"last_login": 1},
    {"email_verification_token": 1},  # Sparse index
    {"password_reset_token": 1},      # Sparse index
    {"locked_until": 1},              # Sparse index
]
```

#### Sessions Collection
**Collection**: `sessions`

```python
class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SessionModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
        allow_population_by_field_name = True
    
    @validator('size_bytes')
    def validate_size_limit(cls, v, values):
        max_size = values.get('max_size_bytes', 107374182400)
        if v > max_size:
            raise ValueError(f'Session size {v} exceeds limit {max_size}')
        return v

# MongoDB Indexes for Sessions
session_indexes = [
    {"session_id": 1},  # Unique index
    {"user_id": 1},
    {"status": 1},
    {"created_at": 1},
    {"updated_at": 1},
    {"started_at": 1},
    {"completed_at": 1},
    {"user_id": 1, "status": 1},        # Compound index
    {"user_id": 1, "created_at": -1},   # Compound index for user sessions
    {"merkle_root": 1},                 # Sparse index
    {"manifest_id": 1},                 # Sparse index
]
```

#### Manifests Collection
**Collection**: `manifests`

```python
class ManifestModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
        allow_population_by_field_name = True

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

# MongoDB Indexes for Manifests
manifest_indexes = [
    {"manifest_id": 1},  # Unique index
    {"session_id": 1},   # Unique index
    {"merkle_root": 1},
    {"created_at": 1},
    {"blockchain_anchored": 1},
    {"blockchain_transaction_id": 1},  # Sparse index
    {"validation_status": 1},
    {"chunks.chunk_id": 1},  # Sparse index for chunk lookups
    {"chunks.index": 1},     # Sparse index for chunk ordering
]
```

#### Blocks Collection
**Collection**: `blocks`

```python
class BlockModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    block_id: str = Field(..., max_length=64)
    height: int = Field(..., ge=0)
    hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$")
    previous_hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$")
    timestamp: datetime = Field(...)
    transactions: List['TransactionInfo'] = Field(default_factory=list)
    merkle_root: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$")
    nonce: Optional[int] = Field(None, ge=0)
    difficulty: Optional[int] = Field(None, ge=0)
    block_size: int = Field(..., ge=0)
    transaction_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True

class TransactionInfo(BaseModel):
    transaction_id: str = Field(..., max_length=64)
    type: str = Field(..., max_length=50)
    status: str = Field(..., regex="^(pending|confirmed|failed)$")
    timestamp: datetime = Field(...)
    sender: Optional[str] = Field(None, max_length=100)
    recipient: Optional[str] = Field(None, max_length=100)
    amount: Optional[float] = Field(None, ge=0)
    fee: Optional[float] = Field(None, ge=0)
    signature: Optional[str] = Field(None, max_length=256)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# MongoDB Indexes for Blocks
block_indexes = [
    {"block_id": 1},    # Unique index
    {"height": 1},      # Unique index
    {"hash": 1},        # Unique index
    {"previous_hash": 1},
    {"timestamp": 1},
    {"created_at": 1},
    {"transactions.transaction_id": 1},  # Sparse index
    {"merkle_root": 1},
]
```

#### Transactions Collection
**Collection**: `transactions`

```python
class TransactionModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    transaction_id: str = Field(..., max_length=64)
    block_id: Optional[str] = Field(None, max_length=64)
    type: str = Field(..., max_length=50)
    status: str = Field(..., regex="^(pending|confirmed|failed)$")
    timestamp: datetime = Field(...)
    sender: Optional[str] = Field(None, max_length=100)
    recipient: Optional[str] = Field(None, max_length=100)
    amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    fee: Optional[float] = Field(None, ge=0)
    signature: Optional[str] = Field(None, max_length=256)
    data: Optional[Dict[str, Any]] = Field(None)
    gas_limit: Optional[int] = Field(None, ge=0)
    gas_used: Optional[int] = Field(None, ge=0)
    gas_price: Optional[float] = Field(None, ge=0)
    nonce: Optional[int] = Field(None, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True

# MongoDB Indexes for Transactions
transaction_indexes = [
    {"transaction_id": 1},  # Unique index
    {"block_id": 1},        # Sparse index
    {"type": 1},
    {"status": 1},
    {"timestamp": 1},
    {"sender": 1},          # Sparse index
    {"recipient": 1},       # Sparse index
    {"created_at": 1},
    {"confirmed_at": 1},    # Sparse index
    {"sender": 1, "status": 1},      # Compound index
    {"recipient": 1, "status": 1},   # Compound index
]
```

#### Trust Policies Collection
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
    _id: Optional[str] = Field(None, alias="_id")
    policy_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="Owner user ID")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rules: List[TrustRule] = Field(..., min_items=1)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
        allow_population_by_field_name = True
    
    @validator('rules')
    def validate_rules(cls, v):
        if not v:
            raise ValueError('Trust policy must have at least one rule')
        
        # Validate rule IDs are unique within policy
        rule_ids = [rule.rule_id for rule in v]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError('Rule IDs must be unique within a policy')
        
        return v

# MongoDB Indexes for Trust Policies
trust_policy_indexes = [
    {"policy_id": 1},  # Unique index
    {"user_id": 1},
    {"enabled": 1},
    {"created_at": 1},
    {"updated_at": 1},
    {"user_id": 1, "enabled": 1},  # Compound index
]
```

#### Wallets Collection
**Collection**: `wallets`

```python
class WalletCurrency(str, Enum):
    USDT = "USDT"
    TRX = "TRX"

class WalletNetwork(str, Enum):
    TRON = "TRON"

class WalletModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
        allow_population_by_field_name = True
    
    @validator('address')
    def validate_tron_address(cls, v):
        if not v or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        if not v.startswith('T'):
            raise ValueError('TRON address must start with T')
        return v

# MongoDB Indexes for Wallets
wallet_indexes = [
    {"wallet_id": 1},  # Unique index
    {"user_id": 1},
    {"address": 1},    # Unique index
    {"currency": 1},
    {"network": 1},
    {"created_at": 1},
    {"user_id": 1, "currency": 1},  # Compound index
    {"user_id": 1, "network": 1},   # Compound index
]
```

#### Authentication Tokens Collection
**Collection**: `auth_tokens`

```python
class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    MAGIC_LINK = "magic_link"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"

class AuthTokenModel(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
        allow_population_by_field_name = True

# MongoDB Indexes for Auth Tokens
auth_token_indexes = [
    {"token_id": 1},    # Unique index
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

## Cache Data Models

### Redis Data Structures

#### Session Cache Model
**Redis Key Pattern**: `session:{session_id}`

```python
class SessionCacheModel(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    size_bytes: int
    chunk_count: int
    last_activity: datetime
    expires_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
```

#### Rate Limit Cache Model
**Redis Key Pattern**: `rate_limit:{identifier}:{endpoint}:{method}`

```python
class RateLimitCacheModel(BaseModel):
    identifier: str  # IP address, user_id, or token
    endpoint: str
    method: str
    requests_count: int
    window_start: datetime
    window_end: datetime
    limit: int
    burst_limit: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### User Cache Model
**Redis Key Pattern**: `user:{user_id}`

```python
class UserCacheModel(BaseModel):
    user_id: uuid.UUID
    email: str
    username: str
    role: str
    last_login: Optional[datetime]
    session_count: int
    expires_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
```

## Search Index Models

### Elasticsearch Index Mappings

#### Sessions Index
**Index Name**: `lucid-sessions`

```json
{
  "mappings": {
    "properties": {
      "session_id": {
        "type": "keyword"
      },
      "user_id": {
        "type": "keyword"
      },
      "name": {
        "type": "text",
        "analyzer": "standard"
      },
      "description": {
        "type": "text",
        "analyzer": "standard"
      },
      "status": {
        "type": "keyword"
      },
      "created_at": {
        "type": "date"
      },
      "started_at": {
        "type": "date"
      },
      "completed_at": {
        "type": "date"
      },
      "size_bytes": {
        "type": "long"
      },
      "chunk_count": {
        "type": "integer"
      },
      "merkle_root": {
        "type": "keyword"
      },
      "metadata": {
        "type": "object",
        "dynamic": true
      }
    }
  }
}
```

#### Users Index
**Index Name**: `lucid-users`

```json
{
  "mappings": {
    "properties": {
      "user_id": {
        "type": "keyword"
      },
      "email": {
        "type": "keyword"
      },
      "username": {
        "type": "keyword"
      },
      "first_name": {
        "type": "text",
        "analyzer": "standard"
      },
      "last_name": {
        "type": "text",
        "analyzer": "standard"
      },
      "role": {
        "type": "keyword"
      },
      "created_at": {
        "type": "date"
      },
      "last_login": {
        "type": "date"
      },
      "hardware_wallet_enabled": {
        "type": "boolean"
      }
    }
  }
}
```

#### Blocks Index
**Index Name**: `lucid-blocks`

```json
{
  "mappings": {
    "properties": {
      "block_id": {
        "type": "keyword"
      },
      "height": {
        "type": "integer"
      },
      "hash": {
        "type": "keyword"
      },
      "previous_hash": {
        "type": "keyword"
      },
      "timestamp": {
        "type": "date"
      },
      "merkle_root": {
        "type": "keyword"
      },
      "transaction_count": {
        "type": "integer"
      },
      "block_size": {
        "type": "long"
      },
      "transactions": {
        "type": "nested",
        "properties": {
          "transaction_id": {
            "type": "keyword"
          },
          "type": {
            "type": "keyword"
          },
          "status": {
            "type": "keyword"
          },
          "timestamp": {
            "type": "date"
          },
          "sender": {
            "type": "keyword"
          },
          "recipient": {
            "type": "keyword"
          },
          "amount": {
            "type": "double"
          }
        }
      }
    }
  }
}
```

## Database Configuration

### MongoDB Configuration

```javascript
// Database initialization script
db = db.getSiblingDB('lucid_blockchain');

// Create collections with validation
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "email", "username", "password_hash", "role"],
      properties: {
        user_id: { bsonType: "binData", subType: "04" },
        email: { 
          bsonType: "string", 
          pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$" 
        },
        username: { 
          bsonType: "string", 
          minLength: 3, 
          maxLength: 50,
          pattern: "^[a-zA-Z0-9_-]+$"
        },
        role: { 
          enum: ["user", "node_operator", "admin", "super_admin"] 
        },
        hardware_wallet_enabled: { bsonType: "bool" },
        email_verified: { bsonType: "bool" },
        login_attempts: { bsonType: "int", minimum: 0 }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

db.createCollection("sessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["session_id", "user_id", "name", "status"],
      properties: {
        session_id: { bsonType: "binData", subType: "04" },
        user_id: { bsonType: "binData", subType: "04" },
        name: { bsonType: "string", minLength: 1, maxLength: 255 },
        status: { 
          enum: ["active", "completed", "failed", "cancelled"] 
        },
        size_bytes: { 
          bsonType: "long", 
          minimum: 0, 
          maximum: 107374182400 
        },
        chunk_count: { bsonType: "int", minimum: 0 }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});
```

### Index Creation Script

```javascript
// Create all indexes for optimal performance
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "role": 1 });
db.users.createIndex({ "created_at": 1 });
db.users.createIndex({ "last_login": 1 });
db.users.createIndex({ "email_verification_token": 1 }, { sparse: true });
db.users.createIndex({ "password_reset_token": 1 }, { sparse: true });

db.sessions.createIndex({ "session_id": 1 }, { unique: true });
db.sessions.createIndex({ "user_id": 1 });
db.sessions.createIndex({ "status": 1 });
db.sessions.createIndex({ "created_at": 1 });
db.sessions.createIndex({ "user_id": 1, "status": 1 });
db.sessions.createIndex({ "user_id": 1, "created_at": -1 });
db.sessions.createIndex({ "merkle_root": 1 }, { sparse: true });

db.manifests.createIndex({ "manifest_id": 1 }, { unique: true });
db.manifests.createIndex({ "session_id": 1 }, { unique: true });
db.manifests.createIndex({ "merkle_root": 1 });
db.manifests.createIndex({ "blockchain_anchored": 1 });
db.manifests.createIndex({ "validation_status": 1 });

db.blocks.createIndex({ "block_id": 1 }, { unique: true });
db.blocks.createIndex({ "height": 1 }, { unique: true });
db.blocks.createIndex({ "hash": 1 }, { unique: true });
db.blocks.createIndex({ "previous_hash": 1 });
db.blocks.createIndex({ "timestamp": 1 });

db.transactions.createIndex({ "transaction_id": 1 }, { unique: true });
db.transactions.createIndex({ "block_id": 1 }, { sparse: true });
db.transactions.createIndex({ "type": 1 });
db.transactions.createIndex({ "status": 1 });
db.transactions.createIndex({ "timestamp": 1 });
db.transactions.createIndex({ "sender": 1 }, { sparse: true });
db.transactions.createIndex({ "recipient": 1 }, { sparse: true });

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
db.auth_tokens.createIndex({ "user_id": 1, "token_type": 1 });
```

## Data Validation Rules

### Field Validation Patterns

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

# Merkle root validation
MERKLE_ROOT_PATTERN = r'^[a-fA-F0-9]{64}$'
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

# Database limits
MAX_COLLECTION_SIZE = 1099511627776    # 1TB
MAX_INDEX_SIZE = 536870912             # 512MB
MAX_DOCUMENT_SIZE = 16777216           # 16MB
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
            "metadata": {},
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

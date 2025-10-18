# Authentication Cluster Data Models

## Request/Response Schemas

### Authentication Models

#### LoginRequest
```json
{
  "type": "object",
  "required": ["tron_address", "signature", "message"],
  "properties": {
    "tron_address": {
      "type": "string",
      "pattern": "^T[1-9A-HJ-NP-Za-km-z]{33}$",
      "description": "TRON wallet address"
    },
    "signature": {
      "type": "string",
      "minLength": 128,
      "maxLength": 128,
      "description": "Ed25519 signature in hex"
    },
    "message": {
      "type": "string",
      "minLength": 32,
      "description": "Message that was signed"
    },
    "hardware_wallet": {
      "$ref": "#/components/schemas/HardwareWalletInfo"
    }
  }
}
```

#### HardwareWalletInfo
```json
{
  "type": "object",
  "required": ["type", "device_id"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["ledger", "trezor", "keepkey"]
    },
    "device_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
    }
  }
}
```

#### TokenPair
```json
{
  "type": "object",
  "required": ["access_token", "refresh_token", "expires_in"],
  "properties": {
    "access_token": {
      "type": "string",
      "description": "JWT access token"
    },
    "refresh_token": {
      "type": "string",
      "description": "JWT refresh token"
    },
    "expires_in": {
      "type": "integer",
      "minimum": 300,
      "maximum": 3600,
      "description": "Token expiration in seconds"
    },
    "user": {
      "$ref": "#/components/schemas/UserProfile"
    }
  }
}
```

### User Models

#### UserProfile
```json
{
  "type": "object",
  "required": ["tron_address", "role"],
  "properties": {
    "tron_address": {
      "type": "string",
      "pattern": "^T[1-9A-HJ-NP-Za-km-z]{33}$"
    },
    "username": {
      "type": "string",
      "minLength": 3,
      "maxLength": 32,
      "pattern": "^[a-zA-Z0-9_-]+$"
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "role": {
      "type": "string",
      "enum": ["user", "admin", "node"]
    },
    "permissions": {
      "type": "array",
      "items": {
        "$ref": "#/components/schemas/Permission"
      }
    },
    "kyc_status": {
      "type": "string",
      "enum": ["pending", "verified", "rejected"]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "last_login": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

#### Permission
```json
{
  "type": "object",
  "required": ["resource", "actions"],
  "properties": {
    "resource": {
      "type": "string",
      "enum": ["sessions", "rdp", "blockchain", "payments", "admin"]
    },
    "actions": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["create", "read", "update", "delete", "execute"]
      }
    },
    "conditions": {
      "type": "object",
      "properties": {
        "max_sessions": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "max_size_gb": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000
        }
      }
    }
  }
}
```

### Session Models

#### SessionInfo
```json
{
  "type": "object",
  "required": ["session_id", "created_at"],
  "properties": {
    "session_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "last_activity": {
      "type": "string",
      "format": "date-time"
    },
    "ip_address": {
      "type": "string",
      "format": "ipv4"
    },
    "user_agent": {
      "type": "string",
      "maxLength": 500
    },
    "expires_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### Hardware Wallet Models

#### HardwareWalletStatus
```json
{
  "type": "object",
  "required": ["connected"],
  "properties": {
    "connected": {
      "type": "boolean"
    },
    "wallet_type": {
      "type": "string",
      "enum": ["ledger", "trezor", "keepkey"]
    },
    "device_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
    },
    "public_key": {
      "type": "string",
      "description": "Device public key"
    },
    "firmware_version": {
      "type": "string"
    }
  }
}
```

## MongoDB Collections

### users Collection
```javascript
{
  _id: ObjectId,
  tron_address: String, // Index: unique
  username: String, // Index: sparse, unique
  email: String, // Index: sparse, unique
  role: String, // Index
  permissions: [Permission],
  kyc_status: String,
  hardware_wallets: [HardwareWalletInfo],
  created_at: Date, // Index
  last_login: Date,
  login_attempts: Number,
  locked_until: Date,
  preferences: Object
}
```

### sessions Collection
```javascript
{
  _id: ObjectId,
  session_id: String, // Index: unique
  user_id: ObjectId, // Index, foreign key to users
  access_token_hash: String,
  refresh_token_hash: String,
  created_at: Date, // Index
  expires_at: Date, // Index: TTL
  last_activity: Date,
  ip_address: String,
  user_agent: String,
  revoked: Boolean, // Index
  revoked_at: Date
}
```

### hardware_wallets Collection
```javascript
{
  _id: ObjectId,
  user_id: ObjectId, // Index, foreign key to users
  wallet_type: String,
  device_id: String, // Index: unique
  public_key: String,
  firmware_version: String,
  registered_at: Date,
  last_used: Date,
  status: String // active, revoked, lost
}
```

## Validation Rules

### TRON Address Validation
- Must start with 'T'
- Must be 34 characters long
- Must match TRON address format

### Signature Validation
- Must be 128 hex characters (64 bytes)
- Must be valid Ed25519 signature
- Must verify against provided message and TRON address

### Rate Limiting Rules
- Login attempts: 10 per minute per IP
- Token refresh: 60 per minute per token
- Profile updates: 10 per minute per token
- Hardware wallet operations: 20 per minute per token

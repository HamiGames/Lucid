# Authentication Cluster API Specification

## OpenAPI 3.0 Specification

### Service Information
- **Title**: Lucid Authentication Service
- **Version**: 1.0.0
- **Base URL**: `https://auth.lucid.onion:8090`
- **Protocol**: HTTPS over Tor (.onion)

## Authentication Endpoints

### POST /auth/login
**Description**: Authenticate user with TRON signature
**Rate Limit**: 10 requests/minute per IP

**Request Body**:
```json
{
  "tron_address": "string",
  "signature": "string", 
  "message": "string",
  "hardware_wallet": {
    "type": "ledger|trezor|keepkey",
    "device_id": "string"
  }
}
```

**Response** (200):
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "user": {
    "tron_address": "string",
    "role": "user|admin|node",
    "permissions": ["string"],
    "kyc_status": "pending|verified|rejected"
  }
}
```

### POST /auth/refresh
**Description**: Refresh access token using refresh token
**Rate Limit**: 60 requests/minute per token

**Request Body**:
```json
{
  "refresh_token": "string"
}
```

### POST /auth/logout
**Description**: Invalidate tokens and logout user
**Authentication**: Bearer token required

**Request Body**:
```json
{
  "logout_all_sessions": false
}
```

## User Management Endpoints

### GET /auth/profile
**Description**: Get user profile information
**Authentication**: Bearer token required

**Response** (200):
```json
{
  "tron_address": "string",
  "username": "string",
  "email": "string",
  "role": "string",
  "permissions": ["string"],
  "kyc_status": "string",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T00:00:00Z"
}
```

### PUT /auth/profile
**Description**: Update user profile
**Authentication**: Bearer token required

**Request Body**:
```json
{
  "username": "string",
  "email": "string"
}
```

## Hardware Wallet Endpoints

### POST /auth/hardware-wallet/verify
**Description**: Verify hardware wallet connection
**Authentication**: Bearer token required

**Request Body**:
```json
{
  "wallet_type": "ledger|trezor|keepkey",
  "device_id": "string",
  "challenge": "string",
  "signature": "string"
}
```

### GET /auth/hardware-wallet/status
**Description**: Check hardware wallet connectivity
**Authentication**: Bearer token required

**Response** (200):
```json
{
  "connected": true,
  "wallet_type": "ledger",
  "device_id": "string",
  "public_key": "string"
}
```

## Session Management Endpoints

### GET /auth/active-sessions
**Description**: List user's active sessions
**Authentication**: Bearer token required

**Response** (200):
```json
{
  "sessions": [
    {
      "session_id": "string",
      "created_at": "2024-01-01T00:00:00Z",
      "last_activity": "2024-01-01T00:00:00Z",
      "ip_address": "string",
      "user_agent": "string"
    }
  ]
}
```

### POST /auth/sessions/{session_id}/revoke
**Description**: Revoke specific session
**Authentication**: Bearer token required

## Permission Endpoints

### GET /auth/permissions
**Description**: Get user permissions
**Authentication**: Bearer token required

**Response** (200):
```json
{
  "permissions": [
    {
      "resource": "sessions",
      "actions": ["create", "read", "update", "delete"],
      "conditions": {
        "max_sessions": 5,
        "max_size_gb": 100
      }
    }
  ]
}
```

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "LUCID_AUTH_1001",
    "message": "Invalid TRON signature",
    "details": {
      "field": "signature",
      "reason": "verification_failed"
    },
    "request_id": "req-uuid-here",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Error Codes
- `LUCID_AUTH_1001` - Invalid TRON signature
- `LUCID_AUTH_1002` - Token expired
- `LUCID_AUTH_1003` - Insufficient permissions
- `LUCID_AUTH_1004` - Hardware wallet not connected
- `LUCID_AUTH_1005` - Account locked
- `LUCID_AUTH_1006` - Rate limit exceeded

## Rate Limiting

### Rate Limit Headers
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1640995200
```

### Rate Limit Policies
- **Login**: 10 requests/minute per IP
- **Refresh**: 60 requests/minute per token
- **Profile**: 100 requests/minute per token
- **Hardware Wallet**: 20 requests/minute per token

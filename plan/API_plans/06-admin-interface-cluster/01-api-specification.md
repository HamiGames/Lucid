# Admin Interface Cluster - API Specification

## OpenAPI 3.0 Specification

### Base Information
- **Title**: Lucid Admin Interface API
- **Version**: 1.0.0
- **Description**: Administrative interface for Lucid RDP system management
- **Base URL**: `https://admin.lucid.local:8096/api/v1`
- **Protocols**: HTTPS, WSS (WebSocket)

### Authentication
- **Type**: Bearer Token (JWT)
- **Scheme**: `Authorization: Bearer <token>`
- **Additional Security**: TOTP (Time-based One-Time Password)

## API Endpoints

### 1. Authentication & Authorization

#### POST /admin/auth/login
**Description**: Admin user authentication  
**Security**: None (public endpoint)

**Request Body**:
```json
{
  "username": "string",
  "password": "string",
  "totp_code": "string",
  "remember_me": "boolean"
}
```

**Response**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "user": {
    "id": "string",
    "username": "string",
    "role": "super-admin|admin|operator",
    "permissions": ["string"],
    "last_login": "2024-01-01T00:00:00Z"
  }
}
```

#### POST /admin/auth/refresh
**Description**: Refresh access token  
**Security**: Bearer Token

**Request Body**:
```json
{
  "refresh_token": "string"
}
```

#### POST /admin/auth/logout
**Description**: Admin logout and token invalidation  
**Security**: Bearer Token

#### GET /admin/auth/me
**Description**: Get current admin user information  
**Security**: Bearer Token

### 2. Role-Based Access Control (RBAC)

#### GET /admin/rbac/roles
**Description**: Get all available roles  
**Security**: Bearer Token (super-admin required)

**Response**:
```json
{
  "roles": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "permissions": ["string"],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### POST /admin/rbac/roles
**Description**: Create new role  
**Security**: Bearer Token (super-admin required)

#### PUT /admin/rbac/roles/{role_id}
**Description**: Update role  
**Security**: Bearer Token (super-admin required)

#### DELETE /admin/rbac/roles/{role_id}
**Description**: Delete role  
**Security**: Bearer Token (super-admin required)

#### GET /admin/rbac/permissions
**Description**: Get all available permissions  
**Security**: Bearer Token (super-admin required)

#### POST /admin/rbac/users/{user_id}/assign-role
**Description**: Assign role to user  
**Security**: Bearer Token (super-admin required)

### 3. Dashboard & Monitoring

#### GET /admin/dashboard/overview
**Description**: Get system overview dashboard data  
**Security**: Bearer Token (admin required)

**Response**:
```json
{
  "system_status": {
    "status": "healthy|warning|critical",
    "uptime": "string",
    "version": "string",
    "last_updated": "2024-01-01T00:00:00Z"
  },
  "active_sessions": {
    "total": 0,
    "active": 0,
    "idle": 0,
    "by_type": {}
  },
  "node_status": {
    "total_nodes": 0,
    "online_nodes": 0,
    "offline_nodes": 0,
    "load_average": 0.0
  },
  "blockchain_status": {
    "network_height": 0,
    "sync_status": "synced|syncing|behind",
    "pending_transactions": 0
  },
  "resource_usage": {
    "cpu_percentage": 0.0,
    "memory_percentage": 0.0,
    "disk_percentage": 0.0,
    "network_io": {
      "bytes_in": 0,
      "bytes_out": 0
    }
  }
}
```

#### GET /admin/dashboard/metrics
**Description**: Get real-time system metrics  
**Security**: Bearer Token (admin required)

**Query Parameters**:
- `timeframe`: `1h|6h|24h|7d|30d`
- `metric`: `cpu|memory|disk|network|sessions`

#### WebSocket /admin/dashboard/stream
**Description**: Real-time dashboard updates  
**Security**: Bearer Token (admin required)

**Message Format**:
```json
{
  "type": "metric_update|system_alert|session_change",
  "data": {},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 4. Session Management

#### GET /admin/sessions
**Description**: List all active sessions  
**Security**: Bearer Token (admin required)

**Query Parameters**:
- `status`: `active|idle|terminated`
- `user_id`: Filter by user
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset

**Response**:
```json
{
  "sessions": [
    {
      "id": "string",
      "user_id": "string",
      "username": "string",
      "status": "active|idle|terminated",
      "start_time": "2024-01-01T00:00:00Z",
      "last_activity": "2024-01-01T00:00:00Z",
      "duration": "string",
      "node_id": "string",
      "ip_address": "string"
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

#### POST /admin/sessions/{session_id}/terminate
**Description**: Terminate specific session  
**Security**: Bearer Token (admin required)

#### POST /admin/sessions/terminate-bulk
**Description**: Terminate multiple sessions  
**Security**: Bearer Token (admin required)

**Request Body**:
```json
{
  "session_ids": ["string"],
  "reason": "string"
}
```

#### GET /admin/sessions/{session_id}/details
**Description**: Get detailed session information  
**Security**: Bearer Token (admin required)

#### GET /admin/sessions/{session_id}/logs
**Description**: Get session activity logs  
**Security**: Bearer Token (admin required)

### 5. Node Management

#### GET /admin/nodes
**Description**: List all nodes and their status  
**Security**: Bearer Token (admin required)

**Response**:
```json
{
  "nodes": [
    {
      "id": "string",
      "hostname": "string",
      "status": "online|offline|maintenance",
      "ip_address": "string",
      "load_average": 0.0,
      "memory_usage": 0.0,
      "disk_usage": 0.0,
      "active_sessions": 0,
      "last_heartbeat": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### POST /admin/nodes/{node_id}/restart
**Description**: Restart specific node  
**Security**: Bearer Token (admin required)

#### POST /admin/nodes/{node_id}/maintenance
**Description**: Put node in maintenance mode  
**Security**: Bearer Token (admin required)

#### GET /admin/nodes/{node_id}/metrics
**Description**: Get node performance metrics  
**Security**: Bearer Token (admin required)

### 6. Blockchain Management

#### GET /admin/blockchain/status
**Description**: Get blockchain network status  
**Security**: Bearer Token (admin required)

**Response**:
```json
{
  "network_height": 0,
  "local_height": 0,
  "sync_status": "synced|syncing|behind",
  "pending_transactions": 0,
  "network_hash_rate": "string",
  "difficulty": "string",
  "last_block_time": "2024-01-01T00:00:00Z"
}
```

#### POST /admin/blockchain/anchor-sessions
**Description**: Trigger blockchain anchoring of sessions  
**Security**: Bearer Token (admin required)

**Request Body**:
```json
{
  "session_ids": ["string"],
  "priority": "low|normal|high",
  "force": false
}
```

#### GET /admin/blockchain/anchoring-queue
**Description**: Get pending anchoring operations  
**Security**: Bearer Token (admin required)

#### POST /admin/blockchain/resync
**Description**: Force blockchain resynchronization  
**Security**: Bearer Token (admin required)

### 7. Payout Management

#### GET /admin/payouts
**Description**: List payout operations  
**Security**: Bearer Token (admin required)

**Query Parameters**:
- `status`: `pending|processing|completed|failed`
- `date_from`: Start date filter
- `date_to`: End date filter

#### POST /admin/payouts/trigger
**Description**: Trigger manual payout processing  
**Security**: Bearer Token (admin required)

**Request Body**:
```json
{
  "user_ids": ["string"],
  "amount": "string",
  "currency": "USDT",
  "reason": "string"
}
```

#### GET /admin/payouts/{payout_id}/status
**Description**: Get payout status and details  
**Security**: Bearer Token (admin required)

### 8. User Management

#### GET /admin/users
**Description**: List all users  
**Security**: Bearer Token (admin required)

**Query Parameters**:
- `status`: `active|suspended|banned`
- `role`: Filter by role
- `search`: Search by username or email

#### POST /admin/users
**Description**: Create new user  
**Security**: Bearer Token (super-admin required)

#### PUT /admin/users/{user_id}
**Description**: Update user information  
**Security**: Bearer Token (admin required)

#### POST /admin/users/{user_id}/suspend
**Description**: Suspend user account  
**Security**: Bearer Token (admin required)

#### POST /admin/users/{user_id}/activate
**Description**: Activate suspended user  
**Security**: Bearer Token (admin required)

### 9. System Configuration

#### GET /admin/config
**Description**: Get system configuration  
**Security**: Bearer Token (admin required)

#### PUT /admin/config
**Description**: Update system configuration  
**Security**: Bearer Token (admin required)

**Request Body**:
```json
{
  "max_sessions_per_user": 0,
  "session_timeout": 0,
  "node_health_check_interval": 0,
  "blockchain_anchoring_interval": 0,
  "payout_processing_interval": 0
}
```

#### GET /admin/config/backup
**Description**: Create configuration backup  
**Security**: Bearer Token (admin required)

#### POST /admin/config/restore
**Description**: Restore configuration from backup  
**Security**: Bearer Token (super-admin required)

### 10. Audit Logging

#### GET /admin/audit/logs
**Description**: Query audit logs  
**Security**: Bearer Token (admin required)

**Query Parameters**:
- `action`: Filter by action type
- `user_id`: Filter by user
- `date_from`: Start date filter
- `date_to`: End date filter
- `severity`: `info|warning|error|critical`

**Response**:
```json
{
  "logs": [
    {
      "id": "string",
      "timestamp": "2024-01-01T00:00:00Z",
      "user_id": "string",
      "username": "string",
      "action": "string",
      "resource": "string",
      "details": {},
      "ip_address": "string",
      "user_agent": "string",
      "severity": "info|warning|error|critical"
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

#### POST /admin/audit/logs/export
**Description**: Export audit logs  
**Security**: Bearer Token (admin required)

**Request Body**:
```json
{
  "format": "json|csv|pdf",
  "date_from": "2024-01-01T00:00:00Z",
  "date_to": "2024-01-01T00:00:00Z",
  "filters": {}
}
```

#### GET /admin/audit/stats
**Description**: Get audit log statistics  
**Security**: Bearer Token (admin required)

### 11. Emergency Controls

#### POST /admin/emergency/stop-all-sessions
**Description**: Emergency stop all active sessions  
**Security**: Bearer Token (super-admin required)

#### POST /admin/emergency/system-lockdown
**Description**: Put system in lockdown mode  
**Security**: Bearer Token (super-admin required)

#### POST /admin/emergency/disable-new-sessions
**Description**: Disable new session creation  
**Security**: Bearer Token (admin required)

#### POST /admin/emergency/enable-new-sessions
**Description**: Enable new session creation  
**Security**: Bearer Token (admin required)

### 12. Health Checks

#### GET /admin/health
**Description**: Basic health check  
**Security**: None

**Response**:
```json
{
  "status": "healthy|unhealthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "string"
}
```

#### GET /admin/health/detailed
**Description**: Detailed health check  
**Security**: Bearer Token (admin required)

#### GET /admin/health/dependencies
**Description**: Check dependency health  
**Security**: Bearer Token (admin required)

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "LUCID_ADMIN_ERR_1001",
    "message": "Admin access denied",
    "details": {
      "required_permission": "admin:users:manage"
    },
    "request_id": "req-uuid-here",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Error Codes

| Code | Message | Description |
|------|---------|-------------|
| LUCID_ADMIN_ERR_1001 | Admin access denied | Insufficient permissions |
| LUCID_ADMIN_ERR_1002 | Invalid admin token | Token expired or invalid |
| LUCID_ADMIN_ERR_1003 | Session not found | Session ID does not exist |
| LUCID_ADMIN_ERR_1004 | Node unavailable | Node is offline or unreachable |
| LUCID_ADMIN_ERR_1005 | Blockchain sync required | Blockchain needs synchronization |
| LUCID_ADMIN_ERR_1006 | Configuration invalid | Invalid configuration parameters |
| LUCID_ADMIN_ERR_1007 | Audit log query failed | Audit log query error |
| LUCID_ADMIN_ERR_1008 | Emergency action failed | Emergency control operation failed |

## Rate Limiting

### Rate Limits
- **Public endpoints**: 10 req/min per IP
- **Authenticated endpoints**: 1000 req/min per token
- **Admin endpoints**: 10000 req/min per admin token
- **Emergency endpoints**: 5 req/min per super-admin token

### Rate Limit Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## WebSocket Events

### Connection
```javascript
const ws = new WebSocket('wss://admin.lucid.local:8096/api/v1/admin/dashboard/stream', {
  headers: {
    'Authorization': 'Bearer <token>'
  }
});
```

### Event Types
- `metric_update`: Real-time system metrics
- `system_alert`: System alerts and notifications
- `session_change`: Session status changes
- `node_status_change`: Node status updates
- `blockchain_update`: Blockchain status updates

## API Versioning

### Version Strategy
- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Header Versioning**: `Accept: application/vnd.lucid-admin.v1+json`
- **Backward Compatibility**: Maintained for at least 2 versions

### Deprecation Policy
- 6 months notice for breaking changes
- Graceful degradation for deprecated endpoints
- Migration guides provided

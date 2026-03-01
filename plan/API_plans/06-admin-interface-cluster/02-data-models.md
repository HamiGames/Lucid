# Admin Interface Cluster - Data Models

## Request/Response Schemas

### Authentication Models

#### LoginRequest
```json
{
  "type": "object",
  "required": ["username", "password", "totp_code"],
  "properties": {
    "username": {
      "type": "string",
      "minLength": 3,
      "maxLength": 50,
      "pattern": "^[a-zA-Z0-9_-]+$",
      "description": "Admin username"
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "maxLength": 128,
      "description": "Admin password"
    },
    "totp_code": {
      "type": "string",
      "pattern": "^[0-9]{6}$",
      "description": "6-digit TOTP code"
    },
    "remember_me": {
      "type": "boolean",
      "default": false,
      "description": "Remember login session"
    }
  }
}
```

#### LoginResponse
```json
{
  "type": "object",
  "required": ["access_token", "refresh_token", "expires_in", "user"],
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
      "maximum": 86400,
      "description": "Token expiration time in seconds"
    },
    "user": {
      "$ref": "#/components/schemas/AdminUser"
    }
  }
}
```

#### AdminUser
```json
{
  "type": "object",
  "required": ["id", "username", "role", "permissions"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique user identifier"
    },
    "username": {
      "type": "string",
      "description": "Admin username"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "Admin email address"
    },
    "role": {
      "type": "string",
      "enum": ["super-admin", "admin", "operator"],
      "description": "Admin role level"
    },
    "permissions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of granted permissions"
    },
    "last_login": {
      "type": "string",
      "format": "date-time",
      "description": "Last login timestamp"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "User creation timestamp"
    },
    "status": {
      "type": "string",
      "enum": ["active", "suspended", "disabled"],
      "description": "User status"
    }
  }
}
```

### RBAC Models

#### Role
```json
{
  "type": "object",
  "required": ["id", "name", "description", "permissions"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique role identifier"
    },
    "name": {
      "type": "string",
      "minLength": 3,
      "maxLength": 50,
      "pattern": "^[a-zA-Z0-9_-]+$",
      "description": "Role name"
    },
    "description": {
      "type": "string",
      "maxLength": 255,
      "description": "Role description"
    },
    "permissions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of permissions granted by this role"
    },
    "is_system": {
      "type": "boolean",
      "default": false,
      "description": "Whether this is a system role"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Role creation timestamp"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Role last update timestamp"
    }
  }
}
```

#### Permission
```json
{
  "type": "object",
  "required": ["id", "name", "resource", "action"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique permission identifier"
    },
    "name": {
      "type": "string",
      "description": "Permission display name"
    },
    "resource": {
      "type": "string",
      "enum": ["users", "sessions", "nodes", "blockchain", "payouts", "config", "audit"],
      "description": "Resource type"
    },
    "action": {
      "type": "string",
      "enum": ["create", "read", "update", "delete", "manage"],
      "description": "Action type"
    },
    "description": {
      "type": "string",
      "description": "Permission description"
    }
  }
}
```

### Dashboard Models

#### SystemOverview
```json
{
  "type": "object",
  "required": ["system_status", "active_sessions", "node_status", "blockchain_status", "resource_usage"],
  "properties": {
    "system_status": {
      "$ref": "#/components/schemas/SystemStatus"
    },
    "active_sessions": {
      "$ref": "#/components/schemas/SessionSummary"
    },
    "node_status": {
      "$ref": "#/components/schemas/NodeSummary"
    },
    "blockchain_status": {
      "$ref": "#/components/schemas/BlockchainStatus"
    },
    "resource_usage": {
      "$ref": "#/components/schemas/ResourceUsage"
    }
  }
}
```

#### SystemStatus
```json
{
  "type": "object",
  "required": ["status", "uptime", "version", "last_updated"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy", "warning", "critical"],
      "description": "Overall system health status"
    },
    "uptime": {
      "type": "string",
      "description": "System uptime in human readable format"
    },
    "version": {
      "type": "string",
      "description": "System version"
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "Last status update timestamp"
    }
  }
}
```

#### SessionSummary
```json
{
  "type": "object",
  "required": ["total", "active", "idle", "by_type"],
  "properties": {
    "total": {
      "type": "integer",
      "minimum": 0,
      "description": "Total number of sessions"
    },
    "active": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of active sessions"
    },
    "idle": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of idle sessions"
    },
    "by_type": {
      "type": "object",
      "additionalProperties": {
        "type": "integer"
      },
      "description": "Session count by type"
    }
  }
}
```

#### NodeSummary
```json
{
  "type": "object",
  "required": ["total_nodes", "online_nodes", "offline_nodes", "load_average"],
  "properties": {
    "total_nodes": {
      "type": "integer",
      "minimum": 0,
      "description": "Total number of nodes"
    },
    "online_nodes": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of online nodes"
    },
    "offline_nodes": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of offline nodes"
    },
    "load_average": {
      "type": "number",
      "minimum": 0,
      "description": "Average system load"
    }
  }
}
```

#### BlockchainStatus
```json
{
  "type": "object",
  "required": ["network_height", "sync_status", "pending_transactions"],
  "properties": {
    "network_height": {
      "type": "integer",
      "minimum": 0,
      "description": "Current blockchain network height"
    },
    "local_height": {
      "type": "integer",
      "minimum": 0,
      "description": "Local blockchain height"
    },
    "sync_status": {
      "type": "string",
      "enum": ["synced", "syncing", "behind"],
      "description": "Blockchain synchronization status"
    },
    "pending_transactions": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of pending transactions"
    },
    "network_hash_rate": {
      "type": "string",
      "description": "Network hash rate"
    },
    "difficulty": {
      "type": "string",
      "description": "Current mining difficulty"
    },
    "last_block_time": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp of last block"
    }
  }
}
```

#### ResourceUsage
```json
{
  "type": "object",
  "required": ["cpu_percentage", "memory_percentage", "disk_percentage", "network_io"],
  "properties": {
    "cpu_percentage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "CPU usage percentage"
    },
    "memory_percentage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Memory usage percentage"
    },
    "disk_percentage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Disk usage percentage"
    },
    "network_io": {
      "type": "object",
      "required": ["bytes_in", "bytes_out"],
      "properties": {
        "bytes_in": {
          "type": "integer",
          "minimum": 0,
          "description": "Bytes received"
        },
        "bytes_out": {
          "type": "integer",
          "minimum": 0,
          "description": "Bytes sent"
        }
      }
    }
  }
}
```

### Session Management Models

#### Session
```json
{
  "type": "object",
  "required": ["id", "user_id", "username", "status", "start_time"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique session identifier"
    },
    "user_id": {
      "type": "string",
      "format": "uuid",
      "description": "User identifier"
    },
    "username": {
      "type": "string",
      "description": "Username"
    },
    "status": {
      "type": "string",
      "enum": ["active", "idle", "terminated"],
      "description": "Session status"
    },
    "start_time": {
      "type": "string",
      "format": "date-time",
      "description": "Session start timestamp"
    },
    "last_activity": {
      "type": "string",
      "format": "date-time",
      "description": "Last activity timestamp"
    },
    "duration": {
      "type": "string",
      "description": "Session duration in human readable format"
    },
    "node_id": {
      "type": "string",
      "description": "Node hosting the session"
    },
    "ip_address": {
      "type": "string",
      "format": "ipv4",
      "description": "Client IP address"
    },
    "user_agent": {
      "type": "string",
      "description": "Client user agent"
    },
    "session_type": {
      "type": "string",
      "enum": ["rdp", "vnc", "ssh"],
      "description": "Type of session"
    }
  }
}
```

#### SessionTerminationRequest
```json
{
  "type": "object",
  "required": ["session_ids", "reason"],
  "properties": {
    "session_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      },
      "minItems": 1,
      "description": "List of session IDs to terminate"
    },
    "reason": {
      "type": "string",
      "maxLength": 255,
      "description": "Reason for termination"
    }
  }
}
```

### Node Management Models

#### Node
```json
{
  "type": "object",
  "required": ["id", "hostname", "status", "ip_address"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique node identifier"
    },
    "hostname": {
      "type": "string",
      "description": "Node hostname"
    },
    "status": {
      "type": "string",
      "enum": ["online", "offline", "maintenance"],
      "description": "Node status"
    },
    "ip_address": {
      "type": "string",
      "format": "ipv4",
      "description": "Node IP address"
    },
    "load_average": {
      "type": "number",
      "minimum": 0,
      "description": "System load average"
    },
    "memory_usage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Memory usage percentage"
    },
    "disk_usage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Disk usage percentage"
    },
    "active_sessions": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of active sessions"
    },
    "last_heartbeat": {
      "type": "string",
      "format": "date-time",
      "description": "Last heartbeat timestamp"
    },
    "version": {
      "type": "string",
      "description": "Node software version"
    }
  }
}
```

### Blockchain Management Models

#### AnchoringRequest
```json
{
  "type": "object",
  "required": ["session_ids", "priority"],
  "properties": {
    "session_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      },
      "minItems": 1,
      "description": "List of session IDs to anchor"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high"],
      "description": "Anchoring priority"
    },
    "force": {
      "type": "boolean",
      "default": false,
      "description": "Force anchoring even if conditions not met"
    }
  }
}
```

#### AnchoringQueue
```json
{
  "type": "object",
  "required": ["pending_operations", "processing_operations"],
  "properties": {
    "pending_operations": {
      "type": "array",
      "items": {
        "$ref": "#/components/schemas/AnchoringOperation"
      },
      "description": "Pending anchoring operations"
    },
    "processing_operations": {
      "type": "array",
      "items": {
        "$ref": "#/components/schemas/AnchoringOperation"
      },
      "description": "Currently processing operations"
    }
  }
}
```

#### AnchoringOperation
```json
{
  "type": "object",
  "required": ["id", "session_ids", "priority", "status", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Operation identifier"
    },
    "session_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      },
      "description": "Session IDs to anchor"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high"],
      "description": "Operation priority"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "processing", "completed", "failed"],
      "description": "Operation status"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Creation timestamp"
    },
    "started_at": {
      "type": "string",
      "format": "date-time",
      "description": "Processing start timestamp"
    },
    "completed_at": {
      "type": "string",
      "format": "date-time",
      "description": "Completion timestamp"
    },
    "transaction_hash": {
      "type": "string",
      "description": "Blockchain transaction hash"
    },
    "error_message": {
      "type": "string",
      "description": "Error message if failed"
    }
  }
}
```

### Payout Management Models

#### Payout
```json
{
  "type": "object",
  "required": ["id", "user_id", "amount", "currency", "status"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Payout identifier"
    },
    "user_id": {
      "type": "string",
      "format": "uuid",
      "description": "User identifier"
    },
    "amount": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]{6}$",
      "description": "Payout amount"
    },
    "currency": {
      "type": "string",
      "enum": ["USDT"],
      "description": "Payout currency"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "processing", "completed", "failed"],
      "description": "Payout status"
    },
    "reason": {
      "type": "string",
      "description": "Payout reason"
    },
    "transaction_hash": {
      "type": "string",
      "description": "Blockchain transaction hash"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Creation timestamp"
    },
    "processed_at": {
      "type": "string",
      "format": "date-time",
      "description": "Processing timestamp"
    },
    "completed_at": {
      "type": "string",
      "format": "date-time",
      "description": "Completion timestamp"
    },
    "error_message": {
      "type": "string",
      "description": "Error message if failed"
    }
  }
}
```

#### PayoutTriggerRequest
```json
{
  "type": "object",
  "required": ["user_ids", "amount", "currency", "reason"],
  "properties": {
    "user_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "uuid"
      },
      "minItems": 1,
      "description": "List of user IDs for payout"
    },
    "amount": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]{6}$",
      "description": "Payout amount per user"
    },
    "currency": {
      "type": "string",
      "enum": ["USDT"],
      "description": "Payout currency"
    },
    "reason": {
      "type": "string",
      "maxLength": 255,
      "description": "Payout reason"
    }
  }
}
```

### User Management Models

#### User
```json
{
  "type": "object",
  "required": ["id", "username", "email", "status", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique user identifier"
    },
    "username": {
      "type": "string",
      "description": "Username"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "Email address"
    },
    "status": {
      "type": "string",
      "enum": ["active", "suspended", "banned"],
      "description": "User status"
    },
    "role": {
      "type": "string",
      "description": "User role"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Creation timestamp"
    },
    "last_login": {
      "type": "string",
      "format": "date-time",
      "description": "Last login timestamp"
    },
    "total_sessions": {
      "type": "integer",
      "minimum": 0,
      "description": "Total number of sessions"
    },
    "active_sessions": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of active sessions"
    }
  }
}
```

#### UserCreateRequest
```json
{
  "type": "object",
  "required": ["username", "email", "password"],
  "properties": {
    "username": {
      "type": "string",
      "minLength": 3,
      "maxLength": 50,
      "pattern": "^[a-zA-Z0-9_-]+$",
      "description": "Username"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "Email address"
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "maxLength": 128,
      "description": "Password"
    },
    "role": {
      "type": "string",
      "description": "User role"
    }
  }
}
```

### System Configuration Models

#### SystemConfig
```json
{
  "type": "object",
  "properties": {
    "max_sessions_per_user": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "description": "Maximum sessions per user"
    },
    "session_timeout": {
      "type": "integer",
      "minimum": 300,
      "maximum": 86400,
      "description": "Session timeout in seconds"
    },
    "node_health_check_interval": {
      "type": "integer",
      "minimum": 10,
      "maximum": 300,
      "description": "Node health check interval in seconds"
    },
    "blockchain_anchoring_interval": {
      "type": "integer",
      "minimum": 300,
      "maximum": 3600,
      "description": "Blockchain anchoring interval in seconds"
    },
    "payout_processing_interval": {
      "type": "integer",
      "minimum": 3600,
      "maximum": 86400,
      "description": "Payout processing interval in seconds"
    },
    "max_session_size_gb": {
      "type": "number",
      "minimum": 1,
      "maximum": 1000,
      "description": "Maximum session size in GB"
    },
    "enable_emergency_controls": {
      "type": "boolean",
      "description": "Enable emergency control features"
    },
    "audit_log_retention_days": {
      "type": "integer",
      "minimum": 30,
      "maximum": 3650,
      "description": "Audit log retention period in days"
    }
  }
}
```

### Audit Logging Models

#### AuditLog
```json
{
  "type": "object",
  "required": ["id", "timestamp", "user_id", "action", "resource"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Audit log identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Event timestamp"
    },
    "user_id": {
      "type": "string",
      "format": "uuid",
      "description": "User who performed the action"
    },
    "username": {
      "type": "string",
      "description": "Username"
    },
    "action": {
      "type": "string",
      "enum": ["create", "read", "update", "delete", "login", "logout", "terminate"],
      "description": "Action performed"
    },
    "resource": {
      "type": "string",
      "enum": ["user", "session", "node", "blockchain", "payout", "config", "system"],
      "description": "Resource affected"
    },
    "resource_id": {
      "type": "string",
      "description": "Resource identifier"
    },
    "details": {
      "type": "object",
      "description": "Additional action details"
    },
    "ip_address": {
      "type": "string",
      "format": "ipv4",
      "description": "Client IP address"
    },
    "user_agent": {
      "type": "string",
      "description": "Client user agent"
    },
    "severity": {
      "type": "string",
      "enum": ["info", "warning", "error", "critical"],
      "description": "Event severity"
    },
    "success": {
      "type": "boolean",
      "description": "Whether the action was successful"
    }
  }
}
```

#### AuditLogQuery
```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "description": "Filter by action type"
    },
    "user_id": {
      "type": "string",
      "format": "uuid",
      "description": "Filter by user ID"
    },
    "resource": {
      "type": "string",
      "description": "Filter by resource type"
    },
    "date_from": {
      "type": "string",
      "format": "date-time",
      "description": "Start date filter"
    },
    "date_to": {
      "type": "string",
      "format": "date-time",
      "description": "End date filter"
    },
    "severity": {
      "type": "string",
      "enum": ["info", "warning", "error", "critical"],
      "description": "Filter by severity"
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 1000,
      "default": 50,
      "description": "Number of results to return"
    },
    "offset": {
      "type": "integer",
      "minimum": 0,
      "default": 0,
      "description": "Pagination offset"
    }
  }
}
```

#### AuditLogExportRequest
```json
{
  "type": "object",
  "required": ["format", "date_from", "date_to"],
  "properties": {
    "format": {
      "type": "string",
      "enum": ["json", "csv", "pdf"],
      "description": "Export format"
    },
    "date_from": {
      "type": "string",
      "format": "date-time",
      "description": "Start date for export"
    },
    "date_to": {
      "type": "string",
      "format": "date-time",
      "description": "End date for export"
    },
    "filters": {
      "type": "object",
      "description": "Additional filters"
    }
  }
}
```

### Emergency Control Models

#### EmergencyAction
```json
{
  "type": "object",
  "required": ["action", "reason"],
  "properties": {
    "action": {
      "type": "string",
      "enum": ["stop_all_sessions", "system_lockdown", "disable_new_sessions", "enable_new_sessions"],
      "description": "Emergency action to perform"
    },
    "reason": {
      "type": "string",
      "maxLength": 255,
      "description": "Reason for emergency action"
    },
    "confirm": {
      "type": "boolean",
      "description": "Confirmation flag for critical actions"
    }
  }
}
```

### Error Models

#### ErrorResponse
```json
{
  "type": "object",
  "required": ["error"],
  "properties": {
    "error": {
      "$ref": "#/components/schemas/Error"
    }
  }
}
```

#### Error
```json
{
  "type": "object",
  "required": ["code", "message", "request_id", "timestamp"],
  "properties": {
    "code": {
      "type": "string",
      "pattern": "^LUCID_ADMIN_ERR_[0-9]{4}$",
      "description": "Error code"
    },
    "message": {
      "type": "string",
      "description": "Error message"
    },
    "details": {
      "type": "object",
      "description": "Additional error details"
    },
    "request_id": {
      "type": "string",
      "format": "uuid",
      "description": "Request identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Error timestamp"
    }
  }
}
```

### WebSocket Models

#### WebSocketMessage
```json
{
  "type": "object",
  "required": ["type", "data", "timestamp"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["metric_update", "system_alert", "session_change", "node_status_change", "blockchain_update"],
      "description": "Message type"
    },
    "data": {
      "type": "object",
      "description": "Message payload"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Message timestamp"
    }
  }
}
```

## MongoDB Collections

### admin_users
```javascript
{
  _id: ObjectId,
  username: String,
  email: String,
  password_hash: String,
  role: String, // "super-admin", "admin", "operator"
  permissions: [String],
  status: String, // "active", "suspended", "disabled"
  totp_secret: String,
  last_login: Date,
  created_at: Date,
  updated_at: Date
}
```

### admin_roles
```javascript
{
  _id: ObjectId,
  name: String,
  description: String,
  permissions: [String],
  is_system: Boolean,
  created_at: Date,
  updated_at: Date
}
```

### admin_audit_logs
```javascript
{
  _id: ObjectId,
  timestamp: Date,
  user_id: ObjectId,
  username: String,
  action: String,
  resource: String,
  resource_id: String,
  details: Object,
  ip_address: String,
  user_agent: String,
  severity: String, // "info", "warning", "error", "critical"
  success: Boolean
}
```

### system_config
```javascript
{
  _id: ObjectId,
  key: String,
  value: Mixed,
  description: String,
  updated_by: ObjectId,
  updated_at: Date
}
```

### emergency_logs
```javascript
{
  _id: ObjectId,
  action: String,
  reason: String,
  user_id: ObjectId,
  username: String,
  timestamp: Date,
  details: Object,
  status: String // "executed", "failed"
}
```

## Validation Rules

### Username Validation
- Minimum length: 3 characters
- Maximum length: 50 characters
- Allowed characters: a-z, A-Z, 0-9, _, -
- Must be unique

### Password Validation
- Minimum length: 8 characters
- Maximum length: 128 characters
- Must contain at least one uppercase letter
- Must contain at least one lowercase letter
- Must contain at least one number
- Must contain at least one special character

### Email Validation
- Must be valid email format
- Maximum length: 254 characters
- Must be unique

### Session ID Validation
- Must be valid UUID v4 format
- Must exist in sessions collection

### Node ID Validation
- Must be valid UUID v4 format
- Must exist in nodes collection

### Amount Validation
- Must be positive number
- Maximum 6 decimal places
- Minimum value: 0.000001
- Maximum value: 1000000.000000

### IP Address Validation
- Must be valid IPv4 or IPv6 format
- For IPv4: 0.0.0.0 to 255.255.255.255
- For IPv6: Full format validation

### Date Range Validation
- date_from must be before date_to
- Maximum range: 365 days
- Must be valid ISO 8601 format

### Pagination Validation
- limit: 1 to 1000 (default: 50)
- offset: 0 or positive integer
- Maximum total results: 10000

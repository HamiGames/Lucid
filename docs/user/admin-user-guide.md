# Lucid Admin User Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-ADMIN-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This comprehensive guide provides administrators with detailed instructions for managing the Lucid blockchain system. It covers user management, system configuration, monitoring, security, and maintenance procedures.

### Admin Interface Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Dashboard                          │
│  User Management + System Monitoring + Configuration       │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                User Management Layer                      │
│  Users + Roles + Permissions + Authentication + MFA        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                System Management Layer                   │
│  Services + Nodes + Network + Storage + Backup          │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Security & Monitoring Layer               │
│  Security + Logs + Alerts + Compliance + Audit            │
└─────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Admin Access

#### Initial Setup

```bash
# Access admin interface
https://admin.lucid.onion:8080

# Default admin credentials (change immediately)
Username: admin
Password: admin123

# First-time setup
1. Change default password
2. Enable MFA
3. Configure admin settings
4. Review security settings
```

#### Admin Authentication

```bash
# Login via API
curl -X POST https://admin.lucid.onion:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password",
    "mfa_code": "123456"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### Admin Dashboard

#### Dashboard Overview

The admin dashboard provides real-time system status and management capabilities:

```bash
# System status endpoint
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "system_status": "healthy",
  "services": {
    "api_gateway": "running",
    "blockchain_engine": "running",
    "auth_service": "running",
    "session_management": "running",
    "rdp_services": "running",
    "node_management": "running",
    "admin_interface": "running",
    "tron_payment": "running",
    "foundation_services": "running"
  },
  "metrics": {
    "total_users": 1250,
    "active_sessions": 45,
    "transactions_per_hour": 1200,
    "system_uptime": "99.9%"
  }
}
```

---

## User Management

### User Administration

#### Creating Users

```bash
# Create new user via API
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "secure_password",
    "roles": ["user"],
    "permissions": ["read:own", "write:own"],
    "mfa_enabled": true
  }'

# Response
{
  "user_id": "user_123456789",
  "username": "newuser",
  "email": "user@example.com",
  "roles": ["user"],
  "permissions": ["read:own", "write:own"],
  "mfa_enabled": true,
  "created_at": "2024-01-14T10:30:00Z",
  "status": "active"
}
```

#### User Roles and Permissions

```bash
# Available roles
{
  "admin": {
    "description": "Full system access",
    "permissions": [
      "read:all",
      "write:all",
      "delete:all",
      "admin:all"
    ]
  },
  "node_operator": {
    "description": "Node management access",
    "permissions": [
      "read:node",
      "write:node",
      "admin:node"
    ]
  },
  "user": {
    "description": "Standard user access",
    "permissions": [
      "read:own",
      "write:own"
    ]
  }
}

# Permission levels
{
  "read:all": "Read all system data",
  "write:all": "Modify all system data",
  "delete:all": "Delete any system data",
  "admin:all": "Full administrative access",
  "read:node": "Read node-specific data",
  "write:node": "Modify node-specific data",
  "admin:node": "Node administrative access",
  "read:own": "Read own data only",
  "write:own": "Modify own data only"
}
```

#### User Management Operations

```bash
# List all users
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/users \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific user
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update user
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "roles": ["user", "node_operator"],
    "permissions": ["read:own", "write:own", "read:node", "write:node"]
  }'

# Deactivate user
curl -X DELETE https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Reset user password
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789/reset-password \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "new_secure_password"
  }'
```

### Authentication Management

#### MFA Configuration

```bash
# Enable MFA for user
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789/mfa/enable \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "mfa_secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789/mfa/qr",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344",
    "44332211"
  ]
}

# Disable MFA for user
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789/mfa/disable \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Session Management

```bash
# List active sessions
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "sessions": [
    {
      "session_id": "sess_123456789",
      "user_id": "user_123456789",
      "username": "user1",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2024-01-14T10:30:00Z",
      "last_activity": "2024-01-14T11:45:00Z",
      "expires_at": "2024-01-14T18:30:00Z"
    }
  ],
  "total_sessions": 45
}

# Terminate specific session
curl -X DELETE https://admin.lucid.onion:8080/api/v1/admin/sessions/sess_123456789 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Terminate all user sessions
curl -X DELETE https://admin.lucid.onion:8080/api/v1/admin/users/user_123456789/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## System Management

### Service Management

#### Service Status

```bash
# Check all services
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/services \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "services": {
    "lucid-api-gateway": {
      "status": "running",
      "uptime": "7d 12h 30m",
      "cpu_usage": "15%",
      "memory_usage": "512MB",
      "port": 8080,
      "health_check": "healthy"
    },
    "lucid-blockchain-engine": {
      "status": "running",
      "uptime": "7d 12h 30m",
      "cpu_usage": "25%",
      "memory_usage": "1GB",
      "port": 8081,
      "health_check": "healthy"
    }
  }
}
```

#### Service Control

```bash
# Start service
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/services/lucid-api-gateway/start \
  -H "Authorization: Bearer YOUR_TOKEN"

# Stop service
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/services/lucid-api-gateway/stop \
  -H "Authorization: Bearer YOUR_TOKEN"

# Restart service
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/services/lucid-api-gateway/restart \
  -H "Authorization: Bearer YOUR_TOKEN"

# Scale service
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/services/lucid-api-gateway/scale \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "replicas": 3
  }'
```

### Node Management

#### Node Status

```bash
# List all nodes
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/nodes \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "nodes": [
    {
      "node_id": "node_123456789",
      "name": "lucid-node-1",
      "status": "online",
      "ip_address": "192.168.1.10",
      "port": 8080,
      "version": "1.0.0",
      "last_seen": "2024-01-14T11:45:00Z",
      "cpu_usage": "20%",
      "memory_usage": "2GB",
      "disk_usage": "45%"
    }
  ],
  "total_nodes": 5,
  "online_nodes": 4,
  "offline_nodes": 1
}
```

#### Node Operations

```bash
# Add new node
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/nodes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "lucid-node-6",
    "ip_address": "192.168.1.15",
    "port": 8080,
    "node_type": "full_node"
  }'

# Update node configuration
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/nodes/node_123456789 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "validator_node",
    "max_connections": 100
  }'

# Remove node
curl -X DELETE https://admin.lucid.onion:8080/api/v1/admin/nodes/node_123456789 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Network Management

#### Network Configuration

```bash
# Get network status
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/network \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "network_status": "healthy",
  "total_nodes": 5,
  "connected_nodes": 4,
  "network_latency": "15ms",
  "bandwidth_usage": "1.2GB/s",
  "protocol_version": "1.0.0"
}

# Update network configuration
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/network \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_connections": 1000,
    "sync_interval": 30,
    "consensus_timeout": 60
  }'
```

---

## Monitoring and Logging

### System Monitoring

#### Performance Metrics

```bash
# Get system metrics
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "system_metrics": {
    "cpu_usage": "25%",
    "memory_usage": "8GB",
    "disk_usage": "45%",
    "network_io": "1.2GB/s",
    "load_average": [1.2, 1.5, 1.8]
  },
  "application_metrics": {
    "requests_per_second": 150,
    "response_time": "50ms",
    "error_rate": "0.1%",
    "active_connections": 250
  },
  "blockchain_metrics": {
    "block_height": 125000,
    "transactions_per_second": 100,
    "pending_transactions": 50,
    "network_hashrate": "1.5TH/s"
  }
}
```

#### Health Checks

```bash
# Comprehensive health check
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/health \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "overall_status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "elasticsearch": "healthy",
    "blockchain": "healthy",
    "network": "healthy"
  },
  "timestamp": "2024-01-14T11:45:00Z"
}
```

### Log Management

#### Log Access

```bash
# Get system logs
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/logs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -G -d "service=api-gateway" -d "level=ERROR" -d "limit=100"

# Response
{
  "logs": [
    {
      "timestamp": "2024-01-14T11:45:00Z",
      "level": "ERROR",
      "service": "api-gateway",
      "message": "Database connection failed",
      "details": {
        "error": "Connection timeout",
        "retry_count": 3
      }
    }
  ],
  "total_logs": 1500
}

# Download log file
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/logs/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -G -d "service=api-gateway" -d "date=2024-01-14" \
  -o api-gateway-2024-01-14.log
```

#### Log Configuration

```bash
# Update log configuration
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/logs/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "log_level": "INFO",
    "retention_days": 30,
    "max_file_size": "100MB",
    "compression": true
  }'
```

---

## Security Management

### Security Configuration

#### Security Settings

```bash
# Get security configuration
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/security \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "security_settings": {
    "password_policy": {
      "min_length": 12,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true,
      "require_symbols": true,
      "max_age_days": 90
    },
    "session_settings": {
      "timeout_minutes": 30,
      "max_concurrent_sessions": 3,
      "require_mfa": true
    },
    "rate_limiting": {
      "requests_per_minute": 100,
      "login_attempts": 5,
      "lockout_duration_minutes": 30
    }
  }
}
```

#### Security Updates

```bash
# Update security settings
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/security \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password_policy": {
      "min_length": 16,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true,
      "require_symbols": true,
      "max_age_days": 60
    },
    "session_settings": {
      "timeout_minutes": 15,
      "max_concurrent_sessions": 2,
      "require_mfa": true
    }
  }'
```

### Audit and Compliance

#### Audit Logs

```bash
# Get audit logs
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/audit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -G -d "action=user_login" -d "user_id=user_123456789" -d "limit=50"

# Response
{
  "audit_logs": [
    {
      "timestamp": "2024-01-14T11:45:00Z",
      "user_id": "user_123456789",
      "username": "admin",
      "action": "user_login",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "result": "success",
      "details": {
        "mfa_used": true,
        "session_id": "sess_123456789"
      }
    }
  ],
  "total_logs": 2500
}
```

#### Compliance Reports

```bash
# Generate compliance report
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/compliance/report \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "security_audit",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-14"
    },
    "format": "pdf"
  }'

# Response
{
  "report_id": "report_123456789",
  "status": "generating",
  "download_url": "https://admin.lucid.onion:8080/api/v1/admin/compliance/reports/report_123456789/download"
}
```

---

## Backup and Recovery

### Backup Management

#### Backup Status

```bash
# Get backup status
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/backups \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "backup_status": "healthy",
  "last_backup": "2024-01-14T02:00:00Z",
  "next_backup": "2024-01-15T02:00:00Z",
  "backup_size": "2.5GB",
  "retention_days": 30,
  "backups": [
    {
      "backup_id": "backup_123456789",
      "timestamp": "2024-01-14T02:00:00Z",
      "size": "2.5GB",
      "status": "completed",
      "type": "full"
    }
  ]
}
```

#### Backup Operations

```bash
# Create manual backup
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/backups \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "full",
    "description": "Manual backup before system update"
  }'

# Restore from backup
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/backups/backup_123456789/restore \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirm": true,
    "restore_type": "full"
  }'
```

---

## System Configuration

### Configuration Management

#### System Settings

```bash
# Get system configuration
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/config \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "system_config": {
    "blockchain": {
      "block_time": 10,
      "max_transactions_per_block": 1000,
      "consensus_algorithm": "proof_of_stake"
    },
    "network": {
      "max_connections": 1000,
      "sync_interval": 30,
      "peer_discovery": true
    },
    "storage": {
      "max_disk_usage": "80%",
      "compression": true,
      "encryption": true
    }
  }
}
```

#### Configuration Updates

```bash
# Update system configuration
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "blockchain": {
      "block_time": 15,
      "max_transactions_per_block": 1500
    },
    "network": {
      "max_connections": 1500,
      "sync_interval": 20
    }
  }'
```

### Environment Management

#### Environment Variables

```bash
# Get environment variables
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/environment \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update environment variables
curl -X PUT https://admin.lucid.onion:8080/api/v1/admin/environment \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "LOG_LEVEL": "INFO",
    "MAX_CONNECTIONS": "1500",
    "BACKUP_RETENTION_DAYS": "30"
  }'
```

---

## Troubleshooting

### Common Issues

#### Service Issues

```bash
# Check service logs
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/services/lucid-api-gateway/logs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -G -d "level=ERROR" -d "limit=50"

# Restart problematic service
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/services/lucid-api-gateway/restart \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Database Issues

```bash
# Check database status
curl -X GET https://admin.lucid.onion:8080/api/v1/admin/database/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Repair database
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/database/repair \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Diagnostic Tools

#### System Diagnostics

```bash
# Run system diagnostics
curl -X POST https://admin.lucid.onion:8080/api/v1/admin/diagnostics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "diagnostics": {
    "system_health": "healthy",
    "issues_found": 0,
    "recommendations": [
      "Consider increasing memory allocation for blockchain service",
      "Monitor disk usage - currently at 75%"
    ],
    "performance_score": 85
  }
}
```

---

## Best Practices

### Security Best Practices

1. **Regular Security Updates**
   - Update system components monthly
   - Monitor security advisories
   - Apply patches promptly

2. **Access Control**
   - Use strong passwords
   - Enable MFA for all admin accounts
   - Regular access reviews

3. **Monitoring**
   - Monitor system logs daily
   - Set up security alerts
   - Regular security audits

### Operational Best Practices

1. **Backup Strategy**
   - Daily automated backups
   - Test restore procedures monthly
   - Offsite backup storage

2. **Performance Monitoring**
   - Monitor system metrics
   - Set performance thresholds
   - Proactive capacity planning

3. **Documentation**
   - Document all changes
   - Maintain runbooks
   - Regular documentation updates

---

## References

- [Node Operator Guide](./node-operator-guide.md)
- [Deployment Guide](../deployment/deployment-guide.md)
- [Troubleshooting Guide](../deployment/troubleshooting-guide.md)
- [Security Hardening Guide](../deployment/security-hardening-guide.md)
- [Master Build Plan](../../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14

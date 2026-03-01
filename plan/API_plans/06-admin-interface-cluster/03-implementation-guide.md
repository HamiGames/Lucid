# Admin Interface Cluster - Implementation Guide

## Code Structure

### Directory Layout
```
admin/
├── ui/
│   ├── admin_ui.py              # Main admin UI service
│   ├── templates/               # HTML templates
│   ├── static/                  # CSS, JS, images
│   └── components/              # UI components
├── system/
│   ├── admin_controller.py      # Backend admin logic
│   ├── rbac/                    # Role-based access control
│   │   ├── roles.py
│   │   ├── permissions.py
│   │   └── middleware.py
│   ├── audit/                   # Audit logging
│   │   ├── logger.py
│   │   └── events.py
│   └── emergency/               # Emergency controls
│       ├── controls.py
│       └── lockdown.py
├── api/
│   ├── auth.py                  # Authentication endpoints
│   ├── dashboard.py             # Dashboard APIs
│   ├── sessions.py              # Session management
│   ├── nodes.py                 # Node management
│   ├── blockchain.py            # Blockchain operations
│   ├── payouts.py               # Payout management
│   ├── users.py                 # User management
│   ├── config.py                # Configuration
│   ├── audit.py                 # Audit logs
│   └── emergency.py             # Emergency controls
└── models/
    ├── admin_user.py            # Admin user model
    ├── role.py                  # Role model
    ├── audit_log.py             # Audit log model
    └── system_config.py         # Configuration model
```

## Service Implementation

### 1. Admin UI Service (`admin_ui.py`)

```python
#!/usr/bin/env python3
"""
Admin UI Service - Web-based administrative dashboard
Port: 8096
Base Image: gcr.io/distroless/python3-debian12
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Service configuration
SERVICE_NAME = "lucid-admin-ui"
VERSION = "0.1.0"
PORT = 8096

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'admin-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)

class AdminUIService:
    def __init__(self):
        self.service_name = SERVICE_NAME
        self.version = VERSION
        self.port = PORT
        self.start_time = datetime.utcnow()
        
    async def get_dashboard_data(self) -> Dict:
        """Get real-time dashboard data"""
        try:
            # Fetch data from admin controller
            data = {
                'system_status': await self._get_system_status(),
                'active_sessions': await self._get_session_summary(),
                'node_status': await self._get_node_summary(),
                'blockchain_status': await self._get_blockchain_status(),
                'resource_usage': await self._get_resource_usage()
            }
            return data
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            raise
    
    async def _get_system_status(self) -> Dict:
        """Get system health status"""
        return {
            'status': 'healthy',
            'uptime': str(datetime.utcnow() - self.start_time),
            'version': self.version,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    # Additional helper methods...

# Routes
@app.route('/')
async def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/v1/admin/dashboard/overview')
async def dashboard_overview():
    """Get dashboard overview data"""
    try:
        admin_ui = AdminUIService()
        data = await admin_ui.get_dashboard_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Admin client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Admin client disconnected: {request.sid}")

@socketio.on('subscribe_metrics')
def handle_subscribe_metrics():
    """Subscribe to real-time metrics"""
    # Implementation for metric streaming
    pass

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
```

### 2. Admin Controller Service (`admin_controller.py`)

```python
#!/usr/bin/env python3
"""
Admin Controller Service - Backend administrative logic
Port: 8096 (internal)
Base Image: gcr.io/distroless/python3-debian12
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import uuid

# Service configuration
SERVICE_NAME = "lucid-admin-controller"
VERSION = "0.1.0"

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)

@dataclass
class AdminUser:
    id: str
    username: str
    role: str
    permissions: List[str]
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None

class AdminController:
    def __init__(self):
        self.service_name = SERVICE_NAME
        self.version = VERSION
        self.start_time = datetime.utcnow()
        self.admin_users: Dict[str, AdminUser] = {}
        self.audit_logs: List[Dict] = []
        
    async def authenticate_admin(self, username: str, password: str, totp_code: str) -> Optional[AdminUser]:
        """Authenticate admin user with TOTP"""
        try:
            # Implementation for admin authentication
            # Verify username/password and TOTP code
            user = self.admin_users.get(username)
            if user and self._verify_password(password) and self._verify_totp(totp_code):
                user.last_login = datetime.utcnow()
                await self._log_audit_event('login', user.id, 'admin', {'username': username})
                return user
            return None
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    async def get_session_list(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict:
        """Get list of active sessions"""
        try:
            # Fetch sessions from session management service
            sessions = await self._fetch_sessions(status, limit, offset)
            return {
                'sessions': sessions,
                'total': len(sessions),
                'limit': limit,
                'offset': offset
            }
        except Exception as e:
            logger.error(f"Failed to get session list: {e}")
            raise
    
    async def terminate_sessions(self, session_ids: List[str], reason: str, admin_user: AdminUser) -> Dict:
        """Terminate multiple sessions"""
        try:
            results = []
            for session_id in session_ids:
                success = await self._terminate_session(session_id, reason)
                results.append({
                    'session_id': session_id,
                    'success': success
                })
                await self._log_audit_event('terminate', admin_user.id, 'session', {
                    'session_id': session_id,
                    'reason': reason
                })
            
            return {
                'terminated': results,
                'total_attempted': len(session_ids),
                'successful': sum(1 for r in results if r['success'])
            }
        except Exception as e:
            logger.error(f"Failed to terminate sessions: {e}")
            raise
    
    async def get_audit_logs(self, filters: Dict, limit: int = 50, offset: int = 0) -> Dict:
        """Query audit logs"""
        try:
            # Apply filters and pagination
            filtered_logs = self._filter_audit_logs(filters)
            paginated_logs = filtered_logs[offset:offset + limit]
            
            return {
                'logs': paginated_logs,
                'total': len(filtered_logs),
                'limit': limit,
                'offset': offset
            }
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            raise
    
    async def emergency_stop_all_sessions(self, admin_user: AdminUser, reason: str) -> Dict:
        """Emergency stop all active sessions"""
        try:
            # Verify super-admin permissions
            if admin_user.role != 'super-admin':
                raise PermissionError("Emergency controls require super-admin role")
            
            # Stop all sessions
            result = await self._stop_all_sessions(reason)
            
            # Log emergency action
            await self._log_audit_event('emergency_stop', admin_user.id, 'system', {
                'reason': reason,
                'sessions_affected': result.get('total_sessions', 0)
            }, severity='critical')
            
            return result
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")
            raise
    
    async def _log_audit_event(self, action: str, user_id: str, resource: str, details: Dict, severity: str = 'info'):
        """Log audit event"""
        audit_event = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details,
            'severity': severity,
            'success': True
        }
        self.audit_logs.append(audit_event)
        logger.info(f"Audit event: {action} on {resource} by {user_id}")
    
    def _verify_password(self, password: str) -> bool:
        """Verify admin password"""
        # Implementation for password verification
        return True
    
    def _verify_totp(self, totp_code: str) -> bool:
        """Verify TOTP code"""
        # Implementation for TOTP verification
        return True
    
    def _filter_audit_logs(self, filters: Dict) -> List[Dict]:
        """Filter audit logs based on criteria"""
        # Implementation for log filtering
        return self.audit_logs

# Initialize controller
admin_controller = AdminController()
```

## RBAC Implementation

### Role-Based Access Control (`rbac/roles.py`)

```python
#!/usr/bin/env python3
"""
Role-Based Access Control for Admin Interface
"""

from enum import Enum
from typing import List, Dict
from dataclasses import dataclass

class Permission(Enum):
    # User management
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Session management
    SESSIONS_READ = "sessions:read"
    SESSIONS_TERMINATE = "sessions:terminate"
    SESSIONS_MANAGE = "sessions:manage"
    
    # Node management
    NODES_READ = "nodes:read"
    NODES_CONTROL = "nodes:control"
    
    # Blockchain operations
    BLOCKCHAIN_READ = "blockchain:read"
    BLOCKCHAIN_ANCHOR = "blockchain:anchor"
    
    # Payout management
    PAYOUTS_READ = "payouts:read"
    PAYOUTS_TRIGGER = "payouts:trigger"
    
    # System configuration
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    
    # Audit logs
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    
    # Emergency controls
    EMERGENCY_CONTROL = "emergency:control"

@dataclass
class Role:
    name: str
    description: str
    permissions: List[Permission]
    is_system: bool = False

# Predefined roles
ROLES = {
    'super-admin': Role(
        name='super-admin',
        description='Full system access',
        permissions=list(Permission),
        is_system=True
    ),
    'admin': Role(
        name='admin',
        description='Administrative access',
        permissions=[
            Permission.USERS_READ,
            Permission.SESSIONS_READ,
            Permission.SESSIONS_TERMINATE,
            Permission.NODES_READ,
            Permission.BLOCKCHAIN_READ,
            Permission.BLOCKCHAIN_ANCHOR,
            Permission.PAYOUTS_READ,
            Permission.PAYOUTS_TRIGGER,
            Permission.CONFIG_READ,
            Permission.AUDIT_READ
        ],
        is_system=True
    ),
    'operator': Role(
        name='operator',
        description='Monitoring and basic operations',
        permissions=[
            Permission.USERS_READ,
            Permission.SESSIONS_READ,
            Permission.NODES_READ,
            Permission.BLOCKCHAIN_READ,
            Permission.PAYOUTS_READ,
            Permission.CONFIG_READ,
            Permission.AUDIT_READ
        ],
        is_system=True
    )
}

class RBACManager:
    def __init__(self):
        self.roles = ROLES.copy()
    
    def get_role(self, role_name: str) -> Optional[Role]:
        """Get role by name"""
        return self.roles.get(role_name)
    
    def has_permission(self, user_role: str, permission: Permission) -> bool:
        """Check if user role has specific permission"""
        role = self.get_role(user_role)
        if not role:
            return False
        return permission in role.permissions
    
    def get_user_permissions(self, user_role: str) -> List[Permission]:
        """Get all permissions for user role"""
        role = self.get_role(user_role)
        return role.permissions if role else []
```

## Audit Logging Implementation

### Audit Logger (`audit/logger.py`)

```python
#!/usr/bin/env python3
"""
Audit Logging System for Admin Actions
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import uuid

class AuditSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    id: str
    timestamp: datetime
    user_id: str
    username: str
    action: str
    resource: str
    resource_id: Optional[str]
    details: Dict
    ip_address: str
    user_agent: str
    severity: AuditSeverity
    success: bool

class AuditLogger:
    def __init__(self, mongodb_client):
        self.mongodb = mongodb_client
        self.audit_collection = mongodb_client.admin_audit_logs
        self.logger = logging.getLogger('audit')
    
    async def log_event(self, event: AuditEvent):
        """Log audit event to database"""
        try:
            document = {
                '_id': event.id,
                'timestamp': event.timestamp,
                'user_id': event.user_id,
                'username': event.username,
                'action': event.action,
                'resource': event.resource,
                'resource_id': event.resource_id,
                'details': event.details,
                'ip_address': event.ip_address,
                'user_agent': event.user_agent,
                'severity': event.severity.value,
                'success': event.success
            }
            
            await self.audit_collection.insert_one(document)
            self.logger.info(f"Audit event logged: {event.action} on {event.resource}")
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            raise
    
    async def query_events(self, filters: Dict, limit: int = 50, offset: int = 0) -> Dict:
        """Query audit events with filters"""
        try:
            # Build MongoDB query
            query = {}
            
            if 'user_id' in filters:
                query['user_id'] = filters['user_id']
            if 'action' in filters:
                query['action'] = filters['action']
            if 'resource' in filters:
                query['resource'] = filters['resource']
            if 'severity' in filters:
                query['severity'] = filters['severity']
            if 'date_from' in filters and 'date_to' in filters:
                query['timestamp'] = {
                    '$gte': filters['date_from'],
                    '$lte': filters['date_to']
                }
            
            # Execute query with pagination
            cursor = self.audit_collection.find(query).skip(offset).limit(limit)
            events = await cursor.to_list(length=limit)
            total = await self.audit_collection.count_documents(query)
            
            return {
                'events': events,
                'total': total,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            self.logger.error(f"Failed to query audit events: {e}")
            raise
    
    async def export_events(self, filters: Dict, format: str) -> bytes:
        """Export audit events in specified format"""
        try:
            events_data = await self.query_events(filters, limit=10000)
            events = events_data['events']
            
            if format == 'json':
                import json
                return json.dumps(events, default=str).encode('utf-8')
            elif format == 'csv':
                import csv
                import io
                output = io.StringIO()
                if events:
                    writer = csv.DictWriter(output, fieldnames=events[0].keys())
                    writer.writeheader()
                    writer.writerows(events)
                return output.getvalue().encode('utf-8')
            elif format == 'pdf':
                # Implementation for PDF export
                pass
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Failed to export audit events: {e}")
            raise

# Global audit logger instance
audit_logger = None

async def init_audit_logger(mongodb_client):
    """Initialize global audit logger"""
    global audit_logger
    audit_logger = AuditLogger(mongodb_client)
```

## Docker Configuration

### Dockerfile
```dockerfile
# Admin Interface Cluster - Distroless Container
FROM gcr.io/distroless/python3-debian12

# Set working directory
WORKDIR /app

# Copy application code
COPY admin/ /app/admin/
COPY requirements.txt /app/

# Install dependencies (in build stage)
# Note: Distroless images don't have package managers
# Dependencies must be installed in multi-stage build

# Set environment variables
ENV PYTHONPATH=/app
ENV SERVICE_NAME=lucid-admin
ENV PORT=8096

# Expose port
EXPOSE 8096

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD ["python3", "-c", "import requests; requests.get('http://localhost:8096/admin/health')"]

# Run application
CMD ["python3", "/app/admin/ui/admin_ui.py"]
```

### Docker Compose Service
```yaml
services:
  lucid-admin:
    build:
      context: .
      dockerfile: admin/Dockerfile
    image: pickme/lucid:admin-latest
    container_name: lucid-admin
    hostname: lucid-admin
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-admin
      - VERSION=0.1.0
      - PORT=8096
      - MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
      - TOR_PROXY_URL=socks5://lucid-tor:9050
      
    ports:
      - "8096:8096"
      - "8097:8097"  # WebSocket port
      
    volumes:
      - admin_config:/app/config
      - admin_logs:/app/logs
      
    networks:
      - lucid-admin-net
      
    depends_on:
      - lucid_mongo
      - lucid-redis
      - lucid-tor
      
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
      
    security_opt:
      - no-new-privileges:true
      
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs

volumes:
  admin_config:
  admin_logs:

networks:
  lucid-admin-net:
    external: true
```

## Configuration Management

### Environment Configuration
```python
#!/usr/bin/env python3
"""
Admin Interface Configuration
"""

import os
from typing import Dict, Any

class AdminConfig:
    def __init__(self):
        # Service configuration
        self.SERVICE_NAME = os.getenv('SERVICE_NAME', 'lucid-admin')
        self.VERSION = os.getenv('VERSION', '0.1.0')
        self.PORT = int(os.getenv('PORT', '8096'))
        
        # Database configuration
        self.MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/lucid')
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Security configuration
        self.JWT_SECRET = os.getenv('JWT_SECRET', 'admin-secret-key')
        self.TOTP_ISSUER = os.getenv('TOTP_ISSUER', 'Lucid Admin')
        self.SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))
        
        # Tor configuration
        self.TOR_PROXY_URL = os.getenv('TOR_PROXY_URL', 'socks5://localhost:9050')
        self.USE_TOR = os.getenv('USE_TOR', 'true').lower() == 'true'
        
        # Rate limiting
        self.RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '1000'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
        
        # Audit logging
        self.AUDIT_LOG_RETENTION_DAYS = int(os.getenv('AUDIT_LOG_RETENTION_DAYS', '365'))
        self.AUDIT_LOG_BATCH_SIZE = int(os.getenv('AUDIT_LOG_BATCH_SIZE', '100'))
        
        # Emergency controls
        self.EMERGENCY_CONTROLS_ENABLED = os.getenv('EMERGENCY_CONTROLS_ENABLED', 'true').lower() == 'true'
        self.EMERGENCY_LOCKDOWN_DURATION = int(os.getenv('EMERGENCY_LOCKDOWN_DURATION', '3600'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'service_name': self.SERVICE_NAME,
            'version': self.VERSION,
            'port': self.PORT,
            'mongodb_url': self.MONGODB_URL,
            'redis_url': self.REDIS_URL,
            'session_timeout': self.SESSION_TIMEOUT,
            'use_tor': self.USE_TOR,
            'rate_limit_requests': self.RATE_LIMIT_REQUESTS,
            'rate_limit_window': self.RATE_LIMIT_WINDOW,
            'audit_log_retention_days': self.AUDIT_LOG_RETENTION_DAYS,
            'emergency_controls_enabled': self.EMERGENCY_CONTROLS_ENABLED
        }

# Global configuration instance
config = AdminConfig()
```

## Naming Conventions

### Consistent Naming Standards
- **Service Name**: `lucid-admin` (Python), `lucid-admin` (containers)
- **Container Image**: `pickme/lucid:admin-latest`
- **Network**: `lucid-admin-net`
- **Volume**: `admin_config`, `admin_logs`
- **Environment Variables**: `LUCID_ADMIN_*`

### File Naming
- **Python Files**: `snake_case.py`
- **Configuration Files**: `snake_case.yaml`
- **Template Files**: `kebab-case.html`
- **Static Assets**: `kebab-case.css`, `kebab-case.js`

### API Endpoints
- **Base Path**: `/api/v1/admin/`
- **Resource Paths**: `/admin/{resource}/`
- **Action Paths**: `/admin/{resource}/{action}/`
- **WebSocket Paths**: `/admin/ws/{channel}/`

## Error Handling

### Standardized Error Responses
```python
from enum import Enum

class AdminErrorCode(Enum):
    ADMIN_ACCESS_DENIED = "LUCID_ADMIN_ERR_1001"
    INVALID_ADMIN_TOKEN = "LUCID_ADMIN_ERR_1002"
    SESSION_NOT_FOUND = "LUCID_ADMIN_ERR_1003"
    NODE_UNAVAILABLE = "LUCID_ADMIN_ERR_1004"
    BLOCKCHAIN_SYNC_REQUIRED = "LUCID_ADMIN_ERR_1005"
    CONFIGURATION_INVALID = "LUCID_ADMIN_ERR_1006"
    AUDIT_LOG_QUERY_FAILED = "LUCID_ADMIN_ERR_1007"
    EMERGENCY_ACTION_FAILED = "LUCID_ADMIN_ERR_1008"

class AdminError(Exception):
    def __init__(self, code: AdminErrorCode, message: str, details: Dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict:
        return {
            'code': self.code.value,
            'message': self.message,
            'details': self.details,
            'timestamp': datetime.utcnow().isoformat()
        }
```

## Testing Strategy

### Unit Tests
```python
import pytest
from unittest.mock import AsyncMock, patch
from admin.system.admin_controller import AdminController
from admin.rbac.roles import RBACManager

@pytest.fixture
async def admin_controller():
    return AdminController()

@pytest.fixture
def rbac_manager():
    return RBACManager()

@pytest.mark.asyncio
async def test_admin_authentication(admin_controller):
    """Test admin authentication with valid credentials"""
    with patch.object(admin_controller, '_verify_password', return_value=True):
        with patch.object(admin_controller, '_verify_totp', return_value=True):
            user = await admin_controller.authenticate_admin('admin', 'password', '123456')
            assert user is not None
            assert user.username == 'admin'

@pytest.mark.asyncio
async def test_session_termination(admin_controller):
    """Test session termination functionality"""
    session_ids = ['session-1', 'session-2']
    admin_user = AdminUser(id='admin-1', username='admin', role='admin', permissions=[], status='active', created_at=datetime.utcnow())
    
    with patch.object(admin_controller, '_terminate_session', return_value=True):
        result = await admin_controller.terminate_sessions(session_ids, 'Test termination', admin_user)
        assert result['total_attempted'] == 2
        assert result['successful'] == 2

def test_rbac_permissions(rbac_manager):
    """Test RBAC permission checking"""
    assert rbac_manager.has_permission('admin', Permission.SESSIONS_READ) == True
    assert rbac_manager.has_permission('operator', Permission.USERS_CREATE) == False
    assert rbac_manager.has_permission('super-admin', Permission.EMERGENCY_CONTROL) == True
```

This implementation guide provides a comprehensive foundation for building the admin interface cluster with proper structure, security, and maintainability.

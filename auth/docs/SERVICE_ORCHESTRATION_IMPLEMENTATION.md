# Lucid Authentication Service - Service Orchestration Implementation

## Date: 2025-01-24

## Overview

Service orchestration capabilities have been **added** to the `lucid-auth-service` to enable spawning clone services (MongoDB instances for nodes) and managing service lifecycle.

## ⚠️ **SECURITY WARNING**

**Service orchestration is DISABLED by default** for security reasons. To enable:

1. Set environment variable: `ENABLE_SERVICE_ORCHESTRATION=true`
2. Mount Docker socket: `/var/run/docker.sock:/var/run/docker.sock:ro` (read-only recommended)
3. Grant additional capabilities (if needed): `cap_add: ["SYS_ADMIN"]` (security risk!)

## Created Modules

### 1. `auth/services/__init__.py`
- Package initialization for service orchestration modules

### 2. `auth/services/orchestrator.py`
- **ServiceOrchestrator** class for Docker container orchestration
- Methods:
  - `spawn_mongodb_clone()` - Spawn MongoDB clone instances
  - `stop_service()` - Stop spawned services
  - `remove_service()` - Remove spawned services
  - `get_service_status()` - Get service status
  - `list_spawned_services()` - List all spawned services
  - `cleanup_stopped_services()` - Cleanup stopped services

### 3. `auth/services/mongodb_clone.py`
- **MongoDBCloneManager** class for MongoDB clone management
- Methods:
  - `create_node_mongodb()` - Create MongoDB clone for a node
  - `get_node_mongodb()` - Get clone information
  - `list_node_clones()` - List all node clones
  - `remove_node_mongodb()` - Remove node clone
  - `health_check()` - Check clone health

### 4. `auth/api/orchestration_routes.py`
- HTTP API endpoints for service orchestration
- Endpoints:
  - `POST /orchestrate/mongodb/clone` - Spawn MongoDB clone
  - `GET /orchestrate/mongodb/clones` - List all clones
  - `GET /orchestrate/mongodb/clones/{node_id}` - Get clone info
  - `DELETE /orchestrate/mongodb/clones/{node_id}` - Remove clone
  - `GET /orchestrate/mongodb/clones/{node_id}/health` - Health check
  - `GET /orchestrate/services/spawned` - List spawned services
  - `GET /orchestrate/services/{service_id}/status` - Service status
  - `DELETE /orchestrate/services/{service_id}` - Remove service

### 5. `auth/config/orchestration-config.yaml`
- Configuration file for orchestration settings
- Resource limits, network settings, monitoring, audit logging

## Updated Modules

### 1. `auth/models/permissions.py`
**Added Permissions**:
- `SPAWN_SERVICES` - Spawn new service instances
- `MANAGE_MONGODB_INSTANCES` - Manage MongoDB instances and clones
- `ORCHESTRATE_CONTAINERS` - Orchestrate Docker containers
- `CLONE_SERVICES` - Clone existing services
- `MANAGE_SERVICE_LIFECYCLE` - Manage service lifecycle (start/stop/restart)
- `VIEW_SPAWNED_SERVICES` - View spawned service instances

### 2. `auth/permissions.py`
**Updated RBAC Permissions**:
- `ADMIN` role now includes:
  - `SPAWN_SERVICES`
  - `MANAGE_MONGODB_INSTANCES`
  - `CLONE_SERVICES`
  - `MANAGE_SERVICE_LIFECYCLE`
  - `VIEW_SPAWNED_SERVICES`
- `SUPER_ADMIN` role has all permissions (including orchestration)

### 3. `auth/api/__init__.py`
- Added `orchestration_router`
- Conditionally imports orchestration routes based on `ENABLE_SERVICE_ORCHESTRATION`

### 4. `auth/main.py`
- Conditionally includes orchestration router if enabled
- Added `import os` for environment variable checks

### 5. `auth/config/endpoints.yaml`
- Added orchestration endpoint group configuration
- All orchestration endpoints disabled by default

## MongoDB Connection Analysis

### Current MongoDB Connection (lucid-mongodb)

**Connection Details**:
- **Host**: `lucid-mongodb` (172.20.0.11)
- **Port**: `27017`
- **Database**: `lucid_auth`
- **Username**: `lucid`
- **Auth Source**: `admin`

**What lucid-auth-service CAN do**:
- ✅ Connect to MongoDB as client
- ✅ Read/write to `lucid_auth` database
- ✅ Create indexes on `lucid_auth` collections
- ✅ Execute `admin.command('ping')` for health checks
- ✅ Query user data, session data, audit logs

**What lucid-auth-service CANNOT do** (without orchestration):
- ❌ Create new MongoDB instances
- ❌ Clone MongoDB instances
- ❌ Manage MongoDB replica sets
- ❌ Access other databases (unless granted)

**What lucid-auth-service CAN do** (with orchestration enabled):
- ✅ Spawn MongoDB clone instances for nodes
- ✅ Configure node-specific MongoDB databases
- ✅ Manage MongoDB clone lifecycle
- ✅ Monitor MongoDB clone health

## Service Orchestration Capabilities

### ✅ **CAN Spawn Services** (when enabled)

1. **MongoDB Clone Instances**
   - Create MongoDB containers for nodes
   - Configure node-specific databases
   - Set up collections and indexes
   - Assign network and IP addresses

2. **Service Lifecycle Management**
   - Start/stop/restart services
   - Monitor service status
   - Cleanup stopped services
   - Track spawned services

3. **Resource Management**
   - Set memory limits
   - Set CPU limits
   - Network allocation
   - Port management

### ⚠️ **Security Constraints**

**Current Container Security** (from `docker-compose.foundation.yml`):
```yaml
user: "65532:65532"  # Non-root
cap_drop: ["ALL"]  # All capabilities dropped
read_only: true  # Read-only filesystem
```

**To Enable Orchestration** (requires security trade-offs):
```yaml
# Option 1: Mount Docker socket (read-only recommended)
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro

# Option 2: Use Docker API over HTTP (more secure)
environment:
  - DOCKER_HOST=tcp://docker-proxy:2375
```

## Usage

### Enable Service Orchestration

**1. Set Environment Variable**:
```bash
export ENABLE_SERVICE_ORCHESTRATION=true
```

**2. Update docker-compose.foundation.yml**:
```yaml
lucid-auth-service:
  environment:
    - ENABLE_SERVICE_ORCHESTRATION=true
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro  # Read-only Docker socket
```

**3. Install Docker Python Library** (if not already installed):
```bash
pip install docker
```

### API Usage

**Spawn MongoDB Clone for Node**:
```bash
curl -X POST http://localhost:8089/orchestrate/mongodb/clone \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node_123456",
    "node_tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
    "port": 27018,
    "network": "lucid-pi-network"
  }'
```

**List MongoDB Clones**:
```bash
curl -X GET http://localhost:8089/orchestrate/mongodb/clones \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Check Clone Health**:
```bash
curl -X GET http://localhost:8089/orchestrate/mongodb/clones/node_123456/health \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Remove MongoDB Clone**:
```bash
curl -X DELETE http://localhost:8089/orchestrate/mongodb/clones/node_123456 \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

## Required Dependencies

### Python Package
Add to `auth/requirements.txt`:
```
docker>=6.0.0  # Docker Python API client
```

### Docker Socket Access
- Mount Docker socket: `/var/run/docker.sock:/var/run/docker.sock:ro`
- Or use Docker API over HTTP: `DOCKER_HOST=tcp://docker-proxy:2375`

## RBAC Permissions

### Required Permissions

**To Spawn Services**:
- `SPAWN_SERVICES` - Required for spawning any service
- `MANAGE_MONGODB_INSTANCES` - Required for MongoDB clones
- `CLONE_SERVICES` - Required for cloning services

**To View Services**:
- `VIEW_SPAWNED_SERVICES` - Required to view spawned services

**To Manage Services**:
- `MANAGE_SERVICE_LIFECYCLE` - Required to stop/remove services

### Role Assignments

- **ADMIN**: Has all orchestration permissions
- **SUPER_ADMIN**: Has all permissions (including orchestration)
- **NODE_OPERATOR**: Cannot spawn services (can request via API)
- **USER**: Cannot access orchestration endpoints

## Configuration

### Environment Variables

```bash
# Enable service orchestration
ENABLE_SERVICE_ORCHESTRATION=true

# Docker socket path (default: /var/run/docker.sock)
DOCKER_HOST=unix:///var/run/docker.sock

# Or use HTTP Docker API (more secure)
DOCKER_HOST=tcp://docker-proxy:2375
```

### Configuration File

`auth/config/orchestration-config.yaml`:
- Resource limits
- Network settings
- Port allocation
- Monitoring configuration
- Audit logging

## Security Considerations

### ⚠️ **CRITICAL SECURITY RISKS**

1. **Docker Socket Access**
   - Access to Docker socket = root-level access
   - Can spawn/stop any container
   - Potential for container escape
   - **Recommendation**: Use read-only socket mount

2. **Privilege Escalation**
   - Container needs elevated privileges
   - Distroless security model compromised
   - **Recommendation**: Use separate orchestration service

3. **Resource Exhaustion**
   - Unlimited spawns could exhaust resources
   - **Mitigation**: Rate limiting and resource limits configured

### ✅ **Security Mitigations**

1. **Disabled by Default**
   - Orchestration disabled unless explicitly enabled
   - Requires environment variable

2. **RBAC Protection**
   - Only ADMIN/SUPER_ADMIN can spawn services
   - All operations require authentication
   - Permission checks on all endpoints

3. **Audit Logging**
   - All orchestration operations logged
   - 90-day retention
   - Track who spawned what

4. **Resource Limits**
   - Default limits on spawned services
   - Maximum concurrent spawns
   - Rate limiting per user

## Testing

### Test Orchestration (when enabled)

```bash
# 1. Check if orchestration is enabled
curl http://localhost:8089/orchestrate/mongodb/clones

# 2. Spawn a test MongoDB clone
curl -X POST http://localhost:8089/orchestrate/mongodb/clone \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"node_id": "test_node", "node_tron_address": "T..."}'

# 3. Check clone health
curl http://localhost:8089/orchestrate/mongodb/clones/test_node/health \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# 4. Remove clone
curl -X DELETE http://localhost:8089/orchestrate/mongodb/clones/test_node \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

## Current Status

**✅ Modules Created**
- Service orchestrator
- MongoDB clone manager
- Orchestration API routes
- Configuration files

**✅ Permissions Added**
- Service orchestration permissions
- RBAC role assignments

**⚠️ Security**
- Disabled by default
- Requires explicit enablement
- RBAC protection
- Audit logging

**❌ Not Enabled**
- Orchestration disabled by default
- Requires `ENABLE_SERVICE_ORCHESTRATION=true`
- Requires Docker socket access
- Requires `docker` Python package

## Next Steps

1. **Decision**: Enable orchestration in auth service or use separate service?
2. **If Enabled**: 
   - Add `docker` to requirements.txt
   - Update docker-compose to mount Docker socket
   - Test orchestration endpoints
3. **If Separate Service**: 
   - Create dedicated orchestration service
   - Auth service delegates requests
   - Better security model

## Files Created

1. ✅ `auth/services/__init__.py`
2. ✅ `auth/services/orchestrator.py`
3. ✅ `auth/services/mongodb_clone.py`
4. ✅ `auth/api/orchestration_routes.py`
5. ✅ `auth/config/orchestration-config.yaml`
6. ✅ `auth/SERVICE_ORCHESTRATION_ANALYSIS.md`
7. ✅ `auth/SERVICE_ORCHESTRATION_IMPLEMENTATION.md`

## Files Modified

1. ✅ `auth/models/permissions.py` - Added orchestration permissions
2. ✅ `auth/permissions.py` - Added orchestration to ADMIN role
3. ✅ `auth/api/__init__.py` - Added orchestration router
4. ✅ `auth/main.py` - Conditionally include orchestration router
5. ✅ `auth/config/endpoints.yaml` - Added orchestration endpoints


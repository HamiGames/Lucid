# Lucid Admin Interface Service

## Overview

The Lucid Admin Interface Service provides comprehensive administrative control over the Lucid RDP system. It implements role-based access control (RBAC), system monitoring, session control, node management, blockchain operations, emergency controls, and audit logging.

**Service Name**: `lucid-admin-interface`  
**Cluster ID**: Phase 4 Support Services  
**Port**: 8083  
**Phase**: Phase 4 Support Services  
**Status**: Production Ready ✅

---

## Features

### Core Administration
- ✅ **Role-Based Access Control (RBAC)** - 4-tier role system (USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN)
- ✅ **System Monitoring** - Real-time system health and metrics
- ✅ **Session Management** - View, control, and terminate user sessions
- ✅ **Node Management** - Monitor and manage blockchain nodes
- ✅ **Blockchain Operations** - View and manage blockchain state
- ✅ **Emergency Controls** - Critical system emergency controls
- ✅ **Audit Logging** - Comprehensive administrative action logging

### Security Features
- ✅ **Authentication Required** - All endpoints require valid JWT token
- ✅ **RBAC Enforcement** - Permission-based access control
- ✅ **Audit Trail** - Complete audit log of all administrative actions
- ✅ **Input Validation** - Comprehensive validation of all inputs
- ✅ **Rate Limiting** - Protection against abuse

### Infrastructure
- ✅ **Distroless Container** - Minimal attack surface with no shell access
- ✅ **Multi-Stage Build** - Optimized container build
- ✅ **Health Checks** - Built-in health monitoring endpoints
- ✅ **Stateless Design** - Horizontal scaling support

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MongoDB 7.0+
- Redis 7.0+
- Python 3.11+ (for local development)
- Active authentication service (Cluster 09)

### Using Docker Compose (Recommended)

```bash
# 1. Navigate to admin directory
cd Lucid/admin

# 2. Copy environment template
cp env.example .env

# 3. Configure environment variables
# Set AUTH_SERVICE_URL to your authentication service URL
# Set MONGODB_URI and REDIS_URI

# 4. Start services
docker-compose up -d

# 5. Verify health
curl http://localhost:8083/admin/health
```

### Using Docker

```bash
# Build container
docker build -t lucid-admin-interface:latest .

# Run container
docker run -d \
  --name lucid-admin-interface \
  --network lucid-network \
  -p 8083:8083 \
  -e AUTH_SERVICE_URL=http://lucid-auth-service:8089 \
  -e MONGODB_URI=mongodb://mongodb:27017/lucid_admin \
  -e REDIS_URI=redis://redis:6379/2 \
  lucid-admin-interface:latest

# Check logs
docker logs lucid-admin-interface
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export AUTH_SERVICE_URL=http://localhost:8089
export MONGODB_URI=mongodb://localhost:27017/lucid_admin
export REDIS_URI=redis://localhost:6379/2

# 4. Run service
python -m admin.main

# Or with uvicorn
uvicorn admin.main:app --host 0.0.0.0 --port 8083 --reload
```

---

## API Endpoints

### Dashboard Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/dashboard` | Get system dashboard data | Admin Token |
| GET | `/admin/dashboard/metrics` | Get system metrics | Admin Token |
| GET | `/admin/dashboard/stats` | Get system statistics | Admin Token |

### User Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/users` | List all users | Admin Token |
| GET | `/admin/users/{user_id}` | Get user details | Admin Token |
| PUT | `/admin/users/{user_id}` | Update user | Admin Token |
| DELETE | `/admin/users/{user_id}` | Delete user | Super Admin Token |

### Session Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/sessions` | List all sessions | Admin Token |
| GET | `/admin/sessions/{session_id}` | Get session details | Admin Token |
| POST | `/admin/sessions/{session_id}/terminate` | Terminate session | Admin Token |

### Blockchain Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/blockchain/status` | Get blockchain status | Admin Token |
| GET | `/admin/blockchain/blocks` | List recent blocks | Admin Token |
| GET | `/admin/blockchain/transactions` | List recent transactions | Admin Token |

### Node Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/nodes` | List all nodes | Admin Token |
| GET | `/admin/nodes/{node_id}` | Get node details | Admin Token |
| POST | `/admin/nodes/{node_id}/ban` | Ban node | Admin Token |

### Audit Log Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/audit/logs` | List audit logs | Admin Token |
| GET | `/admin/audit/logs/{log_id}` | Get audit log details | Admin Token |

### Emergency Control Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/admin/emergency/shutdown` | Emergency shutdown | Super Admin Token |
| POST | `/admin/emergency/maintenance` | Enable maintenance mode | Admin Token |

### Health & Meta Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/admin/health` | Service health check | None |
| GET | `/admin/metrics` | Prometheus metrics | None |

---

## Configuration

### Environment Variables

Key configuration variables:

**Required:**
- `AUTH_SERVICE_URL` - Authentication service URL
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URI` - Redis connection string

**Optional but Recommended:**
- `SERVICE_NAME` - Service name (default: lucid-admin-interface)
- `SERVICE_PORT` - Service port (default: 8083)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENABLE_RBAC` - Enable RBAC enforcement (default: true)
- `AUDIT_LOG_ENABLED` - Enable audit logging (default: true)

---

## Architecture

### Components

- **Admin Controller** - Core administrative logic
- **RBAC Manager** - Role-based access control enforcement
- **Emergency Controller** - Emergency control mechanisms
- **Audit Logger** - Comprehensive audit logging
- **Dashboard API** - System dashboard data
- **User Management API** - User management endpoints
- **Session Management API** - Session control endpoints
- **Blockchain API** - Blockchain management endpoints
- **Node Management API** - Node monitoring endpoints

### Security Model

The service implements a comprehensive security model:
- JWT-based authentication (validated against auth service)
- Role-based access control (RBAC)
- Permission-based endpoint access
- Comprehensive audit logging
- Input validation and sanitization

---

## Development

### Project Structure

```
admin/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── api/                 # API endpoints
│   ├── dashboard.py     # Dashboard endpoints
│   ├── users.py         # User management endpoints
│   ├── sessions.py      # Session management endpoints
│   ├── blockchain.py    # Blockchain endpoints
│   ├── nodes.py         # Node management endpoints
│   ├── audit.py         # Audit log endpoints
│   └── emergency.py     # Emergency control endpoints
├── system/              # System components
│   └── admin_controller.py  # Admin controller
├── rbac/                # RBAC implementation
│   └── manager.py       # RBAC manager
├── audit/               # Audit logging
│   └── logger.py        # Audit logger
├── emergency/           # Emergency controls
│   └── controls.py      # Emergency controller
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Building the Container

```bash
# Build using distroless base image
docker build -t lucid-admin-interface:latest .

# Build for specific platform
docker buildx build --platform linux/arm64 -t lucid-admin-interface:latest .
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=admin --cov-report=html
```

---

## Deployment

### Production Deployment

Deploy using Docker Compose or Kubernetes:

```yaml
# docker-compose.yml
services:
  admin-interface:
    image: lucid-admin-interface:latest
    ports:
      - "8083:8083"
    environment:
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - MONGODB_URI=mongodb://mongodb:27017/lucid_admin
      - REDIS_URI=redis://redis:6379/2
    networks:
      - lucid-network
```

---

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8083/admin/health

# Expected response
{
  "status": "healthy",
  "service": "lucid-admin-interface",
  "version": "1.0.0"
}
```

### Metrics

Prometheus metrics available at `/admin/metrics`:
- Request counts
- Response times
- Error rates
- Active connections

---

## Troubleshooting

### Common Issues

**Service won't start:**
- Check authentication service is running
- Verify MongoDB and Redis connections
- Check environment variables

**Permission denied errors:**
- Verify JWT token is valid
- Check user role has required permissions
- Review RBAC configuration

**Database connection errors:**
- Verify MongoDB URI is correct
- Check network connectivity
- Review MongoDB logs

---

## License

Proprietary - Lucid RDP Development Team

---

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: dev@lucid-rdp.onion
- Documentation: [link]

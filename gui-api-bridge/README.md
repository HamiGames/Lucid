# GUI API Bridge Service

## Overview

The **GUI API Bridge Service** (`gui-api-bridge`) is a FastAPI-based service that bridges the Electron GUI application with Lucid's backend services. It provides API routing, authentication, rate limiting, and specialized session token recovery functionality through blockchain integration.

**Service Name**: `lucid-gui-api-bridge`  
**Port**: `8102`  
**Platform**: ARM64 (Raspberry Pi) / AMD64 (Development)  
**Image**: `pickme/lucid-gui-api-bridge:latest-arm64`  

## Architecture

### Core Components

1. **Main FastAPI Application** (`main.py`)
   - FastAPI server with lifespan management
   - CORS configuration for Electron apps
   - Exception handling and error responses
   - Health check endpoint

2. **Configuration Management** (`config.py`)
   - Pydantic v2 Settings for environment validation
   - URL validation (no localhost allowed in production)
   - Service URL configuration
   - JWT and security settings

3. **Integration Layer** (`integration/`)
   - Service base client with retry logic
   - Backend service clients for each microservice
   - Integration manager for centralized client management
   - **BlockchainEngineClient** for session token recovery

4. **Middleware** (`middleware/`)
   - Authentication middleware (JWT validation)
   - Rate limiting middleware
   - CORS middleware
   - Structured logging middleware

5. **Routers** (`routers/`)
   - User API routes (`/api/v1/user`)
   - Developer API routes (`/api/v1/developer`)
   - Node operator routes (`/api/v1/node`)
   - Admin API routes (`/api/v1/admin`)
   - WebSocket endpoint (`/ws`)

6. **Services** (`services/`)
   - Routing service for API request routing
   - Service discovery for backend services
   - WebSocket service for real-time communication

7. **Health Check** (`healthcheck.py`)
   - Backend service connectivity checks
   - Overall service health status
   - Service status aggregation

## Directory Structure

```
gui-api-bridge/
├── Dockerfile.gui-api-bridge          # Multi-stage distroless Dockerfile
├── requirements.txt                    # Python dependencies
└── gui-api-bridge/
    ├── __init__.py                    # Package initialization
    ├── entrypoint.py                  # Container entrypoint
    ├── main.py                        # FastAPI application
    ├── config.py                      # Configuration management
    ├── gui_api_bridge_service.py     # (Future) Main service logic
    ├── healthcheck.py                 # Health check service
    ├── config/
    │   └── env.gui-api-bridge.template # Environment variables template
    ├── middleware/
    │   ├── __init__.py
    │   ├── auth.py                    # JWT authentication
    │   ├── rate_limit.py             # Rate limiting
    │   ├── cors.py                    # CORS (handled by FastAPI)
    │   └── logging.py                # Request/response logging
    ├── routers/
    │   ├── __init__.py
    │   ├── user.py                   # User API routes
    │   ├── developer.py              # Developer API routes
    │   ├── node.py                   # Node operator routes
    │   ├── admin.py                  # Admin API routes
    │   └── websocket.py              # WebSocket routes
    ├── services/
    │   ├── __init__.py
    │   ├── routing_service.py        # API routing logic
    │   ├── discovery_service.py      # Service discovery
    │   └── websocket_service.py      # WebSocket management
    ├── integration/
    │   ├── __init__.py
    │   ├── service_base.py           # Base service client
    │   ├── integration_manager.py    # Integration manager
    │   ├── api_gateway_client.py     # API Gateway client
    │   ├── blockchain_client.py      # Blockchain Engine client
    │   ├── auth_service_client.py    # Auth Service client
    │   ├── session_api_client.py     # Session API client
    │   ├── node_management_client.py # Node Management client
    │   ├── admin_interface_client.py # Admin Interface client
    │   └── tron_client.py            # TRON Payment client
    ├── models/
    │   ├── __init__.py
    │   ├── common.py                 # Common models
    │   ├── auth.py                   # Auth models
    │   └── routing.py                # Routing models
    └── utils/
        ├── __init__.py
        ├── logging.py                # Logging utilities
        ├── errors.py                 # Error handling
        └── validation.py             # URL/data validation
```

## Backend Services

The service integrates with the following backend microservices:

| Service | URL | Port | Purpose |
|---------|-----|------|---------|
| API Gateway | `http://lucid-api-gateway:8080` | 8080 | Central API gateway |
| Blockchain Engine | `http://lucid-blockchain-engine:8084` | 8084 | Session anchoring & token recovery |
| Auth Service | `http://lucid-auth-service:8089` | 8089 | Authentication |
| Session API | `http://lucid-session-api:8113` | 8113 | Session management |
| Node Management | `http://lucid-node-management:8095` | 8095 | Node operations |
| Admin Interface | `http://lucid-admin-interface:8083` | 8083 | Admin operations |
| TRON Payment | `http://lucid-tron-client:8091` | 8091 | Payment processing |

## API Endpoints

### Health Check

```
GET /health
```
Returns service health and backend service status.

### User API (`/api/v1/user`)

- `GET /profile` - Get user profile
- `GET /sessions` - List user sessions
- `POST /sessions/{session_id}/recover` - **Recover session token from blockchain**

### Developer API (`/api/v1/developer`)

- `GET /status` - Get developer status
- `POST /sessions/{session_id}/recover` - **Recover session token from blockchain**

### Node API (`/api/v1/node`)

- `GET /status` - Get node operator status
- `GET /earnings` - Get earnings information

### Admin API (`/api/v1/admin`)

- `GET /status` - Get admin status
- `GET /services` - List backend services
- `POST /sessions/{session_id}/recover` - **Recover session token from blockchain (admin override)**

### WebSocket

```
WebSocket /ws
```
Real-time bidirectional communication with the GUI.

## Session Token Recovery

### Feature Overview

Session token recovery enables users to recover lost session tokens by querying blockchain anchors stored on the On-System Data Chain.

### Recovery Flow

```
1. Client requests session recovery with session_id and owner_address
2. GUI API Bridge validates JWT authentication
3. Calls BlockchainEngineClient to retrieve session anchor
4. Verifies anchor integrity using merkle root
5. Extracts and returns recovered token
```

### Recovery Endpoints

**User:**
```
POST /api/v1/user/sessions/{session_id}/recover
Content-Type: application/json

{
  "owner_address": "0x..."
}
```

**Developer:**
```
POST /api/v1/developer/sessions/{session_id}/recover
Content-Type: application/json

{
  "owner_address": "0x..."
}
```

**Admin:**
```
POST /api/v1/admin/sessions/{session_id}/recover
Content-Type: application/json

{
  "owner_address": "0x..."
}
```

### Response

```json
{
  "status": "success",
  "session_id": "session-uuid",
  "token": "recovered-session-token"
}
```

## Configuration

### Environment Variables

**Service Configuration:**
```
SERVICE_NAME=gui-api-bridge
SERVICE_VERSION=1.0.0
PORT=8102
HOST=0.0.0.0
SERVICE_URL=http://lucid-gui-api-bridge:8102
```

**Database:**
```
MONGODB_URL=mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
```

**Backend Services:**
```
API_GATEWAY_URL=http://lucid-api-gateway:8080
BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
AUTH_SERVICE_URL=http://lucid-auth-service:8089
SESSION_API_URL=http://lucid-session-api:8113
NODE_MANAGEMENT_URL=http://lucid-node-management:8095
ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
TRON_PAYMENT_URL=http://lucid-tron-client:8091
```

**Security:**
```
JWT_SECRET_KEY={JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRY_SECONDS=900
```

**CORS:**
```
CORS_ORIGINS=http://localhost:*,https://localhost:*,file://*
```

### Template

See `gui-api-bridge/gui-api-bridge/config/env.gui-api-bridge.template` for all available variables.

## Running the Service

### Docker

```bash
# Build image
docker build -f gui-api-bridge/Dockerfile.gui-api-bridge -t lucid-gui-api-bridge:latest-arm64 .

# Run container
docker run -p 8102:8102 \
  --env-file configs/environment/.env.secrets \
  --env-file configs/environment/.env.gui \
  lucid-gui-api-bridge:latest-arm64
```

### Docker Compose

```bash
docker-compose -f configs/docker/docker-compose.gui-integration.yml up lucid-gui-api-bridge
```

### Local Development

```bash
# Install dependencies
pip install -r gui-api-bridge/requirements.txt

# Run server
python -m uvicorn gui_api_bridge.main:app --host 0.0.0.0 --port 8102
```

## Middleware Pipeline

Requests flow through the following middleware in order:

1. **Logging Middleware** - Logs all requests and responses
2. **Auth Middleware** - Validates JWT token
3. **Rate Limit Middleware** - Applies rate limiting
4. **CORS Middleware** - Handles CORS headers
5. **Router Handler** - Routes to appropriate endpoint

## Integration with Blockchain Engine

### BlockchainEngineClient Methods

**Session Recovery:**
```python
token = await client.recover_session_token(session_id, owner_address)
```

**Anchor Verification:**
```python
is_valid = await client.verify_session_anchor(session_id, merkle_root)
```

**Get Session Anchor:**
```python
anchor = await client.get_session_anchor(session_id)
```

**Get Session Status:**
```python
status = await client.get_session_status(session_id)
```

## Error Handling

All endpoints return structured error responses:

```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE",
  "details": {}
}
```

### Common Errors

| Code | Status | Description |
|------|--------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT token |
| `FORBIDDEN` | 403 | User lacks required permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `SERVICE_UNAVAILABLE` | 503 | Backend service unreachable |

## Security

### Authentication

- JWT-based authentication using HS256
- Tokens validated in auth middleware
- Public endpoints: `/health`, `/`, `/api/v1`

### Authorization

- Role-based access control (RBAC)
- Roles: `user`, `developer`, `node_operator`, `admin`
- Role validation in routers and middleware

### CORS

- Configured for Electron apps
- Allows file:// protocol for local apps
- Allows localhost on any port for development

### URL Validation

- Service URLs validated at startup
- No localhost/127.0.0.1 URLs in production
- Invalid URLs cause startup failure

## Performance

### Rate Limiting

- Default: 100 requests/minute
- By role: Different limits per user role
- Redis-based distributed rate limiting

### Caching

- Redis-based response caching
- Default TTL: 300 seconds
- Cache headers: X-Cache-Hit, X-Cache-TTL

### Connection Pooling

- Async HTTP client with pooling
- Max connections: 100
- Connection timeout: 30 seconds

## Monitoring

### Health Checks

- Service-level health check: `/health`
- Includes backend service status
- Includes uptime and timestamp

### Logging

- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging with duration

### Metrics

- Prometheus-compatible metrics endpoint (future)
- Request count and latency
- Backend service response times

## Development

### Project Structure

- **config.py** - Configuration management
- **main.py** - FastAPI application setup
- **integration/** - Backend service clients
- **routers/** - API endpoints
- **middleware/** - Request processing
- **services/** - Business logic
- **models/** - Data models
- **utils/** - Helper utilities

### Adding New Endpoints

1. Create route in appropriate router file
2. Define request/response models
3. Implement endpoint handler
4. Add to router in main.py
5. Test with authentication

### Adding New Backend Service

1. Create client file in `integration/`
2. Extend `ServiceBaseClient`
3. Add to `IntegrationManager`
4. Update health check service
5. Add to configuration

## Docker Compose Integration

The service is part of the GUI integration stack:

```yaml
services:
  gui-api-bridge:
    image: pickme/lucid-gui-api-bridge:latest-arm64
    container_name: lucid-gui-api-bridge
    ports:
      - "8102:8102"
    depends_on:
      lucid-api-gateway:
        condition: service_healthy
```

## Troubleshooting

### Service fails to start

1. Check environment variables are set
2. Verify all backend services are running
3. Check MongoDB and Redis connectivity
4. Review logs: `docker logs lucid-gui-api-bridge`

### Backend service errors

1. Check service health: `curl http://service:port/health`
2. Verify network connectivity between services
3. Check service logs for error details
4. Verify environment variables

### JWT/Authentication errors

1. Check JWT_SECRET_KEY is correctly set
2. Verify token format: `Bearer <token>`
3. Check token expiration
4. Review auth middleware logs

## Future Enhancements

- [ ] Prometheus metrics export
- [ ] Advanced caching strategies
- [ ] Request/response transformation
- [ ] GraphQL API endpoint
- [ ] Advanced rate limiting (per-endpoint)
- [ ] API versioning strategy
- [ ] WebSocket authentication
- [ ] Request signing verification

## References

- **Dockerfile Pattern**: `build/docs/dockerfile-design.md`
- **Config Pattern**: `build/docs/container-design.md`
- **Integration Pattern**: `sessions/pipeline/integration/`
- **Blockchain Engine**: `blockchain/core/blockchain_engine.py`
- **Session Recovery**: `blockchain/blockchain_anchor.py`
- **Docker Compose**: `configs/docker/docker-compose.gui-integration.yml`
- **Service Config**: `configs/services/gui-api-bridge.yml`

## License

Part of the Lucid Project - See main README for details.

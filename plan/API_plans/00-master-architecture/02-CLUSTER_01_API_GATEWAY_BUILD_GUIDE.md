# Cluster 01: API Gateway - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 01-API-GATEWAY |
| Build Phase | Phase 2 (Weeks 3-4) |
| Parallel Track | Track B |
| Version | 1.0.0 |
| Last Updated | 2025-01-14 |

---

## Cluster Overview

### Service Information

| Attribute | Value |
|-----------|-------|
| Cluster Name | API Gateway Cluster |
| Primary Port | 8080 (HTTP), 8081 (HTTPS) |
| Service Type | Core infrastructure - Request routing and authentication |
| Container Base | `gcr.io/distroless/python3-debian12` |
| Language | Python 3.11+ (FastAPI) |

### Responsibilities

- Central API gateway for all external requests
- Request routing to backend services
- Authentication and authorization middleware
- Rate limiting and throttling
- CORS handling
- Request/response logging
- Backend service proxy

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| Cluster 09 (Authentication) | Critical | User authentication, JWT validation |
| Cluster 08 (Storage-Database) | Critical | Session storage, user data |
| Cluster 10 (Cross-Cluster) | Integration | Service discovery |

---

## MVP Files List

### Priority 1: Core Application (15 files, ~2,500 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 1 | `api-gateway/main.py` | 150 | FastAPI application entry point | FastAPI, uvicorn |
| 2 | `api-gateway/config.py` | 200 | Configuration management | pydantic, os, dotenv |
| 3 | `api-gateway/app/__init__.py` | 50 | Package initialization | - |
| 4 | `api-gateway/app/routes.py` | 300 | Route aggregation and mounting | FastAPI |
| 5 | `api-gateway/middleware/__init__.py` | 30 | Middleware package init | - |
| 6 | `api-gateway/middleware/auth.py` | 250 | Authentication middleware | PyJWT, aiohttp |
| 7 | `api-gateway/middleware/rate_limit.py` | 200 | Rate limiting middleware | Redis, asyncio |
| 8 | `api-gateway/middleware/cors.py` | 100 | CORS middleware | FastAPI |
| 9 | `api-gateway/middleware/logging.py` | 180 | Request/response logging | logging, structlog |
| 10 | `api-gateway/models/__init__.py` | 30 | Models package init | - |
| 11 | `api-gateway/models/common.py` | 150 | Common data models | Pydantic |
| 12 | `api-gateway/models/user.py` | 200 | User models | Pydantic |
| 13 | `api-gateway/models/session.py` | 180 | Session models | Pydantic |
| 14 | `api-gateway/models/auth.py` | 220 | Authentication models | Pydantic |
| 15 | `api-gateway/utils/security.py` | 260 | Security utilities | cryptography, hashlib |

**Subtotal**: 2,500 lines

---

### Priority 1: API Endpoints (8 files, ~1,800 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 16 | `api-gateway/endpoints/__init__.py` | 30 | Endpoints package init | - |
| 17 | `api-gateway/endpoints/meta.py` | 200 | Meta endpoints (/meta/*) | FastAPI |
| 18 | `api-gateway/endpoints/auth.py` | 300 | Auth endpoints (/auth/*) | services/auth_service |
| 19 | `api-gateway/endpoints/users.py` | 280 | User endpoints (/users/*) | services/user_service |
| 20 | `api-gateway/endpoints/sessions.py` | 320 | Session endpoints (/sessions/*) | services/session_service |
| 21 | `api-gateway/endpoints/manifests.py` | 220 | Manifest endpoints (/manifests/*) | services/proxy_service |
| 22 | `api-gateway/endpoints/trust.py` | 200 | Trust policy endpoints | services/proxy_service |
| 23 | `api-gateway/endpoints/chain.py` | 250 | Blockchain proxy endpoints | services/proxy_service |

**Subtotal**: 1,800 lines

---

### Priority 1: Service Layer (7 files, ~1,400 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 24 | `api-gateway/services/__init__.py` | 30 | Services package init | - |
| 25 | `api-gateway/services/auth_service.py` | 300 | Authentication service | aiohttp, PyJWT |
| 26 | `api-gateway/services/user_service.py` | 250 | User management service | aiohttp, models |
| 27 | `api-gateway/services/session_service.py` | 280 | Session service | aiohttp, models |
| 28 | `api-gateway/services/rate_limit_service.py` | 200 | Rate limiting service | Redis |
| 29 | `api-gateway/services/proxy_service.py` | 300 | Backend proxy service | aiohttp, Circuit Breaker |
| 30 | `api-gateway/utils/validation.py` | 240 | Input validation | Pydantic, re |

**Subtotal**: 1,400 lines

---

### Priority 1: Container Configuration (5 files, ~400 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 31 | `api-gateway/Dockerfile` | 80 | Multi-stage distroless build | - |
| 32 | `api-gateway/docker-compose.yml` | 120 | Production deployment | - |
| 33 | `api-gateway/docker-compose.dev.yml` | 100 | Development environment | - |
| 34 | `api-gateway/requirements.txt` | 50 | Python dependencies | - |
| 35 | `api-gateway/.env.example` | 50 | Environment variables template | - |

**Subtotal**: 400 lines

---

### Priority 1: Configuration (5 files, ~400 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 36 | `api-gateway/config/openapi.yaml` | 200 | OpenAPI 3.0 specification | - |
| 37 | `api-gateway/database/__init__.py` | 30 | Database package init | - |
| 38 | `api-gateway/database/connection.py` | 100 | MongoDB connection | motor (async MongoDB) |
| 39 | `api-gateway/repositories/user_repository.py` | 150 | User data access | motor |
| 40 | `api-gateway/repositories/session_repository.py` | 120 | Session data access | motor |

**Subtotal**: 600 lines

---

### **Total MVP Files**: 40 files, ~6,700 lines

---

## Enhancement Files List

### Priority 2: Testing Infrastructure (15 files, ~2,000 lines)

| # | File Path | Lines | Purpose |
|---|-----------|-------|---------|
| 41 | `api-gateway/tests/__init__.py` | 20 | Test package init |
| 42 | `api-gateway/tests/conftest.py` | 200 | Pytest configuration |
| 43 | `api-gateway/tests/test_auth.py` | 250 | Authentication tests |
| 44 | `api-gateway/tests/test_users.py` | 200 | User management tests |
| 45 | `api-gateway/tests/test_sessions.py` | 220 | Session tests |
| 46 | `api-gateway/tests/test_rate_limiting.py` | 180 | Rate limiting tests |
| 47 | `api-gateway/tests/test_integration.py` | 300 | Integration tests |
| 48 | `api-gateway/tests/test_performance.py` | 250 | Performance tests |
| 49 | `api-gateway/tests/test_benchmarks.py` | 200 | Benchmark tests |
| 50-55 | Additional test files | 180 | Various component tests |

**Subtotal**: ~2,000 lines

### Priority 2: Monitoring & Documentation (10 files, ~800 lines)

| # | File Path | Lines | Purpose |
|---|-----------|-------|---------|
| 56 | `api-gateway/monitoring/prometheus.yml` | 100 | Prometheus config |
| 57 | `api-gateway/monitoring/alerts.yml` | 80 | Alert rules |
| 58 | `api-gateway/monitoring/dashboard.json` | 200 | Grafana dashboard |
| 59-65 | Documentation files | 420 | API docs, guides |

**Subtotal**: ~800 lines

---

## Build Order Sequence

### Step 1: Foundation Setup (Day 1)

**Files to Create**:
1. `api-gateway/main.py`
2. `api-gateway/config.py`
3. `api-gateway/requirements.txt`
4. `api-gateway/.env.example`

**Actions**:
- Initialize project structure
- Setup FastAPI application
- Configure environment variables
- Install dependencies

**Testing**: FastAPI server starts, health endpoint responds

---

### Step 2: Core Middleware (Day 1-2)

**Files to Create**:
5. `api-gateway/middleware/__init__.py`
6. `api-gateway/middleware/cors.py`
7. `api-gateway/middleware/logging.py`

**Actions**:
- Implement CORS middleware
- Setup structured logging
- Test middleware chain

**Testing**: Middleware processes requests, logs appear

---

### Step 3: Authentication Integration (Day 2-3)

**Files to Create**:
8. `api-gateway/middleware/auth.py`
9. `api-gateway/models/auth.py`
10. `api-gateway/services/auth_service.py`
11. `api-gateway/utils/security.py`

**Actions**:
- Connect to Authentication cluster (Cluster 09)
- Implement JWT validation
- Setup authentication middleware

**Testing**: JWT tokens validated, unauthorized requests rejected

---

### Step 4: Database Integration (Day 3)

**Files to Create**:
12. `api-gateway/database/__init__.py`
13. `api-gateway/database/connection.py`
14. `api-gateway/repositories/user_repository.py`
15. `api-gateway/repositories/session_repository.py`

**Actions**:
- Connect to MongoDB (Cluster 08)
- Implement async database operations
- Test CRUD operations

**Testing**: Database queries successful, connections pooled

---

### Step 5: Data Models (Day 3-4)

**Files to Create**:
16. `api-gateway/models/__init__.py`
17. `api-gateway/models/common.py`
18. `api-gateway/models/user.py`
19. `api-gateway/models/session.py`

**Actions**:
- Define Pydantic models
- Add validation rules
- Test serialization

**Testing**: Models validate correctly, serialize to JSON

---

### Step 6: Service Layer (Day 4-5)

**Files to Create**:
20. `api-gateway/services/__init__.py`
21. `api-gateway/services/user_service.py`
22. `api-gateway/services/session_service.py`
23. `api-gateway/services/proxy_service.py`
24. `api-gateway/utils/validation.py`

**Actions**:
- Implement business logic
- Setup backend proxying
- Add circuit breaker pattern

**Testing**: Services communicate with backend clusters

---

### Step 7: API Endpoints (Day 5-7)

**Files to Create**:
25. `api-gateway/endpoints/__init__.py`
26. `api-gateway/endpoints/meta.py`
27. `api-gateway/endpoints/auth.py`
28. `api-gateway/endpoints/users.py`
29. `api-gateway/endpoints/sessions.py`
30. `api-gateway/endpoints/manifests.py`
31. `api-gateway/endpoints/trust.py`
32. `api-gateway/endpoints/chain.py`
33. `api-gateway/app/routes.py`

**Actions**:
- Implement all API endpoints
- Mount routes to application
- Add endpoint-level validation

**Testing**: All endpoints respond, OpenAPI docs generated

---

### Step 8: Rate Limiting (Day 7-8)

**Files to Create**:
34. `api-gateway/middleware/rate_limit.py`
35. `api-gateway/services/rate_limit_service.py`

**Actions**:
- Connect to Redis
- Implement tiered rate limiting
- Add rate limit headers

**Testing**: Rate limits enforced, 429 responses for excess

---

### Step 9: Container Configuration (Day 8-9)

**Files to Create**:
36. `api-gateway/Dockerfile`
37. `api-gateway/docker-compose.yml`
38. `api-gateway/docker-compose.dev.yml`

**Actions**:
- Create multi-stage Dockerfile
- Use distroless base image
- Setup Docker Compose

**Testing**: Container builds, runs, health check passes

---

### Step 10: OpenAPI & Documentation (Day 9-10)

**Files to Create**:
39. `api-gateway/config/openapi.yaml`

**Actions**:
- Generate OpenAPI specification
- Add endpoint descriptions
- Test with Swagger UI

**Testing**: OpenAPI spec valid, Swagger UI works

---

### Step 11: Integration Testing (Day 10)

**Actions**:
- Test API Gateway → Auth → Database flow
- Test API Gateway → Blockchain proxy
- Load testing with concurrent requests
- Security testing

**Testing**: All integration tests pass

---

## File-by-File Specifications

### File 1: `api-gateway/main.py` (150 lines)

**Purpose**: FastAPI application entry point

**Key Imports**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .config import settings
from .app.routes import api_router
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.logging import LoggingMiddleware
```

**Critical Functions**:
- `create_app()` → FastAPI: Application factory
- `setup_middleware(app)` → None: Configure middleware
- `setup_routes(app)` → None: Mount routers
- `main()` → None: Run uvicorn server

**Integration Points**:
- Middleware chain setup
- Route mounting
- Startup/shutdown events

---

### File 6: `api-gateway/middleware/auth.py` (250 lines)

**Purpose**: Authentication middleware for JWT validation

**Key Imports**:
```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from ..services.auth_service import AuthService
from ..models.auth import TokenPayload
```

**Critical Functions**:
- `AuthMiddleware.__init__(app, auth_service)`: Initialize middleware
- `AuthMiddleware.dispatch(request, call_next)`: Process request
- `extract_token(request)` → str: Extract JWT from header
- `validate_token(token)` → TokenPayload: Validate and decode

**Integration Points**:
- Cluster 09 (Authentication) for token validation
- Injects user context into request.state

---

### File 7: `api-gateway/middleware/rate_limit.py` (200 lines)

**Purpose**: Rate limiting middleware

**Key Imports**:
```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from ..services.rate_limit_service import RateLimitService
```

**Critical Functions**:
- `RateLimitMiddleware.__init__(app, redis_client)`: Initialize
- `RateLimitMiddleware.dispatch(request, call_next)`: Check limits
- `get_client_identifier(request)` → str: Get IP or user ID
- `check_rate_limit(identifier, endpoint)` → bool: Check limit

**Integration Points**:
- Redis (Cluster 08) for rate limit counters
- Returns 429 status code when exceeded

---

### File 18: `api-gateway/endpoints/auth.py` (300 lines)

**Purpose**: Authentication endpoints

**Key Endpoints**:
- `POST /auth/login`: User login with TRON signature
- `POST /auth/verify`: Verify JWT token
- `POST /auth/refresh`: Refresh access token
- `POST /auth/logout`: User logout
- `GET /auth/status`: Authentication status

**Key Imports**:
```python
from fastapi import APIRouter, Depends, HTTPException
from ..models.auth import LoginRequest, TokenResponse
from ..services.auth_service import AuthService
```

**Critical Functions**:
- `login(request: LoginRequest)` → TokenResponse: Login handler
- `verify_token(token: str)` → TokenPayload: Verify handler
- `refresh_token(refresh_token: str)` → TokenResponse: Refresh
- `logout(user_id: str)` → None: Logout handler

**Integration Points**:
- Cluster 09 (Authentication) backend service
- Cluster 08 (Database) for session storage

---

### File 30: `api-gateway/services/proxy_service.py` (300 lines)

**Purpose**: Backend service proxy with circuit breaker

**Key Imports**:
```python
import aiohttp
from typing import Dict, Any
from circuitbreaker import CircuitBreaker
```

**Critical Functions**:
- `ProxyService.__init__(service_urls)`: Initialize with backend URLs
- `proxy_request(service, endpoint, method, data)` → Dict: Proxy request
- `@CircuitBreaker`: Decorator for circuit breaker pattern
- `handle_service_error(error)` → HTTPException: Error handling

**Integration Points**:
- Cluster 02 (Blockchain) for /chain/* endpoints
- Cluster 03 (Session) for /sessions/* endpoints
- Cluster 10 (Cross-Cluster) for service discovery

---

### File 36: `api-gateway/Dockerfile` (80 lines)

**Purpose**: Multi-stage distroless container build

**Structure**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Runtime (distroless)
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /root/.local /root/.local
COPY api-gateway /app
WORKDIR /app
ENTRYPOINT ["python", "-m", "main"]
```

**Critical Sections**:
- Builder stage with dependencies
- Distroless runtime stage
- Health check configuration
- Environment variable injection

**Integration Points**:
- Exposes port 8080
- Health endpoint: /health
- Metrics endpoint: /metrics

---

## Testing Strategy

### Unit Tests (Priority 2)

**Test Files**:
- `test_auth.py`: Authentication middleware tests
- `test_rate_limiting.py`: Rate limiting tests
- `test_users.py`: User endpoint tests
- `test_sessions.py`: Session endpoint tests

**Coverage Target**: >95%

**Key Test Scenarios**:
- JWT validation (valid, expired, invalid signature)
- Rate limiting (within limit, exceeded, different tiers)
- CORS headers present
- Error handling (400, 401, 403, 404, 429, 500)

---

### Integration Tests (Priority 2)

**Test Scenarios**:
1. **Auth Flow**: Login → Get token → Access protected endpoint
2. **Session Flow**: Create session → Get session → List sessions
3. **Blockchain Proxy**: Query /chain/info → Receive blockchain data
4. **Rate Limiting**: Send 101 requests → Receive 429 on 101st

**Dependencies**:
- Cluster 09 (Authentication) running
- Cluster 08 (Database) running
- Mock services for other backends

---

### Performance Tests (Priority 2)

**Benchmarks**:
- Throughput: >1000 requests/second
- Latency: <50ms p95, <100ms p99
- Concurrent connections: >500

**Tools**: Locust, k6, or wrk

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=api-gateway
PORT=8080
DEBUG=false
LOG_LEVEL=INFO

# Authentication
AUTH_SERVICE_URL=http://auth-service:8089
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
TOKEN_EXPIRE_MINUTES=15

# Database
MONGODB_URI=mongodb://mongodb:27017/lucid
REDIS_URI=redis://redis:6379/0

# Backend Services
BLOCKCHAIN_SERVICE_URL=http://blockchain-core:8084
SESSION_SERVICE_URL=http://session-api:8087
NODE_SERVICE_URL=http://node-management:8095

# Rate Limiting
RATE_LIMIT_PUBLIC=100  # per minute
RATE_LIMIT_AUTHENTICATED=1000  # per minute
RATE_LIMIT_ADMIN=10000  # per minute

# CORS
CORS_ORIGINS=["http://localhost:3000", "https://lucid.onion"]
CORS_ALLOW_CREDENTIALS=true

# Service Mesh
SERVICE_MESH_ENABLED=true
SERVICE_DISCOVERY_URL=http://consul:8500
```

---

### Docker Compose Configuration

**Production** (`docker-compose.yml`):
```yaml
version: '3.8'
services:
  api-gateway:
    build:
      context: .
      dockerfile: Dockerfile
    image: lucid-api-gateway:latest
    container_name: lucid-api-gateway
    ports:
      - "8080:8080"
    environment:
      - SERVICE_NAME=api-gateway
      - MONGODB_URI=mongodb://mongodb:27017/lucid
      - AUTH_SERVICE_URL=http://auth-service:8089
    depends_on:
      - mongodb
      - redis
      - auth-service
    networks:
      - lucid-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### Kubernetes Deployment

**Key Resources**:
- Deployment: 3 replicas for HA
- Service: ClusterIP with load balancing
- Ingress: HTTPS termination, rate limiting
- ConfigMap: Environment configuration
- Secret: JWT secret, API keys

---

## Integration Points

### Upstream Dependencies

| Cluster | Integration Type | Endpoints Used |
|---------|-----------------|----------------|
| 09-Authentication | HTTP/REST | POST /auth/login, /auth/verify |
| 08-Storage-Database | MongoDB | users, sessions, tokens collections |
| 08-Storage-Database | Redis | Rate limit counters, cache |

### Downstream Consumers

| Cluster | Integration Type | Traffic Pattern |
|---------|-----------------|-----------------|
| 03-Session-Management | HTTP Proxy | Session CRUD operations |
| 02-Blockchain-Core | HTTP Proxy | Blockchain queries |
| 05-Node-Management | HTTP Proxy | Node operations |
| 06-Admin-Interface | HTTP Client | Admin operations |

---

## Success Criteria

### Functional

- [ ] All 8 endpoint categories operational
- [ ] JWT authentication working
- [ ] Rate limiting enforced (3 tiers)
- [ ] CORS headers correct
- [ ] Request/response logging structured
- [ ] Backend proxy working with circuit breaker
- [ ] Health check endpoint returns 200

### Performance

- [ ] p95 latency <50ms
- [ ] Throughput >1000 req/s
- [ ] <5% error rate under load

### Quality

- [ ] Unit test coverage >95%
- [ ] Integration tests passing
- [ ] Distroless container builds
- [ ] OpenAPI spec valid

---

## References

- [API Gateway Cluster Overview](../01-api-gateway-cluster/00-cluster-overview.md)
- [API Specification](../01-api-gateway-cluster/01-api-specification.md)
- [Data Models](../01-api-gateway-cluster/02-data-models.md)
- [Security Compliance](../01-api-gateway-cluster/04-security-compliance.md)

---

**Build Guide Version**: 1.0.0  
**Status**: READY FOR IMPLEMENTATION  
**Estimated Build Time**: 10 days (2 developers)


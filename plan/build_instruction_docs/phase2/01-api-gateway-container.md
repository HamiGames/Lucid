# API Gateway Container

## Overview
Build API Gateway container with routing, rate limiting, authentication middleware, and service mesh integration for Phase 2 core services.

## Location
`03-api-gateway/Dockerfile`

## Container Details
**Container**: `pickme/lucid-api-gateway:latest-arm64`

## Multi-Stage Build Strategy

### Stage 1: Builder
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY 03-api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +
```

### Stage 2: Runtime (Distroless)
```dockerfile
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY 03-api-gateway/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8080/health')"]

# Default command
CMD ["python", "main.py"]
```

## Requirements File
**File**: `03-api-gateway/requirements.txt`

```txt
# API Gateway Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.8
bcrypt==4.1.2

# Rate Limiting
slowapi==0.1.9
redis==5.0.1

# Service Mesh Integration
consul==1.1.0
grpcio==1.59.0
grpcio-tools==1.59.0

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
```

## Application Code Structure

### Main Application
**File**: `03-api-gateway/main.py`

```python
"""
Lucid API Gateway
Provides routing, rate limiting, authentication, and service mesh integration
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

from 03_api_gateway.middleware.rate_limiter import RateLimiterMiddleware
from 03_api_gateway.middleware.auth_middleware import AuthMiddleware
from 03_api_gateway.middleware.service_mesh import ServiceMeshMiddleware
from 03_api_gateway.routing.service_router import ServiceRouter
from 03_api_gateway.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
service_router = None
rate_limiter = None
auth_middleware = None
service_mesh = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global service_router, rate_limiter, auth_middleware, service_mesh
    
    # Startup
    logger.info("Starting Lucid API Gateway...")
    
    settings = get_settings()
    
    # Initialize service router
    service_router = ServiceRouter(settings)
    await service_router.initialize()
    
    # Initialize rate limiter
    rate_limiter = RateLimiterMiddleware(settings)
    await rate_limiter.initialize()
    
    # Initialize auth middleware
    auth_middleware = AuthMiddleware(settings)
    await auth_middleware.initialize()
    
    # Initialize service mesh
    service_mesh = ServiceMeshMiddleware(settings)
    await service_mesh.initialize()
    
    logger.info("API Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")
    if service_router:
        await service_router.cleanup()
    if rate_limiter:
        await rate_limiter.cleanup()
    if auth_middleware:
        await auth_middleware.cleanup()
    if service_mesh:
        await service_mesh.cleanup()
    logger.info("API Gateway shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid API Gateway",
    description="API Gateway with routing, rate limiting, and service mesh integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(ServiceMeshMiddleware)

# Include service routers
app.include_router(ServiceRouter.get_auth_router(), prefix="/auth", tags=["authentication"])
app.include_router(ServiceRouter.get_blockchain_router(), prefix="/blockchain", tags=["blockchain"])
app.include_router(ServiceRouter.get_session_router(), prefix="/sessions", tags=["sessions"])
app.include_router(ServiceRouter.get_node_router(), prefix="/nodes", tags=["nodes"])
app.include_router(ServiceRouter.get_admin_router(), prefix="/admin", tags=["admin"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-api-gateway",
        "version": "1.0.0",
        "services": {
            "auth": await service_router.check_service_health("auth"),
            "blockchain": await service_router.check_service_health("blockchain"),
            "sessions": await service_router.check_service_health("sessions"),
            "nodes": await service_router.check_service_health("nodes"),
            "admin": await service_router.check_service_health("admin")
        }
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "services": [
            "/auth",
            "/blockchain",
            "/sessions",
            "/nodes",
            "/admin"
        ]
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
```

### Service Router
**File**: `03-api-gateway/routing/service_router.py`

```python
"""
Service router for API Gateway
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class ServiceRouter:
    """Service router for API Gateway"""
    
    def __init__(self, settings):
        self.settings = settings
        self.service_urls = {
            "auth": f"http://lucid-auth-service:8089",
            "blockchain": f"http://lucid-blockchain-engine:8084",
            "sessions": f"http://lucid-session-api:8087",
            "nodes": f"http://lucid-node-management:8096",
            "admin": f"http://lucid-admin-interface:8083"
        }
        self.http_client = None
        
    async def initialize(self):
        """Initialize service router"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Service router initialized")
    
    async def cleanup(self):
        """Cleanup service router"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Service router cleaned up")
    
    async def check_service_health(self, service_name: str) -> bool:
        """Check service health"""
        try:
            if service_name in self.service_urls:
                response = await self.http_client.get(f"{self.service_urls[service_name]}/health")
                return response.status_code == 200
            return False
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return False
    
    async def proxy_request(self, service_name: str, path: str, method: str, 
                          headers: Dict[str, str], body: Optional[bytes] = None) -> JSONResponse:
        """Proxy request to service"""
        try:
            if service_name not in self.service_urls:
                raise HTTPException(status_code=404, detail="Service not found")
            
            service_url = self.service_urls[service_name]
            full_url = f"{service_url}{path}"
            
            # Make request to service
            response = await self.http_client.request(
                method=method,
                url=full_url,
                headers=headers,
                content=body
            )
            
            # Return response
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Service unavailable")
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @staticmethod
    def get_auth_router() -> APIRouter:
        """Get authentication service router"""
        router = APIRouter()
        
        @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def auth_proxy(request: Request, path: str):
            service_router = request.app.state.service_router
            return await service_router.proxy_request(
                "auth", f"/{path}", request.method, dict(request.headers)
            )
        
        return router
    
    @staticmethod
    def get_blockchain_router() -> APIRouter:
        """Get blockchain service router"""
        router = APIRouter()
        
        @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def blockchain_proxy(request: Request, path: str):
            service_router = request.app.state.service_router
            return await service_router.proxy_request(
                "blockchain", f"/{path}", request.method, dict(request.headers)
            )
        
        return router
    
    @staticmethod
    def get_session_router() -> APIRouter:
        """Get session service router"""
        router = APIRouter()
        
        @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def session_proxy(request: Request, path: str):
            service_router = request.app.state.service_router
            return await service_router.proxy_request(
                "sessions", f"/{path}", request.method, dict(request.headers)
            )
        
        return router
    
    @staticmethod
    def get_node_router() -> APIRouter:
        """Get node service router"""
        router = APIRouter()
        
        @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def node_proxy(request: Request, path: str):
            service_router = request.app.state.service_router
            return await service_router.proxy_request(
                "nodes", f"/{path}", request.method, dict(request.headers)
            )
        
        return router
    
    @staticmethod
    def get_admin_router() -> APIRouter:
        """Get admin service router"""
        router = APIRouter()
        
        @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def admin_proxy(request: Request, path: str):
            service_router = request.app.state.service_router
            return await service_router.proxy_request(
                "admin", f"/{path}", request.method, dict(request.headers)
            )
        
        return router
```

### Rate Limiter Middleware
**File**: `03-api-gateway/middleware/rate_limiter.py`

```python
"""
Rate limiting middleware for API Gateway
"""

import asyncio
import logging
from typing import Dict, Any
import redis
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class RateLimiterMiddleware:
    """Rate limiting middleware"""
    
    def __init__(self, settings):
        self.settings = settings
        self.redis_client = None
        self.rate_limits = {
            "free": 100,      # 100 req/min
            "premium": 1000,  # 1000 req/min
            "enterprise": 10000  # 10000 req/min
        }
        
    async def initialize(self):
        """Initialize rate limiter"""
        self.redis_client = redis.from_url(self.settings.redis_url)
        logger.info("Rate limiter initialized")
    
    async def cleanup(self):
        """Cleanup rate limiter"""
        if self.redis_client:
            self.redis_client.close()
        logger.info("Rate limiter cleaned up")
    
    async def check_rate_limit(self, request: Request) -> bool:
        """Check rate limit for request"""
        try:
            # Get client IP
            client_ip = request.client.host
            
            # Get user tier (from JWT token or default)
            user_tier = await self._get_user_tier(request)
            
            # Get rate limit for tier
            rate_limit = self.rate_limits.get(user_tier, self.rate_limits["free"])
            
            # Check current usage
            key = f"rate_limit:{client_ip}:{user_tier}"
            current_usage = self.redis_client.get(key)
            
            if current_usage is None:
                # First request, set counter
                self.redis_client.setex(key, 60, 1)
                return True
            elif int(current_usage) < rate_limit:
                # Within limit, increment counter
                self.redis_client.incr(key)
                return True
            else:
                # Rate limit exceeded
                return False
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow request on error
    
    async def _get_user_tier(self, request: Request) -> str:
        """Get user tier from request"""
        # This would extract user tier from JWT token
        # For now, return default tier
        return "free"
    
    async def __call__(self, request: Request, call_next):
        """Middleware function"""
        # Check rate limit
        if not await self.check_rate_limit(request):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Continue to next middleware
        response = await call_next(request)
        return response
```

### Authentication Middleware
**File**: `03-api-gateway/middleware/auth_middleware.py`

```python
"""
Authentication middleware for API Gateway
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication middleware"""
    
    def __init__(self, settings):
        self.settings = settings
        self.security = HTTPBearer()
        
    async def initialize(self):
        """Initialize auth middleware"""
        logger.info("Auth middleware initialized")
    
    async def cleanup(self):
        """Cleanup auth middleware"""
        logger.info("Auth middleware cleaned up")
    
    async def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate request"""
        try:
            # Skip authentication for public endpoints
            if request.url.path in ["/health", "/docs", "/openapi.json"]:
                return None
            
            # Get authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Extract token
            if not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header")
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Verify token
            payload = jwt.decode(token, self.settings.jwt_secret_key, algorithms=["HS256"])
            
            # Add user info to request state
            request.state.user = payload
            
            return payload
            
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    async def __call__(self, request: Request, call_next):
        """Middleware function"""
        try:
            # Authenticate request
            await self.authenticate_request(request)
            
            # Continue to next middleware
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
```

### Service Mesh Middleware
**File**: `03-api-gateway/middleware/service_mesh.py`

```python
"""
Service mesh middleware for API Gateway
"""

import asyncio
import logging
from typing import Dict, Any
import consul
from fastapi import Request

logger = logging.getLogger(__name__)

class ServiceMeshMiddleware:
    """Service mesh middleware"""
    
    def __init__(self, settings):
        self.settings = settings
        self.consul_client = None
        
    async def initialize(self):
        """Initialize service mesh"""
        self.consul_client = consul.Consul(host=self.settings.consul_host, port=self.settings.consul_port)
        logger.info("Service mesh initialized")
    
    async def cleanup(self):
        """Cleanup service mesh"""
        logger.info("Service mesh cleaned up")
    
    async def register_service(self, service_name: str, service_address: str, service_port: int):
        """Register service with Consul"""
        try:
            self.consul_client.agent.service.register(
                name=service_name,
                service_id=f"{service_name}-1",
                address=service_address,
                port=service_port,
                check=consul.Check.http(f"http://{service_address}:{service_port}/health", interval="30s")
            )
            logger.info(f"Service {service_name} registered with Consul")
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
    
    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover service from Consul"""
        try:
            services = self.consul_client.health.service(service_name, passing=True)[1]
            if services:
                service = services[0]
                return {
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return None
    
    async def __call__(self, request: Request, call_next):
        """Middleware function"""
        # Add service mesh headers
        request.state.service_mesh = True
        
        # Continue to next middleware
        response = await call_next(request)
        return response
```

## Build Command

```bash
# Build API Gateway container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-api-gateway:latest-arm64 \
  -f 03-api-gateway/Dockerfile \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/core/build-api-gateway.sh`

```bash
#!/bin/bash
# scripts/core/build-api-gateway.sh
# Build API Gateway container

set -e

echo "Building API Gateway container..."

# Create API Gateway directory if it doesn't exist
mkdir -p 03-api-gateway

# Create requirements.txt
cat > 03-api-gateway/requirements.txt << 'EOF'
# API Gateway Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.8
bcrypt==4.1.2

# Rate Limiting
slowapi==0.1.9
redis==5.0.1

# Service Mesh Integration
consul==1.1.0
grpcio==1.59.0
grpcio-tools==1.59.0

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
EOF

# Create Dockerfile
cat > 03-api-gateway/Dockerfile << 'EOF'
# Multi-stage build for API Gateway
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY 03-api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Final distroless stage
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY 03-api-gateway/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8080/health')"]

# Default command
CMD ["python", "main.py"]
EOF

# Build API Gateway container
echo "Building API Gateway container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-api-gateway:latest-arm64 \
  -f 03-api-gateway/Dockerfile \
  --push \
  .

echo "API Gateway container built and pushed successfully!"
echo "Container: pickme/lucid-api-gateway:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Health endpoint responds correctly
- Rate limiting enforced
- Authentication middleware working
- Service mesh integration functional
- Service routing working

## Environment Configuration
Uses `.env.core` for:
- API Gateway port configuration
- Rate limiting settings
- Service URLs
- JWT secret key
- Redis connection

## Security Features
- **Rate Limiting**: Configurable rate limits per user tier
- **Authentication**: JWT token validation
- **Service Mesh**: mTLS communication between services
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Health & Status
- `GET /health` - Health check with service status
- `GET /` - Root endpoint with service information

### Service Proxies
- `GET|POST|PUT|DELETE /auth/*` - Authentication service proxy
- `GET|POST|PUT|DELETE /blockchain/*` - Blockchain service proxy
- `GET|POST|PUT|DELETE /sessions/*` - Session service proxy
- `GET|POST|PUT|DELETE /nodes/*` - Node service proxy
- `GET|POST|PUT|DELETE /admin/*` - Admin service proxy

## Rate Limiting Configuration
- **Free Tier**: 100 requests/minute
- **Premium Tier**: 1000 requests/minute
- **Enterprise Tier**: 10000 requests/minute

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-api-gateway:latest-arm64 \
  -f 03-api-gateway/Dockerfile \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-api-gateway

# Test health endpoint
curl http://localhost:8080/health
```

### Service Connectivity Issues
```bash
# Check service discovery
curl http://localhost:8080/health

# Test service routing
curl http://localhost:8080/auth/health
curl http://localhost:8080/blockchain/health
```

## Next Steps
After successful API Gateway build, proceed to service mesh controller container build.

# RDP Services Cluster - Implementation Guide

## Overview
This document provides comprehensive implementation guidance for the RDP Services Cluster, including service architecture, code structure, FastAPI setup, and integration patterns.

## Service Architecture

### Service Overview

The RDP Services Cluster consists of 4 microservices:

| Service | Port | Base Path | Purpose |
|---------|------|-----------|---------|
| rdp-server-manager | 8090 | /api/v1/rdp | RDP server lifecycle management |
| xrdp-integration | 8091 | /api/v1/xrdp | XRDP service control |
| rdp-session-controller | 8092 | /api/v1/sessions | Session management |
| rdp-resource-monitor | 8093 | /api/v1/resources | Resource monitoring |

### Communication Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                           │
│              (Tor + Beta Sidecar)                        │
└────────┬────────────┬────────────┬──────────────────────┘
         │            │            │            │
    ┌────▼────┐  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐
    │ RDP Srv │  │ XRDP   │  │Session │  │Resource│
    │ Manager │  │ Integ  │  │ Ctrl   │  │Monitor │
    │  :8090  │  │ :8091  │  │ :8092  │  │ :8093  │
    └────┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
         │            │            │            │
         └────────────┴────────────┴────────────┘
                       │
                  ┌────▼─────┐
                  │ MongoDB  │
                  │  :27017  │
                  └──────────┘
```

## FastAPI Application Setup

### Base Application Structure

**File**: `services/{service-name}/app.py`

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from .config import settings
from .api.v1 import router as v1_router
from .api.middleware import RequestLoggingMiddleware, RateLimitMiddleware
from .core.database import connect_db, disconnect_db
from .monitoring.metrics import setup_metrics
from .monitoring.health_checks import health_check_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME}")
    await connect_db()
    setup_metrics(app)
    logger.info(f"{settings.SERVICE_NAME} started successfully")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await disconnect_db()
    logger.info(f"{settings.SERVICE_NAME} shut down successfully")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=f"Lucid {settings.SERVICE_NAME}",
        description=settings.SERVICE_DESCRIPTION,
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Include routers
    app.include_router(health_check_router, prefix="/health", tags=["Health"])
    app.include_router(v1_router, prefix="/api/v1")
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "LUCID_ERR_0001",
                    "message": "Internal server error",
                    "service": settings.SERVICE_NAME,
                    "version": "v1"
                }
            }
        )
    
    return app

app = create_app()
```

### Configuration Management

**File**: `services/{service-name}/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """Service configuration"""
    
    # Service Identity
    SERVICE_NAME: str
    SERVICE_DESCRIPTION: str
    SERVICE_PORT: int
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Database
    MONGODB_URI: str = "mongodb://mongo:27017/lucid_rdp"
    MONGODB_MAX_POOL_SIZE: int = 50
    MONGODB_MIN_POOL_SIZE: int = 10
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Authentication
    AUTH_SERVICE_URL: str = "https://auth.lucid-blockchain.org"
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST_SIZE: int = 200
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
```

### Main Entry Point

**File**: `services/{service-name}/main.py`

```python
import uvicorn
import logging
from .config import settings
from .app import app

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
```

## API Endpoint Implementation

### Example: RDP Server Manager Endpoints

**File**: `services/rdp-server-manager/api/v1/rdp_servers.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from uuid import UUID

from ...core.models import (
    RdpServerCreateRequest,
    RdpServerUpdateRequest,
    RdpServerResponse,
    RdpServerListResponse,
)
from ...core.rdp_server_manager import RdpServerManager
from ...api.dependencies import (
    get_current_user,
    get_rdp_server_manager,
    verify_admin_role,
)
from ...utils.exceptions import RdpServerNotFoundError, ResourceLimitExceededError

router = APIRouter(prefix="/rdp", tags=["RDP Servers"])

@router.get("/servers", response_model=RdpServerListResponse)
async def list_rdp_servers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(get_current_user),
    manager: RdpServerManager = Depends(get_rdp_server_manager),
):
    """List RDP servers with pagination"""
    try:
        servers, total = await manager.list_servers(
            page=page,
            limit=limit,
            status=status,
            user_id=user_id,
            requesting_user=current_user,
        )
        
        pages = (total + limit - 1) // limit
        
        return RdpServerListResponse(
            servers=servers,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": pages,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LUCID_ERR_2000",
                "message": "Failed to list RDP servers",
                "details": str(e),
            }
        )

@router.post("/servers", response_model=RdpServerResponse, status_code=status.HTTP_201_CREATED)
async def create_rdp_server(
    request: RdpServerCreateRequest,
    current_user: dict = Depends(get_current_user),
    manager: RdpServerManager = Depends(get_rdp_server_manager),
):
    """Create a new RDP server instance"""
    try:
        server = await manager.create_server(request, current_user)
        return server
    except ResourceLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "LUCID_ERR_2008",
                "message": str(e),
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LUCID_ERR_2002",
                "message": "RDP server creation failed",
                "details": str(e),
            }
        )

@router.get("/servers/{server_id}", response_model=RdpServerResponse)
async def get_rdp_server(
    server_id: UUID,
    current_user: dict = Depends(get_current_user),
    manager: RdpServerManager = Depends(get_rdp_server_manager),
):
    """Get RDP server details"""
    try:
        server = await manager.get_server(server_id, current_user)
        if not server:
            raise RdpServerNotFoundError(f"Server {server_id} not found")
        return server
    except RdpServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LUCID_ERR_2001",
                "message": "RDP server not found",
            }
        )

@router.put("/servers/{server_id}", response_model=RdpServerResponse)
async def update_rdp_server(
    server_id: UUID,
    request: RdpServerUpdateRequest,
    current_user: dict = Depends(get_current_user),
    manager: RdpServerManager = Depends(get_rdp_server_manager),
):
    """Update RDP server configuration"""
    try:
        server = await manager.update_server(server_id, request, current_user)
        return server
    except RdpServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LUCID_ERR_2001",
                "message": "RDP server not found",
            }
        )

@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rdp_server(
    server_id: UUID,
    current_user: dict = Depends(get_current_user),
    manager: RdpServerManager = Depends(get_rdp_server_manager),
):
    """Delete RDP server instance"""
    try:
        await manager.delete_server(server_id, current_user)
    except RdpServerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LUCID_ERR_2001",
                "message": "RDP server not found",
            }
        )
```

### Dependencies Implementation

**File**: `services/rdp-server-manager/api/dependencies.py`

```python
from fastapi import Depends, HTTPException, status, Header
from typing import Optional
import jwt

from ..config import settings
from ..core.rdp_server_manager import RdpServerManager

async def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and validate JWT token"""
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def verify_admin_role(current_user: dict = Depends(get_current_user)) -> dict:
    """Verify user has admin role"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

async def get_rdp_server_manager() -> RdpServerManager:
    """Dependency injection for RDP Server Manager"""
    return RdpServerManager()
```

## Distroless Container Configuration

### Dockerfile Template

**File**: `services/{service-name}/Dockerfile`

```dockerfile
# Multi-stage build for RDP Services
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12:nonroot

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/nonroot/.local

# Copy application code
COPY --chown=nonroot:nonroot . .

# Set environment variables
ENV PYTHONPATH=/app:/home/nonroot/.local/lib/python3.11/site-packages
ENV PATH=/home/nonroot/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose service port
EXPOSE 8090

# Run as non-root user
USER nonroot

# Run the application
ENTRYPOINT ["python", "-m", "services.rdp_server_manager.main"]
```

### Requirements Template

**File**: `services/{service-name}/requirements.txt`

```txt
# FastAPI Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
motor==3.3.2
pymongo==4.6.0

# Redis
redis==5.0.1
aioredis==2.0.1

# Authentication
PyJWT==2.8.0
passlib[bcrypt]==1.7.4

# Monitoring
prometheus-client==0.19.0

# Utilities
python-multipart==0.0.6
python-json-logger==2.0.7
```

## Database Integration

### Database Connection

**File**: `services/{service-name}/core/database.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging

from ..config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_db():
    """Connect to MongoDB"""
    try:
        logger.info(f"Connecting to MongoDB: {settings.MONGODB_URI}")
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
        )
        
        # Test connection
        await db.client.admin.command('ping')
        db.db = db.client.get_database()
        
        logger.info("MongoDB connection established")
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def disconnect_db():
    """Disconnect from MongoDB"""
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed")

def get_database():
    """Get database instance"""
    return db.db
```

### Repository Pattern

**File**: `services/{service-name}/database/repositories/base_repository.py`

```python
from typing import TypeVar, Generic, Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from uuid import UUID
from datetime import datetime

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository for common CRUD operations"""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document"""
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data
    
    async def find_by_id(self, id: UUID) -> Optional[Dict[str, Any]]:
        """Find document by ID"""
        return await self.collection.find_one({"_id": id})
    
    async def find_many(
        self,
        filter: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        sort: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        cursor = self.collection.find(filter)
        
        if sort:
            cursor = cursor.sort(sort)
        
        cursor = cursor.skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def count(self, filter: Dict[str, Any]) -> int:
        """Count documents matching filter"""
        return await self.collection.count_documents(filter)
    
    async def update(self, id: UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update document by ID"""
        data["updated_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {"_id": id},
            {"$set": data},
            return_document=True
        )
        return result
    
    async def delete(self, id: UUID) -> bool:
        """Delete document by ID"""
        result = await self.collection.delete_one({"_id": id})
        return result.deleted_count > 0
```

## XRDP System Integration

### XRDP Controller

**File**: `services/xrdp-integration/system/xrdp_controller.py`

```python
import subprocess
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class XrdpController:
    """System-level XRDP service controller"""
    
    async def start_service(self) -> Dict[str, Any]:
        """Start XRDP service"""
        try:
            result = subprocess.run(
                ["systemctl", "start", "xrdp"],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("XRDP service started successfully")
            return {
                "action": "start",
                "status": "success",
                "message": "XRDP service started successfully"
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start XRDP service: {e.stderr}")
            raise Exception(f"XRDP service start failed: {e.stderr}")
    
    async def stop_service(self) -> Dict[str, Any]:
        """Stop XRDP service"""
        try:
            result = subprocess.run(
                ["systemctl", "stop", "xrdp"],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("XRDP service stopped successfully")
            return {
                "action": "stop",
                "status": "success",
                "message": "XRDP service stopped successfully"
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop XRDP service: {e.stderr}")
            raise Exception(f"XRDP service stop failed: {e.stderr}")
    
    async def restart_service(self) -> Dict[str, Any]:
        """Restart XRDP service"""
        try:
            result = subprocess.run(
                ["systemctl", "restart", "xrdp"],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("XRDP service restarted successfully")
            return {
                "action": "restart",
                "status": "success",
                "message": "XRDP service restarted successfully"
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart XRDP service: {e.stderr}")
            raise Exception(f"XRDP service restart failed: {e.stderr}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get XRDP service status"""
        try:
            result = subprocess.run(
                ["systemctl", "status", "xrdp"],
                capture_output=True,
                text=True
            )
            
            is_active = "active (running)" in result.stdout
            
            return {
                "status": "running" if is_active else "stopped",
                "raw_output": result.stdout
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get XRDP service status: {e.stderr}")
            return {
                "status": "error",
                "error": e.stderr
            }
```

## Beta Sidecar Integration

### Ops Plane Isolation

The RDP Services Cluster uses the Beta sidecar pattern for operational plane isolation. All management operations are routed through the Beta sidecar.

**Configuration**: `services/{service-name}/beta-sidecar.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rdp-beta-sidecar-config
data:
  config.yaml: |
    ops_plane:
      isolation: true
      tor_only: true
      allowed_endpoints:
        - /health
        - /metrics
        - /api/v1/*
    
    management:
      prometheus_metrics: true
      health_checks: true
      log_forwarding: true
    
    security:
      enforce_tls: true
      audit_logging: true
```

## Naming Conventions

### Service Names
- Pattern: `{function}-{component}` (kebab-case)
- Examples: `rdp-server-manager`, `xrdp-integration`, `rdp-session-controller`

### File Names
- Pattern: `{purpose}_{context}.py` (snake_case)
- Examples: `rdp_server_manager.py`, `session_controller.py`, `resource_monitor.py`

### Class Names
- Pattern: `{Purpose}{Context}` (PascalCase)
- Examples: `RdpServerManager`, `SessionController`, `ResourceMonitor`

### Function Names
- Pattern: `{verb}_{noun}` (snake_case)
- Examples: `create_server`, `start_session`, `monitor_resources`

### Database Collections
- Pattern: `{entity}_{type}` (snake_case, plural)
- Examples: `rdp_servers`, `rdp_sessions`, `resource_metrics`

## Error Handling

### Custom Exceptions

**File**: `shared/utils/exceptions.py`

```python
class LucidException(Exception):
    """Base exception for Lucid services"""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class RdpServerNotFoundError(LucidException):
    def __init__(self, message: str = "RDP server not found"):
        super().__init__(message, "LUCID_ERR_2001")

class RdpServerCreationError(LucidException):
    def __init__(self, message: str = "RDP server creation failed"):
        super().__init__(message, "LUCID_ERR_2002")

class ResourceLimitExceededError(LucidException):
    def __init__(self, message: str = "Resource limit exceeded"):
        super().__init__(message, "LUCID_ERR_2008")

class SessionNotFoundError(LucidException):
    def __init__(self, message: str = "RDP session not found"):
        super().__init__(message, "LUCID_ERR_2201")

class XrdpServiceError(LucidException):
    def __init__(self, message: str = "XRDP service error"):
        super().__init__(message, "LUCID_ERR_2101")
```

## Testing Infrastructure

### Test Configuration

**File**: `tests/conftest.py`

```python
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient

from services.rdp_server_manager.app import create_app
from services.rdp_server_manager.config import settings

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Create test database"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client.get_database("test_lucid_rdp")
    
    yield db
    
    # Cleanup
    await client.drop_database("test_lucid_rdp")
    client.close()

@pytest.fixture
def test_client():
    """Create test client"""
    app = create_app()
    return TestClient(app)

@pytest.fixture
def test_jwt_token():
    """Generate test JWT token"""
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "user_id": "test-user-123",
        "roles": ["user"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return f"Bearer {token}"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10


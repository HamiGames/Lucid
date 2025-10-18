# API Gateway Cluster - Implementation Guide

## Overview

This document provides comprehensive implementation guidance for the API Gateway cluster, including code structure, naming conventions, distroless container configuration, and deployment patterns.

## Code Structure

### Project Layout

```
03-api-gateway/
├── Dockerfile                    # Distroless multi-stage build
├── docker-compose.yml           # Local development setup
├── requirements.txt             # Python dependencies
├── api/
│   ├── app/
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── config.py           # Configuration management
│   │   ├── middleware/         # Custom middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Authentication middleware
│   │   │   ├── rate_limit.py   # Rate limiting middleware
│   │   │   ├── cors.py         # CORS middleware
│   │   │   └── logging.py      # Request/response logging
│   │   ├── routers/            # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── meta.py         # Meta endpoints
│   │   │   ├── auth.py         # Authentication endpoints
│   │   │   ├── users.py        # User management endpoints
│   │   │   ├── sessions.py     # Session management endpoints
│   │   │   ├── manifests.py    # Manifest endpoints
│   │   │   ├── trust.py        # Trust policy endpoints
│   │   │   ├── chain.py        # Blockchain proxy endpoints
│   │   │   └── wallets.py      # Wallet proxy endpoints
│   │   ├── services/           # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py # Authentication service
│   │   │   ├── user_service.py # User management service
│   │   │   ├── session_service.py # Session service
│   │   │   ├── rate_limit_service.py # Rate limiting service
│   │   │   └── proxy_service.py # Backend proxy service
│   │   ├── models/             # Data models
│   │   │   ├── __init__.py
│   │   │   ├── user.py         # User models
│   │   │   ├── session.py      # Session models
│   │   │   ├── auth.py         # Authentication models
│   │   │   └── common.py       # Common models
│   │   ├── database/           # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── connection.py   # MongoDB connection
│   │   │   ├── repositories/   # Data repositories
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_repository.py
│   │   │   │   ├── session_repository.py
│   │   │   │   └── auth_repository.py
│   │   │   └── migrations/     # Database migrations
│   │   │       ├── __init__.py
│   │   │       └── v1_initial.py
│   │   └── utils/              # Utility functions
│   │       ├── __init__.py
│   │       ├── security.py     # Security utilities
│   │       ├── validation.py   # Validation utilities
│   │       ├── encryption.py   # Encryption utilities
│   │       └── logging.py      # Logging utilities
│   └── tests/                  # Test suite
│       ├── __init__.py
│       ├── conftest.py         # Test configuration
│       ├── test_auth.py        # Authentication tests
│       ├── test_users.py       # User management tests
│       ├── test_sessions.py    # Session tests
│       └── test_integration.py # Integration tests
├── gateway/                    # Gateway configuration
│   ├── openapi.yaml           # OpenAPI specification
│   ├── openapi.override.yaml  # Environment-specific overrides
│   └── nginx.conf             # Nginx configuration
├── scripts/                   # Deployment scripts
│   ├── build.sh              # Build script
│   ├── deploy.sh             # Deployment script
│   └── health_check.sh       # Health check script
└── docs/                      # Documentation
    ├── README.md
    ├── API.md
    └── DEPLOYMENT.md
```

## Core Implementation Files

### Main Application (api/app/main.py)

```python
"""
API Gateway Main Application

This is the primary entry point for the Lucid API Gateway service.
All routing, middleware, and service initialization happens here.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
import uvicorn

from app.config import get_settings
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.cors import CORSConfig
from app.routers import (
    meta,
    auth,
    users,
    sessions,
    manifests,
    trust,
    chain,
    wallets
)
from app.database.connection import init_database
from app.utils.logging import setup_logging
from app.models.common import ErrorResponse, ErrorDetail
import uuid
from datetime import datetime

# Global settings
settings = get_settings()

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting API Gateway service")
    await init_database()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway service")

# Create FastAPI application
app = FastAPI(
    title="Lucid API Gateway",
    description="Primary entry point for all Lucid blockchain system APIs",
    version=settings.API_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware (order matters!)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORSConfig.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(meta.router, prefix="/api/v1/meta", tags=["Meta"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(manifests.router, prefix="/api/v1/manifests", tags=["Manifests"])
app.include_router(trust.router, prefix="/api/v1/trust", tags=["Trust"])
app.include_router(chain.router, prefix="/api/v1/chain", tags=["Chain"])
app.include_router(wallets.router, prefix="/api/v1/wallets", tags=["Wallets"])

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    error_detail = ErrorDetail(
        code="LUCID_ERR_1001",
        message="Invalid request data",
        details={"validation_errors": exc.errors()},
        request_id=request_id,
        timestamp=datetime.utcnow(),
        service="api-gateway",
        version="v1"
    )
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error=error_detail).dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # Map HTTP status codes to Lucid error codes
    error_code_map = {
        400: "LUCID_ERR_1001",
        401: "LUCID_ERR_2001",
        403: "LUCID_ERR_2004",
        404: "LUCID_ERR_4001",
        409: "LUCID_ERR_4002",
        422: "LUCID_ERR_1001",
        429: "LUCID_ERR_3001",
        500: "LUCID_ERR_5001",
        503: "LUCID_ERR_5008"
    }
    
    error_code = error_code_map.get(exc.status_code, "LUCID_ERR_5001")
    
    error_detail = ErrorDetail(
        code=error_code,
        message=exc.detail,
        request_id=request_id,
        timestamp=datetime.utcnow(),
        service="api-gateway",
        version="v1"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=error_detail).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    logger.exception(f"Unhandled exception: {exc}")
    
    error_detail = ErrorDetail(
        code="LUCID_ERR_5001",
        message="Internal server error",
        request_id=request_id,
        timestamp=datetime.utcnow(),
        service="api-gateway",
        version="v1"
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=error_detail).dict()
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.HTTP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
```

### Configuration Management (api/app/config.py)

```python
"""
Configuration Management

Centralized configuration for the API Gateway service using Pydantic settings.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator, Field
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = Field(default="api-gateway", env="SERVICE_NAME")
    API_VERSION: str = Field(default="v1", env="API_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    
    # Port Configuration
    HTTP_PORT: int = Field(default=8080, env="HTTP_PORT")
    HTTPS_PORT: int = Field(default=8081, env="HTTPS_PORT")
    
    # Security Configuration
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Database Configuration
    MONGODB_URI: str = Field(..., env="MONGODB_URI")
    MONGODB_DATABASE: str = Field(default="lucid_gateway", env="MONGODB_DATABASE")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
    # Backend Service URLs
    BLOCKCHAIN_CORE_URL: str = Field(..., env="BLOCKCHAIN_CORE_URL")
    SESSION_MANAGEMENT_URL: str = Field(..., env="SESSION_MANAGEMENT_URL")
    AUTH_SERVICE_URL: str = Field(..., env="AUTH_SERVICE_URL")
    TRON_PAYMENT_URL: str = Field(..., env="TRON_PAYMENT_URL")
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST_SIZE: int = Field(default=200, env="RATE_LIMIT_BURST_SIZE")
    
    # SSL Configuration
    SSL_ENABLED: bool = Field(default=True, env="SSL_ENABLED")
    SSL_CERT_PATH: Optional[str] = Field(None, env="SSL_CERT_PATH")
    SSL_KEY_PATH: Optional[str] = Field(None, env="SSL_KEY_PATH")
    
    # CORS Configuration
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    @validator('ALLOWED_HOSTS', pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('JWT_SECRET_KEY')
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
```

### Authentication Middleware (api/app/middleware/auth.py)

```python
"""
Authentication Middleware

Handles JWT token validation and user authentication for protected endpoints.
"""

import logging
from typing import Optional, List
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
import redis.asyncio as redis

from app.config import get_settings
from app.database.repositories.auth_repository import AuthRepository
from app.models.auth import TokenPayload, UserRole
from app.utils.security import verify_token_signature

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer()

class AuthMiddleware:
    """Authentication middleware for request processing"""
    
    def __init__(self, app):
        self.app = app
        self.auth_repo = AuthRepository()
        self.redis_client = None
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            await self.app(scope, receive, send)
            return
        
        # Extract and validate token
        token = await self._extract_token(request)
        if not token:
            await self._send_unauthorized_response(send)
            return
        
        # Validate token
        try:
            payload = await self._validate_token(token)
            request.state.user_id = payload.user_id
            request.state.user_role = payload.role
            request.state.token_payload = payload
            
        except HTTPException as e:
            await self._send_error_response(send, e.status_code, e.detail)
            return
        except Exception as e:
            logger.exception(f"Authentication error: {e}")
            await self._send_error_response(send, 500, "Authentication failed")
            return
        
        await self.app(scope, receive, send)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no authentication required)"""
        public_paths = [
            "/api/v1/meta/info",
            "/api/v1/meta/health",
            "/api/v1/meta/version",
            "/api/v1/auth/login",
            "/api/v1/auth/verify",
            "/api/v1/users"  # User registration
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    async def _validate_token(self, token: str) -> TokenPayload:
        """Validate JWT token and return payload"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Create token payload object
            token_payload = TokenPayload(**payload)
            
            # Check if token is blacklisted
            if await self._is_token_blacklisted(token_payload.jti):
                raise HTTPException(
                    status_code=401,
                    detail="Token has been revoked"
                )
            
            # Check user status
            user = await self.auth_repo.get_user_by_id(token_payload.user_id)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="User not found"
                )
            
            if user.locked_until and user.locked_until > datetime.utcnow():
                raise HTTPException(
                    status_code=401,
                    detail="Account is locked"
                )
            
            return token_payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except JWTClaimsError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token claims: {e}"
            )
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {e}"
            )
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted in Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        
        result = await self.redis_client.get(f"blacklist:{jti}")
        return result is not None
    
    async def _send_unauthorized_response(self, send):
        """Send 401 Unauthorized response"""
        response_body = {
            "error": {
                "code": "LUCID_ERR_2001",
                "message": "Authentication required",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "api-gateway",
                "version": "v1"
            }
        }
        
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(str(response_body))).encode()]
            ]
        })
        
        await send({
            "type": "http.response.body",
            "body": str(response_body).encode()
        })
    
    async def _send_error_response(self, send, status_code: int, message: str):
        """Send error response"""
        response_body = {
            "error": {
                "code": "LUCID_ERR_2001",
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "service": "api-gateway",
                "version": "v1"
            }
        }
        
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(str(response_body))).encode()]
            ]
        })
        
        await send({
            "type": "http.response.body",
            "body": str(response_body).encode()
        })

# Dependency for getting current user
async def get_current_user(request: Request) -> TokenPayload:
    """Get current authenticated user from request state"""
    if not hasattr(request.state, 'user_id'):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return request.state.token_payload

# Dependency for role-based access control
def require_role(required_roles: List[UserRole]):
    """Create dependency that requires specific user roles"""
    async def role_checker(current_user: TokenPayload = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )
        return current_user
    
    return role_checker

# Common role dependencies
require_admin = require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
require_super_admin = require_role([UserRole.SUPER_ADMIN])
require_node_operator = require_role([UserRole.NODE_OPERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN])
```

### Rate Limiting Middleware (api/app/middleware/rate_limit.py)

```python
"""
Rate Limiting Middleware

Implements tiered rate limiting for different endpoint types and user roles.
"""

import logging
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import json

from app.config import get_settings
from app.models.common import ErrorResponse, ErrorDetail
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()

class RateLimitMiddleware:
    """Rate limiting middleware for request throttling"""
    
    def __init__(self, app):
        self.app = app
        self.redis_client = None
        self.rate_limits = self._load_rate_limits()
    
    def _load_rate_limits(self) -> Dict[str, Dict]:
        """Load rate limiting configuration"""
        return {
            "public": {
                "requests_per_minute": 100,
                "burst_size": 200,
                "endpoints": [
                    "/api/v1/meta/*",
                    "/api/v1/auth/login",
                    "/api/v1/auth/verify",
                    "/api/v1/users"
                ]
            },
            "authenticated": {
                "requests_per_minute": 1000,
                "burst_size": 2000,
                "endpoints": [
                    "/api/v1/users/*",
                    "/api/v1/sessions/*",
                    "/api/v1/manifests/*",
                    "/api/v1/trust/*",
                    "/api/v1/chain/*",
                    "/api/v1/wallets/*"
                ]
            },
            "admin": {
                "requests_per_minute": 10000,
                "burst_size": 20000,
                "endpoints": [
                    "/api/v1/admin/*",
                    "/api/v1/meta/metrics"
                ]
            },
            "chunk_upload": {
                "bytes_per_second": 10485760,  # 10 MB/sec
                "endpoints": [
                    "/api/v1/sessions/*/chunks"
                ]
            },
            "blockchain_query": {
                "requests_per_minute": 500,
                "burst_size": 1000,
                "endpoints": [
                    "/api/v1/chain/blocks",
                    "/api/v1/chain/blocks/*"
                ]
            }
        }
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return
        
        # Determine rate limit tier
        rate_limit_tier = self._get_rate_limit_tier(request)
        if not rate_limit_tier:
            await self.app(scope, receive, send)
            return
        
        # Check rate limit
        try:
            allowed = await self._check_rate_limit(request, rate_limit_tier)
            if not allowed:
                await self._send_rate_limit_response(send, request)
                return
        except Exception as e:
            logger.exception(f"Rate limiting error: {e}")
            # Allow request to proceed if rate limiting fails
            await self.app(scope, receive, send)
            return
        
        await self.app(scope, receive, send)
    
    def _get_rate_limit_tier(self, request: Request) -> Optional[str]:
        """Determine rate limit tier for request"""
        path = request.url.path
        
        # Check admin endpoints
        if path.startswith("/api/v1/admin/") or path == "/api/v1/meta/metrics":
            # Check if user has admin role
            if hasattr(request.state, 'user_role'):
                if request.state.user_role in ['admin', 'super_admin']:
                    return "admin"
            return None
        
        # Check chunk upload endpoints
        if "/chunks" in path and request.method == "POST":
            return "chunk_upload"
        
        # Check blockchain query endpoints
        if path.startswith("/api/v1/chain/blocks"):
            return "blockchain_query"
        
        # Check public endpoints
        for endpoint_pattern in self.rate_limits["public"]["endpoints"]:
            if self._match_pattern(path, endpoint_pattern):
                return "public"
        
        # Check authenticated endpoints
        for endpoint_pattern in self.rate_limits["authenticated"]["endpoints"]:
            if self._match_pattern(path, endpoint_pattern):
                return "authenticated"
        
        return None
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches endpoint pattern"""
        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])
        return path == pattern
    
    async def _check_rate_limit(self, request: Request, tier: str) -> bool:
        """Check if request is within rate limit"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        
        # Get identifier (IP, user_id, or token)
        identifier = self._get_identifier(request, tier)
        if not identifier:
            return True
        
        # Get rate limit configuration
        config = self.rate_limits[tier]
        
        # Create rate limit key
        current_time = int(time.time())
        window_start = current_time - (current_time % 60)  # 1-minute window
        rate_limit_key = f"rate_limit:{tier}:{identifier}:{window_start}"
        
        # Check current request count
        current_count = await self.redis_client.get(rate_limit_key)
        current_count = int(current_count) if current_count else 0
        
        # Check burst limit
        burst_key = f"rate_limit_burst:{tier}:{identifier}"
        burst_count = await self.redis_client.get(burst_key)
        burst_count = int(burst_count) if burst_count else 0
        
        # Apply rate limiting logic
        if tier == "chunk_upload":
            # Special handling for chunk uploads (bandwidth-based)
            return await self._check_bandwidth_limit(request, identifier, config)
        
        # Standard request count limiting
        requests_per_minute = config["requests_per_minute"]
        burst_size = config["burst_size"]
        
        if current_count >= requests_per_minute:
            # Check burst allowance
            if burst_count >= burst_size:
                return False
            
            # Use burst allowance
            await self.redis_client.incr(burst_key)
            await self.redis_client.expire(burst_key, 300)  # 5-minute burst window
        
        # Increment request count
        await self.redis_client.incr(rate_limit_key)
        await self.redis_client.expire(rate_limit_key, 60)  # 1-minute window
        
        return True
    
    async def _check_bandwidth_limit(self, request: Request, identifier: str, config: Dict) -> bool:
        """Check bandwidth-based rate limit for chunk uploads"""
        content_length = request.headers.get("content-length")
        if not content_length:
            return True
        
        try:
            request_size = int(content_length)
            bytes_per_second = config["bytes_per_second"]
            
            # Create bandwidth tracking key
            current_time = int(time.time())
            bandwidth_key = f"bandwidth:{identifier}:{current_time}"
            
            # Check current bandwidth usage
            current_bandwidth = await self.redis_client.get(bandwidth_key)
            current_bandwidth = int(current_bandwidth) if current_bandwidth else 0
            
            if current_bandwidth + request_size > bytes_per_second:
                return False
            
            # Update bandwidth usage
            await self.redis_client.incrby(bandwidth_key, request_size)
            await self.redis_client.expire(bandwidth_key, 1)  # 1-second window
            
            return True
            
        except (ValueError, TypeError):
            return True
    
    def _get_identifier(self, request: Request, tier: str) -> Optional[str]:
        """Get unique identifier for rate limiting"""
        # For chunk uploads, use session-based identifier
        if tier == "chunk_upload":
            if hasattr(request.state, 'user_id'):
                return f"user:{request.state.user_id}"
            return f"ip:{request.client.host}"
        
        # For authenticated endpoints, use user ID
        if tier == "authenticated" and hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # For admin endpoints, use user ID
        if tier == "admin" and hasattr(request.state, 'user_id'):
            return f"admin:{request.state.user_id}"
        
        # Default to IP address
        return f"ip:{request.client.host}"
    
    async def _send_rate_limit_response(self, send, request: Request):
        """Send rate limit exceeded response"""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        error_detail = ErrorDetail(
            code="LUCID_ERR_3001",
            message="Rate limit exceeded",
            request_id=request_id,
            timestamp=datetime.utcnow(),
            service="api-gateway",
            version="v1"
        )
        
        response_body = ErrorResponse(error=error_detail).dict()
        
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                [b"content-type", b"application/json"],
                [b"retry-after", b"60"],
                [b"x-ratelimit-limit", str(self.rate_limits.get("authenticated", {}).get("requests_per_minute", 1000)).encode()],
                [b"x-ratelimit-remaining", b"0"],
                [b"x-ratelimit-reset", str(int(time.time()) + 60).encode()]
            ]
        })
        
        await send({
            "type": "http.response.body",
            "body": json.dumps(response_body).encode()
        })
```

## Distroless Container Configuration

### Dockerfile

```dockerfile
# Multi-stage build for distroless container
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY api/ ./api/
COPY gateway/ ./gateway/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Production stage - Distroless
FROM gcr.io/distroless/python3-debian12

# Set labels
LABEL maintainer="Lucid Development Team"
LABEL description="Lucid API Gateway - Distroless Container"
LABEL version="1.0.0"

# Copy Python packages from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY --from=builder /app/api /app/api
COPY --from=builder /app/gateway /app/gateway
COPY --from=builder /app/scripts /app/scripts

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/home/app/.local/bin:$PATH

# Create app user (distroless has no useradd)
USER 65532:65532

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/meta/health')"]

# Expose ports
EXPOSE 8080 8081

# Start application
CMD ["python", "-m", "api.app.main"]
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  api-gateway:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        BUILDPLATFORM: linux/amd64
        TARGETPLATFORM: linux/amd64
    image: lucid-api-gateway:latest
    container_name: lucid-api-gateway
    restart: unless-stopped
    
    ports:
      - "8080:8080"  # HTTP
      - "8081:8081"  # HTTPS
    
    environment:
      - SERVICE_NAME=api-gateway
      - API_VERSION=v1
      - DEBUG=false
      - ENVIRONMENT=production
      
      # Port Configuration
      - HTTP_PORT=8080
      - HTTPS_PORT=8081
      
      # Security Configuration
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=HS256
      - JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
      - JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
      
      # Database Configuration
      - MONGODB_URI=mongodb://mongodb:27017/lucid_gateway
      - REDIS_URL=redis://redis:6379/0
      
      # Backend Service URLs
      - BLOCKCHAIN_CORE_URL=http://blockchain-core:8084
      - SESSION_MANAGEMENT_URL=http://session-management:8085
      - AUTH_SERVICE_URL=http://auth-service:8086
      - TRON_PAYMENT_URL=http://tron-payment:8087
      
      # Rate Limiting Configuration
      - RATE_LIMIT_ENABLED=true
      - RATE_LIMIT_REQUESTS_PER_MINUTE=1000
      - RATE_LIMIT_BURST_SIZE=2000
      
      # SSL Configuration
      - SSL_ENABLED=true
      - SSL_CERT_PATH=/certs/api-gateway.crt
      - SSL_KEY_PATH=/certs/api-gateway.key
      
      # CORS Configuration
      - ALLOWED_HOSTS=api.lucid-blockchain.org,localhost
      - CORS_ORIGINS=https://app.lucid-blockchain.org,http://localhost:3000
      
      # Logging Configuration
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      
      # Monitoring Configuration
      - METRICS_ENABLED=true
      - HEALTH_CHECK_INTERVAL=30
    
    volumes:
      - ./certs:/certs:ro
      - ./logs:/app/logs
    
    depends_on:
      - mongodb
      - redis
      - blockchain-core
      - session-management
      - auth-service
    
    networks:
      - lucid-network
    
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/meta/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s

  # Dependencies
  mongodb:
    image: mongo:7.0
    container_name: lucid-mongodb
    restart: unless-stopped
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid_gateway
    volumes:
      - mongodb_data:/data/db
      - ./database/init_collections.js:/docker-entrypoint-initdb.d/init_collections.js:ro
    networks:
      - lucid-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7.2-alpine
    container_name: lucid-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - lucid-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  lucid-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  mongodb_data:
    driver: local
  redis_data:
    driver: local
```

## Naming Conventions

### Service Naming

```python
# Service names must follow the pattern: {cluster}-{service}
SERVICE_NAMES = {
    "api_gateway": "api-gateway",
    "blockchain_core": "lucid-blocks",  # Always use lucid_blocks for on-chain system
    "tron_payment": "tron-payment-service",  # Always isolated from blockchain
    "session_management": "session-management",
    "rdp_services": "rdp-services",
    "node_management": "node-management",
    "admin_interface": "admin-interface",
    "storage_database": "storage-database",
    "authentication": "auth-service"
}

# Container names follow the pattern: lucid-{cluster}-{service}
CONTAINER_NAMES = {
    "api_gateway": "lucid-api-gateway",
    "blockchain_core": "lucid-lucid-blocks",  # lucid_blocks container
    "tron_payment": "lucid-tron-payment-service",
    "session_management": "lucid-session-management",
    # ... etc
}
```

### Variable Naming

```python
# Python variables use snake_case
user_id = "uuid-here"
session_status = "active"
max_session_size_bytes = 107374182400

# Database fields use snake_case
user_collection = {
    "user_id": "uuid",
    "email_address": "user@example.com",
    "created_at": "2025-01-10T19:08:00Z",
    "hardware_wallet_enabled": True
}

# API endpoints use kebab-case
API_ENDPOINTS = {
    "/api/v1/sessions": "session_management",
    "/api/v1/trust-policies": "trust_policy_management",
    "/api/v1/blockchain-info": "blockchain_information"
}

# Error codes use UPPER_CASE with underscores
ERROR_CODES = {
    "LUCID_ERR_1001": "Invalid request data",
    "LUCID_ERR_2001": "Authentication required",
    "LUCID_ERR_3001": "Rate limit exceeded"
}
```

## Deployment Scripts

### Build Script (scripts/build.sh)

```bash
#!/bin/bash
set -e

# Build script for API Gateway
echo "Building Lucid API Gateway..."

# Set build arguments
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION=${VERSION:-1.0.0}
BUILDPLATFORM=${BUILDPLATFORM:-linux/amd64}

# Build Docker image
docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILDPLATFORM="$BUILDPLATFORM" \
    --tag lucid-api-gateway:latest \
    --tag lucid-api-gateway:$VERSION \
    .

# Verify image
echo "Verifying distroless container..."
docker run --rm lucid-api-gateway:latest python -c "print('Container is working')"

echo "Build completed successfully!"
echo "Image: lucid-api-gateway:$VERSION"
```

### Deployment Script (scripts/deploy.sh)

```bash
#!/bin/bash
set -e

# Deployment script for API Gateway
echo "Deploying Lucid API Gateway..."

# Load environment variables
source .env

# Validate required environment variables
required_vars=("JWT_SECRET_KEY" "MONGO_PASSWORD" "REDIS_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set"
        exit 1
    fi
done

# Create necessary directories
mkdir -p logs certs

# Generate SSL certificates if not present
if [ ! -f "certs/api-gateway.crt" ]; then
    echo "Generating SSL certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout certs/api-gateway.key \
        -out certs/api-gateway.crt -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=api.lucid-blockchain.org"
fi

# Deploy with Docker Compose
docker-compose up -d

# Wait for health check
echo "Waiting for service to be healthy..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -f http://localhost:8080/api/v1/meta/health > /dev/null 2>&1; then
        echo "Service is healthy!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "Error: Service failed to become healthy"
    docker-compose logs api-gateway
    exit 1
fi

echo "Deployment completed successfully!"
echo "API Gateway is available at:"
echo "  HTTP:  http://localhost:8080"
echo "  HTTPS: https://localhost:8081"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

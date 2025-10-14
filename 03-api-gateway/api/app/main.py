"""
API Gateway Main Application

File: 03-api-gateway/api/app/main.py
Purpose: Primary entry point for the Lucid API Gateway service.
All routing, middleware, and service initialization happens here.

Architecture Notes:
- lucid_blocks: On-chain blockchain system
- TRON: Isolated payment service (NOT part of lucid_blocks)
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
    logger.info(f"Service Name: {settings.SERVICE_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Blockchain Core: {settings.BLOCKCHAIN_CORE_URL}")
    logger.info(f"TRON Payment (isolated): {settings.TRON_PAYMENT_URL}")
    
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

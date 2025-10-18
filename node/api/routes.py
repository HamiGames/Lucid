# Path: node/api/routes.py
# Lucid Node Management API Routes
# Based on LUCID-STRICT requirements per Spec-1c

"""
Main API router for Lucid Node Management system.

This module sets up the FastAPI application and mounts all sub-routers
for the node management API endpoints.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

from .nodes import router as nodes_router
from .pools import router as pools_router
from .resources import router as resources_router
from .payouts import router as payouts_router
from .poot import router as poot_router

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Lucid Node Management API",
    description="API for managing worker nodes, pools, and PoOT operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.lucid.onion", "https://admin.lucid.onion"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.lucid.onion", "localhost", "127.0.0.1"]
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to all requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add request ID to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests"""
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.info(f"Request {request_id}: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response {request_id}: {response.status_code} ({process_time:.3f}s)")
    
    return response

# Mount API routers
app.include_router(
    nodes_router,
    prefix="/api/v1/nodes",
    tags=["Nodes"]
)

app.include_router(
    pools_router,
    prefix="/api/v1/nodes/pools",
    tags=["Pools"]
)

app.include_router(
    resources_router,
    prefix="/api/v1/nodes",
    tags=["Resources"]
)

app.include_router(
    payouts_router,
    prefix="/api/v1/nodes",
    tags=["Payouts"]
)

app.include_router(
    poot_router,
    prefix="/api/v1/nodes",
    tags=["PoOT"]
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "node-management-api",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "running"
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Lucid Node Management API",
        "version": "1.0.0",
        "description": "API for managing worker nodes, pools, and PoOT operations",
        "docs": "/docs",
        "health": "/health"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(f"Unhandled exception {request_id}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "LUCID_ERR_5000",
                "message": "Internal server error",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "node-management-api",
                "version": "1.0.0"
            }
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with Lucid error format"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"LUCID_ERR_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "node-management-api",
                "version": "1.0.0"
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8095)

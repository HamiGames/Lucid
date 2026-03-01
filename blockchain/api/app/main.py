"""
Blockchain API Main Application

This module initializes the FastAPI application for the Blockchain API.
Implements the OpenAPI 3.0 specification and includes all middleware and routes.

Features:
- FastAPI application with OpenAPI documentation
- Authentication middleware
- Rate limiting middleware
- Request logging middleware
- All blockchain API routes
- Health check endpoints
- Comprehensive error handling
- System monitoring and metrics
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Dict, Any

from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.logging import LoggingMiddleware
from .routes import register_routes
from .config import settings
from .logging_config import setup_logging
from .health_check import health_check_service
from .metrics import metrics_service
from .database import init_database, close_database
from .cache import init_cache, close_cache

# Configure logging
setup_logging(settings.LOG_LEVEL, "standard")
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.get_cors_methods_list(),
    allow_headers=settings.get_cors_headers_list(),
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Register all API routes
register_routes(app)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Lucid Blockchain API")
    logger.info(f"API Documentation available at /api/v1/docs")
    logger.info(f"ReDoc Documentation available at /api/v1/redoc")
    
    # Initialize database
    try:
        await init_database(settings.DATABASE_URL, settings.DATABASE_NAME)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize cache
    try:
        await init_cache(settings.REDIS_URL, settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
        logger.info("Cache initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        # Cache is optional, continue without it
    
    # Initialize health checks
    try:
        await health_check_service.get_health_status()
        logger.info("Health checks initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize health checks: {e}")
        # Health checks are optional, continue without them
    
    logger.info("Lucid Blockchain API started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Lucid Blockchain API")
    
    # Close database connection
    try:
        await close_database()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")
    
    # Close cache connection
    try:
        await close_cache()
        logger.info("Cache connection closed")
    except Exception as e:
        logger.error(f"Error closing cache connection: {e}")
    
    logger.info("Lucid Blockchain API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
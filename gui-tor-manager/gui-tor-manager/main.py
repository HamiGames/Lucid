"""
FastAPI Application Main Module for GUI Tor Manager
Sets up FastAPI app with middleware, routers, and lifespan management
"""

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

from .config import get_config
from .healthcheck import get_health_check
from .utils.logging import setup_logging, get_logger
from .middleware.cors import setup_cors_middleware
from .middleware.logging import LoggingMiddleware
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware

# Setup logging
logger = setup_logging(level="INFO", service_name="gui-tor-manager")


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown"""
    try:
        # Startup
        logger.info("GUI Tor Manager starting up...")
        
        config = get_config()
        config.verify_critical_settings()
        
        logger.info(f"Service: {config.settings.SERVICE_NAME}")
        logger.info(f"Port: {config.settings.PORT}")
        logger.info(f"Tor Proxy: {config.settings.TOR_PROXY_URL}")
        
        yield
        
        # Shutdown
        logger.info("GUI Tor Manager shutting down...")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        sys.exit(1)


# Create FastAPI app
app = FastAPI(
    title="GUI Tor Manager",
    description="Tor management API for Electron GUI",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup CORS
setup_cors_middleware(app)

# Add middleware (in reverse order of execution)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_manager = get_health_check()
    status = await health_manager.get_overall_status()
    
    if status["status"] == "healthy":
        return JSONResponse(content=status, status_code=200)
    elif status["status"] == "degraded":
        return JSONResponse(content=status, status_code=503)
    else:
        return JSONResponse(content=status, status_code=503)


# Root endpoint
@app.get("/")
async def root():
    """Root API endpoint"""
    config = get_config()
    return {
        "service": config.settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "operational",
    }


# API v1 root
@app.get("/api/v1")
async def api_v1_root():
    """API v1 root endpoint"""
    return {
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/tor/status",
            "/api/v1/tor/circuits",
            "/api/v1/onion/list",
            "/api/v1/onion/create",
            "/api/v1/proxy/status",
            "/health",
        ]
    }


# Import and include routers
from routers import tor, onion, proxy, health

app.include_router(tor.router, prefix="/api/v1/tor", tags=["tor"])
app.include_router(onion.router, prefix="/api/v1/onion", tags=["onion"])
app.include_router(proxy.router, prefix="/api/v1/proxy", tags=["proxy"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "main:app",
        host=config.settings.HOST,
        port=config.settings.PORT,
        log_level=config.settings.LOG_LEVEL.lower(),
        reload=config.settings.DEBUG,
    )

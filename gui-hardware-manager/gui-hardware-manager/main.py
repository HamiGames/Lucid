"""
FastAPI Main Application for GUI Hardware Manager
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from gui_hardware_manager.config import get_settings
from gui_hardware_manager.middleware.logging import LoggingMiddleware
from gui_hardware_manager.middleware.rate_limit import RateLimitMiddleware
from gui_hardware_manager.routers import health, devices, wallets, sign
from gui_hardware_manager.services.hardware_service import HardwareService

logger = logging.getLogger(__name__)

# Global state
app_state = {
    "hardware_service": None,
    "settings": None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info("Starting GUI Hardware Manager...")
    settings = get_settings()
    app_state["settings"] = settings
    app_state["hardware_service"] = HardwareService(settings)
    
    # Initialize hardware service
    await app_state["hardware_service"].initialize()
    logger.info("Hardware service initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GUI Hardware Manager...")
    if app_state["hardware_service"]:
        await app_state["hardware_service"].cleanup()
    logger.info("Hardware service cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="GUI Hardware Manager",
    description="Hardware wallet management service for Lucid Electron GUI",
    version="1.0.0",
    lifespan=lifespan
)

# Get settings for middleware configuration
settings = get_settings()

# Add CORS middleware
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.get_cors_methods_list(),
        allow_headers=settings.get_cors_headers_list(),
    )

# Add custom middleware
app.add_middleware(LoggingMiddleware)
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware, 
                      requests_per_minute=settings.rate_limit_requests,
                      burst_size=settings.rate_limit_burst)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
app.include_router(wallets.router, prefix="/api/v1", tags=["Wallets"])
app.include_router(sign.router, prefix="/api/v1", tags=["Signing"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GUI Hardware Manager",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.gui_hardware_manager_host,
        port=settings.gui_hardware_manager_port,
        log_level="info"
    )

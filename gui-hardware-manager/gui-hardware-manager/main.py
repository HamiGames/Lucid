"""
FastAPI Main Application for GUI Hardware Manager
Handles initialization, middleware setup, and router integration
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

# Global state for service management
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
    
    # Log configuration
    logger.info(f"Service: {settings.SERVICE_NAME}")
    logger.info(f"Port: {settings.PORT}")
    logger.info(f"Environment: {settings.LUCID_ENV}")
    logger.info(f"Platform: {settings.LUCID_PLATFORM}")
    logger.info(f"Hardware Support - Ledger: {settings.LEDGER_ENABLED}, Trezor: {settings.TREZOR_ENABLED}, KeepKey: {settings.KEEPKEY_ENABLED}")
    
    # Initialize hardware service
    app_state["hardware_service"] = HardwareService(settings)
    await app_state["hardware_service"].initialize()
    logger.info("Hardware service initialized successfully")
    
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

# Add CORS middleware if enabled
if settings.CORS_ENABLED:
    logger.info("CORS middleware enabled")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.get_cors_methods_list(),
        allow_headers=settings.get_cors_headers_list(),
    )

# Add custom middleware
app.add_middleware(LoggingMiddleware)
if settings.RATE_LIMIT_ENABLED:
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_REQUESTS} req/min")
    app.add_middleware(RateLimitMiddleware, 
                      requests_per_minute=settings.RATE_LIMIT_REQUESTS,
                      burst_size=settings.RATE_LIMIT_BURST)

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
    """Root endpoint - service information"""
    return {
        "service": "GUI Hardware Manager",
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.LUCID_ENV,
    }


@app.get("/version")
async def version():
    """Version endpoint"""
    return {
        "version": "1.0.0",
        "service": "gui-hardware-manager",
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )

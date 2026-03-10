"""
LUCID TRON Relay Service - Main Application
READ-ONLY blockchain relay and caching service for TRON

This service provides:
  - Transaction verification and validation
  - Blockchain data caching and relay
  - Read-only access to TRON network
  - NO private key access or management
  - Multiple relay modes: full, cache, validator, monitor

Configuration via environment variables and YAML config files
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Distroless-safe path resolution
from .config import config, get_service_config, validate_config
from .services.tron_relay import tron_relay_service

# Import utility modules
from .utils.logging_config import setup_structured_logging
from .utils.metrics import get_metrics_collector
from .utils.health_check import get_health_checker
from .utils.config_loader import get_config_loader, load_yaml_config
from .utils.circuit_breaker import get_circuit_breaker_manager, CircuitBreakerConfig
from .utils.rate_limiter import get_rate_limiter_manager, RateLimitConfig

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", config.log_level.value if hasattr(config.log_level, 'value') else str(config.log_level))
log_file = os.getenv("LOG_FILE", os.getenv("TRON_RELAY_LOG_FILE", "/app/logs/tron-relay.log"))
log_format = os.getenv("LOG_FORMAT", "json")

# Ensure log directory exists
log_dir = Path(log_file).parent
log_dir.mkdir(parents=True, exist_ok=True)

# Setup logging
logger = setup_structured_logging(
    service_name="lucid-tron-relay",
    log_level=log_level,
    log_file=log_file,
    log_format=log_format
)

# Initialize app-level state
app_state = {
    "relay_mode": os.getenv("RELAY_MODE", "full"),
    "relay_id": os.getenv("RELAY_ID", "relay-001"),
    "tron_network": os.getenv("TRON_NETWORK", "mainnet"),
    "cache_enabled": os.getenv("CACHE_ENABLED", "true").lower() == "true",
    "cache_ttl": int(os.getenv("CACHE_TTL", "3600")),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup and shutdown"""
    logger.info(f"Starting LUCID TRON Relay Service (Mode: {app_state['relay_mode']})")
    
    # Startup logic
    try:
        # Initialize relay service
        await tron_relay_service.initialize(app_state)
        logger.info("TRON relay service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize relay service: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down LUCID TRON Relay Service")
    try:
        await tron_relay_service.shutdown()
        logger.info("TRON relay service shutdown completed")
    except Exception as e:
        logger.error(f"Error during relay service shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="LUCID TRON Relay Service",
    description="READ-ONLY TRON blockchain relay and caching service",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware
trusted_hosts = os.getenv("TRUSTED_HOSTS", "*").split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts,
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for container health monitoring"""
    try:
        health_status = await tron_relay_service.get_health_status()
        return {
            "status": "healthy" if health_status.get("is_healthy") else "degraded",
            "service": "lucid-tron-relay",
            "mode": app_state["relay_mode"],
            "relay_id": app_state["relay_id"],
            "network": app_state["tron_network"],
            "details": health_status,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "lucid-tron-relay",
            "error": str(e),
        }, status.HTTP_503_SERVICE_UNAVAILABLE


# Readiness check endpoint
@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint"""
    try:
        is_ready = await tron_relay_service.is_ready()
        if is_ready:
            return {"status": "ready", "service": "lucid-tron-relay"}
        else:
            return {
                "status": "not_ready",
                "service": "lucid-tron-relay",
            }, status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "service": "lucid-tron-relay",
            "error": str(e),
        }, status.HTTP_503_SERVICE_UNAVAILABLE


# Liveness check endpoint
@app.get("/live", tags=["health"])
async def liveness_check():
    """Liveness check endpoint"""
    return {"status": "alive", "service": "lucid-tron-relay"}


# Relay information endpoint
@app.get("/api/relay/info", tags=["relay"])
async def get_relay_info():
    """Get relay service information"""
    return {
        "relay_id": app_state["relay_id"],
        "mode": app_state["relay_mode"],
        "network": app_state["tron_network"],
        "cache_enabled": app_state["cache_enabled"],
        "cache_ttl": app_state["cache_ttl"],
    }


# Relay status endpoint
@app.get("/api/relay/status", tags=["relay"])
async def get_relay_status():
    """Get relay service status"""
    try:
        status_info = await tron_relay_service.get_status()
        return {
            "relay_id": app_state["relay_id"],
            "status": "operational" if status_info.get("is_operational") else "degraded",
            "details": status_info,
        }
    except Exception as e:
        logger.error(f"Failed to get relay status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Metrics endpoint
@app.get("/api/metrics", tags=["metrics"])
async def get_metrics():
    """Get service metrics"""
    try:
        metrics = await tron_relay_service.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("FastAPI application started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("FastAPI application shutting down")


def main():
    """Main entry point"""
    try:
        # Get configuration
        service_port = int(os.getenv("SERVICE_PORT", os.getenv("TRON_RELAY_PORT", "8098")))
        service_host = os.getenv("SERVICE_HOST", "0.0.0.0")
        workers = int(os.getenv("WORKERS", "1"))
        
        logger.info(f"Starting TRON Relay Service")
        logger.info(f"  Relay ID: {app_state['relay_id']}")
        logger.info(f"  Mode: {app_state['relay_mode']}")
        logger.info(f"  Network: {app_state['tron_network']}")
        logger.info(f"  Host: {service_host}:{service_port}")
        logger.info(f"  Workers: {workers}")
        logger.info(f"  Cache: {'enabled' if app_state['cache_enabled'] else 'disabled'}")
        
        # Run uvicorn server
        uvicorn.run(
            app,
            host=service_host,
            port=service_port,
            workers=workers,
            log_level=log_level.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Relay service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in relay service: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

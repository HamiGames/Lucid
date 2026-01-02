#!/usr/bin/env python3
"""
LUCID TRON Relay - Main Entry Point
Read-only TRON network relay for distributed caching and verification

SECURITY: This service has NO private key access and performs READ-ONLY operations only.
It provides:
- TRON blockchain data caching
- Transaction verification
- Balance checks
- Receipt validation

It does NOT:
- Sign transactions
- Broadcast transactions
- Access any private keys
- Make payout decisions
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config, get_config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.value),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# Try to add file handler if logs directory exists
try:
    log_dir = Path(config.log_file).parent
    if log_dir.exists():
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(file_handler)
except Exception as e:
    logger.warning(f"Could not add file handler: {e}")


# Service state
service_state: Dict[str, Any] = {
    "started_at": None,
    "registered_with_master": False,
    "cache_stats": {"hits": 0, "misses": 0},
    "verification_stats": {"total": 0, "successful": 0, "failed": 0},
    "last_tron_sync": None,
    "healthy": False
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info(f"Starting {config.service_name} v{config.service_version}")
    logger.info(f"Relay ID: {config.relay_id}")
    logger.info(f"Mode: {config.relay_mode.value}")
    logger.info(f"TRON Network: {config.tron_network}")
    logger.info(f"Master URL: {config.tron_master_url}")
    
    service_state["started_at"] = datetime.utcnow().isoformat()
    
    # Initialize services
    try:
        # Import services after config is loaded
        from services.relay_service import relay_service
        from services.cache_manager import cache_manager
        
        # Initialize cache
        await cache_manager.initialize()
        logger.info("Cache manager initialized")
        
        # Initialize relay service
        await relay_service.initialize()
        logger.info("Relay service initialized")
        
        # Register with master if enabled
        if config.master_registration_enabled:
            asyncio.create_task(register_with_master())
        
        # Start background tasks
        asyncio.create_task(heartbeat_loop())
        asyncio.create_task(cache_cleanup_loop())
        
        service_state["healthy"] = True
        logger.info(f"✅ {config.service_name} started successfully on port {config.service_port}")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        service_state["healthy"] = False
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {config.service_name}")
    service_state["healthy"] = False
    
    try:
        from services.relay_service import relay_service
        from services.cache_manager import cache_manager
        
        await relay_service.shutdown()
        await cache_manager.shutdown()
        logger.info("Services shut down gracefully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def register_with_master():
    """Register this relay with the TRON master service"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            registration_data = {
                "relay_id": config.relay_id,
                "node_id": config.node_id,
                "relay_url": f"http://{config.service_host}:{config.service_port}",
                "capabilities": ["cache", "verify", "monitor"],
                "mode": config.relay_mode.value,
                "api_key_available": bool(config.get_api_key()),
                "network": config.tron_network
            }
            
            response = await client.post(
                f"{config.tron_master_url}/api/v1/relays/register",
                json=registration_data
            )
            
            if response.status_code == 200:
                service_state["registered_with_master"] = True
                logger.info(f"Successfully registered with master: {config.tron_master_url}")
            else:
                logger.warning(f"Master registration returned {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.warning(f"Could not register with master (will retry): {e}")
        service_state["registered_with_master"] = False


async def heartbeat_loop():
    """Send periodic heartbeats to master"""
    import httpx
    
    while True:
        try:
            await asyncio.sleep(config.master_heartbeat_interval)
            
            if not config.master_registration_enabled:
                continue
                
            async with httpx.AsyncClient(timeout=10.0) as client:
                heartbeat_data = {
                    "relay_id": config.relay_id,
                    "cache_stats": service_state["cache_stats"],
                    "verification_stats": service_state["verification_stats"],
                    "healthy": service_state["healthy"],
                    "last_sync": service_state["last_tron_sync"]
                }
                
                response = await client.post(
                    f"{config.tron_master_url}/api/v1/relays/heartbeat",
                    json=heartbeat_data
                )
                
                if response.status_code != 200:
                    logger.warning(f"Heartbeat failed: {response.status_code}")
                    # Try to re-register
                    if not service_state["registered_with_master"]:
                        await register_with_master()
                        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Heartbeat error: {e}")


async def cache_cleanup_loop():
    """Periodically clean up expired cache entries"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            from services.cache_manager import cache_manager
            cleaned = await cache_manager.cleanup_expired()
            
            if cleaned > 0:
                logger.debug(f"Cleaned up {cleaned} expired cache entries")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Cache cleanup error: {e}")


# Create FastAPI application
app = FastAPI(
    title="LUCID TRON Relay",
    description="Read-only TRON network relay for distributed caching and verification. NO PRIVATE KEY ACCESS.",
    version=config.service_version,
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Include API routers
from api.relay_api import router as relay_router
from api.cache_api import router as cache_router
from api.verify_api import router as verify_router

app.include_router(relay_router, prefix="/api/v1/relay", tags=["Relay"])
app.include_router(cache_router, prefix="/api/v1/tron", tags=["TRON Data (Cached)"])
app.include_router(verify_router, prefix="/api/v1/verify", tags=["Verification"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": config.service_name,
        "version": config.service_version,
        "relay_id": config.relay_id,
        "mode": config.relay_mode.value,
        "network": config.tron_network,
        "status": "healthy" if service_state["healthy"] else "degraded",
        "security": "READ-ONLY - No private key access"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from services.relay_service import relay_service
    
    tron_connected = await relay_service.check_tron_connection()
    
    health_status = {
        "status": "healthy" if service_state["healthy"] and tron_connected else "degraded",
        "relay_id": config.relay_id,
        "mode": config.relay_mode.value,
        "tron_network": config.tron_network,
        "tron_connected": tron_connected,
        "registered_with_master": service_state["registered_with_master"],
        "cache_stats": service_state["cache_stats"],
        "verification_stats": service_state["verification_stats"],
        "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(service_state["started_at"])).total_seconds() if service_state["started_at"] else 0,
        "security": "READ-ONLY"
    }
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from services.cache_manager import cache_manager
    
    metrics_data = {
        "cache_hits_total": service_state["cache_stats"]["hits"],
        "cache_misses_total": service_state["cache_stats"]["misses"],
        "verifications_total": service_state["verification_stats"]["total"],
        "verifications_successful": service_state["verification_stats"]["successful"],
        "verifications_failed": service_state["verification_stats"]["failed"],
        "cache_size_bytes": await cache_manager.get_cache_size(),
        "registered_with_master": 1 if service_state["registered_with_master"] else 0
    }
    
    # Format as Prometheus metrics
    lines = []
    for key, value in metrics_data.items():
        lines.append(f"lucid_tron_relay_{key} {value}")
    
    return "\n".join(lines)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.debug else "An unexpected error occurred"
        }
    )


def main():
    """Main entry point"""
    try:
        logger.info(f"Starting {config.service_name}")
        logger.info(f"Host: {config.service_host}:{config.service_port}")
        logger.info(f"Workers: {config.workers}")
        logger.info(f"Debug: {config.debug}")
        
        uvicorn.run(
            "main:app",
            host=config.service_host,
            port=config.service_port,
            workers=config.workers,
            log_level=config.log_level.value.lower(),
            access_log=True,
            reload=config.debug
        )
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


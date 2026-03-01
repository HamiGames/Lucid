"""
LUCID TRON Staking Service - Main Entry Point
Dedicated container: tron-staking
Port: 8096
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import uvicorn

# Add payment-systems directory to path
payment_systems_dir = Path(__file__).parent.parent
if str(payment_systems_dir) not in sys.path:
    sys.path.insert(0, str(payment_systems_dir))

from tron.services.trx_staking import TRXStakingService
from tron.api.staking import router as staking_router

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instance
staking_service: Optional[TRXStakingService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global staking_service
    
    # Startup
    logger.info("Starting TRON Staking Service...")
    
    try:
        # Initialize staking service
        staking_service = TRXStakingService()
        logger.info("TRON Staking Service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start TRON Staking Service: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down TRON Staking Service...")
        
        try:
            if staking_service:
                # Service cleanup
                logger.info("Staking service stopped")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="TRON Staking Service",
    description="TRX staking and resource management service for LUCID platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
    allow_methods=os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(","),
    allow_headers=os.getenv("CORS_HEADERS", "*").split(","),
)

# Include routers
app.include_router(staking_router, prefix="/api/v1/tron", tags=["TRX Staking"])


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global staking_service
    try:
        health_status = {
            "status": "healthy",
            "service": "tron-staking",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if service is initialized
        if staking_service:
            health_status["service_initialized"] = True
            try:
                stats = await staking_service.get_service_stats()
                health_status["staking"] = {
                    "total_staking_records": stats.get("total_staking_records", 0),
                    "active_staking_records": stats.get("active_staking_records", 0),
                    "total_staked_trx": stats.get("total_staked_trx", 0),
                    "total_resource_records": stats.get("total_resource_records", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to get staking stats: {e}")
                health_status["status"] = "degraded"
        else:
            health_status["service_initialized"] = False
            health_status["status"] = "unhealthy"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return health_status if status_code == 200 else (health_status, status_code)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, 500


@app.get("/health/live")
async def liveness_check():
    """Liveness probe - is the service running?"""
    try:
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 503


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe - is the service ready to serve requests?"""
    global staking_service
    try:
        if staking_service:
            return {
                "status": "ready",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, 503
    except Exception as e:
        return {"status": "error", "error": str(e)}, 503


@app.get("/status")
async def service_status():
    """Get service status"""
    global staking_service
    try:
        if not staking_service:
            return {"status": "not_initialized"}, 503
        
        stats = await staking_service.get_service_stats()
        return {
            "service": "tron-staking",
            "status": "running",
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return {"error": str(e)}, 500


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "tron-staking",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "staking_api": "/api/v1/tron/staking",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    try:
        metrics_enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        if not metrics_enabled:
            raise HTTPException(status_code=404, detail="Metrics not enabled")
        
        # Placeholder for metrics
        return {
            "service": "tron-staking",
            "metrics_enabled": True,
            "note": "Full Prometheus metrics implementation required"
        }
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point"""
    try:
        # Get configuration from environment variables
        host = os.getenv("SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("SERVICE_PORT", os.getenv("STAKING_PORT", "8096")))
        workers = int(os.getenv("WORKERS", "1"))
        timeout = int(os.getenv("TIMEOUT", "30"))
        log_level_str = os.getenv("LOG_LEVEL", "INFO").lower()
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        access_log = os.getenv("ACCESS_LOG", "true").lower() == "true"
        
        logger.info(f"Starting TRON Staking Service on {host}:{port}")
        logger.info(f"Configuration: workers={workers}, timeout={timeout}, debug={debug_mode}")
        
        # Start the application
        uvicorn.run(
            "staking_main:app",
            host=host,
            port=port,
            workers=workers,
            timeout_keep_alive=timeout,
            log_level=log_level_str,
            access_log=access_log,
            reload=debug_mode
        )
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

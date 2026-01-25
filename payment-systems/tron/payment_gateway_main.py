"""
LUCID TRON Payment Gateway Service - Main Entry Point
Dedicated container: tron-payment-gateway
Port: 8097
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

# Add payment-systems directory to path
payment_systems_dir = Path(__file__).parent.parent
if str(payment_systems_dir) not in sys.path:
    sys.path.insert(0, str(payment_systems_dir))

from tron.services.payment_gateway_extended import PaymentGatewayService
from tron.api.payment_gateway import router as payment_gateway_router

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instance
payment_service: Optional[PaymentGatewayService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global payment_service
    
    # Startup
    logger.info("Starting TRON Payment Gateway Service...")
    
    try:
        # Initialize payment gateway service
        payment_service = PaymentGatewayService()
        logger.info("TRON Payment Gateway Service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start TRON Payment Gateway Service: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down TRON Payment Gateway Service...")
        
        try:
            if payment_service:
                # Service cleanup
                logger.info("Payment gateway service stopped")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="TRON Payment Gateway Service",
    description="Payment processing and gateway operations for LUCID platform",
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
app.include_router(payment_gateway_router, tags=["Payment Gateway"])


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global payment_service
    try:
        health_status = {
            "status": "healthy",
            "service": "tron-payment-gateway",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if service is initialized
        if payment_service:
            health_status["service_initialized"] = True
            try:
                metrics = await payment_service.get_metrics()
                health_status["metrics"] = {
                    "total_payments": metrics.get("metrics", {}).get("total_payments", 0),
                    "successful_payments": metrics.get("metrics", {}).get("successful_payments", 0),
                    "batches_processed": metrics.get("metrics", {}).get("batches_processed", 0),
                }
            except Exception as e:
                logger.warning(f"Failed to get payment metrics: {e}")
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
    global payment_service
    try:
        if payment_service:
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
    global payment_service
    try:
        if not payment_service:
            return {"status": "not_initialized"}, 503
        
        metrics = await payment_service.get_metrics()
        return {
            "service": "tron-payment-gateway",
            "status": "running",
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return {"error": str(e)}, 500


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "tron-payment-gateway",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "payments_api": "/api/v1/payments",
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
        
        global payment_service
        if not payment_service:
            return {"error": "Service not initialized"}, 503
        
        metrics = await payment_service.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point"""
    try:
        # Get configuration from environment variables
        host = os.getenv("SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("SERVICE_PORT", os.getenv("PAYMENT_GATEWAY_PORT", "8097")))
        workers = int(os.getenv("WORKERS", "1"))
        timeout = int(os.getenv("TIMEOUT", "30"))
        log_level_str = os.getenv("LOG_LEVEL", "INFO").lower()
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        access_log = os.getenv("ACCESS_LOG", "true").lower() == "true"
        
        logger.info(f"Starting TRON Payment Gateway on {host}:{port}")
        logger.info(f"Configuration: workers={workers}, timeout={timeout}, debug={debug_mode}")
        
        # Start the application
        import uvicorn
        uvicorn.run(
            "payment_gateway_main:app",
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

"""
LUCID Payment Systems - TRON Payment Services Main Entry Point
Main application for TRON payment services
Distroless container: lucid-tron-payment-service:latest
"""

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Removed app.config import - using local config module
from .config import config, get_service_config, get_api_endpoints, validate_config
from .services.tron_client import tron_client_service
from .services.wallet_manager import wallet_manager_service
from .services.usdt_manager import usdt_manager_service
from .services.payout_router import payout_router_service
from .services.payment_gateway import payment_gateway_service
from .services.trx_staking import trx_staking_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.value),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/data/payment-systems/logs/tron-payment-service.log')
    ]
)
logger = logging.getLogger(__name__)

# Service instances
services = {
    "tron_client": tron_client_service,
    "wallet_manager": wallet_manager_service,
    "usdt_manager": usdt_manager_service,
    "payout_router": payout_router_service,
    "payment_gateway": payment_gateway_service,
    "trx_staking": trx_staking_service
}

# Service status tracking
service_status = {
    "tron_client": {"status": "starting", "last_check": None, "error": None},
    "wallet_manager": {"status": "starting", "last_check": None, "error": None},
    "usdt_manager": {"status": "starting", "last_check": None, "error": None},
    "payout_router": {"status": "starting", "last_check": None, "error": None},
    "payment_gateway": {"status": "starting", "last_check": None, "error": None},
    "trx_staking": {"status": "starting", "last_check": None, "error": None}
}

# Health check tasks
health_check_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting TRON Payment Services...")
    
    # Validate configuration
    config_errors = validate_config()
    if config_errors:
        logger.error("Configuration validation failed:")
        for error in config_errors:
            logger.error(f"  - {error}")
        if config.get("production_mode", False):
            raise RuntimeError("Configuration validation failed in production mode")
    
    # Initialize services
    await initialize_services()
    
    # Start health monitoring
    await start_health_monitoring()
    
    logger.info("TRON Payment Services started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TRON Payment Services...")
    
    # Stop health monitoring
    await stop_health_monitoring()
    
    # Stop services
    await stop_services()
    
    logger.info("TRON Payment Services stopped")

async def initialize_services():
    """Initialize all services"""
    try:
        logger.info("Initializing services...")
        
        # Initialize each service
        for service_name, service in services.items():
            try:
                logger.info(f"Initializing {service_name}...")
                
                # Service-specific initialization
                if hasattr(service, 'initialize'):
                    await service.initialize()
                
                service_status[service_name]["status"] = "running"
                service_status[service_name]["last_check"] = time.time()
                service_status[service_name]["error"] = None
                
                logger.info(f"{service_name} initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize {service_name}: {e}")
                service_status[service_name]["status"] = "error"
                service_status[service_name]["error"] = str(e)
        
        logger.info("Services initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        raise

async def start_health_monitoring():
    """Start health monitoring tasks"""
    try:
        logger.info("Starting health monitoring...")
        
        # Create health check tasks for each service
        for service_name in services.keys():
            task = asyncio.create_task(monitor_service_health(service_name))
            health_check_tasks.append(task)
        
        logger.info("Health monitoring started")
        
    except Exception as e:
        logger.error(f"Error starting health monitoring: {e}")
        raise

async def stop_health_monitoring():
    """Stop health monitoring tasks"""
    try:
        logger.info("Stopping health monitoring...")
        
        # Cancel all health check tasks
        for task in health_check_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*health_check_tasks, return_exceptions=True)
        
        health_check_tasks.clear()
        
        logger.info("Health monitoring stopped")
        
    except Exception as e:
        logger.error(f"Error stopping health monitoring: {e}")
        raise

async def stop_services():
    """Stop all services"""
    try:
        logger.info("Stopping services...")
        
        # Stop each service
        for service_name, service in services.items():
            try:
                logger.info(f"Stopping {service_name}...")
                
                # Service-specific cleanup
                if hasattr(service, 'stop'):
                    await service.stop()
                
                service_status[service_name]["status"] = "stopped"
                
                logger.info(f"{service_name} stopped successfully")
                
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        logger.info("Services stopped")
        
    except Exception as e:
        logger.error(f"Error stopping services: {e}")
        raise

async def monitor_service_health(service_name: str):
    """Monitor service health"""
    try:
        while True:
            try:
                service = services[service_name]
                
                # Check service health
                if hasattr(service, 'get_service_stats'):
                    stats = await service.get_service_stats()
                    if "error" in stats:
                        service_status[service_name]["status"] = "error"
                        service_status[service_name]["error"] = stats["error"]
                    else:
                        service_status[service_name]["status"] = "running"
                        service_status[service_name]["error"] = None
                else:
                    service_status[service_name]["status"] = "running"
                    service_status[service_name]["error"] = None
                
                service_status[service_name]["last_check"] = time.time()
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                service_status[service_name]["status"] = "error"
                service_status[service_name]["error"] = str(e)
            
            # Wait before next check
            await asyncio.sleep(config.health_check_interval)
            
    except asyncio.CancelledError:
        logger.info(f"Health monitoring cancelled for {service_name}")
    except Exception as e:
        logger.error(f"Error in health monitoring for {service_name}: {e}")

# Create FastAPI application
app = FastAPI(
    title="LUCID TRON Payment Services",
    description="TRON payment services for LUCID blockchain platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check overall service health
        all_services_healthy = all(
            status["status"] == "running" 
            for status in service_status.values()
        )
        
        if all_services_healthy:
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "services": service_status
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": time.time(),
                    "services": service_status
                }
            )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

# Service status endpoint
@app.get("/status")
async def service_status_endpoint():
    """Get detailed service status"""
    try:
        return {
            "timestamp": time.time(),
            "services": service_status,
            "config": {
                "tron_network": config.tron_network.value,
                "debug_mode": config.debug_mode,
                "test_mode": config.test_mode
            }
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Service statistics endpoint
@app.get("/stats")
async def service_stats():
    """Get service statistics"""
    try:
        stats = {}
        
        # Get stats from each service
        for service_name, service in services.items():
            try:
                if hasattr(service, 'get_service_stats'):
                    service_stats = await service.get_service_stats()
                    stats[service_name] = service_stats
                else:
                    stats[service_name] = {"status": "no_stats_available"}
            except Exception as e:
                stats[service_name] = {"error": str(e)}
        
        return {
            "timestamp": time.time(),
            "services": stats
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Service restart endpoint
@app.post("/restart/{service_name}")
async def restart_service(service_name: str):
    """Restart a specific service"""
    try:
        if service_name not in services:
            raise HTTPException(status_code=404, detail="Service not found")
        
        logger.info(f"Restarting service: {service_name}")
        
        # Stop service
        service = services[service_name]
        if hasattr(service, 'stop'):
            await service.stop()
        
        # Reinitialize service
        if hasattr(service, 'initialize'):
            await service.initialize()
        
        service_status[service_name]["status"] = "running"
        service_status[service_name]["error"] = None
        
        logger.info(f"Service {service_name} restarted successfully")
        
        return {
            "message": f"Service {service_name} restarted successfully",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoint
@app.get("/config")
async def get_configuration():
    """Get current configuration"""
    try:
        return {
            "tron_network": config.tron_network.value,
            "tron_http_endpoint": config.tron_http_endpoint,
            "services": {
                "tron_client_url": config.tron_client_url,
                "wallet_manager_url": config.wallet_manager_url,
                "usdt_manager_url": config.usdt_manager_url,
                "payout_router_url": config.payout_router_url,
                "payment_gateway_url": config.payment_gateway_url,
                "trx_staking_url": config.trx_staking_url
            },
            "limits": {
                "max_payment_amount": config.max_payment_amount,
                "min_payment_amount": config.min_payment_amount,
                "daily_payment_limit": config.daily_payment_limit
            },
            "staking": {
                "min_staking_amount": config.min_staking_amount,
                "max_staking_amount": config.max_staking_amount,
                "staking_duration_min": config.staking_duration_min,
                "staking_duration_max": config.staking_duration_max
            },
            "security": {
                "wallet_encryption_enabled": config.wallet_encryption_enabled,
                "rate_limit_enabled": config.rate_limit_enabled,
                "circuit_breaker_enabled": config.circuit_breaker_enabled
            },
            "monitoring": {
                "health_check_interval": config.health_check_interval,
                "metrics_enabled": config.metrics_enabled,
                "log_level": config.log_level.value
            }
        }
    except Exception as e:
        logger.error(f"Config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Service-specific endpoints
@app.get("/tron-client/stats")
async def tron_client_stats():
    """Get TRON client statistics"""
    try:
        stats = await tron_client_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"TRON client stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wallet-manager/stats")
async def wallet_manager_stats():
    """Get wallet manager statistics"""
    try:
        stats = await wallet_manager_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"Wallet manager stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usdt-manager/stats")
async def usdt_manager_stats():
    """Get USDT manager statistics"""
    try:
        stats = await usdt_manager_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"USDT manager stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payout-router/stats")
async def payout_router_stats():
    """Get payout router statistics"""
    try:
        stats = await payout_router_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"Payout router stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payment-gateway/stats")
async def payment_gateway_stats():
    """Get payment gateway statistics"""
    try:
        stats = await payment_gateway_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"Payment gateway stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trx-staking/stats")
async def trx_staking_stats():
    """Get TRX staking statistics"""
    try:
        stats = await trx_staking_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"TRX staking stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Signal handlers
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point"""
    try:
        # Get service configuration
        service_config = get_service_config("tron_payment_service")
        
        # Start the application
        uvicorn.run(
            "payment_systems.tron.main:app",
            host=service_config.get("host", "0.0.0.0"),
            port=service_config.get("port", 8091),
            workers=service_config.get("workers", 1),
            timeout_keep_alive=service_config.get("timeout", 30),
            log_level=config.log_level.value.lower(),
            access_log=True,
            reload=config.debug_mode
        )
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
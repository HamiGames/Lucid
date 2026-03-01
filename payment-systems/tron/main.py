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

# Distroless-safe path resolution - use local paths only
# No need for external project root resolution in containerized service

# Removed app.config import - using local config module
from .config import config, get_service_config, get_api_endpoints, validate_config
from .services.tron_client import tron_client_service
from .services.wallet_manager import wallet_manager_service
from .services.usdt_manager import usdt_manager_service
from .services.payout_router import payout_router_service
from .services.payment_gateway import payment_gateway_service
from .services.trx_staking import trx_staking_service

# Import utility modules
from .utils.logging_config import setup_structured_logging
from .utils.metrics import get_metrics_collector
from .utils.health_check import get_health_checker
from .utils.config_loader import get_config_loader, load_yaml_config
from .utils.circuit_breaker import get_circuit_breaker_manager, CircuitBreakerConfig
from .utils.rate_limiter import get_rate_limiter_manager, RateLimitConfig
from .utils.tor_proxy_client import initialize_tor_proxy_client, get_tor_proxy_client_manager

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", config.log_level.value if hasattr(config.log_level, 'value') else str(config.log_level))
log_file = os.getenv("LOG_FILE", os.getenv("TRON_LOG_FILE", "/app/logs/tron-client.log"))
log_format = os.getenv("LOG_FORMAT", "json")

# Ensure log directory exists
log_dir = Path(log_file).parent
log_dir.mkdir(parents=True, exist_ok=True)

# Setup structured logging
setup_structured_logging(
    log_level=log_level,
    log_format=log_format,
    log_file=log_file,
    include_trace_id=True
)
logger = logging.getLogger(__name__)

# Initialize utility modules
metrics_collector = get_metrics_collector()
health_checker = get_health_checker()
config_loader = get_config_loader()
circuit_breaker_manager = get_circuit_breaker_manager()
rate_limiter_manager = get_rate_limiter_manager()

# Initialize tor-proxy client manager
tor_proxy_manager = initialize_tor_proxy_client(config)
logger.info(f"Tor-proxy integration initialized: {tor_proxy_manager}")

# Load YAML configurations
try:
    circuit_breaker_config = load_yaml_config("circuit-breaker-config.yaml", merge_env=True, env_prefix="TRON")
    retry_config = load_yaml_config("retry-config.yaml", merge_env=True, env_prefix="TRON")
    prometheus_metrics_config = load_yaml_config("prometheus-metrics.yaml", merge_env=True, env_prefix="TRON")
    logger.info("Loaded YAML configuration files")
except Exception as e:
    logger.warning(f"Failed to load YAML configurations: {e}, using defaults")

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
    
    # Update metrics - service starting
    metrics_collector.update_service_health("tron_client", True)
    
    # Validate configuration
    try:
        config_errors = validate_config()
        if config_errors:
            logger.error("Configuration validation failed:")
            for error in config_errors:
                logger.error(f"  - {error}")
            if config.get("production_mode", False):
                raise RuntimeError("Configuration validation failed in production mode")
    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        metrics_collector.update_service_health("tron_client", False)
        if config.get("production_mode", False):
            raise RuntimeError(f"Configuration validation failed in production mode: {e}")
        else:
            logger.warning("Continuing in non-production mode despite config validation errors")
    
    # Initialize circuit breakers from config
    try:
        if circuit_breaker_config:
            cb_configs = circuit_breaker_config.get("tron_network", {})
            if cb_configs.get("enabled", True):
                cb_config = CircuitBreakerConfig(
                    failure_threshold=cb_configs.get("failure_threshold", 5),
                    recovery_timeout=cb_configs.get("recovery_timeout", 60),
                    success_threshold=cb_configs.get("success_threshold", 2),
                    half_open_max_calls=cb_configs.get("half_open_max_calls", 3),
                    name="tron_network"
                )
                await circuit_breaker_manager.get_breaker("tron_network", cb_config)
                logger.info("Initialized circuit breaker: tron_network")
    except Exception as e:
        logger.warning(f"Failed to initialize circuit breakers: {e}")
    
    # Initialize rate limiters from config
    try:
        rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        if rate_limit_enabled:
            rate_config = RateLimitConfig(
                requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
                burst_size=int(os.getenv("RATE_LIMIT_BURST", "200")),
                window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
                enabled=True
            )
            await rate_limiter_manager.get_limiter("tron_client", rate_config)
            logger.info("Initialized rate limiter: tron_client")
    except Exception as e:
        logger.warning(f"Failed to initialize rate limiters: {e}")
    
    # Initialize services
    await initialize_services()
    
    # Start health monitoring
    await start_health_monitoring()
    
    # Update metrics - service started
    metrics_collector.update_service_health("tron_client", True)
    logger.info("TRON Payment Services started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TRON Payment Services...")
    
    # Update metrics - service shutting down
    metrics_collector.update_service_health("tron_client", False)
    
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
    """Monitor service health with metrics collection"""
    try:
        while True:
            try:
                service = services[service_name]
                check_start = time.time()
                
                # Check service health
                if hasattr(service, 'get_service_stats'):
                    stats = await service.get_service_stats()
                    if "error" in stats:
                        service_status[service_name]["status"] = "error"
                        service_status[service_name]["error"] = stats["error"]
                        metrics_collector.update_service_health(service_name, False)
                    else:
                        service_status[service_name]["status"] = "running"
                        service_status[service_name]["error"] = None
                        metrics_collector.update_service_health(service_name, True)
                        
                        # Update service-specific metrics
                        if service_name == "tron_client":
                            if "pending_transactions" in stats:
                                metrics_collector.update_pending_transactions(stats["pending_transactions"])
                            if "confirmed_transactions" in stats:
                                metrics_collector.update_confirmed_transactions(stats["confirmed_transactions"])
                            if "cached_accounts" in stats:
                                metrics_collector.update_account_cache_size(stats["cached_accounts"])
                            if "monitoring_tasks" in stats:
                                metrics_collector.update_monitoring_tasks(stats["monitoring_tasks"])
                else:
                    service_status[service_name]["status"] = "running"
                    service_status[service_name]["error"] = None
                    metrics_collector.update_service_health(service_name, True)
                
                service_status[service_name]["last_check"] = time.time()
                
                # Record health check duration
                check_duration = time.time() - check_start
                metrics_collector.record_account_operation(f"health_check_{service_name}", "success")
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                service_status[service_name]["status"] = "error"
                service_status[service_name]["error"] = str(e)
                metrics_collector.update_service_health(service_name, False)
                metrics_collector.record_account_operation(f"health_check_{service_name}", "error")
            
            # Wait before next check
            health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", str(config.health_check_interval if hasattr(config, 'health_check_interval') else 60)))
            await asyncio.sleep(health_check_interval)
            
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

# Add middleware - configured from environment variables
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
cors_methods = os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
cors_headers = os.getenv("CORS_HEADERS", "*").split(",")
trusted_hosts = os.getenv("TRUSTED_HOSTS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts
)

# Include API routers
from .api import tron_network, wallets, usdt, payouts, staking, transactions_extended, payments

app.include_router(tron_network.router)
app.include_router(wallets.router)
app.include_router(usdt.router)
app.include_router(payouts.router)
app.include_router(staking.router)
app.include_router(transactions_extended.router)
app.include_router(payments.router)

# Health check endpoint - enhanced with HealthChecker
@app.get("/health")
async def health_check():
    """Health check endpoint with comprehensive dependency checks"""
    try:
        # Get overall health from HealthChecker
        overall_health = await health_checker.get_overall_health()
        
        # Check service status
        all_services_healthy = all(
            status["status"] == "running" 
            for status in service_status.values()
        )
        
        # Combine health check results
        health_status = overall_health["status"]
        if all_services_healthy and health_status in ["healthy", "degraded"]:
            status_code = 200 if health_status == "healthy" else 200  # Degraded still returns 200
            return {
                "status": health_status,
                "timestamp": time.time(),
                "services": service_status,
                "dependencies": overall_health["components"]
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": time.time(),
                    "services": service_status,
                    "dependencies": overall_health["components"]
                }
            )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        metrics_collector.record_network_error("health_check_error", "/health")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

# Liveness probe endpoint
@app.get("/health/live")
async def liveness_check():
    """Liveness probe - is the service running?"""
    is_alive = await health_checker.liveness_check()
    if is_alive:
        return {"status": "alive", "timestamp": time.time()}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_alive", "timestamp": time.time()}
        )

# Readiness probe endpoint
@app.get("/health/ready")
async def readiness_check():
    """Readiness probe - is the service ready to serve requests?"""
    is_ready = await health_checker.readiness_check()
    if is_ready:
        return {"status": "ready", "timestamp": time.time()}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "timestamp": time.time()}
        )

# Metrics endpoint - Prometheus format
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    try:
        metrics_enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        if not metrics_enabled:
            raise HTTPException(status_code=404, detail="Metrics not enabled")
        
        return metrics_collector.get_metrics_response()
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    """Get service statistics with metrics"""
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
        
        # Add circuit breaker stats
        try:
            stats["circuit_breakers"] = circuit_breaker_manager.get_all_stats()
        except Exception as e:
            logger.warning(f"Failed to get circuit breaker stats: {e}")
        
        # Add rate limiter stats
        try:
            stats["rate_limiters"] = rate_limiter_manager.get_all_stats()
        except Exception as e:
            logger.warning(f"Failed to get rate limiter stats: {e}")
        
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
        # Determine service name from environment variable or default to tron_client
        service_name = os.getenv("SERVICE_NAME", "tron_client")
        # Map service names to config keys
        service_config_map = {
            "lucid-tron-client": "tron_client",
            "tron-client": "tron_client",
            "tron-payout-router": "payout_router",
            "payout-router": "payout_router",
            "tron-wallet-manager": "wallet_manager",
            "wallet-manager": "wallet_manager",
            "tron-usdt-manager": "usdt_manager",
            "usdt-manager": "usdt_manager",
            "tron-payment-gateway": "payment_gateway",
            "payment-gateway": "payment_gateway",
            "tron-staking": "trx_staking",
            "trx-staking": "trx_staking"
        }
        config_key = service_config_map.get(service_name.lower(), "tron_client")
        
        # Get service configuration from environment or config
        service_config = get_service_config(config_key)
        
        # Get configuration from environment variables (priority) or config
        host = os.getenv("SERVICE_HOST", os.getenv("BIND_ADDRESS", service_config.get("host", "0.0.0.0")))
        # Use service-specific port env var or fallback to SERVICE_PORT
        port_env_vars = {
            "tron_client": "TRON_CLIENT_PORT",
            "payout_router": "PAYOUT_ROUTER_PORT",
            "wallet_manager": "WALLET_MANAGER_PORT",
            "usdt_manager": "USDT_MANAGER_PORT",
            "payment_gateway": "PAYMENT_GATEWAY_PORT",
            "trx_staking": "TRX_STAKING_PORT"
        }
        port_env = port_env_vars.get(config_key, "SERVICE_PORT")
        port = int(os.getenv(port_env, os.getenv("SERVICE_PORT", str(service_config.get("port", 8091)))))
        workers = int(os.getenv("WORKERS", str(service_config.get("workers", 1))))
        timeout = int(os.getenv("TIMEOUT", str(service_config.get("timeout", 30))))
        log_level = os.getenv("LOG_LEVEL", config.log_level.value if hasattr(config.log_level, 'value') else str(config.log_level)).lower()
        debug_mode = os.getenv("DEBUG", str(config.debug_mode if hasattr(config, 'debug_mode') else False)).lower() == "true"
        
        # Start the application
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            workers=workers,
            timeout_keep_alive=timeout,
            log_level=log_level,
            access_log=os.getenv("ACCESS_LOG", "true").lower() == "true",
            reload=debug_mode
        )
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
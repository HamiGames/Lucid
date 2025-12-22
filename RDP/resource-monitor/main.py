"""
RDP Resource Monitor - Main Entry Point

FastAPI application for RDP resource monitoring service.
"""

import asyncio
import logging
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field

from .resource_monitor import ResourceMonitor
from .metrics_collector import MetricsCollector
from .config import MonitorConfig, MonitorSettings, load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
resource_monitor = None
metrics_collector = None
monitor_config = None

# Pydantic request/response models
class StartMonitoringRequest(BaseModel):
    """Request model for starting monitoring"""
    session_id: UUID = Field(..., description="Session ID to monitor")
    session_config: Dict[str, Any] = Field(default_factory=dict, description="Session configuration")

class CollectMetricsRequest(BaseModel):
    """Request model for collecting metrics"""
    session_id: UUID = Field(..., description="Session ID to collect metrics for")
    metrics_data: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics data")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    global resource_monitor, metrics_collector, monitor_config
    
    # Startup
    logger.info("Starting RDP Resource Monitor")
    
    # Load configuration
    try:
        settings = load_config()
        monitor_config = MonitorConfig(settings)
        logger.info(f"Configuration loaded: {monitor_config.settings.SERVICE_NAME} v{monitor_config.settings.SERVICE_VERSION}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        logger.warning("Using default configuration and environment variables only")
        from .config import MonitorConfig, MonitorSettings
        monitor_config = MonitorConfig(MonitorSettings())
    
    # Initialize components with config (dependency injection pattern)
    resource_monitor = ResourceMonitor(config=monitor_config)
    metrics_collector = MetricsCollector(config=monitor_config)
    
    # Start background monitoring tasks
    asyncio.create_task(resource_monitor.start_continuous_monitoring())
    asyncio.create_task(metrics_collector.start_collection())
    
    logger.info("RDP Resource Monitor started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RDP Resource Monitor")
    await resource_monitor.stop_continuous_monitoring()
    await metrics_collector.stop_collection()
    logger.info("RDP Resource Monitor shut down successfully")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Lucid RDP Resource Monitor",
        description="RDP resource monitoring and metrics collection service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # CORS_ORIGINS env var: comma-separated list of origins, or "*" for all
    # Default to ["*"] if not set
    cors_origins_str = os.getenv('CORS_ORIGINS', '*')
    if cors_origins_str == "*":
        cors_origins = ["*"]
    else:
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        global resource_monitor, metrics_collector
        
        if not resource_monitor or not metrics_collector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not fully initialized"
            )
        
        try:
            # Get basic health information
            active_sessions = len(resource_monitor.active_sessions)
            
            return {
                "status": "healthy",
                "service": "rdp-resource-monitor",
                "version": "1.0.0",
                "active_sessions": active_sessions,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Health check failed"
            )
    
    # Resource monitoring endpoints
    @app.post("/api/v1/monitoring/start")
    async def start_monitoring(request: StartMonitoringRequest):
        """Start monitoring a session"""
        global resource_monitor, metrics_collector
        
        if not resource_monitor or not metrics_collector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            await resource_monitor.start_monitoring(request.session_id, request.session_config)
            await metrics_collector.record_session_created(
                request.session_id, 
                request.session_config.get('user_id', 'unknown')
            )
            return {
                "status": "monitoring_started",
                "session_id": str(request.session_id),
                "timestamp": datetime.utcnow().isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to start monitoring for session {request.session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start monitoring: {str(e)}"
            )
    
    @app.post("/api/v1/monitoring/sessions/{session_id}/stop")
    async def stop_monitoring(session_id: UUID):
        """Stop monitoring a session"""
        global resource_monitor
        
        if not resource_monitor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            await resource_monitor.stop_monitoring(session_id)
            return {
                "status": "monitoring_stopped",
                "session_id": str(session_id),
                "timestamp": datetime.utcnow().isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to stop monitoring for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop monitoring: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/sessions/{session_id}/metrics")
    async def get_session_metrics(session_id: UUID):
        """Get current metrics for a session"""
        global resource_monitor
        
        if not resource_monitor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            metrics = await resource_monitor.get_session_metrics(session_id)
            if not metrics:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or not being monitored"
                )
            return metrics.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get metrics for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get session metrics: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/sessions/{session_id}/history")
    async def get_session_history(
        session_id: UUID,
        hours: int = Query(1, ge=1, le=24, description="Number of hours of history to retrieve")
    ):
        """Get metrics history for a session"""
        global resource_monitor
        
        if not resource_monitor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            history = await resource_monitor.get_metrics_history(session_id, hours)
            return {
                "session_id": str(session_id),
                "hours": hours,
                "metrics_count": len(history),
                "history": [metrics.to_dict() for metrics in history]
            }
        except Exception as e:
            logger.error(f"Failed to get history for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get session history: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/sessions/{session_id}/alerts")
    async def get_session_alerts(session_id: UUID):
        """Get alerts for a session"""
        global resource_monitor
        
        if not resource_monitor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            alerts = await resource_monitor.check_alerts(session_id)
            return {
                "session_id": str(session_id),
                "alerts": alerts,
                "alert_count": len(alerts),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get alerts for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get session alerts: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/summary")
    async def get_system_summary():
        """Get system-wide resource summary"""
        global resource_monitor
        
        if not resource_monitor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            summary = await resource_monitor.get_system_summary()
            return summary
        except Exception as e:
            logger.error(f"Failed to get system summary: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get system summary: {str(e)}"
            )
    
    # Metrics endpoints
    @app.get("/api/v1/metrics")
    async def get_metrics():
        """Get Prometheus metrics"""
        global metrics_collector
        
        if not metrics_collector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            metrics_data = await metrics_collector.export_metrics()
            return Response(
                content=metrics_data,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to export metrics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get metrics: {str(e)}"
            )
    
    @app.get("/api/v1/metrics/summary")
    async def get_metrics_summary():
        """Get metrics collection summary"""
        global metrics_collector
        
        if not metrics_collector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            summary = await metrics_collector.get_metrics_summary()
            return summary
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get metrics summary: {str(e)}"
            )
    
    # Resource collection endpoint
    @app.post("/api/v1/monitoring/collect")
    async def collect_metrics(request: CollectMetricsRequest):
        """Manually collect metrics for a session"""
        global resource_monitor, metrics_collector
        
        if not resource_monitor or not metrics_collector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
        
        try:
            # Collect metrics using resource monitor
            metrics = await resource_monitor.collect_metrics(request.session_id)
            
            # Record metrics using metrics collector
            await metrics_collector.collect_session_metrics(request.session_id, request.metrics_data)
            
            return {
                "status": "metrics_collected",
                "session_id": str(request.session_id),
                "metrics": metrics.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to collect metrics for session {request.session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to collect metrics: {str(e)}"
            )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        """Global exception handler for unhandled errors"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "LUCID_ERR_2300",
                    "message": "Internal server error",
                    "service": "rdp-resource-monitor",
                    "version": "1.0.0",
                    "details": str(exc) if app.debug else "An unexpected error occurred"
                }
            }
        )
    
    return app

app = create_app()

if __name__ == "__main__":
    # Get configuration from environment (from docker-compose.application.yml)
    host = "0.0.0.0"  # Always bind to all interfaces in container
    port_str = os.getenv("RDP_MONITOR_PORT", os.getenv("MONITOR_PORT", "8093"))
    try:
        port = int(port_str)
    except ValueError:
        logger.error(f"Invalid RDP_MONITOR_PORT/MONITOR_PORT value: {port_str}")
        sys.exit(1)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

"""
RDP Resource Monitor - Main Entry Point

FastAPI application for RDP resource monitoring service.
"""

import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from resource_monitor import ResourceMonitor, ResourceMetrics
from metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
resource_monitor = None
metrics_collector = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    global resource_monitor, metrics_collector
    
    # Startup
    logger.info("Starting RDP Resource Monitor")
    
    resource_monitor = ResourceMonitor()
    metrics_collector = MetricsCollector()
    
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
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "rdp-resource-monitor",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Resource monitoring endpoints
    @app.post("/api/v1/monitoring/start")
    async def start_monitoring(
        session_id: UUID,
        session_config: Dict[str, Any]
    ):
        """Start monitoring a session"""
        try:
            await resource_monitor.start_monitoring(session_id, session_config)
            await metrics_collector.record_session_created(session_id, session_config.get('user_id', 'unknown'))
            return {"status": "monitoring_started", "session_id": str(session_id)}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start monitoring: {str(e)}"
            )
    
    @app.post("/api/v1/monitoring/stop")
    async def stop_monitoring(session_id: UUID):
        """Stop monitoring a session"""
        try:
            await resource_monitor.stop_monitoring(session_id)
            return {"status": "monitoring_stopped", "session_id": str(session_id)}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop monitoring: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/sessions/{session_id}/metrics")
    async def get_session_metrics(session_id: UUID):
        """Get current metrics for a session"""
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get session metrics: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/sessions/{session_id}/history")
    async def get_session_history(
        session_id: UUID,
        hours: int = Query(1, ge=1, le=24)
    ):
        """Get metrics history for a session"""
        try:
            history = await resource_monitor.get_metrics_history(session_id, hours)
            return [metrics.to_dict() for metrics in history]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get session history: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/sessions/{session_id}/alerts")
    async def get_session_alerts(session_id: UUID):
        """Get alerts for a session"""
        try:
            alerts = await resource_monitor.check_alerts(session_id)
            return {"alerts": alerts}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get session alerts: {str(e)}"
            )
    
    @app.get("/api/v1/monitoring/summary")
    async def get_system_summary():
        """Get system-wide resource summary"""
        try:
            summary = await resource_monitor.get_system_summary()
            return summary
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get system summary: {str(e)}"
            )
    
    # Metrics endpoints
    @app.get("/api/v1/metrics")
    async def get_metrics():
        """Get Prometheus metrics"""
        try:
            metrics_data = await metrics_collector.export_metrics()
            return Response(
                content=metrics_data,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get metrics: {str(e)}"
            )
    
    @app.get("/api/v1/metrics/summary")
    async def get_metrics_summary():
        """Get metrics collection summary"""
        try:
            summary = await metrics_collector.get_metrics_summary()
            return summary
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get metrics summary: {str(e)}"
            )
    
    # Resource collection endpoint
    @app.post("/api/v1/monitoring/collect")
    async def collect_metrics(
        session_id: UUID,
        metrics_data: Dict[str, Any]
    ):
        """Manually collect metrics for a session"""
        try:
            # Collect metrics using resource monitor
            metrics = await resource_monitor.collect_metrics(session_id)
            
            # Record metrics using metrics collector
            await metrics_collector.collect_session_metrics(session_id, metrics_data)
            
            return {
                "status": "metrics_collected",
                "session_id": str(session_id),
                "metrics": metrics.to_dict()
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to collect metrics: {str(e)}"
            )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return {
            "error": {
                "code": "LUCID_ERR_2300",
                "message": "Internal server error",
                "service": "rdp-resource-monitor",
                "version": "v1"
            }
        }
    
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8093,
        log_level="info",
        access_log=True
    )

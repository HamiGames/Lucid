"""
HTTP Server for Service Mesh Controller
Provides health, status, metrics, and service discovery endpoints
Connects to services across all clusters: foundation, core, application, support, base

File: infrastructure/service-mesh/controller/http_server.py
Purpose: HTTP API for service mesh controller
Dependencies: fastapi, uvicorn, asyncio, logging
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("FastAPI not available - HTTP server will not start")

logger = logging.getLogger(__name__)


class HTTPServer:
    """
    HTTP server for service mesh controller.
    
    Provides endpoints for:
    - Health checks (Docker healthcheck)
    - Controller status
    - Service discovery across all clusters
    - Service health metrics
    - Cluster connectivity
    """
    
    def __init__(self, controller, port: int = 8088):
        """
        Initialize HTTP server.
        
        Args:
            controller: ServiceMeshController instance
            port: HTTP server port (default: 8088)
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI is required but not installed")
        
        self.controller = controller
        self.port = port
        self.app = FastAPI(
            title="Lucid Service Mesh Controller API",
            version="1.0.0",
            description="Service mesh controller HTTP API for cross-cluster service discovery and management",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self.server_task: Optional[asyncio.Task] = None
        self.server: Optional[uvicorn.Server] = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/health", tags=["health"], summary="Health check endpoint")
        async def health() -> Dict[str, Any]:
            """
            Health check endpoint for Docker healthcheck.
            Returns 200 if controller is running.
            """
            try:
                status = self.controller.get_status()
                return {
                    "status": "healthy",
                    "service": "service-mesh-controller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "controller_running": status.get("status") == "running"
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
        
        @self.app.get("/status", tags=["status"], summary="Get controller status")
        async def status() -> Dict[str, Any]:
            """
            Get detailed controller status including all components.
            """
            try:
                return self.controller.get_status()
            except Exception as e:
                logger.error(f"Status endpoint failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")
        
        @self.app.get("/metrics", tags=["metrics"], summary="Get controller metrics")
        async def metrics() -> Dict[str, Any]:
            """
            Get controller metrics including service health status.
            """
            try:
                health_status = self.controller.health_checker.get_all_health_status()
                controller_status = self.controller.get_status()
                
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "controller": {
                        "status": controller_status.get("status"),
                        "components": controller_status.get("components", {}),
                        "tasks": controller_status.get("tasks", {})
                    },
                    "services": {
                        "health_status": health_status,
                        "healthy_count": len(self.controller.health_checker.get_healthy_services()),
                        "unhealthy_count": len(self.controller.health_checker.get_unhealthy_services())
                    }
                }
            except Exception as e:
                logger.error(f"Metrics endpoint failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
        
        @self.app.get("/services", tags=["discovery"], summary="List all discovered services")
        async def list_services() -> Dict[str, Any]:
            """
            List all services discovered across all clusters.
            """
            try:
                health_status = self.controller.health_checker.get_all_health_status()
                healthy_services = self.controller.health_checker.get_healthy_services()
                unhealthy_services = self.controller.health_checker.get_unhealthy_services()
                
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_services": len(health_status),
                    "healthy_services": healthy_services,
                    "unhealthy_services": unhealthy_services,
                    "service_status": health_status
                }
            except Exception as e:
                logger.error(f"Services endpoint failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to list services: {str(e)}")
        
        @self.app.get("/services/{service_name}", tags=["discovery"], summary="Get service details")
        async def get_service(service_name: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific service.
            """
            try:
                health_status = self.controller.health_checker.get_service_health(service_name)
                health_history = self.controller.health_checker.get_health_history(service_name)
                
                if health_status is None:
                    raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
                
                return {
                    "service_name": service_name,
                    "health_status": health_status.value if hasattr(health_status, 'value') else str(health_status),
                    "health_history": health_history[-10:] if health_history else [],  # Last 10 checks
                    "last_check": health_history[-1] if health_history else None
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Get service endpoint failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get service: {str(e)}")
        
        @self.app.get("/clusters", tags=["discovery"], summary="List all clusters")
        async def list_clusters() -> Dict[str, Any]:
            """
            List all clusters and their services.
            Clusters: foundation, core, application, support, base
            """
            try:
                # Get all service health status
                health_status = self.controller.health_checker.get_all_health_status()
                
                # Group services by cluster (based on service naming patterns)
                clusters = {
                    "foundation": [],
                    "core": [],
                    "application": [],
                    "support": [],
                    "base": []
                }
                
                for service_name, status in health_status.items():
                    # Determine cluster based on service name patterns
                    if any(x in service_name.lower() for x in ["mongodb", "redis", "tor", "consul"]):
                        clusters["foundation"].append({"name": service_name, "status": status})
                    elif any(x in service_name.lower() for x in ["api-gateway", "blockchain", "session", "auth"]):
                        clusters["core"].append({"name": service_name, "status": status})
                    elif any(x in service_name.lower() for x in ["node", "admin", "wallet", "payment"]):
                        clusters["application"].append({"name": service_name, "status": status})
                    elif any(x in service_name.lower() for x in ["monitoring", "logging", "metrics"]):
                        clusters["support"].append({"name": service_name, "status": status})
                    else:
                        clusters["base"].append({"name": service_name, "status": status})
                
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "clusters": clusters,
                    "cluster_summary": {
                        cluster: {
                            "total": len(services),
                            "healthy": sum(1 for s in services if s["status"] == "healthy"),
                            "unhealthy": sum(1 for s in services if s["status"] == "unhealthy")
                        }
                        for cluster, services in clusters.items()
                    }
                }
            except Exception as e:
                logger.error(f"Clusters endpoint failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to list clusters: {str(e)}")
        
        @self.app.get("/clusters/{cluster_name}", tags=["discovery"], summary="Get cluster details")
        async def get_cluster(cluster_name: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific cluster.
            """
            try:
                cluster_name_lower = cluster_name.lower()
                if cluster_name_lower not in ["foundation", "core", "application", "support", "base"]:
                    raise HTTPException(status_code=404, detail=f"Cluster '{cluster_name}' not found")
                
                # Get cluster services
                clusters_response = await list_clusters()
                cluster_services = clusters_response["clusters"].get(cluster_name_lower, [])
                
                return {
                    "cluster_name": cluster_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "services": cluster_services,
                    "summary": clusters_response["cluster_summary"].get(cluster_name_lower, {})
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Get cluster endpoint failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get cluster: {str(e)}")
        
        @self.app.get("/", tags=["info"], summary="API information")
        async def root() -> Dict[str, Any]:
            """
            API root endpoint with information and available endpoints.
            """
            return {
                "service": "lucid-service-mesh-controller",
                "version": "1.0.0",
                "description": "Service mesh controller for cross-cluster service discovery and management",
                "endpoints": {
                    "health": "/health",
                    "status": "/status",
                    "metrics": "/metrics",
                    "services": "/services",
                    "clusters": "/clusters",
                    "docs": "/docs",
                    "redoc": "/redoc"
                },
                "clusters": ["foundation", "core", "application", "support", "base"]
            }
    
    async def start(self):
        """Start HTTP server as background task."""
        try:
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info",
                access_log=False,  # Reduce noise in logs
                loop="asyncio"
            )
            self.server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(self.server.serve())
            logger.info(f"HTTP server started on port {self.port}")
            logger.info(f"API documentation available at http://0.0.0.0:{self.port}/docs")
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            raise
    
    async def stop(self):
        """Stop HTTP server."""
        try:
            if self.server and self.server_task:
                # Gracefully shutdown uvicorn server
                self.server.should_exit = True
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            logger.info("HTTP server stopped")
        except Exception as e:
            logger.error(f"Error stopping HTTP server: {e}")


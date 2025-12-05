"""
HTTP Server for Lucid Authentication Service
Provides customizable HTTP endpoints for authentication, user management, sessions, and hardware wallets
Follows the service-mesh-controller pattern for consistency across Lucid project

File: auth/http_server.py
Purpose: HTTP API server for authentication service with customizable endpoints
Dependencies: fastapi, uvicorn, asyncio, logging, yaml
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("FastAPI not available - HTTP server will not start")

logger = logging.getLogger(__name__)


class HTTPServer:
    """
    HTTP server for Lucid Authentication Service.
    
    Provides customizable endpoints for:
    - Health checks (Docker healthcheck)
    - Authentication (login, register, refresh, logout, verify)
    - User management (get, update, list)
    - Session management (list, get, revoke)
    - Hardware wallet operations (connect, sign, status, disconnect)
    - Service metadata and information
    """
    
    def __init__(self, app_instance, port: int = 8089, endpoint_config: Optional[Dict[str, Any]] = None):
        """
        Initialize HTTP server.
        
        Args:
            app_instance: FastAPI application instance (from main.py)
            port: HTTP server port (default: 8089)
            endpoint_config: Optional endpoint configuration dictionary
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI is required but not installed")
        
        self.app = app_instance
        self.port = port
        self.endpoint_config = endpoint_config or {}
        self.server_task: Optional[asyncio.Task] = None
        self.server: Optional[uvicorn.Server] = None
        
        # Load endpoint configuration
        self._load_endpoint_config()
        
        # Setup additional routes if needed
        self._setup_custom_routes()
    
    def _load_endpoint_config(self):
        """Load endpoint configuration from YAML file."""
        try:
            config_path = Path(__file__).parent / "config" / "endpoints.yaml"
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    self.endpoint_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded endpoint configuration from {config_path}")
            else:
                logger.warning(f"Endpoint configuration file not found: {config_path}, using defaults")
        except Exception as e:
            logger.warning(f"Failed to load endpoint configuration: {e}, using defaults")
    
    def _setup_custom_routes(self):
        """Setup custom routes based on endpoint configuration."""
        try:
            # Get enabled endpoints from config
            enabled_endpoints = self.endpoint_config.get("endpoints", {})
            
            # Setup meta/info endpoint if enabled
            if enabled_endpoints.get("meta", {}).get("enabled", True):
                @self.app.get("/meta/info", tags=["meta"], summary="Service information")
                async def meta_info() -> Dict[str, Any]:
                    """
                    Get service metadata and information.
                    """
                    try:
                        return {
                            "service": "lucid-auth-service",
                            "version": "1.0.0",
                            "description": "Lucid Authentication Service - User authentication, session management, and hardware wallet integration",
                            "cluster": "foundation",
                            "timestamp": datetime.utcnow().isoformat(),
                            "endpoints": {
                                "health": "/health",
                                "meta": "/meta/info",
                                "auth": "/auth",
                                "users": "/users",
                                "sessions": "/sessions",
                                "hardware_wallet": "/hw",
                                "docs": "/docs",
                                "redoc": "/redoc"
                            },
                            "features": {
                                "authentication": True,
                                "user_management": True,
                                "session_management": True,
                                "hardware_wallet": True,
                                "jwt_tokens": True,
                                "rbac": True
                            }
                        }
                    except Exception as e:
                        logger.error(f"Meta info endpoint failed: {e}")
                        raise HTTPException(status_code=500, detail=f"Failed to get service info: {str(e)}")
            
            # Setup root endpoint
            @self.app.get("/", tags=["info"], summary="API root")
            async def root() -> Dict[str, Any]:
                """
                API root endpoint with information and available endpoints.
                """
                return {
                    "service": "lucid-auth-service",
                    "version": "1.0.0",
                    "description": "Lucid Authentication Service API",
                    "endpoints": {
                        "health": "/health",
                        "meta": "/meta/info",
                        "auth": "/auth",
                        "users": "/users",
                        "sessions": "/sessions",
                        "hardware_wallet": "/hw",
                        "docs": "/docs",
                        "redoc": "/redoc"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Failed to setup custom routes: {e}")
    
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


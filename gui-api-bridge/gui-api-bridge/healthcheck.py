"""
Health Check Service for GUI API Bridge
File: gui-api-bridge/gui-api-bridge/healthcheck.py
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .config import GuiAPIBridgeSettings
from .integration.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)


class HealthCheck:
    """Health check service for GUI API Bridge"""
    
    def __init__(self, config: GuiAPIBridgeSettings, integration_manager: IntegrationManager):
        """Initialize health check service"""
        self.config = config
        self.integration_manager = integration_manager
        self.start_time = datetime.now(timezone.utc)
    
    async def check_backend_service(self, service_name: str, service_url: str) -> Dict[str, Any]:
        """Check health of a backend service"""
        try:
            # Get appropriate client based on service name
            client = None
            
            if service_name == "api_gateway":
                client = self.integration_manager.api_gateway_client
            elif service_name == "blockchain_engine":
                client = self.integration_manager.blockchain_client
            elif service_name == "auth_service":
                client = self.integration_manager.auth_service_client
            elif service_name == "session_api":
                client = self.integration_manager.session_api_client
            elif service_name == "node_management":
                client = self.integration_manager.node_management_client
            elif service_name == "admin_interface":
                client = self.integration_manager.admin_interface_client
            elif service_name == "tron_payment":
                client = self.integration_manager.tron_client
            
            if client is None:
                return {
                    "service": service_name,
                    "status": "unknown",
                    "message": "Client not available",
                }
            
            # Try to check service health
            try:
                # Use httpx client to check health endpoint
                response = await client.health_check()
                
                return {
                    "service": service_name,
                    "status": "healthy" if response else "unhealthy",
                    "url": service_url,
                }
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                return {
                    "service": service_name,
                    "status": "unhealthy",
                    "url": service_url,
                    "error": str(e),
                }
        
        except Exception as e:
            logger.error(f"Error checking {service_name} health: {e}")
            return {
                "service": service_name,
                "status": "error",
                "error": str(e),
            }
    
    async def check(self) -> Dict[str, Any]:
        """
        Perform full health check
        Returns JSON response with service health status
        """
        try:
            now = datetime.now(timezone.utc)
            uptime = (now - self.start_time).total_seconds()
            
            # Check backend services
            backend_checks = await asyncio.gather(
                self.check_backend_service("api_gateway", self.config.API_GATEWAY_URL),
                self.check_backend_service("blockchain_engine", self.config.BLOCKCHAIN_ENGINE_URL),
                self.check_backend_service("auth_service", self.config.AUTH_SERVICE_URL),
                self.check_backend_service("session_api", self.config.SESSION_API_URL),
                self.check_backend_service("node_management", self.config.NODE_MANAGEMENT_URL),
                self.check_backend_service("admin_interface", self.config.ADMIN_INTERFACE_URL),
                self.check_backend_service("tron_payment", self.config.TRON_PAYMENT_URL),
            )
            
            # Determine overall health status
            unhealthy_services = [s for s in backend_checks if s.get("status") != "healthy"]
            
            if unhealthy_services:
                overall_status = "degraded"
            else:
                overall_status = "healthy"
            
            return {
                "service": self.config.SERVICE_NAME,
                "version": self.config.SERVICE_VERSION,
                "status": overall_status,
                "timestamp": now.isoformat(),
                "uptime_seconds": uptime,
                "backend_services": backend_checks,
                "checks": {
                    "service": "ok",
                    "configuration": "ok",
                    "database": "pending",
                },
            }
        
        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            return {
                "service": self.config.SERVICE_NAME,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

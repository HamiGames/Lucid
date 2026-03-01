"""
GUI API Bridge Service Logic
File: gui-api-bridge/gui-api-bridge/gui_api_bridge_service.py
Main service orchestration for API routing and backend integration
"""

import logging
from typing import Optional, Dict, Any
from .config import GuiAPIBridgeSettings
from .integration.integration_manager import IntegrationManager
from .services.routing_service import RoutingService
from .services.discovery_service import ServiceDiscoveryService

logger = logging.getLogger(__name__)


class GuiAPIBridgeService:
    """
    Main GUI API Bridge service for coordinating API routing and backend integration
    Orchestrates integration manager, routing, and service discovery
    """
    
    def __init__(self, config: GuiAPIBridgeSettings, integration_manager: IntegrationManager):
        """Initialize GUI API Bridge service"""
        self.config = config
        self.integration_manager = integration_manager
        self.routing_service = RoutingService(config, integration_manager)
        self.discovery_service = ServiceDiscoveryService(config)
        logger.info(f"GUI API Bridge service initialized for {config.SERVICE_NAME}")
    
    async def initialize(self):
        """Initialize all service components"""
        try:
            logger.info("Initializing GUI API Bridge service components")
            
            # Integration manager already initialized by caller
            logger.debug("Integration manager ready")
            
            # Discovery service is stateless, ready immediately
            logger.debug("Service discovery ready")
            
            logger.info("GUI API Bridge service components initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize GUI API Bridge service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup service resources"""
        try:
            logger.info("Cleaning up GUI API Bridge service")
            # Cleanup handled by integration manager
            logger.info("GUI API Bridge service cleanup complete")
        
        except Exception as e:
            logger.error(f"Error during service cleanup: {e}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status and backend service info"""
        return {
            "service": self.config.SERVICE_NAME,
            "version": "1.0.0",
            "port": self.config.PORT,
            "host": self.config.HOST,
            "services": self.discovery_service.list_services(),
        }
    
    async def get_backend_status(self) -> Dict[str, Any]:
        """Get status of all backend services"""
        services_status = {}
        
        try:
            # Check API Gateway
            is_healthy = await self.integration_manager.api_gateway_client.health_check()
            services_status["api-gateway"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking api-gateway: {e}")
            services_status["api-gateway"] = "error"
        
        try:
            # Check Blockchain Engine
            is_healthy = await self.integration_manager.blockchain_client.health_check()
            services_status["blockchain-engine"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking blockchain-engine: {e}")
            services_status["blockchain-engine"] = "error"
        
        try:
            # Check Auth Service
            is_healthy = await self.integration_manager.auth_service_client.health_check()
            services_status["auth-service"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking auth-service: {e}")
            services_status["auth-service"] = "error"
        
        try:
            # Check Session API
            is_healthy = await self.integration_manager.session_api_client.health_check()
            services_status["session-api"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking session-api: {e}")
            services_status["session-api"] = "error"
        
        try:
            # Check Node Management
            is_healthy = await self.integration_manager.node_management_client.health_check()
            services_status["node-management"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking node-management: {e}")
            services_status["node-management"] = "error"
        
        try:
            # Check Admin Interface
            is_healthy = await self.integration_manager.admin_interface_client.health_check()
            services_status["admin-interface"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking admin-interface: {e}")
            services_status["admin-interface"] = "error"
        
        try:
            # Check TRON Payment
            is_healthy = await self.integration_manager.tron_client.health_check()
            services_status["tron-client"] = "healthy" if is_healthy else "unhealthy"
        except Exception as e:
            logger.warning(f"Error checking tron-client: {e}")
            services_status["tron-client"] = "error"
        
        return services_status

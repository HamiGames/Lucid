"""
Service Discovery Service
File: gui-api-bridge/gui-api-bridge/services/discovery_service.py
"""

import logging
from typing import Dict, List, Optional, Any
from ..config import GuiAPIBridgeSettings

logger = logging.getLogger(__name__)


class ServiceDiscoveryService:
    """Service discovery for backend services"""
    
    def __init__(self, config: GuiAPIBridgeSettings):
        """Initialize service discovery"""
        self.config = config
        self.services = self._build_service_registry()
    
    def _build_service_registry(self) -> Dict[str, Dict[str, str]]:
        """Build service registry from configuration"""
        return {
            "api-gateway": {
                "url": self.config.API_GATEWAY_URL,
                "health": "/health",
            },
            "blockchain-engine": {
                "url": self.config.BLOCKCHAIN_ENGINE_URL,
                "health": "/health",
            },
            "auth-service": {
                "url": self.config.AUTH_SERVICE_URL,
                "health": "/health",
            },
            "session-api": {
                "url": self.config.SESSION_API_URL,
                "health": "/health",
            },
            "node-management": {
                "url": self.config.NODE_MANAGEMENT_URL,
                "health": "/health",
            },
            "admin-interface": {
                "url": self.config.ADMIN_INTERFACE_URL,
                "health": "/health",
            },
            "tron-client": {
                "url": self.config.TRON_PAYMENT_URL,
                "health": "/health",
            },
        }
    
    def get_service(self, service_name: str) -> Optional[Dict[str, str]]:
        """Get service configuration by name"""
        return self.services.get(service_name)
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all configured services"""
        return [
            {
                "name": name,
                "url": info["url"],
            }
            for name, info in self.services.items()
        ]

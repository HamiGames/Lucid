"""
Onion Service Module for GUI Tor Manager
Encapsulates onion service management logic
"""

from typing import List, Dict, Any, Optional
from utils.logging import get_logger

logger = get_logger(__name__)


class OnionService:
    """Service for onion service management"""
    
    def __init__(self, tor_proxy_client):
        """
        Initialize onion service
        
        Args:
            tor_proxy_client: TorProxyClient instance
        """
        self.tor_proxy_client = tor_proxy_client
        self._services: Dict[str, Dict[str, Any]] = {}
    
    async def create_service(
        self,
        ports: List[int],
        targets: Optional[List[Dict[str, Any]]] = None,
        persistent: bool = True,
    ) -> Dict[str, Any]:
        """Create onion service"""
        result = await self.tor_proxy_client.add_onion_service(ports, targets, persistent)
        service_id = result.get("service_id")
        if service_id:
            self._services[service_id] = result
        return result
    
    async def delete_service(self, service_id: str) -> bool:
        """Delete onion service"""
        success = await self.tor_proxy_client.remove_onion_service(service_id)
        if success and service_id in self._services:
            del self._services[service_id]
        return success
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """List all onion services"""
        return list(self._services.values())
    
    async def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get onion service details"""
        return self._services.get(service_id)

"""
GUI Tor Manager Service
Main orchestration logic for Tor operations
"""

from typing import Optional, List, Dict, Any
import asyncio

from config import get_config
from integration.tor_proxy_client import TorProxyClient
from utils.logging import get_logger
from utils.errors import TorProxyConnectionError, TorOperationError

logger = get_logger(__name__)


class GuiTorManagerService:
    """Main service for GUI Tor Manager"""
    
    def __init__(self):
        """Initialize the service"""
        self.config = get_config()
        self._tor_client: Optional[TorProxyClient] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize service connections"""
        try:
            logger.info("Initializing GUI Tor Manager Service...")
            
            # Create Tor proxy client
            self._tor_client = TorProxyClient(
                tor_proxy_url=self.config.settings.TOR_PROXY_URL,
                tor_control_port=self.config.settings.TOR_CONTROL_PORT,
            )
            
            # Connect to Tor proxy
            await self._tor_client.connect()
            
            # Verify connection
            is_healthy = await self._tor_client.health_check()
            if not is_healthy:
                logger.warning("Tor proxy health check failed, but continuing...")
            
            self._initialized = True
            logger.info("GUI Tor Manager Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise TorProxyConnectionError(
                message="Failed to initialize GUI Tor Manager Service",
                details={"error": str(e)}
            )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get overall service status
        
        Returns:
            Service status dictionary
        """
        return {
            "service": self.config.settings.SERVICE_NAME,
            "version": "1.0.0",
            "initialized": self._initialized,
            "tor_connected": self._tor_client is not None,
        }
    
    async def get_tor_status(self) -> Dict[str, Any]:
        """
        Get Tor proxy status
        
        Returns:
            Tor status information
        """
        if not self._tor_client:
            raise TorProxyConnectionError("Tor client not initialized")
        
        try:
            return await self._tor_client.get_tor_status()
        except Exception as e:
            logger.error(f"Failed to get Tor status: {e}")
            raise TorOperationError(
                message="Failed to get Tor status",
                details={"error": str(e)}
            )
    
    async def get_circuits(self) -> List[Dict[str, Any]]:
        """
        Get list of active Tor circuits
        
        Returns:
            List of circuits
        """
        if not self._tor_client:
            raise TorProxyConnectionError("Tor client not initialized")
        
        try:
            return await self._tor_client.get_circuits()
        except Exception as e:
            logger.error(f"Failed to get circuits: {e}")
            raise TorOperationError(
                message="Failed to get circuits",
                details={"error": str(e)}
            )
    
    async def create_onion_service(
        self,
        ports: List[int],
        targets: Optional[List[Dict[str, Any]]] = None,
        persistent: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new onion service
        
        Args:
            ports: List of ports to expose
            targets: Port target mappings
            persistent: Whether to make service persistent
        
        Returns:
            Created onion service information
        """
        if not self._tor_client:
            raise TorProxyConnectionError("Tor client not initialized")
        
        try:
            logger.info(f"Creating onion service with ports: {ports}")
            result = await self._tor_client.add_onion_service(ports, targets, persistent)
            logger.info(f"Onion service created: {result.get('address')}")
            return result
        except Exception as e:
            logger.error(f"Failed to create onion service: {e}")
            raise TorOperationError(
                message="Failed to create onion service",
                details={"error": str(e), "ports": ports}
            )
    
    async def delete_onion_service(self, service_id: str) -> bool:
        """
        Delete an onion service
        
        Args:
            service_id: Service identifier to delete
        
        Returns:
            True if successful
        """
        if not self._tor_client:
            raise TorProxyConnectionError("Tor client not initialized")
        
        try:
            logger.info(f"Deleting onion service: {service_id}")
            result = await self._tor_client.remove_onion_service(service_id)
            logger.info(f"Onion service deleted: {service_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete onion service: {e}")
            raise TorOperationError(
                message="Failed to delete onion service",
                details={"error": str(e), "service_id": service_id}
            )
    
    async def shutdown(self) -> None:
        """Shutdown service and cleanup"""
        try:
            logger.info("Shutting down GUI Tor Manager Service...")
            
            if self._tor_client:
                await self._tor_client.close()
            
            self._initialized = False
            logger.info("GUI Tor Manager Service shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Singleton instance
_service_instance: Optional[GuiTorManagerService] = None


async def get_service() -> GuiTorManagerService:
    """Get or create service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = GuiTorManagerService()
        await _service_instance.initialize()
    return _service_instance


async def shutdown_service() -> None:
    """Shutdown service"""
    global _service_instance
    if _service_instance:
        await _service_instance.shutdown()
        _service_instance = None

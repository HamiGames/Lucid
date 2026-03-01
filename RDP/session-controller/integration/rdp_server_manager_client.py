"""
RDP Server Manager Client

HTTP client for integrating with rdp-server-manager service.
"""

import logging
from typing import Dict, Any, Optional
from .service_base import ServiceClientBase, ServiceError, ServiceNotFoundError

logger = logging.getLogger(__name__)


class RDPServerManagerClient(ServiceClientBase):
    """HTTP client for rdp-server-manager service"""
    
    async def create_server(
        self,
        user_id: str,
        session_id: str,
        display_config: Optional[Dict[str, Any]] = None,
        security_level: str = "high"
    ) -> Dict[str, Any]:
        """
        Create a new RDP server instance
        
        Args:
            user_id: User ID associated with the server
            session_id: Session ID associated with the server
            display_config: Optional display configuration
            security_level: Security level (low, medium, high, maximum)
            
        Returns:
            Server creation result with server_id, port, status
        """
        try:
            payload = {
                "user_id": user_id,
                "session_id": session_id,
                "display_config": display_config or {},
                "security_level": security_level
            }
            
            result = await self._make_request('POST', '/servers', json_data=payload)
            logger.info(f"Created RDP server for session {session_id}")
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to create RDP server for session {session_id}: {str(e)}")
            raise
    
    async def get_server(self, server_id: str) -> Dict[str, Any]:
        """
        Get RDP server status
        
        Args:
            server_id: Server ID
            
        Returns:
            Server status information
        """
        try:
            result = await self._make_request('GET', f'/servers/{server_id}')
            return result
            
        except ServiceNotFoundError:
            return {"status": "not_found"}
        except ServiceError as e:
            logger.error(f"Failed to get server {server_id}: {str(e)}")
            raise
    
    async def list_servers(self) -> Dict[str, Any]:
        """
        List all active RDP servers
        
        Returns:
            List of active servers
        """
        try:
            result = await self._make_request('GET', '/servers')
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to list servers: {str(e)}")
            raise
    
    async def start_server(self, server_id: str) -> Dict[str, Any]:
        """
        Start an RDP server
        
        Args:
            server_id: Server ID
            
        Returns:
            Start result
        """
        try:
            result = await self._make_request('POST', f'/servers/{server_id}/start')
            logger.info(f"Started RDP server {server_id}")
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to start server {server_id}: {str(e)}")
            raise
    
    async def stop_server(self, server_id: str) -> Dict[str, Any]:
        """
        Stop an RDP server
        
        Args:
            server_id: Server ID
            
        Returns:
            Stop result
        """
        try:
            result = await self._make_request('POST', f'/servers/{server_id}/stop')
            logger.info(f"Stopped RDP server {server_id}")
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to stop server {server_id}: {str(e)}")
            raise
    
    async def restart_server(self, server_id: str) -> Dict[str, Any]:
        """
        Restart an RDP server
        
        Args:
            server_id: Server ID
            
        Returns:
            Restart result
        """
        try:
            result = await self._make_request('POST', f'/servers/{server_id}/restart')
            logger.info(f"Restarted RDP server {server_id}")
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to restart server {server_id}: {str(e)}")
            raise
    
    async def delete_server(self, server_id: str) -> Dict[str, Any]:
        """
        Delete an RDP server
        
        Args:
            server_id: Server ID
            
        Returns:
            Delete result
        """
        try:
            result = await self._make_request('DELETE', f'/servers/{server_id}')
            logger.info(f"Deleted RDP server {server_id}")
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to delete server {server_id}: {str(e)}")
            raise


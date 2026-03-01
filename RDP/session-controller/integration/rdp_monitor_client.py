"""
RDP Monitor Client

HTTP client for integrating with rdp-monitor service.
"""

import logging
from typing import Dict, Any, Optional
from .service_base import ServiceClientBase, ServiceError, ServiceNotFoundError

logger = logging.getLogger(__name__)


class RDPMonitorClient(ServiceClientBase):
    """HTTP client for rdp-monitor service"""
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system-wide metrics
        
        Returns:
            System metrics including CPU, memory, disk, network
        """
        try:
            result = await self._make_request('GET', '/metrics/system')
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to get system metrics: {str(e)}")
            raise
    
    async def get_server_metrics(self, server_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific RDP server
        
        Args:
            server_id: Server ID
            
        Returns:
            Server-specific metrics
        """
        try:
            result = await self._make_request('GET', f'/metrics/servers/{server_id}')
            return result
            
        except ServiceNotFoundError:
            return {"status": "not_found"}
        except ServiceError as e:
            logger.error(f"Failed to get metrics for server {server_id}: {str(e)}")
            raise
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific session
        
        Args:
            session_id: Session ID
            
        Returns:
            Session-specific metrics
        """
        try:
            result = await self._make_request('GET', f'/metrics/sessions/{session_id}')
            return result
            
        except ServiceNotFoundError:
            return {"status": "not_found"}
        except ServiceError as e:
            logger.error(f"Failed to get metrics for session {session_id}: {str(e)}")
            raise
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of monitored services
        
        Returns:
            Health status for all monitored services
        """
        try:
            result = await self._make_request('GET', '/health/status')
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to get health status: {str(e)}")
            raise
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get resource usage statistics
        
        Returns:
            Resource usage including CPU, memory, disk, network
        """
        try:
            result = await self._make_request('GET', '/resources/usage')
            return result
            
        except ServiceError as e:
            logger.error(f"Failed to get resource usage: {str(e)}")
            raise


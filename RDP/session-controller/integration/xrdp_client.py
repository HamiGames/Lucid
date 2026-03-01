"""
XRDP Service Client

HTTP client for integrating with rdp-xrdp service.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)


class XRDPClient:
    """HTTP client for rdp-xrdp service"""
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize XRDP service client
        
        Args:
            base_url: Base URL for rdp-xrdp service (e.g., http://rdp-xrdp:3389)
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized XRDPClient for {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check rdp-xrdp service health"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def start_service(
        self,
        process_id: str,
        port: int,
        config_path: str,
        log_path: str,
        session_path: str
    ) -> Dict[str, Any]:
        """
        Start an XRDP service process
        
        Args:
            process_id: Unique ID for the XRDP process
            port: Port for the XRDP service
            config_path: Path to the XRDP configuration directory
            log_path: Path to the XRDP log directory
            session_path: Path to the XRDP session directory
            
        Returns:
            Service start result with process_id, status, port, started_at, pid
        """
        try:
            client = await self._get_client()
            payload = {
                "process_id": process_id,
                "port": port,
                "config_path": config_path,
                "log_path": log_path,
                "session_path": session_path
            }
            
            response = await client.post("/services", json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Started XRDP service for process {process_id} on port {port}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to start XRDP service for process {process_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error starting XRDP service for process {process_id}: {e}")
            raise
    
    async def get_service_status(self, process_id: str) -> Dict[str, Any]:
        """
        Get XRDP service status
        
        Args:
            process_id: ID of the XRDP process
            
        Returns:
            Service status information
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/services/{process_id}")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_found"}
            logger.error(f"Failed to get service status for process {process_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting service status for process {process_id}: {e}")
            raise
    
    async def stop_service(self, process_id: str) -> Dict[str, Any]:
        """
        Stop an XRDP service process
        
        Args:
            process_id: ID of the XRDP process to stop
            
        Returns:
            Stop result
        """
        try:
            client = await self._get_client()
            response = await client.post(f"/services/{process_id}/stop")
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Stopped XRDP service for process {process_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to stop XRDP service for process {process_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error stopping XRDP service for process {process_id}: {e}")
            raise
    
    async def restart_service(self, process_id: str) -> Dict[str, Any]:
        """
        Restart an XRDP service process
        
        Args:
            process_id: ID of the XRDP process to restart
            
        Returns:
            Restart result
        """
        try:
            client = await self._get_client()
            response = await client.post(f"/services/{process_id}/restart")
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Restarted XRDP service for process {process_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to restart XRDP service for process {process_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error restarting XRDP service for process {process_id}: {e}")
            raise
    
    async def list_services(self) -> Dict[str, Any]:
        """
        List all XRDP services
        
        Returns:
            List of active services
        """
        try:
            client = await self._get_client()
            response = await client.get("/services")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            raise
    
    async def create_config(
        self,
        server_id: str,
        port: int,
        user_id: str,
        session_id: str,
        display_config: Optional[Dict[str, Any]] = None,
        security_level: str = "high"
    ) -> Dict[str, Any]:
        """
        Create XRDP configuration
        
        Args:
            server_id: Unique ID for the RDP server
            port: Port for the XRDP service
            user_id: User ID associated with the server
            session_id: Session ID associated with the server
            display_config: Optional display configuration
            security_level: Security level (low, medium, high, maximum)
            
        Returns:
            Configuration creation result
        """
        try:
            client = await self._get_client()
            # FastAPI endpoint uses query parameters
            # Note: display_config is Optional[Dict] which is problematic as query param
            # For now, pass simple params as query params (display_config support may require API update)
            params = {
                "server_id": server_id,
                "port": port,
                "user_id": user_id,
                "session_id": session_id,
                "security_level": security_level
            }
            
            response = await client.post("/config/create", params=params)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Created XRDP configuration for server {server_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create config for server {server_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating config for server {server_id}: {e}")
            raise
    
    async def validate_config(self, config_path: str) -> Dict[str, Any]:
        """
        Validate XRDP configuration
        
        Args:
            config_path: Path to the configuration directory
            
        Returns:
            Validation result
        """
        try:
            client = await self._get_client()
            payload = {
                "config_path": config_path
            }
            
            response = await client.post("/config/validate", json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to validate config at {config_path}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error validating config at {config_path}: {e}")
            raise
    
    async def cleanup_config(self, server_id: str) -> Dict[str, Any]:
        """
        Cleanup XRDP configuration
        
        Args:
            server_id: ID of the server to clean up configuration for
            
        Returns:
            Cleanup result
        """
        try:
            client = await self._get_client()
            response = await client.delete(f"/config/{server_id}")
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Cleaned up XRDP configuration for server {server_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cleanup config for server {server_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error cleaning up config for server {server_id}: {e}")
            raise


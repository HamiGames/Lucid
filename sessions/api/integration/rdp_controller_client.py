"""
RDP Controller Client

HTTP client for integrating with rdp-controller service.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
import httpx

logger = logging.getLogger(__name__)


class RDPControllerClient:
    """HTTP client for rdp-controller service"""
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize RDP controller client
        
        Args:
            base_url: Base URL for rdp-controller service (e.g., http://rdp-controller:8092)
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized RDPControllerClient for {self.base_url}")
    
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
        """Check rdp-controller service health"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_session(
        self,
        user_id: str,
        server_id: str,
        session_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new RDP session and get session-id and session-room (connection_id)
        
        Args:
            user_id: User identifier
            server_id: Server UUID string
            session_config: Session configuration dictionary
            
        Returns:
            Session creation result with session_id and connection_id (session-room)
        """
        try:
            client = await self._get_client()
            # rdp-controller endpoint expects query parameters or JSON body
            # Based on the endpoint signature, we'll send as JSON body
            payload = {
                "user_id": user_id,
                "server_id": server_id,
                "session_config": session_config
            }
            
            response = await client.post("/api/v1/sessions", json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Created RDP session {result.get('session_id')} for user {user_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create RDP session for user {user_id}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating RDP session for user {user_id}: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get session by ID
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            Session information
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/sessions/{session_id}")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_found"}
            logger.error(f"Failed to get session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise
    
    async def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            response = await client.delete(f"/api/v1/sessions/{session_id}")
            response.raise_for_status()
            
            logger.info(f"Terminated session {session_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to terminate session {session_id}: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            return False
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get session metrics
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            Session metrics
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/sessions/{session_id}/metrics")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_found"}
            logger.error(f"Failed to get metrics for session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting metrics for session {session_id}: {e}")
            raise


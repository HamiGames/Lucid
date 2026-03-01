"""
Session Recorder Client

HTTP client for integrating with session-recorder service.
"""

import logging
from typing import Dict, Any, Optional
import httpx
from uuid import UUID

logger = logging.getLogger(__name__)


class SessionRecorderClient:
    """HTTP client for session-recorder service"""
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize session recorder client
        
        Args:
            base_url: Base URL for session-recorder service (e.g., http://session-recorder:8090)
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized SessionRecorderClient for {self.base_url}")
    
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
        """Check session-recorder service health"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def start_recording(
        self,
        session_id: str,
        owner_address: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start recording a session
        
        Args:
            session_id: Session ID (UUID string)
            owner_address: Owner address
            metadata: Optional metadata dictionary
            
        Returns:
            Recording start result
        """
        try:
            client = await self._get_client()
            payload = {
                "session_id": session_id,
                "owner_address": owner_address,
                "metadata": metadata or {}
            }
            
            response = await client.post("/recordings/start", json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Started recording for session {session_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to start recording for session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error starting recording for session {session_id}: {e}")
            raise
    
    async def stop_recording(self, session_id: str) -> Dict[str, Any]:
        """
        Stop recording a session
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            Recording stop result with chunk information
        """
        try:
            client = await self._get_client()
            response = await client.post(f"/recordings/{session_id}/stop")
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Stopped recording for session {session_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to stop recording for session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error stopping recording for session {session_id}: {e}")
            raise
    
    async def get_recording(self, session_id: str) -> Dict[str, Any]:
        """
        Get recording information
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            Recording information
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/recordings/{session_id}")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_found"}
            logger.error(f"Failed to get recording for session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting recording for session {session_id}: {e}")
            raise
    
    async def delete_recording(self, session_id: str) -> bool:
        """
        Delete a recording
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            response = await client.delete(f"/recordings/{session_id}")
            response.raise_for_status()
            
            logger.info(f"Deleted recording for session {session_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete recording for session {session_id}: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error deleting recording for session {session_id}: {e}")
            return False


"""
Session Processor Client

HTTP client for integrating with session-processor service.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx
from uuid import UUID

logger = logging.getLogger(__name__)


class SessionProcessorClient:
    """HTTP client for session-processor service"""
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize session processor client
        
        Args:
            base_url: Base URL for session-processor service (e.g., http://session-processor:8091)
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized SessionProcessorClient for {self.base_url}")
    
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
        """Check session-processor service health"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def process_chunk(
        self,
        session_id: str,
        chunk_id: str,
        chunk_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a single chunk
        
        Args:
            session_id: Session ID (UUID string)
            chunk_id: Chunk ID
            chunk_data: Chunk data as bytes
            metadata: Optional metadata dictionary
            
        Returns:
            Processing result
        """
        try:
            import base64
            client = await self._get_client()
            
            # Encode chunk data as base64
            chunk_data_b64 = base64.b64encode(chunk_data).decode('utf-8')
            
            payload = {
                "session_id": session_id,
                "chunk_id": chunk_id,
                "chunk_data": chunk_data_b64,
                "metadata": metadata or {}
            }
            
            response = await client.post("/api/v1/chunks/process", json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Processed chunk {chunk_id} for session {session_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to process chunk {chunk_id} for session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_id} for session {session_id}: {e}")
            raise
    
    async def process_batch(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process multiple chunks in batch
        
        Args:
            chunks: List of chunk dictionaries with session_id, chunk_id, chunk_data, metadata
            
        Returns:
            Batch processing result
        """
        try:
            import base64
            client = await self._get_client()
            
            # Encode chunk data as base64 for each chunk
            encoded_chunks = []
            for chunk in chunks:
                encoded_chunk = chunk.copy()
                if 'chunk_data' in encoded_chunk and isinstance(encoded_chunk['chunk_data'], bytes):
                    encoded_chunk['chunk_data'] = base64.b64encode(encoded_chunk['chunk_data']).decode('utf-8')
                encoded_chunks.append(encoded_chunk)
            
            payload = {
                "chunks": encoded_chunks
            }
            
            response = await client.post("/api/v1/chunks/process-batch", json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Processed batch of {len(chunks)} chunks")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to process batch: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise
    
    async def get_merkle_root(self, session_id: str) -> Dict[str, Any]:
        """
        Get Merkle root for a session
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            Merkle root information
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/sessions/{session_id}/merkle-root")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_found"}
            logger.error(f"Failed to get Merkle root for session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting Merkle root for session {session_id}: {e}")
            raise
    
    async def finalize_session(self, session_id: str) -> Dict[str, Any]:
        """
        Finalize session processing
        
        Args:
            session_id: Session ID (UUID string)
            
        Returns:
            Finalization result
        """
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/sessions/{session_id}/finalize")
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Finalized processing for session {session_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to finalize session {session_id}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error finalizing session {session_id}: {e}")
            raise


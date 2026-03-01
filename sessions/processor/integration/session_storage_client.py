#!/usr/bin/env python3
"""
Session Storage Integration Client
Handles interaction with session-storage service for chunk persistence
"""

import logging
import os
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime

from .service_base import ServiceClientBase, ServiceError
import httpx

# Use core.logging if available, fallback to standard logging
try:
    from core.logging import get_logger
except ImportError:
    logger = logging.getLogger(__name__)
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class SessionStorageClient(ServiceClientBase):
    """
    Client for interacting with session-storage service
    Handles chunk storage, retrieval, and session management
    """

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """
        Initialize Session Storage client

        Args:
            base_url: Base URL for session-storage (from SESSION_STORAGE_URL env var if not provided)
            **kwargs: Additional arguments passed to ServiceClientBase
        """
        url = base_url or os.getenv('SESSION_STORAGE_URL', '')
        if not url:
            raise ValueError("SESSION_STORAGE_URL environment variable is required")

        super().__init__(base_url=url, **kwargs)

    async def store_chunk(
        self,
        session_id: str,
        chunk_id: str,
        chunk_data: bytes,
        chunk_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a chunk for a session

        Args:
            session_id: Session identifier
            chunk_id: Chunk identifier
            chunk_data: Chunk data (bytes)
            chunk_metadata: Optional chunk metadata

        Returns:
            Storage response
        """
        try:
            # Encode chunk data as base64 for JSON transport
            chunk_data_b64 = base64.b64encode(chunk_data).decode('utf-8')

            # Prepare metadata with required fields
            metadata = chunk_metadata or {}
            metadata.setdefault('chunk_id', chunk_id)
            metadata.setdefault('timestamp', datetime.utcnow().isoformat())

            payload = {
                "chunk_data": chunk_data_b64,
                "chunk_metadata": metadata
            }

            url = f"{self.base_url}/sessions/{session_id}/chunks"

            request_headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            if self.api_key:
                request_headers['Authorization'] = f'Bearer {self.api_key}'

            # Retry logic
            last_error = None
            for attempt in range(self.retry_count):
                try:
                    logger.debug(f"Storing chunk {chunk_id} for session {session_id} (attempt {attempt + 1}/{self.retry_count})")

                    response = await self.client.post(
                        url,
                        json=payload,
                        headers=request_headers,
                        timeout=httpx.Timeout(self.timeout, connect=5.0)
                    )

                    response.raise_for_status()
                    result = response.json()

                    logger.info(f"Successfully stored chunk {chunk_id} for session {session_id}")
                    return result

                except httpx.TimeoutException as e:
                    last_error = ServiceError(f"Request to {url} timed out after {self.timeout}s")
                    logger.warning(f"Request timeout (attempt {attempt + 1}/{self.retry_count}): {str(e)}")

                except httpx.HTTPStatusError as e:
                    last_error = ServiceError(f"HTTP error {e.response.status_code}: {e.response.text}")
                    logger.warning(f"HTTP error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")

                    if 400 <= e.response.status_code < 500:
                        raise last_error

                except Exception as e:
                    last_error = ServiceError(f"Request failed: {str(e)}")
                    logger.warning(f"Request error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")

                if attempt < self.retry_count - 1:
                    import asyncio
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            raise last_error or ServiceError(f"Request to {url} failed after {self.retry_count} attempts")

        except Exception as e:
            logger.error(f"Failed to store chunk {chunk_id} for session {session_id}: {str(e)}")
            raise ServiceError(f"Chunk storage failed: {str(e)}")

    async def get_chunk(self, session_id: str, chunk_id: str) -> Optional[bytes]:
        """
        Retrieve a chunk for a session

        Args:
            session_id: Session identifier
            chunk_id: Chunk identifier

        Returns:
            Chunk data (bytes) or None if not found
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint=f'/sessions/{session_id}/chunks/{chunk_id}'
            )

            # Extract chunk data from response
            chunk_data_b64 = response.get('data') or response.get('chunk_data')
            if chunk_data_b64:
                chunk_data = base64.b64decode(chunk_data_b64)
                logger.debug(f"Retrieved chunk {chunk_id} for session {session_id}")
                return chunk_data

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id} for session {session_id}: {str(e)}")
            raise ServiceError(f"Chunk retrieval failed: {str(e)}")

    async def list_session_chunks(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List chunks for a session

        Args:
            session_id: Session identifier
            limit: Maximum number of chunks to return
            offset: Offset for pagination

        Returns:
            List of chunk metadata
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint=f'/sessions/{session_id}/chunks',
                params={
                    'limit': limit,
                    'offset': offset
                }
            )

            chunks = response.get('chunks', [])
            logger.debug(f"Retrieved {len(chunks)} chunks for session {session_id}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to list chunks for session {session_id}: {str(e)}")
            raise ServiceError(f"Chunk listing failed: {str(e)}")

    async def delete_chunk(self, session_id: str, chunk_id: str) -> Dict[str, Any]:
        """
        Delete a chunk for a session

        Args:
            session_id: Session identifier
            chunk_id: Chunk identifier

        Returns:
            Deletion response
        """
        try:
            response = await self._make_request(
                method='DELETE',
                endpoint=f'/sessions/{session_id}/chunks/{chunk_id}'
            )

            logger.info(f"Deleted chunk {chunk_id} for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id} for session {session_id}: {str(e)}")
            raise ServiceError(f"Chunk deletion failed: {str(e)}")


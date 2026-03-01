#!/usr/bin/env python3
"""
Session Pipeline Integration Client
Handles interaction with session-pipeline service for pipeline orchestration
"""

import logging
import os
import base64
from typing import Dict, Any, Optional
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


class SessionPipelineClient(ServiceClientBase):
    """
    Client for interacting with session-pipeline service
    Handles pipeline creation, starting, stopping, and chunk processing
    """

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """
        Initialize Session Pipeline client

        Args:
            base_url: Base URL for session-pipeline (from SESSION_PIPELINE_URL env var if not provided)
            **kwargs: Additional arguments passed to ServiceClientBase
        """
        url = base_url or os.getenv('SESSION_PIPELINE_URL', '')
        if not url:
            raise ValueError("SESSION_PIPELINE_URL environment variable is required")

        super().__init__(base_url=url, **kwargs)

    async def create_pipeline(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new pipeline for a session

        Args:
            session_id: Session identifier
            metadata: Optional pipeline metadata

        Returns:
            Pipeline creation response
        """
        try:
            payload = {
                "session_id": session_id,
                "metadata": metadata or {}
            }

            response = await self._make_request(
                method='POST',
                endpoint='/pipelines',
                params={"session_id": session_id},
                json_data=payload
            )

            logger.info(f"Created pipeline for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to create pipeline for session {session_id}: {str(e)}")
            raise ServiceError(f"Pipeline creation failed: {str(e)}")

    async def start_pipeline(self, session_id: str) -> Dict[str, Any]:
        """
        Start a pipeline for a session

        Args:
            session_id: Session identifier

        Returns:
            Pipeline start response
        """
        try:
            response = await self._make_request(
                method='POST',
                endpoint=f'/pipelines/{session_id}/start'
            )

            logger.info(f"Started pipeline for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to start pipeline for session {session_id}: {str(e)}")
            raise ServiceError(f"Pipeline start failed: {str(e)}")

    async def stop_pipeline(self, session_id: str) -> Dict[str, Any]:
        """
        Stop a pipeline for a session

        Args:
            session_id: Session identifier

        Returns:
            Pipeline stop response
        """
        try:
            response = await self._make_request(
                method='POST',
                endpoint=f'/pipelines/{session_id}/stop'
            )

            logger.info(f"Stopped pipeline for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to stop pipeline for session {session_id}: {str(e)}")
            raise ServiceError(f"Pipeline stop failed: {str(e)}")

    async def process_chunk(
        self,
        session_id: str,
        chunk_data: bytes,
        chunk_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chunk through the pipeline

        Args:
            session_id: Session identifier
            chunk_data: Raw chunk data (bytes)
            chunk_metadata: Optional chunk metadata

        Returns:
            Processing response
        """
        try:
            # Encode chunk data as base64 for JSON transport
            chunk_data_b64 = base64.b64encode(chunk_data).decode('utf-8')

            payload = {
                "chunk_data": chunk_data_b64,
                "chunk_metadata": chunk_metadata or {}
            }

            # Use _make_request_with_binary for binary data handling
            url = f"{self.base_url}/pipelines/{session_id}/chunks"

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
                    logger.debug(f"Sending chunk to pipeline for session {session_id} (attempt {attempt + 1}/{self.retry_count})")

                    response = await self.client.post(
                        url,
                        json=payload,
                        headers=request_headers,
                        timeout=httpx.Timeout(self.timeout, connect=5.0)
                    )

                    response.raise_for_status()
                    result = response.json()

                    logger.debug(f"Successfully sent chunk to pipeline for session {session_id}")
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
            logger.error(f"Failed to process chunk for session {session_id}: {str(e)}")
            raise ServiceError(f"Chunk processing failed: {str(e)}")

    async def get_pipeline_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get pipeline status for a session

        Args:
            session_id: Session identifier

        Returns:
            Pipeline status information
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint=f'/pipelines/{session_id}/status'
            )
            return response
        except Exception as e:
            logger.error(f"Failed to get pipeline status for session {session_id}: {str(e)}")
            raise ServiceError(f"Pipeline status retrieval failed: {str(e)}")

    async def cleanup_pipeline(self, session_id: str) -> Dict[str, Any]:
        """
        Clean up pipeline resources for a session

        Args:
            session_id: Session identifier

        Returns:
            Cleanup response
        """
        try:
            response = await self._make_request(
                method='DELETE',
                endpoint=f'/pipelines/{session_id}'
            )

            logger.info(f"Cleaned up pipeline for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to cleanup pipeline for session {session_id}: {str(e)}")
            raise ServiceError(f"Pipeline cleanup failed: {str(e)}")


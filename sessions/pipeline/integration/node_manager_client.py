#!/usr/bin/env python3
"""
Node Management Integration Client
Handles interaction with node-management service for node coordination
"""

import logging
import os
from typing import Dict, Any, Optional, List

from .service_base import ServiceClientBase, ServiceError
from core.logging import get_logger

logger = get_logger(__name__)


class NodeManagerClient(ServiceClientBase):
    """
    Client for interacting with node-management service
    Handles node registration, resource allocation, and node coordination
    """
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """
        Initialize Node Manager client
        
        Args:
            base_url: Base URL for node-management (from NODE_MANAGEMENT_URL env var if not provided)
            **kwargs: Additional arguments passed to ServiceClientBase
        """
        url = base_url or os.getenv('NODE_MANAGEMENT_URL', '')
        if not url:
            raise ValueError("NODE_MANAGEMENT_URL environment variable is required")
        
        super().__init__(base_url=url, **kwargs)
    
    async def register_session_pipeline(
        self,
        node_id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register session-pipeline node with node-management service
        
        Args:
            node_id: Optional node identifier (auto-generated if not provided)
            capabilities: Optional node capabilities dictionary
            
        Returns:
            Registration confirmation
        """
        try:
            payload = {
                "node_type": "session-pipeline",
                "node_id": node_id or os.getenv('SESSION_PIPELINE_HOST', 'session-pipeline'),
                "capabilities": capabilities or {
                    "max_concurrent_sessions": int(os.getenv('MAX_CONCURRENT_SESSIONS', '100')),
                    "chunk_processing": True,
                    "encryption": True,
                    "compression": True
                },
                "status": "active"
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/nodes/register',
                json_data=payload
            )
            
            logger.info(f"Registered session-pipeline node: {payload['node_id']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to register node: {str(e)}")
            raise ServiceError(f"Node registration failed: {str(e)}")
    
    async def get_node_status(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get node status
        
        Args:
            node_id: Node identifier (uses SESSION_PIPELINE_HOST if not provided)
            
        Returns:
            Node status information
        """
        try:
            node_id = node_id or os.getenv('SESSION_PIPELINE_HOST', 'session-pipeline')
            
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/v1/nodes/{node_id}/status'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get node status: {str(e)}")
            raise ServiceError(f"Failed to get node status: {str(e)}")
    
    async def update_node_metrics(
        self,
        node_id: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update node metrics
        
        Args:
            node_id: Node identifier (uses SESSION_PIPELINE_HOST if not provided)
            metrics: Metrics dictionary (active_sessions, cpu_usage, memory_usage, etc.)
            
        Returns:
            Update confirmation
        """
        try:
            node_id = node_id or os.getenv('SESSION_PIPELINE_HOST', 'session-pipeline')
            
            payload = {
                "metrics": metrics or {}
            }
            
            response = await self._make_request(
                method='POST',
                endpoint=f'/api/v1/nodes/{node_id}/metrics',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to update node metrics: {str(e)}")
            raise ServiceError(f"Failed to update node metrics: {str(e)}")
    
    async def get_available_nodes(
        self,
        node_type: Optional[str] = None,
        min_capacity: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of available nodes
        
        Args:
            node_type: Optional filter by node type
            min_capacity: Optional minimum capacity requirement
            
        Returns:
            List of available nodes
        """
        try:
            params = {}
            if node_type:
                params['node_type'] = node_type
            if min_capacity:
                params['min_capacity'] = min_capacity
            
            response = await self._make_request(
                method='GET',
                endpoint='/api/v1/nodes/available',
                params=params
            )
            
            return response.get('nodes', [])
            
        except Exception as e:
            logger.error(f"Failed to get available nodes: {str(e)}")
            raise ServiceError(f"Failed to get available nodes: {str(e)}")
    
    async def request_resources(
        self,
        resource_type: str,
        quantity: int,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Request resources from node-management service
        
        Args:
            resource_type: Type of resource (cpu, memory, storage, etc.)
            quantity: Quantity of resources needed
            session_id: Optional session identifier for tracking
            
        Returns:
            Resource allocation confirmation
        """
        try:
            payload = {
                "resource_type": resource_type,
                "quantity": quantity,
                "session_id": session_id
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/resources/request',
                json_data=payload
            )
            
            logger.info(f"Requested {quantity} {resource_type} resources for session {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to request resources: {str(e)}")
            raise ServiceError(f"Resource request failed: {str(e)}")
    
    async def release_resources(
        self,
        allocation_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Release allocated resources
        
        Args:
            allocation_id: Resource allocation identifier
            session_id: Optional session identifier
            
        Returns:
            Release confirmation
        """
        try:
            payload = {
                "allocation_id": allocation_id,
                "session_id": session_id
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/resources/release',
                json_data=payload
            )
            
            logger.info(f"Released resources {allocation_id} for session {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to release resources: {str(e)}")
            raise ServiceError(f"Resource release failed: {str(e)}")


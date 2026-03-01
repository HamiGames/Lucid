#!/usr/bin/env python3
"""
Integration Manager
Manages initialization and lifecycle of all integration clients
"""

import logging
from typing import Optional, Dict, Any
from .blockchain_engine_client import BlockchainEngineClient
from .node_manager_client import NodeManagerClient
from .api_gateway_client import APIGatewayClient
from .auth_service_client import AuthServiceClient
from .service_base import ServiceError
from core.logging import get_logger

logger = get_logger(__name__)


class IntegrationManager:
    """
    Manages all integration service clients
    Provides centralized access to external service integrations
    """
    
    def __init__(self, config: Any):
        """
        Initialize integration manager with pipeline configuration
        
        Args:
            config: PipelineConfig instance containing service URLs
        """
        self.config = config
        self._blockchain_client: Optional[BlockchainEngineClient] = None
        self._node_manager_client: Optional[NodeManagerClient] = None
        self._api_gateway_client: Optional[APIGatewayClient] = None
        self._auth_service_client: Optional[AuthServiceClient] = None
        
        logger.info("Initializing IntegrationManager")
    
    @property
    def blockchain(self) -> Optional[BlockchainEngineClient]:
        """Get blockchain engine client (lazy initialization)"""
        if self._blockchain_client is None and self.config.settings.BLOCKCHAIN_ENGINE_URL:
            try:
                self._blockchain_client = BlockchainEngineClient(
                    base_url=self.config.settings.BLOCKCHAIN_ENGINE_URL,
                    timeout=self.config.settings.SERVICE_TIMEOUT_SECONDS,
                    retry_count=self.config.settings.SERVICE_RETRY_COUNT,
                    retry_delay=self.config.settings.SERVICE_RETRY_DELAY_SECONDS
                )
                logger.info("Initialized BlockchainEngineClient")
            except Exception as e:
                logger.warning(f"Failed to initialize BlockchainEngineClient: {str(e)}")
        return self._blockchain_client
    
    @property
    def node_manager(self) -> Optional[NodeManagerClient]:
        """Get node manager client (lazy initialization)"""
        if self._node_manager_client is None and self.config.settings.NODE_MANAGEMENT_URL:
            try:
                self._node_manager_client = NodeManagerClient(
                    base_url=self.config.settings.NODE_MANAGEMENT_URL,
                    timeout=self.config.settings.SERVICE_TIMEOUT_SECONDS,
                    retry_count=self.config.settings.SERVICE_RETRY_COUNT,
                    retry_delay=self.config.settings.SERVICE_RETRY_DELAY_SECONDS
                )
                logger.info("Initialized NodeManagerClient")
            except Exception as e:
                logger.warning(f"Failed to initialize NodeManagerClient: {str(e)}")
        return self._node_manager_client
    
    @property
    def api_gateway(self) -> Optional[APIGatewayClient]:
        """Get API gateway client (lazy initialization)"""
        if self._api_gateway_client is None and self.config.settings.API_GATEWAY_URL:
            try:
                self._api_gateway_client = APIGatewayClient(
                    base_url=self.config.settings.API_GATEWAY_URL,
                    timeout=self.config.settings.SERVICE_TIMEOUT_SECONDS,
                    retry_count=self.config.settings.SERVICE_RETRY_COUNT,
                    retry_delay=self.config.settings.SERVICE_RETRY_DELAY_SECONDS
                )
                logger.info("Initialized APIGatewayClient")
            except Exception as e:
                logger.warning(f"Failed to initialize APIGatewayClient: {str(e)}")
        return self._api_gateway_client
    
    @property
    def auth_service(self) -> Optional[AuthServiceClient]:
        """Get auth service client (lazy initialization)"""
        if self._auth_service_client is None and self.config.settings.AUTH_SERVICE_URL:
            try:
                self._auth_service_client = AuthServiceClient(
                    base_url=self.config.settings.AUTH_SERVICE_URL,
                    timeout=self.config.settings.SERVICE_TIMEOUT_SECONDS,
                    retry_count=self.config.settings.SERVICE_RETRY_COUNT,
                    retry_delay=self.config.settings.SERVICE_RETRY_DELAY_SECONDS
                )
                logger.info("Initialized AuthServiceClient")
            except Exception as e:
                logger.warning(f"Failed to initialize AuthServiceClient: {str(e)}")
        return self._auth_service_client
    
    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health check on all initialized clients
        
        Returns:
            Dictionary of health status for each service
        """
        results = {}
        
        if self._blockchain_client:
            try:
                results['blockchain'] = await self._blockchain_client.health_check()
            except Exception as e:
                results['blockchain'] = {"status": "error", "error": str(e)}
        
        if self._node_manager_client:
            try:
                results['node_manager'] = await self._node_manager_client.health_check()
            except Exception as e:
                results['node_manager'] = {"status": "error", "error": str(e)}
        
        if self._api_gateway_client:
            try:
                results['api_gateway'] = await self._api_gateway_client.health_check()
            except Exception as e:
                results['api_gateway'] = {"status": "error", "error": str(e)}
        
        if self._auth_service_client:
            try:
                results['auth_service'] = await self._auth_service_client.health_check()
            except Exception as e:
                results['auth_service'] = {"status": "error", "error": str(e)}
        
        return results
    
    async def close_all(self):
        """Close all client connections"""
        if self._blockchain_client:
            try:
                await self._blockchain_client.close()
            except Exception as e:
                logger.warning(f"Error closing blockchain client: {str(e)}")
        
        if self._node_manager_client:
            try:
                await self._node_manager_client.close()
            except Exception as e:
                logger.warning(f"Error closing node manager client: {str(e)}")
        
        if self._api_gateway_client:
            try:
                await self._api_gateway_client.close()
            except Exception as e:
                logger.warning(f"Error closing api gateway client: {str(e)}")
        
        if self._auth_service_client:
            try:
                await self._auth_service_client.close()
            except Exception as e:
                logger.warning(f"Error closing auth service client: {str(e)}")
        
        logger.info("Closed all integration clients")


#!/usr/bin/env python3
"""
Integration Manager for Session Processor
Manages initialization and lifecycle of integration clients
"""

import logging
import os
from typing import Optional, Dict, Any

# Use core.logging if available, fallback to standard logging
try:
    from core.logging import get_logger
except ImportError:
    logger = logging.getLogger(__name__)
    def get_logger(name):
        return logging.getLogger(name)

# Import clients from pipeline integration (shared across services)
# Note: PYTHONPATH includes /app, so sessions.pipeline.integration is accessible
try:
    from sessions.pipeline.integration.blockchain_engine_client import BlockchainEngineClient
    from sessions.pipeline.integration.node_manager_client import NodeManagerClient
    from sessions.pipeline.integration.api_gateway_client import APIGatewayClient
    from sessions.pipeline.integration.auth_service_client import AuthServiceClient
except ImportError:
    # Fallback if pipeline integration clients are not available
    BlockchainEngineClient = None
    NodeManagerClient = None
    APIGatewayClient = None
    AuthServiceClient = None

# Import local processor integration clients
try:
    from .session_pipeline_client import SessionPipelineClient
    from .session_storage_client import SessionStorageClient
except ImportError:
    # Fallback if local clients fail to import
    SessionPipelineClient = None
    SessionStorageClient = None

logger = get_logger(__name__)


class IntegrationManager:
    """
    Manages integration service clients for session-processor
    Provides centralized access to external service integrations
    """
    
    def __init__(self, service_timeout: float = 30.0, service_retry_count: int = 3, service_retry_delay: float = 1.0):
        """
        Initialize integration manager
        
        Args:
            service_timeout: Service call timeout in seconds
            service_retry_count: Number of retry attempts
            service_retry_delay: Delay between retries in seconds
        """
        self.service_timeout = float(os.getenv('SERVICE_TIMEOUT_SECONDS', service_timeout))
        self.service_retry_count = int(os.getenv('SERVICE_RETRY_COUNT', service_retry_count))
        self.service_retry_delay = float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', service_retry_delay))
        
        self._blockchain_client: Optional[BlockchainEngineClient] = None
        self._node_manager_client: Optional[NodeManagerClient] = None
        self._api_gateway_client: Optional[APIGatewayClient] = None
        self._auth_service_client: Optional[AuthServiceClient] = None
        self._pipeline_client: Optional[SessionPipelineClient] = None
        self._storage_client: Optional[SessionStorageClient] = None
        
        logger.info("Initializing IntegrationManager for session-processor")
    
    @property
    def blockchain(self) -> Optional[BlockchainEngineClient]:
        """Get blockchain engine client (lazy initialization)"""
        if self._blockchain_client is None and BlockchainEngineClient:
            url = os.getenv('BLOCKCHAIN_ENGINE_URL', '')
            if url:
                try:
                    self._blockchain_client = BlockchainEngineClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized BlockchainEngineClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize BlockchainEngineClient: {str(e)}")
        return self._blockchain_client
    
    @property
    def node_manager(self) -> Optional[NodeManagerClient]:
        """Get node manager client (lazy initialization)"""
        if self._node_manager_client is None and NodeManagerClient:
            url = os.getenv('NODE_MANAGEMENT_URL', '')
            if url:
                try:
                    self._node_manager_client = NodeManagerClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized NodeManagerClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize NodeManagerClient: {str(e)}")
        return self._node_manager_client
    
    @property
    def api_gateway(self) -> Optional[APIGatewayClient]:
        """Get API gateway client (lazy initialization)"""
        if self._api_gateway_client is None and APIGatewayClient:
            url = os.getenv('API_GATEWAY_URL', '')
            if url:
                try:
                    self._api_gateway_client = APIGatewayClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized APIGatewayClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize APIGatewayClient: {str(e)}")
        return self._api_gateway_client
    
    @property
    def auth_service(self) -> Optional[AuthServiceClient]:
        """Get auth service client (lazy initialization)"""
        if self._auth_service_client is None and AuthServiceClient:
            url = os.getenv('AUTH_SERVICE_URL', '')
            if url:
                try:
                    self._auth_service_client = AuthServiceClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized AuthServiceClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize AuthServiceClient: {str(e)}")
        return self._auth_service_client
    
    @property
    def pipeline(self) -> Optional[SessionPipelineClient]:
        """Get session pipeline client (lazy initialization)"""
        if self._pipeline_client is None and SessionPipelineClient:
            url = os.getenv('SESSION_PIPELINE_URL', '')
            if url:
                try:
                    self._pipeline_client = SessionPipelineClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay,
                        api_key=os.getenv('JWT_SECRET_KEY', '')
                    )
                    logger.info("Initialized SessionPipelineClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize SessionPipelineClient: {str(e)}")
        return self._pipeline_client
    
    @property
    def storage(self) -> Optional[SessionStorageClient]:
        """Get session storage client (lazy initialization)"""
        if self._storage_client is None and SessionStorageClient:
            url = os.getenv('SESSION_STORAGE_URL', '')
            if url:
                try:
                    self._storage_client = SessionStorageClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay,
                        api_key=os.getenv('JWT_SECRET_KEY', '')
                    )
                    logger.info("Initialized SessionStorageClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize SessionStorageClient: {str(e)}")
        return self._storage_client
    
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
        
        if self._pipeline_client:
            try:
                results['pipeline'] = await self._pipeline_client.health_check()
            except Exception as e:
                results['pipeline'] = {"status": "error", "error": str(e)}
        
        if self._storage_client:
            try:
                results['storage'] = await self._storage_client.health_check()
            except Exception as e:
                results['storage'] = {"status": "error", "error": str(e)}
        
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
        
        if self._pipeline_client:
            try:
                await self._pipeline_client.close()
            except Exception as e:
                logger.warning(f"Error closing pipeline client: {str(e)}")
        
        if self._storage_client:
            try:
                await self._storage_client.close()
            except Exception as e:
                logger.warning(f"Error closing storage client: {str(e)}")
        
        logger.info("Closed all integration clients")


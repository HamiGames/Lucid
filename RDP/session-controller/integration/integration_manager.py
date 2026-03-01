"""
Integration Manager for RDP Session Controller

Manages initialization and lifecycle of integration clients for
RDP and session services.
"""

import logging
import os
from typing import Optional, Dict, Any

from .session_recorder_client import SessionRecorderClient
from .session_processor_client import SessionProcessorClient
from .xrdp_client import XRDPClient
from .rdp_server_manager_client import RDPServerManagerClient
from .rdp_monitor_client import RDPMonitorClient

logger = logging.getLogger(__name__)


class IntegrationManager:
    """
    Manages integration service clients for rdp-controller
    Provides centralized access to session-recorder, session-processor, and rdp-xrdp
    """
    
    def __init__(
        self,
        service_timeout: float = 30.0,
        service_retry_count: int = 3,
        service_retry_delay: float = 1.0
    ):
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
        
        self._recorder_client: Optional[SessionRecorderClient] = None
        self._processor_client: Optional[SessionProcessorClient] = None
        self._xrdp_client: Optional[XRDPClient] = None
        self._server_manager_client: Optional[RDPServerManagerClient] = None
        self._monitor_client: Optional[RDPMonitorClient] = None
        
        logger.info("Initializing IntegrationManager for rdp-controller")
    
    @property
    def recorder(self) -> Optional[SessionRecorderClient]:
        """Get session recorder client (lazy initialization)"""
        if self._recorder_client is None:
            url = os.getenv('SESSION_RECORDER_URL', '')
            if url:
                try:
                    self._recorder_client = SessionRecorderClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized SessionRecorderClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize SessionRecorderClient: {str(e)}")
            else:
                logger.warning("SESSION_RECORDER_URL not set, recorder client unavailable")
        return self._recorder_client
    
    @property
    def processor(self) -> Optional[SessionProcessorClient]:
        """Get session processor client (lazy initialization)"""
        if self._processor_client is None:
            url = os.getenv('SESSION_PROCESSOR_URL', '')
            if url:
                try:
                    self._processor_client = SessionProcessorClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized SessionProcessorClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize SessionProcessorClient: {str(e)}")
            else:
                logger.warning("SESSION_PROCESSOR_URL not set, processor client unavailable")
        return self._processor_client
    
    @property
    def xrdp(self) -> Optional[XRDPClient]:
        """Get XRDP service client (lazy initialization)"""
        if self._xrdp_client is None:
            url = os.getenv('RDP_XRDP_URL', '')
            if url:
                try:
                    self._xrdp_client = XRDPClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized XRDPClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize XRDPClient: {str(e)}")
            else:
                logger.warning("RDP_XRDP_URL not set, XRDP client unavailable")
        return self._xrdp_client
    
    @property
    def server_manager(self) -> Optional[RDPServerManagerClient]:
        """Get RDP server manager client (lazy initialization)"""
        if self._server_manager_client is None:
            url = os.getenv('RDP_SERVER_MANAGER_URL', '')
            if url:
                try:
                    self._server_manager_client = RDPServerManagerClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized RDPServerManagerClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize RDPServerManagerClient: {str(e)}")
            else:
                logger.warning("RDP_SERVER_MANAGER_URL not set, server manager client unavailable")
        return self._server_manager_client
    
    @property
    def monitor(self) -> Optional[RDPMonitorClient]:
        """Get RDP monitor client (lazy initialization)"""
        if self._monitor_client is None:
            url = os.getenv('RDP_MONITOR_URL', '')
            if url:
                try:
                    self._monitor_client = RDPMonitorClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized RDPMonitorClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize RDPMonitorClient: {str(e)}")
            else:
                logger.warning("RDP_MONITOR_URL not set, monitor client unavailable")
        return self._monitor_client
    
    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health check on all initialized clients
        
        Returns:
            Dictionary of health status for each service
        """
        results = {}
        
        if self._recorder_client:
            try:
                results['recorder'] = await self._recorder_client.health_check()
            except Exception as e:
                results['recorder'] = {"status": "error", "error": str(e)}
        else:
            results['recorder'] = {"status": "not_initialized"}
        
        if self._processor_client:
            try:
                results['processor'] = await self._processor_client.health_check()
            except Exception as e:
                results['processor'] = {"status": "error", "error": str(e)}
        else:
            results['processor'] = {"status": "not_initialized"}
        
        if self._xrdp_client:
            try:
                results['xrdp'] = await self._xrdp_client.health_check()
            except Exception as e:
                results['xrdp'] = {"status": "error", "error": str(e)}
        else:
            results['xrdp'] = {"status": "not_initialized"}
        
        if self._server_manager_client:
            try:
                results['server_manager'] = await self._server_manager_client.health_check()
            except Exception as e:
                results['server_manager'] = {"status": "error", "error": str(e)}
        else:
            results['server_manager'] = {"status": "not_initialized"}
        
        if self._monitor_client:
            try:
                results['monitor'] = await self._monitor_client.health_check()
            except Exception as e:
                results['monitor'] = {"status": "error", "error": str(e)}
        else:
            results['monitor'] = {"status": "not_initialized"}
        
        return results
    
    async def close_all(self):
        """Close all client connections"""
        if self._recorder_client:
            try:
                await self._recorder_client.close()
            except Exception as e:
                logger.warning(f"Error closing recorder client: {str(e)}")
        
        if self._processor_client:
            try:
                await self._processor_client.close()
            except Exception as e:
                logger.warning(f"Error closing processor client: {str(e)}")
        
        if self._xrdp_client:
            try:
                await self._xrdp_client.close()
            except Exception as e:
                logger.warning(f"Error closing XRDP client: {str(e)}")
        
        if self._server_manager_client:
            try:
                await self._server_manager_client.close()
            except Exception as e:
                logger.warning(f"Error closing server manager client: {str(e)}")
        
        if self._monitor_client:
            try:
                await self._monitor_client.close()
            except Exception as e:
                logger.warning(f"Error closing monitor client: {str(e)}")
        
        logger.info("Closed all integration clients")


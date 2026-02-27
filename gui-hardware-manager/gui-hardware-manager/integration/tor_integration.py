"""
Tor Proxy Integration Module for GUI Hardware Manager
Handles communication with tor-proxy service for onion address management
and anonymous transaction routing
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class TorServiceStatus(str, Enum):
    """Tor service status enumeration"""
    OPERATIONAL = "operational"
    INITIALIZING = "initializing"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"


class TorIntegrationManager:
    """Manages integration with tor-proxy service"""
    
    def __init__(self, tor_proxy_url: str, timeout: int = 30):
        """
        Initialize Tor integration manager
        
        Args:
            tor_proxy_url: Base URL of tor-proxy service (e.g., http://tor-proxy:9051)
            timeout: HTTP request timeout in seconds
        """
        self.tor_proxy_url = tor_proxy_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[httpx.AsyncClient] = None
        self.initialized = False
        self._health_check_interval = 60
        self._last_health_check = 0
        self._cached_status: Optional[Dict[str, Any]] = None
    
    async def initialize(self) -> bool:
        """
        Initialize Tor integration and verify connectivity
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing Tor integration with {self.tor_proxy_url}")
            
            # Create HTTP client
            self.session = httpx.AsyncClient(
                base_url=self.tor_proxy_url,
                timeout=self.timeout,
                follow_redirects=True
            )
            
            # Verify connectivity
            status = await self.check_health()
            if status.get("status") == TorServiceStatus.OPERATIONAL.value:
                self.initialized = True
                logger.info("Tor proxy service is operational")
                return True
            else:
                logger.warning(f"Tor proxy status: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Tor integration: {e}")
            return False
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check health status of tor-proxy service
        
        Returns:
            dict: Health status information
        """
        try:
            if not self.session:
                return {
                    "status": TorServiceStatus.UNREACHABLE.value,
                    "error": "Tor client not initialized"
                }
            
            response = await self.session.get("/health", timeout=self.timeout)
            
            if response.status_code == 200:
                return {
                    "status": TorServiceStatus.OPERATIONAL.value,
                    "service": "tor-proxy",
                    "details": response.json() if response.is_json else {}
                }
            else:
                logger.warning(f"Tor proxy health check failed: {response.status_code}")
                return {
                    "status": TorServiceStatus.UNHEALTHY.value,
                    "code": response.status_code
                }
                
        except asyncio.TimeoutError:
            logger.error("Tor proxy health check timed out")
            return {
                "status": TorServiceStatus.UNREACHABLE.value,
                "error": "Health check timeout"
            }
        except Exception as e:
            logger.error(f"Tor proxy health check failed: {e}")
            return {
                "status": TorServiceStatus.UNREACHABLE.value,
                "error": str(e)
            }
    
    async def get_onion_address(self) -> Optional[str]:
        """
        Get the current onion address from tor-proxy
        
        Returns:
            str: Onion address, or None if unavailable
        """
        try:
            if not self.session:
                logger.warning("Tor session not initialized")
                return None
            
            response = await self.session.get("/onion/address", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                onion_address = data.get("address")
                if onion_address:
                    logger.info(f"Onion address retrieved: {onion_address[:20]}...")
                    return onion_address
            else:
                logger.warning(f"Failed to get onion address: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error retrieving onion address: {e}")
        
        return None
    
    async def get_tor_circuit_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about current Tor circuit
        
        Returns:
            dict: Circuit information, or None if unavailable
        """
        try:
            if not self.session:
                logger.warning("Tor session not initialized")
                return None
            
            response = await self.session.get("/circuit/info", timeout=self.timeout)
            
            if response.status_code == 200:
                circuit_info = response.json()
                logger.debug(f"Circuit info retrieved: {circuit_info}")
                return circuit_info
            else:
                logger.warning(f"Failed to get circuit info: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error retrieving circuit info: {e}")
        
        return None
    
    async def get_circuit_status(self) -> Dict[str, Any]:
        """
        Get detailed circuit status
        
        Returns:
            dict: Circuit status details
        """
        try:
            circuit_info = await self.get_tor_circuit_info()
            if circuit_info:
                return {
                    "status": "active",
                    "circuit": circuit_info
                }
            return {"status": "unavailable"}
        except Exception as e:
            logger.error(f"Failed to get circuit status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def rotate_circuit(self) -> bool:
        """
        Request Tor to rotate the circuit (get new exit node)
        
        Returns:
            bool: True if rotation successful, False otherwise
        """
        try:
            if not self.session:
                logger.warning("Tor session not initialized")
                return False
            
            response = await self.session.post("/circuit/rotate", timeout=self.timeout)
            
            if response.status_code == 200:
                logger.info("Circuit rotated successfully")
                return True
            else:
                logger.warning(f"Failed to rotate circuit: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error rotating circuit: {e}")
            return False
    
    async def route_transaction_through_tor(
        self,
        transaction_hex: str,
        chain: str = "TRON"
    ) -> Dict[str, Any]:
        """
        Route transaction through Tor network
        
        Args:
            transaction_hex: Transaction hex data
            chain: Blockchain chain identifier
            
        Returns:
            dict: Routing result with tor routing metadata
        """
        try:
            if not self.session:
                logger.warning("Tor session not initialized")
                return {
                    "status": "error",
                    "error": "Tor integration not available"
                }
            
            payload = {
                "transaction": transaction_hex,
                "chain": chain,
                "anonymous": True
            }
            
            response = await self.session.post(
                "/transaction/route",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Transaction routed through Tor: {result.get('routing_id')}")
                return result
            else:
                logger.error(f"Failed to route transaction: {response.status_code}")
                return {
                    "status": "error",
                    "code": response.status_code
                }
                
        except Exception as e:
            logger.error(f"Error routing transaction through Tor: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_exit_node_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about current exit node
        
        Returns:
            dict: Exit node information, or None if unavailable
        """
        try:
            if not self.session:
                logger.warning("Tor session not initialized")
                return None
            
            response = await self.session.get("/circuit/exit-node", timeout=self.timeout)
            
            if response.status_code == 200:
                exit_info = response.json()
                logger.debug(f"Exit node info: {exit_info}")
                return exit_info
            else:
                logger.warning(f"Failed to get exit node info: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error retrieving exit node info: {e}")
        
        return None
    
    async def verify_anonymity(self) -> Dict[str, Any]:
        """
        Verify current anonymity status and Tor connectivity
        
        Returns:
            dict: Anonymity verification status
        """
        try:
            if not self.session:
                return {
                    "anonymity": "unavailable",
                    "tor_connected": False
                }
            
            # Check if Tor is connected
            health = await self.check_health()
            if health.get("status") != TorServiceStatus.OPERATIONAL.value:
                return {
                    "anonymity": "unavailable",
                    "tor_connected": False,
                    "error": health.get("error")
                }
            
            # Get exit node to confirm Tor routing
            exit_info = await self.get_exit_node_info()
            if exit_info:
                return {
                    "anonymity": "verified",
                    "tor_connected": True,
                    "exit_node": exit_info
                }
            
            return {
                "anonymity": "uncertain",
                "tor_connected": True
            }
            
        except Exception as e:
            logger.error(f"Error verifying anonymity: {e}")
            return {
                "anonymity": "error",
                "error": str(e)
            }
    
    async def cleanup(self):
        """Cleanup Tor integration and close connections"""
        try:
            if self.session:
                await self.session.aclose()
                logger.info("Tor integration cleaned up")
        except Exception as e:
            logger.error(f"Error during Tor integration cleanup: {e}")
        finally:
            self.initialized = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

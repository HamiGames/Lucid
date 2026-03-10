"""
Tor Proxy Client for GUI Tor Manager
Client for communicating with tor-proxy service using Tor control protocol
Uses stem library for Tor control protocol interactions
"""

import socket
import asyncio
from typing import Optional, List, Dict, Any
import json
import re

from stem.control import Controller
from stem.process import launch_tor

from .service_base import ServiceBaseClient
from ..utils.logging import get_logger
from ..utils.errors import TorProxyConnectionError, TorOperationError
from ..utils.validation import parse_host_port

logger = get_logger(__name__)


class TorProxyClient(ServiceBaseClient):
    """Client for tor-proxy service integration"""
    
    def __init__(self, tor_proxy_url: str, tor_control_port: int = 9051):
        """
        Initialize Tor proxy client
        
        Args:
            tor_proxy_url: Tor proxy service URL (e.g., http://tor-proxy:9051)
            tor_control_port: Tor control port (default: 9051)
        """
        super().__init__(base_url=tor_proxy_url)
        self.tor_control_port = tor_control_port
        self.tor_control_host = None
        self._controller: Optional[Controller] = None
        
        # Parse host from URL
        try:
            self.tor_control_host = self._parse_host_from_url(tor_proxy_url)
            logger.info(f"Parsed Tor proxy host: {self.tor_control_host}")
        except Exception as e:
            logger.warning(f"Failed to parse Tor proxy URL: {e}")
    
    @staticmethod
    def _parse_host_from_url(url: str) -> str:
        """
        Parse host from URL string
        
        Args:
            url: URL string (e.g., 'http://tor-proxy:9051' or 'tor-proxy:9051')
        
        Returns:
            Host name/IP address
        
        Raises:
            ValueError: If URL format is invalid
        """
        # Remove protocol if present
        if "://" in url:
            _, url_part = url.split("://", 1)
        else:
            url_part = url
        
        # Extract host (before port)
        if ":" in url_part:
            host, port_str = url_part.rsplit(":", 1)
            return host.strip()
        else:
            return url_part.strip()
    
    async def connect(self) -> None:
        """Connect to Tor control port"""
        try:
            logger.info(f"Connecting to Tor control port: {self.tor_control_host}:{self.tor_control_port}")
            
            # Run stem connection in executor (blocking operation)
            loop = asyncio.get_event_loop()
            self._controller = await loop.run_in_executor(
                None,
                self._create_controller
            )
            
            logger.info("Successfully connected to Tor control port")
        except Exception as e:
            logger.error(f"Failed to connect to Tor: {e}")
            raise TorProxyConnectionError(
                message=f"Failed to connect to Tor control port",
                details={"host": self.tor_control_host, "port": self.tor_control_port, "error": str(e)}
            )
    
    def _create_controller(self) -> Controller:
        """Create Tor controller (blocking)"""
        controller = Controller.from_port(
            address=self.tor_control_host,
            port=self.tor_control_port
        )
        controller.authenticate()
        return controller
    
    async def get_tor_status(self) -> Dict[str, Any]:
        """
        Get Tor proxy status
        
        Returns:
            Dictionary with Tor status information
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(
                None,
                self._get_status
            )
            return status
        except Exception as e:
            logger.error(f"Failed to get Tor status: {e}")
            raise TorOperationError(
                message="Failed to get Tor status",
                details={"error": str(e)}
            )
    
    def _get_status(self) -> Dict[str, Any]:
        """Get Tor status (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        return {
            "running": True,
            "version": str(self._controller.get_version()),
            "process_id": None,
            "config_file": None,
            "data_dir": None,
            "socks_listeners": [],
            "control_listeners": [],
        }
    
    async def get_circuits(self) -> List[Dict[str, Any]]:
        """
        Get list of active Tor circuits
        
        Returns:
            List of circuit information dictionaries
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            circuits = await loop.run_in_executor(
                None,
                self._get_circuits
            )
            return circuits
        except Exception as e:
            logger.error(f"Failed to get circuits: {e}")
            raise TorOperationError(
                message="Failed to get circuits",
                details={"error": str(e)}
            )
    
    def _get_circuits(self) -> List[Dict[str, Any]]:
        """Get circuits (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        circuits = []
        for circuit in self._controller.get_circuits():
            circuits.append({
                "circuit_id": circuit.id,
                "status": circuit.status,
                "purpose": circuit.purpose,
                "nodes": [{"nickname": node.nickname} for node in circuit.path],
            })
        return circuits
    
    async def add_onion_service(
        self,
        ports: List[int],
        targets: Optional[List[Dict[str, Any]]] = None,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new onion service
        
        Args:
            ports: List of ports to listen on
            targets: Port target mappings
            persistent: Whether to make service persistent
        
        Returns:
            Dictionary with onion service information
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._add_onion_service,
                ports,
                targets,
                persistent
            )
            return result
        except Exception as e:
            logger.error(f"Failed to add onion service: {e}")
            raise TorOperationError(
                message="Failed to add onion service",
                details={"error": str(e), "ports": ports}
            )
    
    def _add_onion_service(
        self,
        ports: List[int],
        targets: Optional[List[Dict[str, Any]]] = None,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """Add onion service (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        # Create port mappings
        port_mapping = {}
        for i, port in enumerate(ports):
            target = targets[i] if targets and i < len(targets) else {"port": port}
            target_port = target.get("port", port)
            port_mapping[port] = ("127.0.0.1", target_port)
        
        # Create onion service
        service = self._controller.create_ephemeral_hidden_service(
            port_mapping,
            await_publication=True
        )
        
        return {
            "service_id": service.service_id,
            "address": service.onion_host,
            "ports": ports,
            "persistent": persistent,
        }
    
    async def remove_onion_service(self, service_id: str) -> bool:
        """
        Remove an onion service
        
        Args:
            service_id: Service identifier to remove
        
        Returns:
            True if successful
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._remove_onion_service,
                service_id
            )
            return result
        except Exception as e:
            logger.error(f"Failed to remove onion service: {e}")
            raise TorOperationError(
                message="Failed to remove onion service",
                details={"error": str(e), "service_id": service_id}
            )
    
    def _remove_onion_service(self, service_id: str) -> bool:
        """Remove onion service (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        # Remove the onion service
        self._controller.remove_ephemeral_hidden_service(service_id)
        return True
    
    async def close(self) -> None:
        """Close Tor connection"""
        if self._controller:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._close_controller)
            except Exception as e:
                logger.warning(f"Error closing Tor controller: {e}")
            finally:
                self._controller = None
        
        await super().close()
    
    def _close_controller(self) -> None:
        """Close controller (blocking)"""
        if self._controller:
            self._controller.close()
    
    async def connect(self) -> None:
        """Connect to Tor control port"""
        try:
            logger.info(f"Connecting to Tor control port: {self.tor_control_host}:{self.tor_control_port}")
            
            # Run stem connection in executor (blocking operation)
            loop = asyncio.get_event_loop()
            self._controller = await loop.run_in_executor(
                None,
                self._create_controller
            )
            
            logger.info("Successfully connected to Tor control port")
        except Exception as e:
            logger.error(f"Failed to connect to Tor: {e}")
            raise TorProxyConnectionError(
                message=f"Failed to connect to Tor control port",
                details={"host": self.tor_control_host, "port": self.tor_control_port, "error": str(e)}
            )
    
    def _create_controller(self) -> Controller:
        """Create Tor controller (blocking)"""
        controller = Controller.from_port(
            address=self.tor_control_host,
            port=self.tor_control_port
        )
        controller.authenticate()
        return controller
    
    async def get_tor_status(self) -> Dict[str, Any]:
        """
        Get Tor proxy status
        
        Returns:
            Dictionary with Tor status information
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(
                None,
                self._get_status
            )
            return status
        except Exception as e:
            logger.error(f"Failed to get Tor status: {e}")
            raise TorOperationError(
                message="Failed to get Tor status",
                details={"error": str(e)}
            )
    
    def _get_status(self) -> Dict[str, Any]:
        """Get Tor status (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        return {
            "running": True,
            "version": str(self._controller.get_version()),
            "process_id": None,
            "config_file": None,
            "data_dir": None,
            "socks_listeners": [],
            "control_listeners": [],
        }
    
    async def get_circuits(self) -> List[Dict[str, Any]]:
        """
        Get list of active Tor circuits
        
        Returns:
            List of circuit information dictionaries
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            circuits = await loop.run_in_executor(
                None,
                self._get_circuits
            )
            return circuits
        except Exception as e:
            logger.error(f"Failed to get circuits: {e}")
            raise TorOperationError(
                message="Failed to get circuits",
                details={"error": str(e)}
            )
    
    def _get_circuits(self) -> List[Dict[str, Any]]:
        """Get circuits (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        circuits = []
        for circuit in self._controller.get_circuits():
            circuits.append({
                "circuit_id": circuit.id,
                "status": circuit.status,
                "purpose": circuit.purpose,
                "nodes": [{"nickname": node.nickname} for node in circuit.path],
            })
        return circuits
    
    async def add_onion_service(
        self,
        ports: List[int],
        targets: Optional[List[Dict[str, Any]]] = None,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new onion service
        
        Args:
            ports: List of ports to listen on
            targets: Port target mappings
            persistent: Whether to make service persistent
        
        Returns:
            Dictionary with onion service information
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._add_onion_service,
                ports,
                targets,
                persistent
            )
            return result
        except Exception as e:
            logger.error(f"Failed to add onion service: {e}")
            raise TorOperationError(
                message="Failed to add onion service",
                details={"error": str(e), "ports": ports}
            )
    
    def _add_onion_service(
        self,
        ports: List[int],
        targets: Optional[List[Dict[str, Any]]] = None,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """Add onion service (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        # Create port mappings
        port_mapping = {}
        for i, port in enumerate(ports):
            target = targets[i] if targets and i < len(targets) else {"port": port}
            target_port = target.get("port", port)
            port_mapping[port] = ("127.0.0.1", target_port)
        
        # Create onion service
        service = self._controller.create_ephemeral_hidden_service(
            port_mapping,
            await_publication=True
        )
        
        return {
            "service_id": service.service_id,
            "address": service.onion_host,
            "ports": ports,
            "persistent": persistent,
        }
    
    async def remove_onion_service(self, service_id: str) -> bool:
        """
        Remove an onion service
        
        Args:
            service_id: Service identifier to remove
        
        Returns:
            True if successful
        """
        try:
            if not self._controller:
                await self.connect()
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._remove_onion_service,
                service_id
            )
            return result
        except Exception as e:
            logger.error(f"Failed to remove onion service: {e}")
            raise TorOperationError(
                message="Failed to remove onion service",
                details={"error": str(e), "service_id": service_id}
            )
    
    def _remove_onion_service(self, service_id: str) -> bool:
        """Remove onion service (blocking)"""
        if not self._controller:
            raise RuntimeError("Not connected to Tor control port")
        
        # Remove the onion service
        self._controller.remove_ephemeral_hidden_service(service_id)
        return True
    
    async def close(self) -> None:
        """Close Tor connection"""
        if self._controller:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._close_controller)
            except Exception as e:
                logger.warning(f"Error closing Tor controller: {e}")
            finally:
                self._controller = None
        
        await super().close()
    
    def _close_controller(self) -> None:
        """Close controller (blocking)"""
        if self._controller:
            self._controller.close()

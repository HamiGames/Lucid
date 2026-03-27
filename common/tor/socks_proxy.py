"""
SOCKS proxy management for Lucid RDP.

This module provides comprehensive SOCKS proxy management, connection pooling,
routing, and integration with the LUCID-STRICT security model.
"""

import asyncio
import logging
import socket
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union, Set
import aiofiles
import aiohttp
import socks

from ..security.trust_nothing_engine import (
    TrustNothingEngine, SecurityContext, SecurityAssessment,
    TrustLevel, RiskLevel, ActionType, PolicyLevel
)


class SocksVersion(Enum):
    """SOCKS protocol versions"""
    SOCKS4 = 4
    SOCKS4A = 4
    SOCKS5 = 5


class SocksCommand(Enum):
    """SOCKS commands"""
    CONNECT = 1
    BIND = 2
    UDP_ASSOCIATE = 3


class SocksAuthMethod(Enum):
    """SOCKS authentication methods"""
    NO_AUTH = 0
    GSSAPI = 1
    USERNAME_PASSWORD = 2
    NO_ACCEPTABLE = 255


class ConnectionStatus(Enum):
    """Connection status states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class ProxyType(Enum):
    """Types of proxy connections"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    TOR = "tor"


@dataclass
class ProxyConfig:
    """SOCKS proxy configuration"""
    config_id: str
    proxy_type: ProxyType
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    max_connections: int = 100
    keep_alive: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0
    dns_resolution: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxyConnection:
    """SOCKS proxy connection information"""
    connection_id: str
    config: ProxyConfig
    status: ConnectionStatus
    local_address: Optional[Tuple[str, int]] = None
    remote_address: Optional[Tuple[str, int]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bytes_sent: int = 0
    bytes_received: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxyRequest:
    """SOCKS proxy request"""
    request_id: str
    target_host: str
    target_port: int
    proxy_config: ProxyConfig
    timeout: int = 30
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxyResponse:
    """SOCKS proxy response"""
    response_id: str
    request: ProxyRequest
    success: bool
    connection: Optional[ProxyConnection] = None
    error_message: Optional[str] = None
    response_time: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxyPool:
    """SOCKS proxy connection pool"""
    pool_id: str
    config: ProxyConfig
    max_connections: int
    active_connections: Set[str] = field(default_factory=set)
    available_connections: List[ProxyConnection] = field(default_factory=list)
    connection_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_cleanup: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SocksProxy:
    """
    Comprehensive SOCKS proxy management for Lucid RDP.
    
    Provides connection pooling, routing, monitoring, and integration
    with the LUCID-STRICT security model.
    """
    
    def __init__(self, trust_engine: Optional[TrustNothingEngine] = None):
        self.trust_engine = trust_engine or TrustNothingEngine()
        self.logger = logging.getLogger(__name__)
        
        # Proxy state
        self.proxy_configs: Dict[str, ProxyConfig] = {}
        self.proxy_connections: Dict[str, ProxyConnection] = {}
        self.proxy_pools: Dict[str, ProxyPool] = {}
        self.active_requests: Dict[str, ProxyRequest] = {}
        
        # Connection management
        self.connection_cleanup_task: Optional[asyncio.Task] = None
        self.cleanup_interval = 60  # seconds
        self.max_idle_time = 300  # seconds
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "active_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
        
        # Security integration
        self.security_context_cache: Dict[str, SecurityContext] = {}
        self.rate_limits: Dict[str, Tuple[datetime, int]] = {}
        self.blocked_hosts: Set[str] = set()
        self.allowed_hosts: Set[str] = set()
        
        self.logger.info("SocksProxy initialized")
    
    async def initialize(self, auto_cleanup: bool = True) -> bool:
        """Initialize SOCKS proxy manager"""
        try:
            # Create default Tor proxy configuration
            tor_config = ProxyConfig(
                config_id="tor_default",
                proxy_type=ProxyType.TOR,
                host="127.0.0.1",
                port=9050,
                timeout=30,
                max_connections=50,
                keep_alive=True
            )
            
            await self.add_proxy_config(tor_config)
            
            # Start cleanup task
            if auto_cleanup:
                self.connection_cleanup_task = asyncio.create_task(self._cleanup_connections())
            
            self.logger.info("SocksProxy initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SocksProxy: {e}")
            return False
    
    async def add_proxy_config(self, config: ProxyConfig) -> bool:
        """Add a proxy configuration"""
        try:
            # Security assessment
            context = SecurityContext(
                request_id=f"proxy_add_{config.config_id}_{int(time.time())}",
                service_name="socks_proxy",
                component_name="config_management",
                operation="add_proxy_config",
                resource_path=f"/proxy/config/{config.config_id}"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.MEDIUM)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Store configuration
            self.proxy_configs[config.config_id] = config
            
            # Create connection pool
            pool = ProxyPool(
                pool_id=f"pool_{config.config_id}",
                config=config,
                max_connections=config.max_connections
            )
            self.proxy_pools[config.config_id] = pool
            
            self.logger.info(f"Added proxy configuration: {config.config_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add proxy config {config.config_id}: {e}")
            return False
    
    async def remove_proxy_config(self, config_id: str) -> bool:
        """Remove a proxy configuration"""
        try:
            if config_id not in self.proxy_configs:
                self.logger.error(f"Proxy config {config_id} not found")
                return False
            
            # Security assessment
            context = SecurityContext(
                request_id=f"proxy_remove_{config_id}_{int(time.time())}",
                service_name="socks_proxy",
                component_name="config_management",
                operation="remove_proxy_config",
                resource_path=f"/proxy/config/{config_id}"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.MEDIUM)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Close all connections for this proxy
            await self._close_proxy_connections(config_id)
            
            # Remove configuration and pool
            del self.proxy_configs[config_id]
            if config_id in self.proxy_pools:
                del self.proxy_pools[config_id]
            
            self.logger.info(f"Removed proxy configuration: {config_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove proxy config {config_id}: {e}")
            return False
    
    async def create_connection(
        self,
        target_host: str,
        target_port: int,
        proxy_config_id: str = "tor_default",
        timeout: int = 30,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ProxyResponse:
        """Create a SOCKS proxy connection"""
        start_time = time.time()
        request_id = f"req_{int(time.time())}_{target_host}_{target_port}"
        
        try:
            # Security assessment
            context = SecurityContext(
                request_id=request_id,
                service_name="socks_proxy",
                component_name="connection_management",
                operation="create_connection",
                resource_path=f"/proxy/connect/{target_host}:{target_port}"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.MEDIUM)
            if assessment.recommended_action != ActionType.ALLOW:
                error_msg = f"Security assessment failed: {assessment.recommended_action}"
                self.logger.error(error_msg)
                return ProxyResponse(
                    response_id=f"resp_{request_id}",
                    request=ProxyRequest(
                        request_id=request_id,
                        target_host=target_host,
                        target_port=target_port,
                        proxy_config=self.proxy_configs.get(proxy_config_id),
                        timeout=timeout,
                        user_id=user_id,
                        session_id=session_id
                    ),
                    success=False,
                    error_message=error_msg,
                    response_time=time.time() - start_time
                )
            
            # Check if proxy config exists
            if proxy_config_id not in self.proxy_configs:
                error_msg = f"Proxy config {proxy_config_id} not found"
                return ProxyResponse(
                    response_id=f"resp_{request_id}",
                    request=ProxyRequest(
                        request_id=request_id,
                        target_host=target_host,
                        target_port=target_port,
                        proxy_config=None,
                        timeout=timeout,
                        user_id=user_id,
                        session_id=session_id
                    ),
                    success=False,
                    error_message=error_msg,
                    response_time=time.time() - start_time
                )
            
            # Check host restrictions
            if not await self._is_host_allowed(target_host):
                error_msg = f"Host {target_host} is not allowed"
                return ProxyResponse(
                    response_id=f"resp_{request_id}",
                    request=ProxyRequest(
                        request_id=request_id,
                        target_host=target_host,
                        target_port=target_port,
                        proxy_config=self.proxy_configs[proxy_config_id],
                        timeout=timeout,
                        user_id=user_id,
                        session_id=session_id
                    ),
                    success=False,
                    error_message=error_msg,
                    response_time=time.time() - start_time
                )
            
            # Create request
            request = ProxyRequest(
                request_id=request_id,
                target_host=target_host,
                target_port=target_port,
                proxy_config=self.proxy_configs[proxy_config_id],
                timeout=timeout,
                user_id=user_id,
                session_id=session_id
            )
            
            self.active_requests[request_id] = request
            self.stats["total_requests"] += 1
            
            # Try to get connection from pool
            connection = await self._get_connection_from_pool(proxy_config_id)
            
            if connection:
                # Use existing connection
                self.stats["pool_hits"] += 1
                connection.last_activity = datetime.now(timezone.utc)
            else:
                # Create new connection
                self.stats["pool_misses"] += 1
                connection = await self._create_new_connection(request)
            
            response_time = time.time() - start_time
            
            if connection and connection.status == ConnectionStatus.CONNECTED:
                self.stats["successful_requests"] += 1
                self.stats["active_connections"] += 1
                
                response = ProxyResponse(
                    response_id=f"resp_{request_id}",
                    request=request,
                    success=True,
                    connection=connection,
                    response_time=response_time
                )
            else:
                self.stats["failed_requests"] += 1
                error_msg = connection.error_message if connection else "Failed to create connection"
                
                response = ProxyResponse(
                    response_id=f"resp_{request_id}",
                    request=request,
                    success=False,
                    error_message=error_msg,
                    response_time=response_time
                )
            
            # Clean up request
            if request_id in self.active_requests:
                del self.active_requests[request_id]
            
            return response
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            error_msg = f"Connection creation failed: {e}"
            self.logger.error(error_msg)
            
            return ProxyResponse(
                response_id=f"resp_{request_id}",
                request=ProxyRequest(
                    request_id=request_id,
                    target_host=target_host,
                    target_port=target_port,
                    proxy_config=self.proxy_configs.get(proxy_config_id),
                    timeout=timeout,
                    user_id=user_id,
                    session_id=session_id
                ),
                success=False,
                error_message=error_msg,
                response_time=time.time() - start_time
            )
    
    async def close_connection(self, connection_id: str) -> bool:
        """Close a proxy connection"""
        try:
            if connection_id not in self.proxy_connections:
                self.logger.warning(f"Connection {connection_id} not found")
                return False
            
            connection = self.proxy_connections[connection_id]
            
            # Update statistics
            self.stats["total_bytes_sent"] += connection.bytes_sent
            self.stats["total_bytes_received"] += connection.bytes_received
            self.stats["active_connections"] = max(0, self.stats["active_connections"] - 1)
            
            # Remove from pool if it exists
            config_id = connection.config.config_id
            if config_id in self.proxy_pools:
                pool = self.proxy_pools[config_id]
                if connection_id in pool.active_connections:
                    pool.active_connections.remove(connection_id)
                
                # Remove from available connections
                pool.available_connections = [
                    conn for conn in pool.available_connections
                    if conn.connection_id != connection_id
                ]
            
            # Remove connection
            del self.proxy_connections[connection_id]
            
            self.logger.info(f"Closed connection {connection_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to close connection {connection_id}: {e}")
            return False
    
    async def get_connection_info(self, connection_id: str) -> Optional[ProxyConnection]:
        """Get information about a proxy connection"""
        return self.proxy_connections.get(connection_id)
    
    async def list_connections(self, proxy_config_id: Optional[str] = None) -> List[ProxyConnection]:
        """List proxy connections"""
        if proxy_config_id:
            return [
                conn for conn in self.proxy_connections.values()
                if conn.config.config_id == proxy_config_id
            ]
        return list(self.proxy_connections.values())
    
    async def get_proxy_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        return {
            **self.stats,
            "proxy_configs": len(self.proxy_configs),
            "proxy_pools": len(self.proxy_pools),
            "active_requests": len(self.active_requests),
            "blocked_hosts": len(self.blocked_hosts),
            "allowed_hosts": len(self.allowed_hosts)
        }
    
    async def add_blocked_host(self, host: str) -> bool:
        """Add a host to the blocked list"""
        self.blocked_hosts.add(host)
        self.logger.info(f"Added blocked host: {host}")
        return True
    
    async def remove_blocked_host(self, host: str) -> bool:
        """Remove a host from the blocked list"""
        self.blocked_hosts.discard(host)
        self.logger.info(f"Removed blocked host: {host}")
        return True
    
    async def add_allowed_host(self, host: str) -> bool:
        """Add a host to the allowed list"""
        self.allowed_hosts.add(host)
        self.logger.info(f"Added allowed host: {host}")
        return True
    
    async def remove_allowed_host(self, host: str) -> bool:
        """Remove a host from the allowed list"""
        self.allowed_hosts.discard(host)
        self.logger.info(f"Removed allowed host: {host}")
        return True
    
    async def _get_connection_from_pool(self, proxy_config_id: str) -> Optional[ProxyConnection]:
        """Get a connection from the pool"""
        try:
            if proxy_config_id not in self.proxy_pools:
                return None
            
            pool = self.proxy_pools[proxy_config_id]
            
            # Check for available connections
            while pool.available_connections:
                connection = pool.available_connections.pop(0)
                
                # Check if connection is still valid
                if await self._is_connection_valid(connection):
                    pool.active_connections.add(connection.connection_id)
                    return connection
                else:
                    # Remove invalid connection
                    if connection.connection_id in self.proxy_connections:
                        del self.proxy_connections[connection.connection_id]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get connection from pool: {e}")
            return None
    
    async def _create_new_connection(self, request: ProxyRequest) -> Optional[ProxyConnection]:
        """Create a new proxy connection"""
        try:
            connection_id = f"conn_{int(time.time())}_{secrets.token_hex(4)}"
            config = request.proxy_config
            
            # Create connection object
            connection = ProxyConnection(
                connection_id=connection_id,
                config=config,
                status=ConnectionStatus.CONNECTING
            )
            
            # Store connection
            self.proxy_connections[connection_id] = connection
            
            # Create actual connection based on proxy type
            if config.proxy_type == ProxyType.TOR:
                success = await self._create_tor_connection(connection, request)
            elif config.proxy_type == ProxyType.SOCKS5:
                success = await self._create_socks5_connection(connection, request)
            elif config.proxy_type == ProxyType.SOCKS4:
                success = await self._create_socks4_connection(connection, request)
            elif config.proxy_type in [ProxyType.HTTP, ProxyType.HTTPS]:
                success = await self._create_http_connection(connection, request)
            else:
                connection.status = ConnectionStatus.ERROR
                connection.error_message = f"Unsupported proxy type: {config.proxy_type}"
                success = False
            
            if success:
                connection.status = ConnectionStatus.CONNECTED
                connection.last_activity = datetime.now(timezone.utc)
                
                # Add to pool
                if config.config_id in self.proxy_pools:
                    pool = self.proxy_pools[config.config_id]
                    if len(pool.active_connections) < pool.max_connections:
                        pool.active_connections.add(connection_id)
                        pool.available_connections.append(connection)
            else:
                connection.status = ConnectionStatus.ERROR
            
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to create new connection: {e}")
            return None
    
    async def _create_tor_connection(self, connection: ProxyConnection, request: ProxyRequest) -> bool:
        """Create a Tor connection"""
        try:
            # For Tor, we'll use aiohttp with proxy
            proxy_url = f"socks5://{connection.config.host}:{connection.config.port}"
            
            # Create aiohttp session with Tor proxy
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=request.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                # Test connection
                test_url = f"http://{request.target_host}:{request.target_port}"
                async with session.get(test_url, proxy=proxy_url) as response:
                    if response.status < 400:
                        connection.remote_address = (request.target_host, request.target_port)
                        return True
                    else:
                        connection.error_message = f"HTTP error: {response.status}"
                        return False
            
        except Exception as e:
            connection.error_message = f"Tor connection failed: {e}"
            return False
    
    async def _create_socks5_connection(self, connection: ProxyConnection, request: ProxyRequest) -> bool:
        """Create a SOCKS5 connection"""
        try:
            # Create SOCKS5 socket
            sock = socks.socksocket()
            sock.set_proxy(
                socks.SOCKS5,
                connection.config.host,
                connection.config.port,
                username=connection.config.username,
                password=connection.config.password
            )
            
            # Connect to target
            sock.settimeout(request.timeout)
            sock.connect((request.target_host, request.target_port))
            
            connection.remote_address = (request.target_host, request.target_port)
            connection.local_address = sock.getsockname()
            
            return True
            
        except Exception as e:
            connection.error_message = f"SOCKS5 connection failed: {e}"
            return False
    
    async def _create_socks4_connection(self, connection: ProxyConnection, request: ProxyRequest) -> bool:
        """Create a SOCKS4 connection"""
        try:
            # Create SOCKS4 socket
            sock = socks.socksocket()
            sock.set_proxy(
                socks.SOCKS4,
                connection.config.host,
                connection.config.port
            )
            
            # Connect to target
            sock.settimeout(request.timeout)
            sock.connect((request.target_host, request.target_port))
            
            connection.remote_address = (request.target_host, request.target_port)
            connection.local_address = sock.getsockname()
            
            return True
            
        except Exception as e:
            connection.error_message = f"SOCKS4 connection failed: {e}"
            return False
    
    async def _create_http_connection(self, connection: ProxyConnection, request: ProxyRequest) -> bool:
        """Create an HTTP proxy connection"""
        try:
            # Create HTTP proxy URL
            if connection.config.username and connection.config.password:
                auth = f"{connection.config.username}:{connection.config.password}@"
            else:
                auth = ""
            
            proxy_url = f"http://{auth}{connection.config.host}:{connection.config.port}"
            
            # Create aiohttp session with HTTP proxy
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=request.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                # Test connection
                test_url = f"http://{request.target_host}:{request.target_port}"
                async with session.get(test_url, proxy=proxy_url) as response:
                    if response.status < 400:
                        connection.remote_address = (request.target_host, request.target_port)
                        return True
                    else:
                        connection.error_message = f"HTTP error: {response.status}"
                        return False
            
        except Exception as e:
            connection.error_message = f"HTTP proxy connection failed: {e}"
            return False
    
    async def _is_connection_valid(self, connection: ProxyConnection) -> bool:
        """Check if a connection is still valid"""
        try:
            # Check if connection is too old
            if connection.last_activity:
                age = (datetime.now(timezone.utc) - connection.last_activity).total_seconds()
                if age > self.max_idle_time:
                    return False
            
            # Check connection status
            if connection.status != ConnectionStatus.CONNECTED:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking connection validity: {e}")
            return False
    
    async def _is_host_allowed(self, host: str) -> bool:
        """Check if a host is allowed"""
        # Check blocked hosts first
        if self.blocked_hosts and host in self.blocked_hosts:
            return False
        
        # Check allowed hosts
        if self.allowed_hosts and host not in self.allowed_hosts:
            return False
        
        return True
    
    async def _close_proxy_connections(self, proxy_config_id: str) -> None:
        """Close all connections for a proxy configuration"""
        try:
            connections_to_close = [
                conn_id for conn_id, conn in self.proxy_connections.items()
                if conn.config.config_id == proxy_config_id
            ]
            
            for conn_id in connections_to_close:
                await self.close_connection(conn_id)
                
        except Exception as e:
            self.logger.error(f"Error closing proxy connections: {e}")
    
    async def _cleanup_connections(self) -> None:
        """Clean up idle and invalid connections"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                connections_to_remove = []
                
                for conn_id, connection in self.proxy_connections.items():
                    # Check for idle connections
                    if connection.last_activity:
                        idle_time = (current_time - connection.last_activity).total_seconds()
                        if idle_time > self.max_idle_time:
                            connections_to_remove.append(conn_id)
                            continue
                    
                    # Check for error connections
                    if connection.status == ConnectionStatus.ERROR:
                        connections_to_remove.append(conn_id)
                        continue
                
                # Remove invalid connections
                for conn_id in connections_to_remove:
                    await self.close_connection(conn_id)
                
                # Update pool cleanup time
                for pool in self.proxy_pools.values():
                    pool.last_cleanup = current_time
                
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in connection cleanup: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def shutdown(self) -> None:
        """Shutdown SOCKS proxy manager"""
        try:
            # Cancel cleanup task
            if self.connection_cleanup_task:
                self.connection_cleanup_task.cancel()
                try:
                    await self.connection_cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close all connections
            for conn_id in list(self.proxy_connections.keys()):
                await self.close_connection(conn_id)
            
            # Clear all data
            self.proxy_configs.clear()
            self.proxy_connections.clear()
            self.proxy_pools.clear()
            self.active_requests.clear()
            
            self.logger.info("SocksProxy shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Global instance management
_socks_proxy_instance: Optional[SocksProxy] = None


def get_socks_proxy() -> Optional[SocksProxy]:
    """Get the global SocksProxy instance"""
    return _socks_proxy_instance


def create_socks_proxy(trust_engine: Optional[TrustNothingEngine] = None) -> SocksProxy:
    """Create a new SocksProxy instance"""
    global _socks_proxy_instance
    _socks_proxy_instance = SocksProxy(trust_engine)
    return _socks_proxy_instance


async def main():
    """Example usage of SocksProxy"""
    # Create SOCKS proxy manager
    socks_proxy = create_socks_proxy()
    
    # Initialize
    await socks_proxy.initialize()
    
    # Create a connection through Tor
    response = await socks_proxy.create_connection(
        target_host="example.com",
        target_port=80,
        proxy_config_id="tor_default",
        timeout=30
    )
    
    if response.success:
        print(f"Connection created: {response.connection.connection_id}")
        print(f"Response time: {response.response_time:.2f}s")
        
        # Get connection info
        conn_info = await socks_proxy.get_connection_info(response.connection.connection_id)
        print(f"Connection status: {conn_info.status}")
        
        # Close connection
        await socks_proxy.close_connection(response.connection.connection_id)
    else:
        print(f"Connection failed: {response.error_message}")
    
    # Get statistics
    stats = await socks_proxy.get_proxy_stats()
    print(f"Proxy stats: {stats}")
    
    # Shutdown
    await socks_proxy.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

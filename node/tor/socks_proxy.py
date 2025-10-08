"""
LUCID Node Tor - SOCKS Proxy Management
Handles SOCKS proxy connections, tunneling, and network routing
Distroless container: pickme/lucid:node-worker:latest
"""

import asyncio
import json
import logging
import os
import socket
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import aiohttp
import socks
import struct

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SocksVersion(str, Enum):
    """SOCKS protocol versions"""
    SOCKS4 = "socks4"
    SOCKS4A = "socks4a"
    SOCKS5 = "socks5"

class SocksAuthMethod(str, Enum):
    """SOCKS authentication methods"""
    NO_AUTH = "no_auth"
    USERNAME_PASSWORD = "username_password"
    GSSAPI = "gssapi"

class ProxyStatus(str, Enum):
    """Proxy connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"

class TunnelProtocol(str, Enum):
    """Tunnel protocol types"""
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"

@dataclass
class SocksProxyConfig:
    """SOCKS proxy configuration"""
    proxy_host: str
    proxy_port: int
    version: SocksVersion
    username: Optional[str] = None
    password: Optional[str] = None
    auth_method: SocksAuthMethod = SocksAuthMethod.NO_AUTH
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

@dataclass
class ProxyConnection:
    """SOCKS proxy connection information"""
    connection_id: str
    config: SocksProxyConfig
    status: ProxyStatus
    created_at: datetime
    last_used: Optional[datetime] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    connection_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None

@dataclass
class TunnelConfig:
    """Tunnel configuration"""
    tunnel_id: str
    local_host: str
    local_port: int
    remote_host: str
    remote_port: int
    protocol: TunnelProtocol
    proxy_connection_id: str
    created_at: datetime
    status: str = "active"
    bytes_tunneled: int = 0

class SocksProxyRequest(BaseModel):
    """Request model for creating SOCKS proxy connections"""
    proxy_host: str = Field(..., description="Proxy host address")
    proxy_port: int = Field(..., description="Proxy port")
    version: SocksVersion = Field(default=SocksVersion.SOCKS5, description="SOCKS version")
    username: Optional[str] = Field(default=None, description="Username for authentication")
    password: Optional[str] = Field(default=None, description="Password for authentication")
    timeout: int = Field(default=30, description="Connection timeout in seconds")

class TunnelRequest(BaseModel):
    """Request model for creating tunnels"""
    local_host: str = Field(default="127.0.0.1", description="Local bind host")
    local_port: int = Field(..., description="Local bind port")
    remote_host: str = Field(..., description="Remote target host")
    remote_port: int = Field(..., description="Remote target port")
    protocol: TunnelProtocol = Field(default=TunnelProtocol.TCP, description="Tunnel protocol")
    proxy_connection_id: str = Field(..., description="Proxy connection to use")

class SocksProxyManager:
    """Manages SOCKS proxy connections and tunneling"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.connections_dir = data_dir / "socks_connections"
        self.tunnels_dir = data_dir / "tunnels"
        self.logs_dir = data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.connections_dir, self.tunnels_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Connection and tunnel management
        self.proxy_connections: Dict[str, ProxyConnection] = {}
        self.active_tunnels: Dict[str, TunnelConfig] = {}
        
        # Load existing connections
        asyncio.create_task(self._load_existing_connections())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_connections())
        asyncio.create_task(self._monitor_tunnels())
    
    async def _load_existing_connections(self):
        """Load existing proxy connections from disk"""
        try:
            connections_file = self.connections_dir / "connections_registry.json"
            if connections_file.exists():
                async with aiofiles.open(connections_file, "r") as f:
                    data = await f.read()
                    connections_data = json.loads(data)
                    
                    for connection_id, connection_data in connections_data.items():
                        # Convert datetime strings back to datetime objects
                        if 'created_at' in connection_data:
                            connection_data['created_at'] = datetime.fromisoformat(connection_data['created_at'])
                        if 'last_used' in connection_data and connection_data['last_used']:
                            connection_data['last_used'] = datetime.fromisoformat(connection_data['last_used'])
                        
                        connection = ProxyConnection(**connection_data)
                        self.proxy_connections[connection_id] = connection
                    
                logger.info(f"Loaded {len(self.proxy_connections)} existing proxy connections")
                
        except Exception as e:
            logger.error(f"Error loading existing connections: {e}")
    
    async def _save_connections_registry(self):
        """Save connections registry to disk"""
        try:
            connections_data = {}
            for connection_id, connection in self.proxy_connections.items():
                # Convert to dict and handle datetime serialization
                connection_dict = asdict(connection)
                if connection_dict['created_at']:
                    connection_dict['created_at'] = connection_dict['created_at'].isoformat()
                if connection_dict['last_used']:
                    connection_dict['last_used'] = connection_dict['last_used'].isoformat()
                connections_data[connection_id] = connection_dict
            
            connections_file = self.connections_dir / "connections_registry.json"
            async with aiofiles.open(connections_file, "w") as f:
                await f.write(json.dumps(connections_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving connections registry: {e}")
    
    async def create_proxy_connection(self, request: SocksProxyRequest) -> str:
        """Create a new SOCKS proxy connection"""
        try:
            logger.info(f"Creating SOCKS proxy connection: {request.proxy_host}:{request.proxy_port}")
            
            # Generate connection ID
            connection_id = await self._generate_connection_id(request)
            
            # Create proxy configuration
            config = SocksProxyConfig(
                proxy_host=request.proxy_host,
                proxy_port=request.proxy_port,
                version=request.version,
                username=request.username,
                password=request.password,
                auth_method=SocksAuthMethod.USERNAME_PASSWORD if request.username else SocksAuthMethod.NO_AUTH,
                timeout=request.timeout
            )
            
            # Test connection
            if await self._test_proxy_connection(config):
                status = ProxyStatus.CONNECTED
            else:
                status = ProxyStatus.ERROR
            
            # Create connection info
            connection = ProxyConnection(
                connection_id=connection_id,
                config=config,
                status=status,
                created_at=datetime.now()
            )
            
            # Store connection
            self.proxy_connections[connection_id] = connection
            
            # Save registry
            await self._save_connections_registry()
            
            # Log connection creation
            await self._log_socks_event(connection_id, "proxy_connection_created", {
                "proxy_host": request.proxy_host,
                "proxy_port": request.proxy_port,
                "version": request.version.value,
                "status": status.value
            })
            
            logger.info(f"Created SOCKS proxy connection: {connection_id} -> {status.value}")
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Error creating proxy connection: {e}")
            raise
    
    async def _generate_connection_id(self, request: SocksProxyRequest) -> str:
        """Generate unique connection ID"""
        timestamp = int(time.time())
        host_hash = hashlib.sha256(f"{request.proxy_host}:{request.proxy_port}".encode()).hexdigest()[:8]
        version_hash = hashlib.sha256(request.version.value.encode()).hexdigest()[:4]
        
        return f"socks_{timestamp}_{host_hash}_{version_hash}"
    
    async def _test_proxy_connection(self, config: SocksProxyConfig) -> bool:
        """Test SOCKS proxy connection"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(config.timeout)
            
            # Connect to proxy
            sock.connect((config.proxy_host, config.proxy_port))
            
            # Test SOCKS handshake
            if config.version == SocksVersion.SOCKS5:
                success = await self._test_socks5_handshake(sock, config)
            elif config.version == SocksVersion.SOCKS4:
                success = await self._test_socks4_handshake(sock, config)
            else:
                success = False
            
            sock.close()
            return success
            
        except Exception as e:
            logger.debug(f"Proxy connection test failed: {e}")
            return False
    
    async def _test_socks5_handshake(self, sock: socket.socket, config: SocksProxyConfig) -> bool:
        """Test SOCKS5 handshake"""
        try:
            # Send greeting
            if config.auth_method == SocksAuthMethod.NO_AUTH:
                greeting = b'\x05\x01\x00'  # SOCKS5, 1 auth method, no auth
            else:
                greeting = b'\x05\x02\x00\x02'  # SOCKS5, 2 auth methods, no auth + username/password
            
            sock.send(greeting)
            
            # Receive server response
            response = sock.recv(2)
            if len(response) != 2 or response[0] != 0x05:
                return False
            
            # Check selected auth method
            if response[1] == 0x00:  # No auth
                return True
            elif response[1] == 0x02:  # Username/password
                if not config.username or not config.password:
                    return False
                
                # Send username/password
                username_bytes = config.username.encode('utf-8')
                password_bytes = config.password.encode('utf-8')
                
                auth_request = struct.pack('BB', 0x01, len(username_bytes))
                auth_request += username_bytes
                auth_request += struct.pack('B', len(password_bytes))
                auth_request += password_bytes
                
                sock.send(auth_request)
                
                # Receive auth response
                auth_response = sock.recv(2)
                return len(auth_response) == 2 and auth_response[1] == 0x00
            
            return False
            
        except Exception as e:
            logger.debug(f"SOCKS5 handshake failed: {e}")
            return False
    
    async def _test_socks4_handshake(self, sock: socket.socket, config: SocksProxyConfig) -> bool:
        """Test SOCKS4 handshake"""
        try:
            # SOCKS4 connect request to test server
            request = struct.pack('>BBH', 0x04, 0x01, 80)  # SOCKS4, CONNECT, port 80
            request += socket.inet_aton('127.0.0.1')  # IP address
            request += b'\x00'  # Null terminator for user ID
            
            sock.send(request)
            
            # Receive response
            response = sock.recv(8)
            if len(response) < 2:
                return False
            
            return response[1] == 0x5A  # Request granted
            
        except Exception as e:
            logger.debug(f"SOCKS4 handshake failed: {e}")
            return False
    
    async def create_tunnel(self, request: TunnelRequest) -> str:
        """Create a new tunnel through SOCKS proxy"""
        try:
            if request.proxy_connection_id not in self.proxy_connections:
                raise ValueError(f"Proxy connection not found: {request.proxy_connection_id}")
            
            proxy_connection = self.proxy_connections[request.proxy_connection_id]
            if proxy_connection.status != ProxyStatus.CONNECTED:
                raise RuntimeError(f"Proxy connection not active: {request.proxy_connection_id}")
            
            logger.info(f"Creating tunnel: {request.local_host}:{request.local_port} -> {request.remote_host}:{request.remote_port}")
            
            # Generate tunnel ID
            tunnel_id = await self._generate_tunnel_id(request)
            
            # Create tunnel configuration
            tunnel_config = TunnelConfig(
                tunnel_id=tunnel_id,
                local_host=request.local_host,
                local_port=request.local_port,
                remote_host=request.remote_host,
                remote_port=request.remote_port,
                protocol=request.protocol,
                proxy_connection_id=request.proxy_connection_id,
                created_at=datetime.now()
            )
            
            # Start tunnel
            tunnel_task = asyncio.create_task(self._run_tunnel(tunnel_config))
            
            # Store tunnel
            self.active_tunnels[tunnel_id] = tunnel_config
            
            # Log tunnel creation
            await self._log_socks_event(tunnel_id, "tunnel_created", {
                "local_host": request.local_host,
                "local_port": request.local_port,
                "remote_host": request.remote_host,
                "remote_port": request.remote_port,
                "protocol": request.protocol.value,
                "proxy_connection_id": request.proxy_connection_id
            })
            
            logger.info(f"Created tunnel: {tunnel_id}")
            
            return tunnel_id
            
        except Exception as e:
            logger.error(f"Error creating tunnel: {e}")
            raise
    
    async def _generate_tunnel_id(self, request: TunnelRequest) -> str:
        """Generate unique tunnel ID"""
        timestamp = int(time.time())
        local_hash = hashlib.sha256(f"{request.local_host}:{request.local_port}".encode()).hexdigest()[:6]
        remote_hash = hashlib.sha256(f"{request.remote_host}:{request.remote_port}".encode()).hexdigest()[:6]
        
        return f"tunnel_{timestamp}_{local_hash}_{remote_hash}"
    
    async def _run_tunnel(self, tunnel_config: TunnelConfig):
        """Run tunnel forwarding"""
        try:
            proxy_connection = self.proxy_connections[tunnel_config.proxy_connection_id]
            
            # Create local server socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((tunnel_config.local_host, tunnel_config.local_port))
            server_socket.listen(5)
            
            logger.info(f"Tunnel server listening on {tunnel_config.local_host}:{tunnel_config.local_port}")
            
            while tunnel_config.status == "active":
                try:
                    # Accept client connection
                    client_socket, client_addr = server_socket.accept()
                    
                    # Handle client connection
                    asyncio.create_task(self._handle_tunnel_client(
                        client_socket, tunnel_config, proxy_connection
                    ))
                    
                except Exception as e:
                    logger.error(f"Error accepting tunnel connection: {e}")
                    break
            
            server_socket.close()
            
        except Exception as e:
            logger.error(f"Error running tunnel: {e}")
            tunnel_config.status = "error"
    
    async def _handle_tunnel_client(self, client_socket: socket.socket, 
                                  tunnel_config: TunnelConfig, 
                                  proxy_connection: ProxyConnection):
        """Handle tunnel client connection"""
        try:
            # Create SOCKS connection to remote host
            remote_socket = await self._create_socks_connection(
                proxy_connection, tunnel_config.remote_host, tunnel_config.remote_port
            )
            
            if not remote_socket:
                client_socket.close()
                return
            
            # Start bidirectional forwarding
            async def forward_data(source: socket.socket, destination: socket.socket):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        
                        destination.send(data)
                        
                        # Update tunnel statistics
                        if source == client_socket:
                            tunnel_config.bytes_tunneled += len(data)
                        
                except Exception as e:
                    logger.debug(f"Forwarding error: {e}")
                finally:
                    source.close()
                    destination.close()
            
            # Start forwarding tasks
            client_to_remote = asyncio.create_task(
                forward_data(client_socket, remote_socket)
            )
            remote_to_client = asyncio.create_task(
                forward_data(remote_socket, client_socket)
            )
            
            # Wait for either direction to complete
            await asyncio.gather(client_to_remote, remote_to_client, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error handling tunnel client: {e}")
            client_socket.close()
    
    async def _create_socks_connection(self, proxy_connection: ProxyConnection, 
                                     remote_host: str, remote_port: int) -> Optional[socket.socket]:
        """Create SOCKS connection to remote host"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(proxy_connection.config.timeout)
            
            # Connect to proxy
            sock.connect((proxy_connection.config.proxy_host, proxy_connection.config.proxy_port))
            
            # Perform SOCKS handshake
            if proxy_connection.config.version == SocksVersion.SOCKS5:
                success = await self._socks5_connect(sock, proxy_connection, remote_host, remote_port)
            elif proxy_connection.config.version == SocksVersion.SOCKS4:
                success = await self._socks4_connect(sock, remote_host, remote_port)
            else:
                success = False
            
            if success:
                return sock
            else:
                sock.close()
                return None
                
        except Exception as e:
            logger.error(f"Error creating SOCKS connection: {e}")
            return None
    
    async def _socks5_connect(self, sock: socket.socket, proxy_connection: ProxyConnection,
                            remote_host: str, remote_port: int) -> bool:
        """SOCKS5 connect to remote host"""
        try:
            # Send greeting
            if proxy_connection.config.auth_method == SocksAuthMethod.NO_AUTH:
                greeting = b'\x05\x01\x00'
            else:
                greeting = b'\x05\x02\x00\x02'
            
            sock.send(greeting)
            
            # Receive server response
            response = sock.recv(2)
            if len(response) != 2 or response[0] != 0x05:
                return False
            
            # Handle authentication if required
            if response[1] == 0x02:  # Username/password
                username_bytes = proxy_connection.config.username.encode('utf-8')
                password_bytes = proxy_connection.config.password.encode('utf-8')
                
                auth_request = struct.pack('BB', 0x01, len(username_bytes))
                auth_request += username_bytes
                auth_request += struct.pack('B', len(password_bytes))
                auth_request += password_bytes
                
                sock.send(auth_request)
                
                auth_response = sock.recv(2)
                if len(auth_response) != 2 or auth_response[1] != 0x00:
                    return False
            
            # Send connect request
            connect_request = b'\x05\x01\x00'  # SOCKS5, CONNECT, reserved
            
            # Add address
            try:
                # Try as IP address first
                ip_bytes = socket.inet_aton(remote_host)
                connect_request += b'\x01' + ip_bytes  # IPv4
            except socket.error:
                # Use domain name
                host_bytes = remote_host.encode('utf-8')
                connect_request += b'\x03' + struct.pack('B', len(host_bytes)) + host_bytes
            
            # Add port
            connect_request += struct.pack('>H', remote_port)
            
            sock.send(connect_request)
            
            # Receive connect response
            response = sock.recv(10)
            if len(response) < 2:
                return False
            
            return response[1] == 0x00  # Success
            
        except Exception as e:
            logger.debug(f"SOCKS5 connect failed: {e}")
            return False
    
    async def _socks4_connect(self, sock: socket.socket, remote_host: str, remote_port: int) -> bool:
        """SOCKS4 connect to remote host"""
        try:
            # Resolve hostname to IP
            try:
                remote_ip = socket.inet_aton(remote_host)
            except socket.error:
                remote_ip = socket.inet_aton(socket.gethostbyname(remote_host))
            
            # Send connect request
            request = struct.pack('>BBH', 0x04, 0x01, remote_port)
            request += remote_ip
            request += b'\x00'  # Null terminator for user ID
            
            sock.send(request)
            
            # Receive response
            response = sock.recv(8)
            if len(response) < 2:
                return False
            
            return response[1] == 0x5A  # Request granted
            
        except Exception as e:
            logger.debug(f"SOCKS4 connect failed: {e}")
            return False
    
    async def _monitor_connections(self):
        """Monitor proxy connections health"""
        try:
            while True:
                for connection_id, connection in self.proxy_connections.items():
                    if connection.status == ProxyStatus.CONNECTED:
                        # Test connection
                        if not await self._test_proxy_connection(connection.config):
                            connection.status = ProxyStatus.ERROR
                            connection.error_count += 1
                            connection.last_error = "Connection test failed"
                            
                            await self._save_connections_registry()
                            
                            logger.warning(f"Proxy connection failed health check: {connection_id}")
                
                # Wait before next check
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("Connection monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in connection monitoring: {e}")
    
    async def _monitor_tunnels(self):
        """Monitor active tunnels"""
        try:
            while True:
                # Check tunnel health and clean up inactive ones
                inactive_tunnels = []
                
                for tunnel_id, tunnel_config in self.active_tunnels.items():
                    if tunnel_config.status == "error":
                        inactive_tunnels.append(tunnel_id)
                
                # Remove inactive tunnels
                for tunnel_id in inactive_tunnels:
                    del self.active_tunnels[tunnel_id]
                    logger.info(f"Removed inactive tunnel: {tunnel_id}")
                
                # Wait before next check
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Tunnel monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in tunnel monitoring: {e}")
    
    async def remove_proxy_connection(self, connection_id: str) -> bool:
        """Remove a proxy connection"""
        try:
            if connection_id not in self.proxy_connections:
                return False
            
            connection = self.proxy_connections[connection_id]
            
            # Close any active tunnels using this connection
            tunnels_to_remove = []
            for tunnel_id, tunnel_config in self.active_tunnels.items():
                if tunnel_config.proxy_connection_id == connection_id:
                    tunnels_to_remove.append(tunnel_id)
            
            for tunnel_id in tunnels_to_remove:
                await self.remove_tunnel(tunnel_id)
            
            # Remove connection
            del self.proxy_connections[connection_id]
            
            # Save registry
            await self._save_connections_registry()
            
            # Log removal
            await self._log_socks_event(connection_id, "proxy_connection_removed", {
                "proxy_host": connection.config.proxy_host,
                "proxy_port": connection.config.proxy_port
            })
            
            logger.info(f"Removed proxy connection: {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing proxy connection: {e}")
            return False
    
    async def remove_tunnel(self, tunnel_id: str) -> bool:
        """Remove a tunnel"""
        try:
            if tunnel_id not in self.active_tunnels:
                return False
            
            tunnel_config = self.active_tunnels[tunnel_id]
            
            # Stop tunnel
            tunnel_config.status = "stopped"
            
            # Remove from active tunnels
            del self.active_tunnels[tunnel_id]
            
            # Log removal
            await self._log_socks_event(tunnel_id, "tunnel_removed", {
                "local_host": tunnel_config.local_host,
                "local_port": tunnel_config.local_port,
                "remote_host": tunnel_config.remote_host,
                "remote_port": tunnel_config.remote_port
            })
            
            logger.info(f"Removed tunnel: {tunnel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing tunnel: {e}")
            return False
    
    async def list_proxy_connections(self) -> List[Dict[str, Any]]:
        """List all proxy connections"""
        try:
            connections = []
            for connection in self.proxy_connections.values():
                connections.append({
                    "connection_id": connection.connection_id,
                    "proxy_host": connection.config.proxy_host,
                    "proxy_port": connection.config.proxy_port,
                    "version": connection.config.version.value,
                    "auth_method": connection.config.auth_method.value,
                    "status": connection.status.value,
                    "created_at": connection.created_at.isoformat(),
                    "last_used": connection.last_used.isoformat() if connection.last_used else None,
                    "bytes_sent": connection.bytes_sent,
                    "bytes_received": connection.bytes_received,
                    "connection_count": connection.connection_count,
                    "error_count": connection.error_count,
                    "last_error": connection.last_error
                })
            
            return connections
            
        except Exception as e:
            logger.error(f"Error listing proxy connections: {e}")
            return []
    
    async def list_tunnels(self) -> List[Dict[str, Any]]:
        """List all active tunnels"""
        try:
            tunnels = []
            for tunnel_config in self.active_tunnels.values():
                tunnels.append({
                    "tunnel_id": tunnel_config.tunnel_id,
                    "local_host": tunnel_config.local_host,
                    "local_port": tunnel_config.local_port,
                    "remote_host": tunnel_config.remote_host,
                    "remote_port": tunnel_config.remote_port,
                    "protocol": tunnel_config.protocol.value,
                    "proxy_connection_id": tunnel_config.proxy_connection_id,
                    "status": tunnel_config.status,
                    "created_at": tunnel_config.created_at.isoformat(),
                    "bytes_tunneled": tunnel_config.bytes_tunneled
                })
            
            return tunnels
            
        except Exception as e:
            logger.error(f"Error listing tunnels: {e}")
            return []
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        try:
            total_connections = len(self.proxy_connections)
            active_connections = sum(1 for c in self.proxy_connections.values() 
                                   if c.status == ProxyStatus.CONNECTED)
            total_tunnels = len(self.active_tunnels)
            active_tunnels = sum(1 for t in self.active_tunnels.values() 
                               if t.status == "active")
            
            total_bytes_sent = sum(c.bytes_sent for c in self.proxy_connections.values())
            total_bytes_received = sum(c.bytes_received for c in self.proxy_connections.values())
            total_bytes_tunneled = sum(t.bytes_tunneled for t in self.active_tunnels.values())
            
            return {
                "proxy_connections": {
                    "total": total_connections,
                    "active": active_connections,
                    "bytes_sent": total_bytes_sent,
                    "bytes_received": total_bytes_received
                },
                "tunnels": {
                    "total": total_tunnels,
                    "active": active_tunnels,
                    "bytes_tunneled": total_bytes_tunneled
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            return {"error": str(e)}
    
    async def _log_socks_event(self, event_id: str, event_type: str, data: Dict[str, Any]):
        """Log SOCKS proxy event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_id": event_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"socks_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging SOCKS event: {e}")

# Convenience functions for external use
async def create_socks_connection(request: SocksProxyRequest, data_dir: Path) -> str:
    """Create a new SOCKS proxy connection"""
    manager = SocksProxyManager(data_dir)
    return await manager.create_proxy_connection(request)

async def create_tunnel(request: TunnelRequest, data_dir: Path) -> str:
    """Create a new tunnel"""
    manager = SocksProxyManager(data_dir)
    return await manager.create_tunnel(request)

async def list_proxy_connections(data_dir: Path) -> List[Dict[str, Any]]:
    """List all proxy connections"""
    manager = SocksProxyManager(data_dir)
    return await manager.list_proxy_connections()

async def list_tunnels(data_dir: Path) -> List[Dict[str, Any]]:
    """List all active tunnels"""
    manager = SocksProxyManager(data_dir)
    return await manager.list_tunnels()

if __name__ == "__main__":
    # Example usage
    async def main():
        data_dir = Path("/data/node/socks")
        
        # Create Tor SOCKS proxy connection
        tor_proxy_request = SocksProxyRequest(
            proxy_host="127.0.0.1",
            proxy_port=9050,
            version=SocksVersion.SOCKS5
        )
        
        connection_id = await create_socks_connection(tor_proxy_request, data_dir)
        print(f"Tor SOCKS connection created: {connection_id}")
        
        # Create tunnel through Tor
        tunnel_request = TunnelRequest(
            local_port=8080,
            remote_host="example.onion",
            remote_port=80,
            proxy_connection_id=connection_id
        )
        
        tunnel_id = await create_tunnel(tunnel_request, data_dir)
        print(f"Tunnel created: {tunnel_id}")
        
        # List connections and tunnels
        connections = await list_proxy_connections(data_dir)
        tunnels = await list_tunnels(data_dir)
        
        print(f"Active connections: {len(connections)}")
        print(f"Active tunnels: {len(tunnels)}")
    
    asyncio.run(main())

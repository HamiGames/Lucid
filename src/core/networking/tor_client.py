"""
Networking-layer Tor client implementation for Lucid project.

This module provides low-level Tor networking functionality including:
- Tor connection management
- SOCKS5 proxy integration
- Circuit management
- Stream handling
- Onion service connectivity
- Network security enforcement
"""

import os
import sys
import time
import socket
import struct
import logging
import threading
import asyncio
from typing import Optional, Dict, Any, List, Tuple, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from contextlib import asynccontextmanager, contextmanager
import ssl
import socks
import requests
from urllib.parse import urlparse
import json
import base64
import hashlib
import hmac
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class TorConnectionState(Enum):
    """Tor connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"
    CLOSING = "closing"


class TorCircuitState(Enum):
    """Tor circuit state enumeration."""
    UNKNOWN = "unknown"
    LAUNCHED = "launched"
    BUILT = "built"
    EXTENDED = "extended"
    FAILED = "failed"
    CLOSED = "closed"


class StreamState(Enum):
    """Stream state enumeration."""
    UNKNOWN = "unknown"
    NEW = "new"
    NEWRESOLV = "newresolv"
    REMAP = "remap"
    SENTCONNECT = "sentconnect"
    SENTRESOLVE = "sentresolve"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CLOSED = "closed"


class TorError(Exception):
    """Base exception for Tor networking errors."""
    pass


class TorConnectionError(TorError):
    """Tor connection related errors."""
    pass


class TorAuthenticationError(TorError):
    """Tor authentication errors."""
    pass


class TorCircuitError(TorError):
    """Tor circuit related errors."""
    pass


class TorStreamError(TorError):
    """Tor stream related errors."""
    pass


@dataclass
class TorConfig:
    """Tor networking configuration."""
    socks_host: str = "127.0.0.1"
    socks_port: int = 9050
    control_host: str = "127.0.0.1"
    control_port: int = 9051
    control_password: Optional[str] = None
    control_cookie: Optional[bytes] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    circuit_build_timeout: int = 10
    stream_timeout: int = 60
    max_circuits: int = 10
    max_streams_per_circuit: int = 100
    enforce_tor_only: bool = True
    verify_certificates: bool = True
    custom_exit_nodes: Optional[List[str]] = None
    strict_exit_nodes: bool = False


@dataclass
class CircuitInfo:
    """Information about a Tor circuit."""
    circuit_id: int
    state: TorCircuitState
    path: List[str] = field(default_factory=list)
    purpose: str = "general"
    created_at: float = field(default_factory=time.time)
    bytes_read: int = 0
    bytes_written: int = 0


@dataclass
class StreamInfo:
    """Information about a Tor stream."""
    stream_id: int
    circuit_id: int
    state: StreamState
    target_host: str = ""
    target_port: int = 0
    created_at: float = field(default_factory=time.time)
    bytes_read: int = 0
    bytes_written: int = 0


class TorControlProtocol:
    """Tor control protocol implementation."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9051, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password
        self.socket: Optional[socket.socket] = None
        self.authenticated = False
        self._lock = threading.Lock()
    
    async def connect(self) -> bool:
        """Connect to Tor control port."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.connect, (self.host, self.port)
            )
            
            # Read initial response
            response = await self._read_response()
            if not response.startswith("250"):
                raise TorConnectionError(f"Unexpected control response: {response}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Tor control port: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Tor control port."""
        if not self.socket:
            raise TorConnectionError("Not connected to control port")
        
        try:
            if self.password:
                # Authenticate with password
                command = f"AUTHENTICATE \"{self.password}\"\r\n"
                await self._send_command(command)
                response = await self._read_response()
                
                if response.startswith("250"):
                    self.authenticated = True
                    return True
                else:
                    raise TorAuthenticationError(f"Authentication failed: {response}")
            else:
                # Try cookie authentication
                cookie_file = Path.home() / ".tor" / "control_auth_cookie"
                if cookie_file.exists():
                    cookie_data = cookie_file.read_bytes()
                    cookie_b64 = base64.b64encode(cookie_data).decode('ascii')
                    command = f"AUTHENTICATE {cookie_b64}\r\n"
                    await self._send_command(command)
                    response = await self._read_response()
                    
                    if response.startswith("250"):
                        self.authenticated = True
                        return True
                
                raise TorAuthenticationError("No authentication method available")
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def send_command(self, command: str) -> str:
        """Send command to Tor control port."""
        if not self.authenticated:
            raise TorAuthenticationError("Not authenticated")
        
        await self._send_command(command)
        return await self._read_response()
    
    async def get_info(self, info_key: str) -> str:
        """Get information from Tor."""
        response = await self.send_command(f"GETINFO {info_key}\r\n")
        if response.startswith("250"):
            # Parse the response
            lines = response.split('\n')
            for line in lines:
                if line.startswith(f"250-{info_key}="):
                    return line.split('=', 1)[1]
                elif line.startswith(f"250 {info_key}="):
                    return line.split('=', 1)[1]
        return ""
    
    async def get_circuits(self) -> List[CircuitInfo]:
        """Get list of circuits."""
        response = await self.send_command("GETINFO circuit-status\r\n")
        circuits = []
        
        if response.startswith("250"):
            lines = response.split('\n')
            for line in lines:
                if line.startswith("250-circuit-status="):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        circuit_id = int(parts[1])
                        state_str = parts[2].split()[0] if parts[2] else "UNKNOWN"
                        
                        # Map Tor circuit states to our enum
                        state_map = {
                            "LAUNCHED": TorCircuitState.LAUNCHED,
                            "BUILT": TorCircuitState.BUILT,
                            "EXTENDED": TorCircuitState.EXTENDED,
                            "FAILED": TorCircuitState.FAILED,
                            "CLOSED": TorCircuitState.CLOSED,
                        }
                        
                        state = state_map.get(state_str, TorCircuitState.UNKNOWN)
                        circuits.append(CircuitInfo(circuit_id=circuit_id, state=state))
        
        return circuits
    
    async def get_streams(self) -> List[StreamInfo]:
        """Get list of streams."""
        response = await self.send_command("GETINFO stream-status\r\n")
        streams = []
        
        if response.startswith("250"):
            lines = response.split('\n')
            for line in lines:
                if line.startswith("250-stream-status="):
                    parts = line.split()
                    if len(parts) >= 5:
                        stream_id = int(parts[1])
                        circuit_id = int(parts[2])
                        state_str = parts[3]
                        target = parts[4] if len(parts) > 4 else ""
                        
                        # Map Tor stream states to our enum
                        state_map = {
                            "NEW": StreamState.NEW,
                            "NEWRESOLV": StreamState.NEWRESOLV,
                            "REMAP": StreamState.REMAP,
                            "SENTCONNECT": StreamState.SENTCONNECT,
                            "SENTRESOLVE": StreamState.SENTRESOLVE,
                            "SUCCEEDED": StreamState.SUCCEEDED,
                            "FAILED": StreamState.FAILED,
                            "CLOSED": StreamState.CLOSED,
                        }
                        
                        state = state_map.get(state_str, StreamState.UNKNOWN)
                        
                        # Parse target host:port
                        target_host = ""
                        target_port = 0
                        if ':' in target:
                            target_host, port_str = target.rsplit(':', 1)
                            try:
                                target_port = int(port_str)
                            except ValueError:
                                pass
                        
                        streams.append(StreamInfo(
                            stream_id=stream_id,
                            circuit_id=circuit_id,
                            state=state,
                            target_host=target_host,
                            target_port=target_port
                        ))
        
        return streams
    
    async def new_circuit(self) -> int:
        """Create a new circuit."""
        response = await self.send_command("EXTENDCIRCUIT 0\r\n")
        if response.startswith("250"):
            # Parse circuit ID from response
            parts = response.split()
            if len(parts) >= 2:
                return int(parts[1])
        raise TorCircuitError("Failed to create new circuit")
    
    async def close_circuit(self, circuit_id: int) -> bool:
        """Close a circuit."""
        response = await self.send_command(f"CLOSECIRCUIT {circuit_id}\r\n")
        return response.startswith("250")
    
    async def _send_command(self, command: str) -> None:
        """Send command to control port."""
        with self._lock:
            if self.socket:
                self.socket.send(command.encode('ascii'))
    
    async def _read_response(self) -> str:
        """Read response from control port."""
        with self._lock:
            if not self.socket:
                return ""
            
            response = ""
            while True:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.socket.recv, 4096
                )
                if not data:
                    break
                
                response += data.decode('ascii', errors='ignore')
                if response.endswith('\r\n.\r\n'):
                    break
            
            return response.strip()
    
    def close(self) -> None:
        """Close control connection."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            finally:
                self.socket = None
        self.authenticated = False


class TorSOCKSProxy:
    """SOCKS5 proxy implementation for Tor."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9050):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
    
    async def connect(self, target_host: str, target_port: int, timeout: int = 30) -> socket.socket:
        """Connect to target through Tor SOCKS proxy."""
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            # Connect to SOCKS proxy
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.connect, (self.host, self.port)
            )
            
            # SOCKS5 handshake
            await self._socks5_handshake()
            
            # Connect to target
            await self._socks5_connect(target_host, target_port)
            
            return self.socket
            
        except Exception as e:
            if self.socket:
                self.socket.close()
                self.socket = None
            raise TorConnectionError(f"SOCKS5 connection failed: {e}")
    
    async def _socks5_handshake(self) -> None:
        """Perform SOCKS5 handshake."""
        # Send authentication methods
        auth_methods = b'\x05\x01\x00'  # SOCKS5, 1 method, no auth
        await asyncio.get_event_loop().run_in_executor(
            None, self.socket.send, auth_methods
        )
        
        # Receive server response
        response = await asyncio.get_event_loop().run_in_executor(
            None, self.socket.recv, 2
        )
        
        if len(response) != 2 or response[0] != 0x05:
            raise TorConnectionError("Invalid SOCKS5 handshake response")
        
        if response[1] != 0x00:  # No authentication required
            raise TorConnectionError(f"SOCKS5 authentication method not supported: {response[1]}")
    
    async def _socks5_connect(self, target_host: str, target_port: int) -> None:
        """Send SOCKS5 CONNECT command."""
        # Build CONNECT request
        request = bytearray()
        request.extend([0x05, 0x01, 0x00])  # SOCKS5, CONNECT, reserved
        
        # Add address type and address
        try:
            # Try to parse as IP address
            ip_bytes = socket.inet_aton(target_host)
            request.extend([0x01])  # IPv4
            request.extend(ip_bytes)
        except socket.error:
            # Domain name
            host_bytes = target_host.encode('ascii')
            request.extend([0x03, len(host_bytes)])  # Domain name, length
            request.extend(host_bytes)
        
        # Add port
        request.extend(struct.pack('>H', target_port))
        
        # Send request
        await asyncio.get_event_loop().run_in_executor(
            None, self.socket.send, bytes(request)
        )
        
        # Receive response
        response = await asyncio.get_event_loop().run_in_executor(
            None, self.socket.recv, 10
        )
        
        if len(response) < 8 or response[0] != 0x05 or response[1] != 0x00:
            raise TorConnectionError(f"SOCKS5 connection failed: {response[1] if len(response) > 1 else 'unknown'}")


class TorNetworkClient:
    """Main Tor networking client."""
    
    def __init__(self, config: Optional[TorConfig] = None):
        self.config = config or TorConfig()
        self.control_protocol: Optional[TorControlProtocol] = None
        self.socks_proxy: Optional[TorSOCKSProxy] = None
        self.state = TorConnectionState.DISCONNECTED
        self.circuits: Dict[int, CircuitInfo] = {}
        self.streams: Dict[int, StreamInfo] = {}
        self._lock = threading.Lock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def connect(self) -> bool:
        """Connect to Tor network."""
        try:
            self.state = TorConnectionState.CONNECTING
            
            # Initialize control protocol
            self.control_protocol = TorControlProtocol(
                host=self.config.control_host,
                port=self.config.control_port,
                password=self.config.control_password
            )
            
            # Connect to control port
            if not await self.control_protocol.connect():
                raise TorConnectionError("Failed to connect to Tor control port")
            
            # Authenticate
            self.state = TorConnectionState.AUTHENTICATING
            if not await self.control_protocol.authenticate():
                raise TorAuthenticationError("Failed to authenticate with Tor")
            
            self.state = TorConnectionState.AUTHENTICATED
            
            # Initialize SOCKS proxy
            self.socks_proxy = TorSOCKSProxy(
                host=self.config.socks_host,
                port=self.config.socks_port
            )
            
            # Test SOCKS connection
            if not await self._test_socks_connection():
                raise TorConnectionError("SOCKS proxy test failed")
            
            self.state = TorConnectionState.CONNECTED
            
            # Start monitoring
            await self._start_monitoring()
            
            logger.info("Connected to Tor network successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Tor: {e}")
            self.state = TorConnectionState.FAILED
            await self.disconnect()
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Tor network."""
        try:
            self.state = TorConnectionState.CLOSING
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Close control connection
            if self.control_protocol:
                self.control_protocol.close()
                self.control_protocol = None
            
            # Close SOCKS connection
            if self.socks_proxy and self.socks_proxy.socket:
                self.socks_proxy.socket.close()
                self.socks_proxy.socket = None
            
            self.state = TorConnectionState.DISCONNECTED
            logger.info("Disconnected from Tor network")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Tor: {e}")
            return False
    
    async def create_connection(self, target_host: str, target_port: int, 
                              timeout: Optional[int] = None) -> socket.socket:
        """Create a connection through Tor to target host:port."""
        if self.state != TorConnectionState.CONNECTED:
            raise TorConnectionError("Not connected to Tor network")
        
        if not self.socks_proxy:
            raise TorConnectionError("SOCKS proxy not available")
        
        timeout = timeout or self.config.stream_timeout
        
        try:
            # Create new circuit if needed
            await self._ensure_circuit_available()
            
            # Connect through SOCKS proxy
            sock = await self.socks_proxy.connect(target_host, target_port, timeout)
            
            logger.debug(f"Created connection to {target_host}:{target_port} through Tor")
            return sock
            
        except Exception as e:
            logger.error(f"Failed to create connection to {target_host}:{target_port}: {e}")
            raise TorConnectionError(f"Connection failed: {e}")
    
    async def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request through Tor."""
        if self.state != TorConnectionState.CONNECTED:
            raise TorConnectionError("Not connected to Tor network")
        
        # Configure SOCKS proxy for requests
        proxies = {
            'http': f'socks5://{self.config.socks_host}:{self.config.socks_port}',
            'https': f'socks5://{self.config.socks_host}:{self.config.socks_port}'
        }
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.config.stream_timeout
        
        try:
            response = requests.request(method, url, proxies=proxies, **kwargs)
            logger.debug(f"Made {method} request to {url} through Tor")
            return response
            
        except Exception as e:
            logger.error(f"Request to {url} failed: {e}")
            raise TorConnectionError(f"Request failed: {e}")
    
    async def get_circuit_info(self) -> List[CircuitInfo]:
        """Get information about current circuits."""
        if not self.control_protocol:
            return []
        
        try:
            circuits = await self.control_protocol.get_circuits()
            with self._lock:
                self.circuits = {circuit.circuit_id: circuit for circuit in circuits}
            return circuits
        except Exception as e:
            logger.error(f"Failed to get circuit info: {e}")
            return []
    
    async def get_stream_info(self) -> List[StreamInfo]:
        """Get information about current streams."""
        if not self.control_protocol:
            return []
        
        try:
            streams = await self.control_protocol.get_streams()
            with self._lock:
                self.streams = {stream.stream_id: stream for stream in streams}
            return streams
        except Exception as e:
            logger.error(f"Failed to get stream info: {e}")
            return []
    
    async def test_connection(self, test_url: str = "https://httpbin.org/ip") -> bool:
        """Test Tor connection by making a request."""
        try:
            response = await self.make_request('GET', test_url)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
    
    async def _test_socks_connection(self) -> bool:
        """Test SOCKS proxy connection."""
        try:
            test_sock = await self.socks_proxy.connect("httpbin.org", 80, timeout=10)
            test_sock.close()
            return True
        except Exception as e:
            logger.warning(f"SOCKS connection test failed: {e}")
            return False
    
    async def _ensure_circuit_available(self) -> None:
        """Ensure at least one circuit is available."""
        circuits = await self.get_circuit_info()
        built_circuits = [c for c in circuits if c.state == TorCircuitState.BUILT]
        
        if not built_circuits and self.control_protocol:
            # Create new circuit
            try:
                circuit_id = await self.control_protocol.new_circuit()
                logger.info(f"Created new circuit: {circuit_id}")
                
                # Wait for circuit to be built
                for _ in range(self.config.circuit_build_timeout):
                    await asyncio.sleep(1)
                    circuits = await self.get_circuit_info()
                    circuit = next((c for c in circuits if c.circuit_id == circuit_id), None)
                    if circuit and circuit.state == TorCircuitState.BUILT:
                        break
                else:
                    logger.warning(f"Circuit {circuit_id} did not build within timeout")
                    
            except Exception as e:
                logger.error(f"Failed to create circuit: {e}")
    
    async def _start_monitoring(self) -> None:
        """Start monitoring Tor connections."""
        self._event_loop = asyncio.get_event_loop()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def _stop_monitoring(self) -> None:
        """Stop monitoring Tor connections."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Update circuit and stream information
                await self.get_circuit_info()
                await self.get_stream_info()
                
                # Check connection health
                if not await self.test_connection():
                    logger.warning("Tor connection health check failed")
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    @asynccontextmanager
    async def connection_context(self, target_host: str, target_port: int):
        """Context manager for Tor connections."""
        sock = None
        try:
            sock = await self.create_connection(target_host, target_port)
            yield sock
        finally:
            if sock:
                sock.close()
    
    @contextmanager
    def requests_session(self):
        """Context manager for Tor HTTP requests."""
        session = requests.Session()
        try:
            # Configure SOCKS proxy
            proxies = {
                'http': f'socks5://{self.config.socks_host}:{self.config.socks_port}',
                'https': f'socks5://{self.config.socks_host}:{self.config.socks_port}'
            }
            session.proxies.update(proxies)
            session.timeout = self.config.stream_timeout
            
            yield session
        finally:
            session.close()


# Global Tor client instance
_tor_client: Optional[TorNetworkClient] = None


def get_tor_client(config: Optional[TorConfig] = None) -> TorNetworkClient:
    """Get global Tor network client instance."""
    global _tor_client
    if _tor_client is None:
        _tor_client = TorNetworkClient(config)
    return _tor_client


async def connect_to_tor(config: Optional[TorConfig] = None) -> bool:
    """Connect to Tor network."""
    client = get_tor_client(config)
    return await client.connect()


async def disconnect_from_tor() -> bool:
    """Disconnect from Tor network."""
    global _tor_client
    if _tor_client:
        result = await _tor_client.disconnect()
        _tor_client = None
        return result
    return True


async def make_tor_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request through Tor."""
    client = get_tor_client()
    return await client.make_request(method, url, **kwargs)


async def create_tor_connection(target_host: str, target_port: int, 
                               timeout: Optional[int] = None) -> socket.socket:
    """Create connection through Tor."""
    client = get_tor_client()
    return await client.create_connection(target_host, target_port, timeout)


def cleanup_tor_client() -> None:
    """Cleanup global Tor client."""
    global _tor_client
    if _tor_client:
        asyncio.create_task(_tor_client.disconnect())
        _tor_client = None

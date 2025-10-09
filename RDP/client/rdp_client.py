# Path: RDP/client/rdp_client.py
# Lucid RDP Client - Client-side RDP connection management
# Implements R-MUST-003: Remote Desktop Host Support with client connectivity
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import socket
import ssl
import subprocess
import platform

# Import existing project modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from sessions.session_recorder import SessionRecorder, SessionMetadata

logger = logging.getLogger(__name__)

# Configuration from environment
DEFAULT_RDP_PORT = int(os.getenv("DEFAULT_RDP_PORT", "3389"))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))
RECONNECT_ATTEMPTS = int(os.getenv("RECONNECT_ATTEMPTS", "3"))
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))
CLIENT_BUFFER_SIZE = int(os.getenv("CLIENT_BUFFER_SIZE", "8192"))


class ClientConnectionState(Enum):
    """Client connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    ESTABLISHED = "established"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ClientPlatform(Enum):
    """Supported client platforms"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"


class ClientCapability(Enum):
    """Client capabilities"""
    AUDIO_REDIRECTION = "audio_redirection"
    CLIPBOARD_REDIRECTION = "clipboard_redirection"
    FILE_TRANSFER = "file_transfer"
    PRINTER_REDIRECTION = "printer_redirection"
    USB_REDIRECTION = "usb_redirection"
    SMART_CARD = "smart_card"
    MULTIMONITOR = "multimonitor"
    COMPRESSION = "compression"
    ENCRYPTION = "encryption"


@dataclass
class ClientConfig:
    """Client configuration"""
    server_host: str
    server_port: int = DEFAULT_RDP_PORT
    username: str = ""
    password: str = ""
    domain: str = ""
    resolution: Tuple[int, int] = (1920, 1080)
    color_depth: int = 32
    audio_enabled: bool = True
    clipboard_enabled: bool = True
    file_transfer_enabled: bool = False
    printer_enabled: bool = False
    usb_enabled: bool = False
    smart_card_enabled: bool = False
    compression_enabled: bool = True
    encryption_enabled: bool = True
    connection_timeout: int = CONNECTION_TIMEOUT
    reconnect_attempts: int = RECONNECT_ATTEMPTS
    reconnect_delay: int = RECONNECT_DELAY
    capabilities: Set[ClientCapability] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    connection_time: float
    authentication_time: float
    total_bytes_sent: int
    total_bytes_received: int
    packets_sent: int
    packets_received: int
    latency_ms: float
    bandwidth_mbps: float
    compression_ratio: float
    encryption_overhead: float
    timestamp: datetime


@dataclass
class ClientSession:
    """Client session information"""
    session_id: str
    client_id: str
    config: ClientConfig
    state: ClientConnectionState
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    metrics: List[ConnectionMetrics] = field(default_factory=list)
    error_count: int = 0
    reconnect_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RDPClient:
    """
    Client-side RDP connection manager for connecting to Lucid RDP servers.
    Supports multiple platforms and provides comprehensive connection management.
    """
    
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig(server_host="localhost")
        self.client_id = str(uuid.uuid4())
        self.platform = self._detect_platform()
        self.current_session: Optional[ClientSession] = None
        self.connection_callbacks: List[Callable] = []
        self.data_callbacks: List[Callable] = []
        
        # Connection management
        self._running = False
        self._connection_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Platform-specific components
        self._rdp_client_process: Optional[subprocess.Popen] = None
        self._connection_socket: Optional[socket.socket] = None
        
        logger.info(f"RDPClient initialized for platform: {self.platform.value}")
    
    async def start(self) -> None:
        """Start the RDP client"""
        if self._running:
            logger.warning("RDPClient is already running")
            return
        
        try:
            self._running = True
            logger.info("RDPClient started")
            
        except Exception as e:
            logger.error(f"Failed to start RDPClient: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the RDP client"""
        if not self._running:
            return
        
        logger.info("Stopping RDPClient...")
        self._running = False
        
        # Disconnect current session
        await self.disconnect()
        
        # Cancel background tasks
        tasks = [self._connection_task, self._heartbeat_task, self._metrics_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("RDPClient stopped")
    
    async def connect(
        self,
        session_id: str,
        config: Optional[ClientConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Connect to an RDP session"""
        async with self._lock:
            if self.current_session and self.current_session.state == ClientConnectionState.CONNECTED:
                logger.warning("Already connected to a session")
                return False
            
            # Use provided config or default
            client_config = config or self.config
            
            # Create client session
            self.current_session = ClientSession(
                session_id=session_id,
                client_id=self.client_id,
                config=client_config,
                state=ClientConnectionState.CONNECTING,
                metadata=metadata or {}
            )
            
            try:
                # Update state
                self.current_session.state = ClientConnectionState.CONNECTING
                
                # Start connection process
                self._connection_task = asyncio.create_task(self._connect_async())
                
                # Wait for connection
                await asyncio.wait_for(self._connection_task, timeout=client_config.connection_timeout)
                
                if self.current_session.state == ClientConnectionState.ESTABLISHED:
                    self.current_session.connected_at = datetime.now(timezone.utc)
                    
                    # Start background tasks
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    self._metrics_task = asyncio.create_task(self._metrics_loop())
                    
                    logger.info(f"Connected to session {session_id}")
                    return True
                else:
                    logger.error(f"Failed to connect to session {session_id}")
                    return False
                
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout for session {session_id}")
                self.current_session.state = ClientConnectionState.TIMEOUT
                return False
            except Exception as e:
                logger.error(f"Connection error for session {session_id}: {e}")
                self.current_session.state = ClientConnectionState.FAILED
                self.current_session.error_count += 1
                return False
    
    async def disconnect(self, force: bool = False) -> bool:
        """Disconnect from current session"""
        async with self._lock:
            if not self.current_session:
                return True
            
            try:
                self.current_session.state = ClientConnectionState.DISCONNECTING
                
                # Stop background tasks
                tasks = [self._heartbeat_task, self._metrics_task]
                for task in tasks:
                    if task:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                
                # Close RDP client process
                if self._rdp_client_process:
                    if force:
                        self._rdp_client_process.kill()
                    else:
                        self._rdp_client_process.terminate()
                    
                    try:
                        await asyncio.wait_for(self._rdp_client_process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self._rdp_client_process.kill()
                    
                    self._rdp_client_process = None
                
                # Close socket connection
                if self._connection_socket:
                    self._connection_socket.close()
                    self._connection_socket = None
                
                # Update session state
                self.current_session.state = ClientConnectionState.DISCONNECTED
                self.current_session.disconnected_at = datetime.now(timezone.utc)
                
                logger.info(f"Disconnected from session {self.current_session.session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
                return False
    
    async def reconnect(self) -> bool:
        """Reconnect to current session"""
        if not self.current_session:
            logger.error("No current session to reconnect")
            return False
        
        if self.current_session.reconnect_count >= self.config.reconnect_attempts:
            logger.error("Maximum reconnect attempts exceeded")
            return False
        
        logger.info(f"Reconnecting to session {self.current_session.session_id}...")
        
        # Wait before reconnecting
        await asyncio.sleep(self.config.reconnect_delay)
        
        # Disconnect current connection
        await self.disconnect(force=True)
        
        # Update reconnect count
        self.current_session.reconnect_count += 1
        self.current_session.state = ClientConnectionState.RECONNECTING
        
        # Attempt to reconnect
        return await self.connect(
            self.current_session.session_id,
            self.current_session.config,
            self.current_session.metadata
        )
    
    async def send_data(self, data: bytes) -> bool:
        """Send data to the RDP server"""
        if not self.current_session or self.current_session.state != ClientConnectionState.ESTABLISHED:
            logger.error("Not connected to a session")
            return False
        
        try:
            if self._connection_socket:
                self._connection_socket.send(data)
                return True
            else:
                logger.error("No connection socket available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send data: {e}")
            return False
    
    async def receive_data(self, buffer_size: int = CLIENT_BUFFER_SIZE) -> Optional[bytes]:
        """Receive data from the RDP server"""
        if not self.current_session or self.current_session.state != ClientConnectionState.ESTABLISHED:
            logger.error("Not connected to a session")
            return None
        
        try:
            if self._connection_socket:
                data = self._connection_socket.recv(buffer_size)
                return data if data else None
            else:
                logger.error("No connection socket available")
                return None
                
        except Exception as e:
            logger.error(f"Failed to receive data: {e}")
            return None
    
    def get_connection_status(self) -> Optional[Dict[str, Any]]:
        """Get current connection status"""
        if not self.current_session:
            return None
        
        latest_metrics = None
        if self.current_session.metrics:
            latest_metrics = self.current_session.metrics[-1]
        
        return {
            "session_id": self.current_session.session_id,
            "client_id": self.client_id,
            "state": self.current_session.state.value,
            "platform": self.platform.value,
            "connected_at": self.current_session.connected_at.isoformat() if self.current_session.connected_at else None,
            "disconnected_at": self.current_session.disconnected_at.isoformat() if self.current_session.disconnected_at else None,
            "error_count": self.current_session.error_count,
            "reconnect_count": self.current_session.reconnect_count,
            "latest_metrics": latest_metrics.__dict__ if latest_metrics else None,
            "config": {
                "server_host": self.current_session.config.server_host,
                "server_port": self.current_session.config.server_port,
                "resolution": self.current_session.config.resolution,
                "audio_enabled": self.current_session.config.audio_enabled,
                "clipboard_enabled": self.current_session.config.clipboard_enabled,
                "file_transfer_enabled": self.current_session.config.file_transfer_enabled
            },
            "metadata": self.current_session.metadata
        }
    
    async def _connect_async(self) -> None:
        """Asynchronous connection process"""
        try:
            # Update state
            self.current_session.state = ClientConnectionState.CONNECTING
            
            # Platform-specific connection
            if self.platform == ClientPlatform.WINDOWS:
                await self._connect_windows()
            elif self.platform == ClientPlatform.MACOS:
                await self._connect_macos()
            elif self.platform == ClientPlatform.LINUX:
                await self._connect_linux()
            else:
                raise NotImplementedError(f"Platform {self.platform.value} not supported")
            
            # Update state to connected
            self.current_session.state = ClientConnectionState.ESTABLISHED
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.current_session.state = ClientConnectionState.FAILED
            self.current_session.error_count += 1
            raise
    
    async def _connect_windows(self) -> None:
        """Connect using Windows RDP client"""
        try:
            # Use mstsc.exe for Windows
            cmd = [
                "mstsc.exe",
                f"/v:{self.current_session.config.server_host}:{self.current_session.config.server_port}",
                f"/w:{self.current_session.config.resolution[0]}",
                f"/h:{self.current_session.config.resolution[1]}",
                f"/admin" if self.current_session.config.username == "administrator" else ""
            ]
            
            # Remove empty strings
            cmd = [arg for arg in cmd if arg]
            
            self._rdp_client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            logger.info("Started Windows RDP client")
            
        except Exception as e:
            logger.error(f"Failed to start Windows RDP client: {e}")
            raise
    
    async def _connect_macos(self) -> None:
        """Connect using macOS RDP client"""
        try:
            # Use Microsoft Remote Desktop or built-in client
            # This is a simplified implementation
            cmd = [
                "open",
                f"rdp://{self.current_session.config.server_host}:{self.current_session.config.server_port}"
            ]
            
            self._rdp_client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("Started macOS RDP client")
            
        except Exception as e:
            logger.error(f"Failed to start macOS RDP client: {e}")
            raise
    
    async def _connect_linux(self) -> None:
        """Connect using Linux RDP client (FreeRDP)"""
        try:
            # Use xfreerdp for Linux
            cmd = [
                "xfreerdp",
                f"/v:{self.current_session.config.server_host}:{self.current_session.config.server_port}",
                f"/size:{self.current_session.config.resolution[0]}x{self.current_session.config.resolution[1]}",
                f"/bpp:{self.current_session.config.color_depth}",
                "/network:auto",
                "/compression" if self.current_session.config.compression_enabled else "/no-compression",
                "/encryption" if self.current_session.config.encryption_enabled else "/no-encryption",
                "/audio" if self.current_session.config.audio_enabled else "/no-audio",
                "/clipboard" if self.current_session.config.clipboard_enabled else "/no-clipboard",
                "/drive:home,/home" if self.current_session.config.file_transfer_enabled else "",
                "/printer" if self.current_session.config.printer_enabled else "/no-printer",
                "/usb" if self.current_session.config.usb_enabled else "/no-usb",
                "/smartcard" if self.current_session.config.smart_card_enabled else "/no-smartcard"
            ]
            
            # Add credentials if provided
            if self.current_session.config.username:
                cmd.append(f"/u:{self.current_session.config.username}")
            if self.current_session.config.password:
                cmd.append(f"/p:{self.current_session.config.password}")
            if self.current_session.config.domain:
                cmd.append(f"/d:{self.current_session.config.domain}")
            
            # Remove empty strings
            cmd = [arg for arg in cmd if arg]
            
            self._rdp_client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("Started Linux RDP client")
            
        except Exception as e:
            logger.error(f"Failed to start Linux RDP client: {e}")
            raise
    
    async def _heartbeat_loop(self) -> None:
        """Background heartbeat loop"""
        while self._running and self.current_session and self.current_session.state == ClientConnectionState.ESTABLISHED:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                # Check if RDP client process is still running
                if self._rdp_client_process and self._rdp_client_process.poll() is not None:
                    logger.warning("RDP client process terminated unexpectedly")
                    await self.reconnect()
                    break
                
                # Send heartbeat data
                heartbeat_data = json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "client_id": self.client_id
                }).encode()
                
                await self.send_data(heartbeat_data)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _metrics_loop(self) -> None:
        """Background metrics collection loop"""
        while self._running and self.current_session and self.current_session.state == ClientConnectionState.ESTABLISHED:
            try:
                await asyncio.sleep(60)  # Collect metrics every minute
                
                # Collect connection metrics
                metrics = await self._collect_connection_metrics()
                if metrics:
                    self.current_session.metrics.append(metrics)
                    
                    # Keep only last 100 metrics
                    if len(self.current_session.metrics) > 100:
                        self.current_session.metrics = self.current_session.metrics[-100:]
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _collect_connection_metrics(self) -> Optional[ConnectionMetrics]:
        """Collect connection performance metrics"""
        try:
            # This is a simplified implementation
            # In a real implementation, you would collect actual network metrics
            return ConnectionMetrics(
                connection_time=0.0,  # Would be measured during connection
                authentication_time=0.0,  # Would be measured during auth
                total_bytes_sent=0,  # Would be collected from socket
                total_bytes_received=0,  # Would be collected from socket
                packets_sent=0,  # Would be collected from network interface
                packets_received=0,  # Would be collected from network interface
                latency_ms=0.0,  # Would be measured via ping
                bandwidth_mbps=0.0,  # Would be calculated from throughput
                compression_ratio=1.0,  # Would be calculated from compression
                encryption_overhead=0.0,  # Would be calculated from encryption
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Failed to collect connection metrics: {e}")
            return None
    
    def _detect_platform(self) -> ClientPlatform:
        """Detect the current platform"""
        system = platform.system().lower()
        if system == "windows":
            return ClientPlatform.WINDOWS
        elif system == "darwin":
            return ClientPlatform.MACOS
        elif system == "linux":
            return ClientPlatform.LINUX
        else:
            logger.warning(f"Unknown platform: {system}, defaulting to Linux")
            return ClientPlatform.LINUX
    
    def add_connection_callback(self, callback: Callable) -> None:
        """Add a callback for connection events"""
        self.connection_callbacks.append(callback)
    
    def add_data_callback(self, callback: Callable) -> None:
        """Add a callback for data events"""
        self.data_callbacks.append(callback)
    
    def remove_connection_callback(self, callback: Callable) -> None:
        """Remove a connection callback"""
        try:
            self.connection_callbacks.remove(callback)
        except ValueError:
            pass
    
    def remove_data_callback(self, callback: Callable) -> None:
        """Remove a data callback"""
        try:
            self.data_callbacks.remove(callback)
        except ValueError:
            pass


# Global RDP client instance
_rdp_client: Optional[RDPClient] = None


def get_rdp_client() -> RDPClient:
    """Get the global RDP client instance"""
    global _rdp_client
    if _rdp_client is None:
        _rdp_client = RDPClient()
    return _rdp_client


async def start_rdp_client():
    """Start the global RDP client"""
    client = get_rdp_client()
    await client.start()


async def stop_rdp_client():
    """Stop the global RDP client"""
    global _rdp_client
    if _rdp_client:
        await _rdp_client.stop()
        _rdp_client = None


if __name__ == "__main__":
    async def test_rdp_client():
        """Test the RDP client"""
        client = RDPClient()
        
        try:
            await client.start()
            
            # Create test config
            config = ClientConfig(
                server_host="localhost",
                server_port=3389,
                username="test_user",
                resolution=(1920, 1080)
            )
            
            # Test connection
            session_id = "test_session_123"
            connected = await client.connect(session_id, config)
            
            if connected:
                print(f"Connected to session: {session_id}")
                
                # Get connection status
                status = client.get_connection_status()
                print(f"Connection status: {status}")
                
                # Wait a bit
                await asyncio.sleep(10)
                
                # Disconnect
                await client.disconnect()
                
            else:
                print("Failed to connect")
                
        finally:
            await client.stop()
    
    # Run test
    asyncio.run(test_rdp_client())

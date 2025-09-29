# Path: RDP/client/rdp_client.py
# Lucid RDP Client - Client-side RDP connection management
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import os
import asyncio
import logging
import socket
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import subprocess
import platform

# Import from reorganized structure
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from sessions.core.session_generator import SecureSessionGenerator
from sessions.encryption.session_crypto import SessionCrypto
from RDP.security.trust_controller import TrustController
from user_content.wallet.user_wallet import UserWallet

logger = logging.getLogger(__name__)

# RDP Client Constants
DEFAULT_RDP_PORT = 3389
CONNECTION_TIMEOUT = 30  # seconds
HEARTBEAT_INTERVAL = 60  # seconds
MAX_RETRY_ATTEMPTS = 3
SUPPORTED_RDP_CLIENTS = ["mstsc", "rdesktop", "freerdp", "xfreerdp"]


class ConnectionStatus(Enum):
    """RDP connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class RDPClientType(Enum):
    """RDP client types"""
    WINDOWS_MSTSC = "mstsc"
    LINUX_RDESKTOP = "rdesktop"
    LINUX_FREERDP = "freerdp"
    CROSS_PLATFORM_XFREERDP = "xfreerdp"


@dataclass
class RDPConnectionInfo:
    """RDP connection information"""
    session_id: str
    node_address: str
    rdp_host: str
    rdp_port: int
    username: Optional[str] = None
    password: Optional[str] = None
    domain: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "node_address": self.node_address,
            "rdp_host": self.rdp_host,
            "rdp_port": self.rdp_port,
            "username": self.username,
            "domain": self.domain
            # Note: password not included for security
        }


class RDPClient:
    """
    RDP client for connecting to Lucid nodes.
    
    Handles:
    - RDP client detection and management
    - Secure connection establishment
    - Session authentication and encryption
    - Connection monitoring and recovery
    - Cross-platform RDP client support
    """
    
    def __init__(self, user_address: str):
        self.user_address = user_address
        self.user_wallet = UserWallet(user_address)
        
        # Components
        self.session_crypto = SessionCrypto()
        self.trust_controller = TrustController()
        
        # Connection state
        self.connection_info: Optional[RDPConnectionInfo] = None
        self.status = ConnectionStatus.DISCONNECTED
        self.client_type: Optional[RDPClientType] = None
        self.client_process: Optional[subprocess.Popen] = None
        
        # Session tracking
        self.current_session_id: Optional[str] = None
        self.connection_start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "connection_established": [],
            "connection_lost": [],
            "session_terminated": [],
            "authentication_failed": []
        }
        
        # Detect available RDP client
        self.client_type = self._detect_rdp_client()
        
        logger.info(f"RDP client initialized for user: {user_address}")
        logger.info(f"Detected RDP client: {self.client_type}")
    
    async def connect_to_session(self, session_id: str, node_address: str, 
                               connection_params: Dict[str, Any]) -> bool:
        """
        Connect to RDP session on node.
        
        Args:
            session_id: Session identifier
            node_address: Node operator address
            connection_params: Connection parameters
            
        Returns:
            True if connection successful
        """
        try:
            if self.status in [ConnectionStatus.CONNECTING, ConnectionStatus.CONNECTED]:
                logger.warning("Already connected or connecting")
                return False
            
            if not self.client_type:
                logger.error("No suitable RDP client found")
                return False
            
            self.status = ConnectionStatus.CONNECTING
            self.current_session_id = session_id
            
            # Extract connection parameters
            rdp_host = connection_params.get("rdp_host", node_address)
            rdp_port = connection_params.get("rdp_port", DEFAULT_RDP_PORT)
            username = connection_params.get("username", "lucid_user")
            password = connection_params.get("password")
            domain = connection_params.get("domain")
            
            # Create connection info
            self.connection_info = RDPConnectionInfo(
                session_id=session_id,
                node_address=node_address,
                rdp_host=rdp_host,
                rdp_port=rdp_port,
                username=username,
                password=password,
                domain=domain
            )
            
            # Verify node trust
            trust_score = await self.trust_controller.get_trust_score(node_address)
            if trust_score < 0.5:
                logger.error(f"Node trust score too low: {trust_score}")
                self.status = ConnectionStatus.ERROR
                return False
            
            # Test connectivity
            if not await self._test_connectivity(rdp_host, rdp_port):
                logger.error(f"Cannot reach RDP server: {rdp_host}:{rdp_port}")
                self.status = ConnectionStatus.ERROR
                return False
            
            # Launch RDP client
            success = await self._launch_rdp_client()
            
            if success:
                self.status = ConnectionStatus.CONNECTED
                self.connection_start_time = datetime.now(timezone.utc)
                self.last_heartbeat = self.connection_start_time
                
                # Start connection monitoring
                asyncio.create_task(self._monitor_connection())
                
                # Trigger connection established event
                await self._trigger_event("connection_established", {
                    "session_id": session_id,
                    "node_address": node_address,
                    "connection_info": self.connection_info.to_dict()
                })
                
                logger.info(f"RDP connection established: {session_id}")
                return True
            else:
                self.status = ConnectionStatus.ERROR
                self.connection_info = None
                return False
                
        except Exception as e:
            logger.error(f"RDP connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from RDP session"""
        try:
            if self.status == ConnectionStatus.DISCONNECTED:
                return True
            
            logger.info(f"Disconnecting from session: {self.current_session_id}")
            
            # Terminate RDP client process
            if self.client_process:
                try:
                    self.client_process.terminate()
                    
                    # Wait for process to terminate
                    try:
                        self.client_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logger.warning("RDP client did not terminate gracefully, killing...")
                        self.client_process.kill()
                        
                except Exception as e:
                    logger.error(f"Error terminating RDP client: {e}")
                
                self.client_process = None
            
            # Update status
            self.status = ConnectionStatus.DISCONNECTED
            
            # Trigger session terminated event
            if self.current_session_id:
                await self._trigger_event("session_terminated", {
                    "session_id": self.current_session_id,
                    "disconnected_at": datetime.now(timezone.utc)
                })
            
            # Clean up
            self.current_session_id = None
            self.connection_info = None
            self.connection_start_time = None
            self.last_heartbeat = None
            
            logger.info("RDP client disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        try:
            connection_duration = None
            if self.connection_start_time:
                connection_duration = (datetime.now(timezone.utc) - self.connection_start_time).total_seconds()
            
            return {
                "user_address": self.user_address,
                "status": self.status.value,
                "session_id": self.current_session_id,
                "client_type": self.client_type.value if self.client_type else None,
                "connection_info": self.connection_info.to_dict() if self.connection_info else None,
                "connection_start_time": self.connection_start_time,
                "connection_duration_seconds": connection_duration,
                "last_heartbeat": self.last_heartbeat,
                "client_process_running": self.client_process is not None and self.client_process.poll() is None
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection status: {e}")
            return {"error": str(e)}
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to maintain connection"""
        try:
            if self.status != ConnectionStatus.CONNECTED:
                return False
            
            # Simple heartbeat - just check if process is still running
            if self.client_process:
                if self.client_process.poll() is None:
                    self.last_heartbeat = datetime.now(timezone.utc)
                    return True
                else:
                    logger.warning("RDP client process has terminated")
                    self.status = ConnectionStatus.DISCONNECTED
                    await self._trigger_event("connection_lost", {
                        "session_id": self.current_session_id,
                        "lost_at": datetime.now(timezone.utc)
                    })
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False
    
    def _detect_rdp_client(self) -> Optional[RDPClientType]:
        """Detect available RDP client"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                # Windows has built-in mstsc
                return RDPClientType.WINDOWS_MSTSC
            
            elif system in ["linux", "darwin"]:  # Linux or macOS
                # Check for available RDP clients
                for client in ["xfreerdp", "freerdp", "rdesktop"]:
                    try:
                        result = subprocess.run(
                            ["which", client],
                            capture_output=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            if client == "xfreerdp":
                                return RDPClientType.CROSS_PLATFORM_XFREERDP
                            elif client == "freerdp":
                                return RDPClientType.LINUX_FREERDP
                            elif client == "rdesktop":
                                return RDPClientType.LINUX_RDESKTOP
                    except Exception:
                        continue
            
            logger.warning(f"No suitable RDP client found for system: {system}")
            return None
            
        except Exception as e:
            logger.error(f"RDP client detection failed: {e}")
            return None
    
    async def _test_connectivity(self, host: str, port: int) -> bool:
        """Test network connectivity to RDP server"""
        try:
            # Create socket connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CONNECTION_TIMEOUT)
            
            try:
                result = sock.connect_ex((host, port))
                return result == 0
            finally:
                sock.close()
                
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False
    
    async def _launch_rdp_client(self) -> bool:
        """Launch appropriate RDP client"""
        try:
            if not self.connection_info or not self.client_type:
                return False
            
            conn = self.connection_info
            
            if self.client_type == RDPClientType.WINDOWS_MSTSC:
                return await self._launch_mstsc(conn)
            
            elif self.client_type == RDPClientType.CROSS_PLATFORM_XFREERDP:
                return await self._launch_xfreerdp(conn)
            
            elif self.client_type == RDPClientType.LINUX_FREERDP:
                return await self._launch_freerdp(conn)
            
            elif self.client_type == RDPClientType.LINUX_RDESKTOP:
                return await self._launch_rdesktop(conn)
            
            else:
                logger.error(f"Unsupported RDP client type: {self.client_type}")
                return False
                
        except Exception as e:
            logger.error(f"RDP client launch failed: {e}")
            return False
    
    async def _launch_mstsc(self, conn: RDPConnectionInfo) -> bool:
        """Launch Windows mstsc client"""
        try:
            # Build mstsc command
            cmd = ["mstsc"]
            
            # Create temporary RDP file
            rdp_content = [
                f"full address:s:{conn.rdp_host}:{conn.rdp_port}",
                f"username:s:{conn.username or ''}",
                "screen mode id:i:2",  # Fullscreen
                "use multimon:i:0",
                "session bpp:i:32",
                "compression:i:1",
                "keyboardhook:i:2",
                "audiocapturemode:i:0",
                "videoplaybackmode:i:1",
                "connection type:i:7",
                "displayconnectionbar:i:1",
                "disable wallpaper:i:0",
                "allow font smoothing:i:0",
                "allow desktop composition:i:0",
                "disable full window drag:i:1",
                "disable menu anims:i:1",
                "disable themes:i:0",
                "disable cursor setting:i:0",
                "bitmapcachepersistenable:i:1",
                "autoreconnection enabled:i:1",
                "alternate shell:s:",
                "shell working directory:s:",
                "authentication level:i:0",
                "connect to console:i:0",
                "gatewayusagemethod:i:4",
                "disable wallpaper:i:1",
                "disable full window drag:i:1",
                "disable menu anims:i:1",
                "disable themes:i:1",
                "bitmapcachepersistenable:i:1"
            ]
            
            # Write RDP file
            rdp_file = Path.home() / f"lucid_session_{conn.session_id}.rdp"
            
            try:
                rdp_file.write_text('\n'.join(rdp_content))
                cmd.append(str(rdp_file))
                
                # Launch mstsc
                self.client_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                logger.info(f"Launched mstsc with PID: {self.client_process.pid}")
                return True
                
            finally:
                # Clean up RDP file after a delay
                asyncio.create_task(self._cleanup_temp_file(rdp_file, 30))
            
        except Exception as e:
            logger.error(f"mstsc launch failed: {e}")
            return False
    
    async def _launch_xfreerdp(self, conn: RDPConnectionInfo) -> bool:
        """Launch xfreerdp client"""
        try:
            cmd = [
                "xfreerdp",
                f"/v:{conn.rdp_host}:{conn.rdp_port}",
                f"/u:{conn.username or 'lucid_user'}",
                "/cert-ignore",
                "/compression",
                "/clipboard",
                "/auto-reconnect-max-retries:3",
                "/auto-reconnect:true",
                "/heartbeat",
                "/gfx-progressive",
                "/rfx"
            ]
            
            # Add password if provided
            if conn.password:
                cmd.append(f"/p:{conn.password}")
            
            # Add domain if provided
            if conn.domain:
                cmd.append(f"/d:{conn.domain}")
            
            # Launch xfreerdp
            self.client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Launched xfreerdp with PID: {self.client_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"xfreerdp launch failed: {e}")
            return False
    
    async def _launch_freerdp(self, conn: RDPConnectionInfo) -> bool:
        """Launch freerdp client"""
        try:
            cmd = [
                "freerdp",
                f"{conn.rdp_host}:{conn.rdp_port}",
                "-u", conn.username or "lucid_user",
                "-z",  # Enable compression
                "--ignore-certificate",
                "--plugin", "cliprdr",
                "--plugin", "rdpsnd"
            ]
            
            # Add password if provided
            if conn.password:
                cmd.extend(["-p", conn.password])
            
            # Add domain if provided
            if conn.domain:
                cmd.extend(["-d", conn.domain])
            
            # Launch freerdp
            self.client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Launched freerdp with PID: {self.client_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"freerdp launch failed: {e}")
            return False
    
    async def _launch_rdesktop(self, conn: RDPConnectionInfo) -> bool:
        """Launch rdesktop client"""
        try:
            cmd = [
                "rdesktop",
                f"{conn.rdp_host}:{conn.rdp_port}",
                "-u", conn.username or "lucid_user",
                "-z",  # Enable compression
                "-P",  # Enable bitmap caching
                "-x", "l",  # LAN connection type
                "-r", "clipboard:PRIMARYCLIPBOARD",
                "-r", "sound:local"
            ]
            
            # Add password if provided
            if conn.password:
                cmd.extend(["-p", conn.password])
            
            # Add domain if provided
            if conn.domain:
                cmd.extend(["-d", conn.domain])
            
            # Launch rdesktop
            self.client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Launched rdesktop with PID: {self.client_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"rdesktop launch failed: {e}")
            return False
    
    async def _monitor_connection(self):
        """Monitor RDP connection health"""
        try:
            while self.status == ConnectionStatus.CONNECTED:
                # Send heartbeat
                heartbeat_success = await self.send_heartbeat()
                
                if not heartbeat_success:
                    logger.warning("Heartbeat failed, connection may be lost")
                    break
                
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
        except Exception as e:
            logger.error(f"Connection monitoring failed: {e}")
    
    async def _cleanup_temp_file(self, file_path: Path, delay: int):
        """Clean up temporary file after delay"""
        try:
            await asyncio.sleep(delay)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup temp file: {e}")
    
    async def _trigger_event(self, event_name: str, data: Any):
        """Trigger event handlers"""
        try:
            handlers = self.event_handlers.get(event_name, [])
            for handler in handlers:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger event: {e}")
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """Add event handler"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)


# Global RDP client instances
_rdp_clients: Dict[str, RDPClient] = {}


def get_rdp_client(user_address: str) -> RDPClient:
    """Get RDP client instance for user"""
    global _rdp_clients
    
    if user_address not in _rdp_clients:
        _rdp_clients[user_address] = RDPClient(user_address)
    
    return _rdp_clients[user_address]


async def cleanup_rdp_clients():
    """Cleanup all RDP client instances"""
    global _rdp_clients
    
    for client in _rdp_clients.values():
        await client.disconnect()
    
    _rdp_clients.clear()
    logger.info("RDP clients cleaned up")


if __name__ == "__main__":
    # Test RDP client
    async def test_rdp_client():
        print("Testing Lucid RDP Client...")
        
        # Test with sample user address
        test_user = "TTestUserAddress123456789012345"
        client = get_rdp_client(test_user)
        
        # Get connection status
        status = await client.get_connection_status()
        print(f"Connection status: {status}")
        
        # Test connection (will fail without real server)
        connection_params = {
            "rdp_host": "127.0.0.1",
            "rdp_port": 3389,
            "username": "test_user",
            "password": "test_pass"
        }
        
        try:
            connected = await client.connect_to_session(
                session_id="test_session_123",
                node_address="TTestNodeAddress123456789012345",
                connection_params=connection_params
            )
            print(f"Connection result: {connected}")
        except Exception as e:
            print(f"Connection failed (expected): {e}")
        
        # Get updated status
        status = await client.get_connection_status()
        print(f"Final status: {status}")
        
        print("Test completed")
    
    asyncio.run(test_rdp_client())
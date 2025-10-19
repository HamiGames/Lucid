#!/usr/bin/env python3
"""
LUCID RDP Server Manager - SPEC-1B Implementation
Manages RDP server instances and session hosting
"""

import asyncio
import logging
import time
import subprocess
import psutil
import socket
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import threading
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RDPStatus(Enum):
    """RDP server status"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class SessionType(Enum):
    """RDP session type"""
    USER_SESSION = "user_session"
    ADMIN_SESSION = "admin_session"
    GUEST_SESSION = "guest_session"

@dataclass
class RDPConfig:
    """RDP server configuration"""
    base_port: int = 3389
    max_servers: int = 10
    session_timeout_minutes: int = 480  # 8 hours
    server_startup_timeout: int = 30
    xrdp_config_path: str = "/etc/xrdp"
    xrdp_log_path: str = "/var/log/xrdp"
    desktop_environment: str = "xfce4"
    resolution: str = "1920x1080"
    color_depth: int = 16
    encryption_level: str = "high"

@dataclass
class RDPServer:
    """RDP server instance"""
    server_id: str
    port: int
    session_id: str
    user_id: str
    status: RDPStatus
    config: Dict[str, Any]
    process_id: Optional[int] = None
    start_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    connection_count: int = 0
    error_message: Optional[str] = None

@dataclass
class RDPConnection:
    """RDP connection information"""
    connection_id: str
    server_id: str
    client_ip: str
    client_port: int
    connected_at: datetime
    last_activity: datetime
    session_type: SessionType
    is_active: bool = True

class RDPServerManager:
    """
    LUCID RDP Server Manager
    
    Manages RDP server instances with:
    1. Dynamic server creation and destruction
    2. Port management and allocation
    3. Session monitoring and cleanup
    4. Resource usage tracking
    5. XRDP integration
    """
    
    def __init__(self, config: RDPConfig):
        self.config = config
        self.servers: Dict[str, RDPServer] = {}
        self.connections: Dict[str, RDPConnection] = {}
        self.available_ports: List[int] = []
        self.used_ports: set = set()
        self.monitoring_active = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Initialize available ports
        self._initialize_ports()
        
    def _initialize_ports(self):
        """Initialize available port pool"""
        self.available_ports = list(range(
            self.config.base_port,
            self.config.base_port + self.config.max_servers
        ))
        
    async def initialize(self) -> bool:
        """
        Initialize RDP server manager
        
        Returns:
            success: True if initialization successful
        """
        try:
            logger.info("Initializing RDP server manager")
            
            # Check XRDP installation
            if not await self._check_xrdp_installation():
                logger.error("XRDP not installed or not accessible")
                return False
            
            # Start monitoring
            self.monitoring_active = True
            self.cleanup_task = asyncio.create_task(self._cleanup_monitor())
            
            logger.info("RDP server manager initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RDP server manager: {e}")
            return False
    
    async def _check_xrdp_installation(self) -> bool:
        """Check if XRDP is installed and accessible"""
        try:
            # Check if xrdp service exists
            result = subprocess.run(
                ["systemctl", "is-active", "xrdp"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("XRDP service is active")
                return True
            else:
                logger.warning("XRDP service is not active")
                
                # Try to start XRDP service
                start_result = subprocess.run(
                    ["sudo", "systemctl", "start", "xrdp"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if start_result.returncode == 0:
                    logger.info("XRDP service started successfully")
                    return True
                else:
                    logger.error(f"Failed to start XRDP service: {start_result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to check XRDP installation: {e}")
            return False
    
    async def create_server(self, session_id: str, user_id: str, session_config: Dict[str, Any]) -> Optional[str]:
        """
        Create new RDP server instance
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            session_config: Session configuration
            
        Returns:
            server_id: Created server identifier or None if failed
        """
        try:
            # Check server limit
            if len(self.servers) >= self.config.max_servers:
                logger.warning(f"Maximum server limit reached: {self.config.max_servers}")
                return None
            
            # Get available port
            if not self.available_ports:
                logger.warning("No available ports for new RDP server")
                return None
            
            port = self.available_ports.pop(0)
            self.used_ports.add(port)
            
            # Generate server ID
            server_id = f"rdp_server_{session_id}_{int(time.time())}"
            
            # Create server configuration
            server_config = {
                "session_id": session_id,
                "user_id": user_id,
                "port": port,
                "desktop_environment": session_config.get("desktop_environment", self.config.desktop_environment),
                "resolution": session_config.get("resolution", self.config.resolution),
                "color_depth": session_config.get("color_depth", self.config.color_depth),
                "encryption_level": session_config.get("encryption_level", self.config.encryption_level)
            }
            
            # Create server instance
            server = RDPServer(
                server_id=server_id,
                port=port,
                session_id=session_id,
                user_id=user_id,
                status=RDPStatus.STARTING,
                config=server_config
            )
            
            self.servers[server_id] = server
            
            # Start RDP server
            success = await self._start_rdp_server(server)
            
            if success:
                server.status = RDPStatus.RUNNING
                server.start_time = datetime.utcnow()
                server.last_activity = datetime.utcnow()
                
                logger.info(f"RDP server {server_id} created on port {port}")
                return server_id
            else:
                # Cleanup failed server
                del self.servers[server_id]
                self.available_ports.append(port)
                self.used_ports.discard(port)
                
                logger.error(f"Failed to start RDP server {server_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create RDP server: {e}")
            return None
    
    async def _start_rdp_server(self, server: RDPServer) -> bool:
        """Start RDP server process"""
        try:
            # Create XRDP session configuration
            session_config_path = f"/etc/xrdp/sesman.ini"
            
            # Start XRDP session
            cmd = [
                "xrdp-sesman",
                "--config", session_config_path,
                "--port", str(server.port),
                "--desktop", server.config["desktop_environment"],
                "--geometry", server.config["resolution"],
                "--depth", str(server.config["color_depth"])
            ]
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            server.process_id = process.pid
            
            # Wait for server to start
            await asyncio.sleep(2)
            
            # Check if process is running
            if process.poll() is None:
                logger.info(f"RDP server {server.server_id} started with PID {process.pid}")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"RDP server failed to start: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start RDP server process: {e}")
            return False
    
    async def stop_server(self, server_id: str) -> bool:
        """
        Stop RDP server instance
        
        Args:
            server_id: Server identifier
            
        Returns:
            success: True if stopped successfully
        """
        try:
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} not found")
                return False
            
            server = self.servers[server_id]
            
            if server.status == RDPStatus.STOPPED:
                logger.info(f"Server {server_id} already stopped")
                return True
            
            server.status = RDPStatus.STOPPING
            
            # Stop server process
            if server.process_id:
                try:
                    process = psutil.Process(server.process_id)
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        # Force kill if needed
                        process.kill()
                        process.wait()
                    
                    logger.info(f"RDP server {server_id} process stopped")
                    
                except psutil.NoSuchProcess:
                    logger.warning(f"Process {server.process_id} not found")
                except Exception as e:
                    logger.error(f"Failed to stop process {server.process_id}: {e}")
            
            # Cleanup connections
            await self._cleanup_server_connections(server_id)
            
            # Release port
            if server.port in self.used_ports:
                self.used_ports.discard(server.port)
                self.available_ports.append(server.port)
            
            # Update server status
            server.status = RDPStatus.STOPPED
            server.process_id = None
            
            logger.info(f"RDP server {server_id} stopped successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop RDP server {server_id}: {e}")
            return False
    
    async def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Get RDP server information
        
        Args:
            server_id: Server identifier
            
        Returns:
            server_info: Server information or None if not found
        """
        if server_id not in self.servers:
            return None
        
        server = self.servers[server_id]
        
        # Get process info
        process_info = None
        if server.process_id:
            try:
                process = psutil.Process(server.process_id)
                process_info = {
                    "pid": process.pid,
                    "cpu_percent": process.cpu_percent(),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "status": process.status(),
                    "create_time": datetime.fromtimestamp(process.create_time())
                }
            except psutil.NoSuchProcess:
                process_info = {"error": "Process not found"}
        
        # Get connection info
        server_connections = [
            conn for conn in self.connections.values()
            if conn.server_id == server_id and conn.is_active
        ]
        
        return {
            "server_id": server.server_id,
            "session_id": server.session_id,
            "user_id": server.user_id,
            "port": server.port,
            "status": server.status.value,
            "config": server.config,
            "process_info": process_info,
            "start_time": server.start_time.isoformat() if server.start_time else None,
            "last_activity": server.last_activity.isoformat() if server.last_activity else None,
            "connection_count": len(server_connections),
            "connections": [
                {
                    "connection_id": conn.connection_id,
                    "client_ip": conn.client_ip,
                    "connected_at": conn.connected_at.isoformat(),
                    "session_type": conn.session_type.value
                }
                for conn in server_connections
            ],
            "error_message": server.error_message
        }
    
    async def get_all_servers(self) -> List[Dict[str, Any]]:
        """Get information for all RDP servers"""
        server_infos = []
        for server_id in self.servers:
            server_info = await self.get_server_info(server_id)
            if server_info:
                server_infos.append(server_info)
        return server_infos
    
    async def add_connection(self, server_id: str, client_ip: str, client_port: int, session_type: SessionType) -> Optional[str]:
        """
        Add new connection to server
        
        Args:
            server_id: Server identifier
            client_ip: Client IP address
            client_port: Client port
            session_type: Type of session
            
        Returns:
            connection_id: Connection identifier or None if failed
        """
        try:
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} not found")
                return None
            
            server = self.servers[server_id]
            
            if server.status != RDPStatus.RUNNING:
                logger.warning(f"Server {server_id} is not running")
                return None
            
            # Create connection
            connection_id = f"conn_{server_id}_{int(time.time())}"
            connection = RDPConnection(
                connection_id=connection_id,
                server_id=server_id,
                client_ip=client_ip,
                client_port=client_port,
                connected_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                session_type=session_type
            )
            
            self.connections[connection_id] = connection
            
            # Update server connection count
            server.connection_count += 1
            server.last_activity = datetime.utcnow()
            
            logger.info(f"Connection {connection_id} added to server {server_id}")
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to add connection: {e}")
            return None
    
    async def remove_connection(self, connection_id: str) -> bool:
        """
        Remove connection
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            success: True if removed successfully
        """
        try:
            if connection_id not in self.connections:
                logger.warning(f"Connection {connection_id} not found")
                return False
            
            connection = self.connections[connection_id]
            
            # Update server connection count
            if connection.server_id in self.servers:
                server = self.servers[connection.server_id]
                server.connection_count = max(0, server.connection_count - 1)
            
            # Remove connection
            del self.connections[connection_id]
            
            logger.info(f"Connection {connection_id} removed")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove connection: {e}")
            return False
    
    async def _cleanup_server_connections(self, server_id: str):
        """Cleanup all connections for a server"""
        connections_to_remove = [
            conn_id for conn_id, conn in self.connections.items()
            if conn.server_id == server_id
        ]
        
        for conn_id in connections_to_remove:
            await self.remove_connection(conn_id)
    
    async def _cleanup_monitor(self):
        """Monitor and cleanup inactive servers and connections"""
        while self.monitoring_active:
            try:
                await self._cleanup_inactive_sessions()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Cleanup monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_inactive_sessions(self):
        """Cleanup inactive sessions"""
        try:
            current_time = datetime.utcnow()
            timeout_delta = timedelta(minutes=self.config.session_timeout_minutes)
            
            # Find inactive servers
            inactive_servers = []
            for server_id, server in self.servers.items():
                if (server.last_activity and 
                    current_time - server.last_activity > timeout_delta):
                    inactive_servers.append(server_id)
            
            # Stop inactive servers
            for server_id in inactive_servers:
                logger.info(f"Stopping inactive server {server_id}")
                await self.stop_server(server_id)
            
            # Find inactive connections
            inactive_connections = []
            for conn_id, connection in self.connections.items():
                if (current_time - connection.last_activity > timedelta(minutes=30)):
                    inactive_connections.append(conn_id)
            
            # Remove inactive connections
            for conn_id in inactive_connections:
                logger.info(f"Removing inactive connection {conn_id}")
                await self.remove_connection(conn_id)
            
            if inactive_servers or inactive_connections:
                logger.info(f"Cleanup completed: {len(inactive_servers)} servers, {len(inactive_connections)} connections")
                
        except Exception as e:
            logger.error(f"Failed to cleanup inactive sessions: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get RDP manager status"""
        active_servers = sum(1 for server in self.servers.values() if server.status == RDPStatus.RUNNING)
        active_connections = sum(1 for conn in self.connections.values() if conn.is_active)
        
        return {
            "total_servers": len(self.servers),
            "active_servers": active_servers,
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "available_ports": len(self.available_ports),
            "used_ports": len(self.used_ports),
            "max_servers": self.config.max_servers,
            "monitoring_active": self.monitoring_active,
            "config": asdict(self.config)
        }
    
    async def shutdown(self):
        """Shutdown RDP server manager"""
        try:
            logger.info("Shutting down RDP server manager")
            
            self.monitoring_active = False
            
            # Stop cleanup task
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Stop all servers
            for server_id in list(self.servers.keys()):
                await self.stop_server(server_id)
            
            logger.info("RDP server manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Failed to shutdown RDP server manager: {e}")

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize RDP server manager
        config = RDPConfig(
            base_port=3389,
            max_servers=5,
            session_timeout_minutes=480,
            desktop_environment="xfce4"
        )
        
        manager = RDPServerManager(config)
        
        # Initialize
        success = await manager.initialize()
        print(f"RDP manager initialized: {success}")
        
        if success:
            # Create a test server
            session_config = {
                "desktop_environment": "xfce4",
                "resolution": "1920x1080",
                "color_depth": 16
            }
            
            server_id = await manager.create_server("session_123", "user_456", session_config)
            print(f"Server created: {server_id}")
            
            if server_id:
                # Get server info
                server_info = await manager.get_server_info(server_id)
                print(f"Server info: {json.dumps(server_info, indent=2, default=str)}")
                
                # Add a connection
                connection_id = await manager.add_connection(
                    server_id, "192.168.1.100", 12345, SessionType.USER_SESSION
                )
                print(f"Connection added: {connection_id}")
                
                # Wait a bit
                await asyncio.sleep(5)
                
                # Get manager status
                status = manager.get_manager_status()
                print(f"Manager status: {json.dumps(status, indent=2, default=str)}")
                
                # Stop server
                stopped = await manager.stop_server(server_id)
                print(f"Server stopped: {stopped}")
            
            # Shutdown
            await manager.shutdown()
            print("Manager shutdown completed")
    
    asyncio.run(main())
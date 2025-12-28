# LUCID RDP Server Manager - Server Lifecycle Management
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ServerStatus(Enum):
    """RDP server status states"""
    CREATING = "creating"
    CONFIGURING = "configuring"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"

@dataclass
class RDPServer:
    """RDP server instance"""
    server_id: str
    user_id: str
    session_id: str
    port: int
    status: ServerStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    display_config: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    connection_info: Dict[str, Any] = field(default_factory=dict)
    process: Optional[subprocess.Popen] = None
    config_path: Optional[Path] = None
    log_path: Optional[Path] = None

class RDPServerManager:
    """
    RDP server lifecycle management for Lucid system.
    
    Manages RDP server instances, port allocation, and resource management.
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self, config_manager, port_manager):
        """Initialize RDP server manager"""
        self.config_manager = config_manager
        self.port_manager = port_manager
        
        # Server tracking
        self.active_servers: Dict[str, RDPServer] = {}
        self.server_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration - use writable locations in distroless container
        self.base_config_path = Path("/var/lib/lucid/xrdp/servers")
        self.base_log_path = Path("/var/lib/lucid/logs/xrdp/servers")
        self.base_session_path = Path("/var/lib/lucid/sessions")
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [self.base_config_path, self.base_log_path, self.base_session_path]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
    async def initialize(self) -> None:
        """Initialize server manager"""
        logger.info("Initializing RDP Server Manager...")
        
        # Load existing servers from database
        await self._load_existing_servers()
        
        logger.info("RDP Server Manager initialized")
    
    async def _load_existing_servers(self) -> None:
        """Load existing servers from database"""
        # TODO: Implement database loading
        logger.info("Loading existing servers...")
    
    async def create_server(self, 
                           user_id: str, 
                           session_id: str,
                           display_config: Optional[Dict[str, Any]] = None,
                           resource_limits: Optional[Dict[str, Any]] = None) -> RDPServer:
        """Create new RDP server instance"""
        try:
            # Generate server ID
            server_id = f"rdp_{uuid.uuid4().hex[:8]}"
            
            # Allocate port
            port = await self.port_manager.allocate_port()
            if not port:
                raise Exception("No available ports")
            
            # Create server object
            server = RDPServer(
                server_id=server_id,
                user_id=user_id,
                session_id=session_id,
                port=port,
                status=ServerStatus.CREATING,
                created_at=datetime.now(timezone.utc),
                display_config=display_config or {},
                resource_limits=resource_limits or {}
            )
            
            # Store server
            self.active_servers[server_id] = server
            
            # Create server configuration
            await self._create_server_config(server)
            
            # Update status
            server.status = ServerStatus.CONFIGURING
            
            logger.info(f"Created RDP server: {server_id} on port {port}")
            
            return server
            
        except Exception as e:
            logger.error(f"Server creation failed: {e}")
            # Cleanup on failure
            if server_id in self.active_servers:
                await self.port_manager.release_port(port)
                del self.active_servers[server_id]
            raise
    
    async def _create_server_config(self, server: RDPServer) -> None:
        """Create server-specific configuration"""
        try:
            # Create server directories
            server.config_path = self.base_config_path / server.server_id
            server.log_path = self.base_log_path / server.server_id
            server.session_path = self.base_session_path / server.server_id
            
            for path in [server.config_path, server.log_path, server.session_path]:
                path.mkdir(parents=True, exist_ok=True)
            
            # Generate XRDP configuration
            config_file = server.config_path / "xrdp.ini"
            config_content = await self._generate_xrdp_config(server)
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            # Generate session configuration
            session_config = await self._generate_session_config(server)
            session_file = server.config_path / "session.ini"
            
            with open(session_file, 'w') as f:
                f.write(session_config)
            
            logger.info(f"Created server configuration: {server.server_id}")
            
        except Exception as e:
            logger.error(f"Server configuration creation failed: {e}")
            raise
    
    async def _generate_xrdp_config(self, server: RDPServer) -> str:
        """Generate XRDP configuration for server"""
        config = f"""[globals]
bitmap_cache=true
bitmap_compression=true
port={server.port}
crypt_level=high
channel_code=1
max_bpp=24
use_fastpath=both

[security]
allow_root_login=false
max_login_attempts=3
login_timeout=60
ssl_protocols=TLSv1.2,TLSv1.3
certificate_path={server.config_path}/server.crt
key_path={server.config_path}/server.key

[channels]
rdpdr=true
rdpsnd=true
drdynvc=true
cliprdr=true
rail=true

[logging]
log_file={server.log_path}/xrdp.log
log_level=INFO
enable_syslog=false

[display]
display_server=wayland
session_path={server.session_path}
"""
        
        # Add display configuration
        if server.display_config:
            config += f"""
[display_config]
resolution={server.display_config.get('resolution', '1920x1080')}
color_depth={server.display_config.get('color_depth', '24')}
"""
        
        # Add resource limits
        if server.resource_limits:
            config += f"""
[resource_limits]
max_cpu={server.resource_limits.get('max_cpu', '80')}
max_memory={server.resource_limits.get('max_memory', '1024')}
max_bandwidth={server.resource_limits.get('max_bandwidth', '1000')}
"""
        
        return config
    
    async def _generate_session_config(self, server: RDPServer) -> str:
        """Generate session configuration"""
        config = f"""[session]
server_id={server.server_id}
user_id={server.user_id}
session_id={server.session_id}
port={server.port}
created_at={server.created_at.isoformat()}

[environment]
DISPLAY=:0
WAYLAND_DISPLAY=wayland-0
XDG_RUNTIME_DIR=/tmp/runtime-{server.server_id}

[security]
session_timeout=3600
idle_timeout=1800
max_connections=1
"""
        
        return config
    
    async def start_server(self, server_id: str) -> Dict[str, Any]:
        """Start RDP server"""
        if server_id not in self.active_servers:
            raise Exception("Server not found")
        
        server = self.active_servers[server_id]
        
        try:
            server.status = ServerStatus.STARTING
            logger.info(f"Starting RDP server: {server_id}")
            
            # Start XRDP process
            cmd = [
                "xrdp",
                "--port", str(server.port),
                "--config", str(server.config_path / "xrdp.ini"),
                "--session-path", str(server.session_path),
                "--log-file", str(server.log_path / "xrdp.log")
            ]
            
            # Start process
            server.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(server.session_path)
            )
            
            # Wait for startup
            await asyncio.sleep(3)
            
            # Check if process is running
            if server.process.poll() is None:
                server.status = ServerStatus.RUNNING
                server.started_at = datetime.now(timezone.utc)
                
                # Generate connection info
                # Host should be the service name, not localhost (for external connections)
                # Use RDP_SERVER_MANAGER_HOST from environment (set by docker-compose)
                rdp_host = os.getenv("RDP_SERVER_MANAGER_HOST", "rdp-server-manager")
                server.connection_info = {
                    "host": rdp_host,  # Service name for Docker network connections
                    "port": server.port,
                    "username": f"lucid_{server.server_id[:8]}",
                    "password": f"lucid_{server.server_id[-8:]}",
                    "session_id": server.session_id
                }
                
                # Start monitoring task
                task = asyncio.create_task(self._monitor_server(server))
                self.server_tasks[server_id] = task
                
                logger.info(f"RDP server started: {server_id} on port {server.port}")
                
                return {
                    "server_id": server_id,
                    "status": server.status.value,
                    "port": server.port,
                    "started_at": server.started_at.isoformat(),
                    "connection_info": server.connection_info
                }
            else:
                server.status = ServerStatus.FAILED
                logger.error(f"RDP server failed to start: {server_id}")
                return {"status": "failed", "message": "Server failed to start"}
                
        except Exception as e:
            server.status = ServerStatus.FAILED
            logger.error(f"Server start failed: {e}")
            raise
    
    async def stop_server(self, server_id: str) -> Dict[str, Any]:
        """Stop RDP server"""
        if server_id not in self.active_servers:
            raise Exception("Server not found")
        
        server = self.active_servers[server_id]
        
        try:
            server.status = ServerStatus.STOPPING
            logger.info(f"Stopping RDP server: {server_id}")
            
            # Cancel monitoring task
            if server_id in self.server_tasks:
                self.server_tasks[server_id].cancel()
                del self.server_tasks[server_id]
            
            # Stop process
            if server.process:
                server.process.terminate()
                try:
                    server.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.process.kill()
                    server.process.wait()
                server.process = None
            
            server.status = ServerStatus.STOPPED
            server.stopped_at = datetime.now(timezone.utc)
            
            # Release port
            await self.port_manager.release_port(server.port)
            
            logger.info(f"RDP server stopped: {server_id}")
            
            return {
                "server_id": server_id,
                "status": server.status.value,
                "stopped_at": server.stopped_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Server stop failed: {e}")
            raise
    
    async def restart_server(self, server_id: str) -> Dict[str, Any]:
        """Restart RDP server"""
        await self.stop_server(server_id)
        await asyncio.sleep(2)
        return await self.start_server(server_id)
    
    async def delete_server(self, server_id: str) -> Dict[str, Any]:
        """Delete RDP server"""
        if server_id not in self.active_servers:
            raise Exception("Server not found")
        
        server = self.active_servers[server_id]
        
        try:
            # Stop server if running
            if server.status == ServerStatus.RUNNING:
                await self.stop_server(server_id)
            
            # Cleanup files
            await self._cleanup_server_files(server)
            
            # Remove from tracking
            del self.active_servers[server_id]
            
            logger.info(f"RDP server deleted: {server_id}")
            
            return {
                "server_id": server_id,
                "status": "deleted",
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Server deletion failed: {e}")
            raise
    
    async def _cleanup_server_files(self, server: RDPServer) -> None:
        """Cleanup server files"""
        try:
            import shutil
            
            # Remove server directories
            for path in [server.config_path, server.log_path, server.session_path]:
                if path and path.exists():
                    shutil.rmtree(path)
            
            logger.info(f"Cleaned up server files: {server.server_id}")
            
        except Exception as e:
            logger.error(f"Server cleanup failed: {e}")
    
    async def _monitor_server(self, server: RDPServer) -> None:
        """Monitor server health and resource usage"""
        try:
            while server.status == ServerStatus.RUNNING:
                # Check process status
                if server.process and server.process.poll() is not None:
                    server.status = ServerStatus.FAILED
                    logger.error(f"RDP server process died: {server.server_id}")
                    break
                
                # Update resource usage
                await self._update_resource_usage(server)
                
                # Sleep between checks
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info(f"Server monitoring cancelled: {server.server_id}")
        except Exception as e:
            logger.error(f"Server monitoring error: {e}")
            server.status = ServerStatus.FAILED
    
    async def _update_resource_usage(self, server: RDPServer) -> None:
        """Update server resource usage"""
        try:
            # TODO: Implement actual resource monitoring
            server.resource_usage = {
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "network_mbps": 0.0,
                "disk_mb": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Resource usage update failed: {e}")
    
    async def get_server(self, server_id: str) -> Optional[RDPServer]:
        """Get server by ID"""
        return self.active_servers.get(server_id)
    
    async def list_servers(self) -> List[RDPServer]:
        """List all active servers"""
        return list(self.active_servers.values())
    
    async def shutdown(self) -> None:
        """Shutdown server manager"""
        logger.info("Shutting down RDP Server Manager...")
        
        # Stop all servers
        for server_id in list(self.active_servers.keys()):
            try:
                await self.stop_server(server_id)
            except Exception as e:
                logger.error(f"Failed to stop server {server_id}: {e}")
        
        logger.info("RDP Server Manager shutdown complete")

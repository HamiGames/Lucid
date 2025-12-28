# LUCID XRDP Configuration Manager - XRDP Configuration Management
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

from __future__ import annotations

import asyncio
import logging
import os
import ssl
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigFormat(Enum):
    """Configuration file formats"""
    INI = "ini"
    JSON = "json"
    YAML = "yaml"

class SecurityLevel(Enum):
    """Security levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"

@dataclass
class XRDPConfig:
    """XRDP configuration settings"""
    port: int
    config_path: Path
    log_path: Path
    session_path: Path
    security_level: SecurityLevel
    ssl_enabled: bool
    ssl_cert_path: Optional[Path] = None
    ssl_key_path: Optional[Path] = None
    display_server: str = "wayland"
    hardware_acceleration: bool = True
    max_connections: int = 10
    session_timeout: int = 3600
    idle_timeout: int = 1800

class XRDPConfigManager:
    """
    XRDP configuration manager for Lucid system.
    
    Manages XRDP service configuration, SSL certificates, and security settings.
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self):
        """Initialize XRDP config manager"""
        # Use writable volume mount locations (/app/config and /app/logs are volume mounts)
        self.config_path = Path("/app/config")
        self.log_path = Path("/app/logs")
        self.session_path = Path("/app/config/sessions")  # Sessions under config since no /app/data mount
        self.ssl_path = Path("/app/config/ssl")
        
        # Configuration templates
        self.config_templates: Dict[str, str] = {}
        
        # Initialize templates
        self._initialize_templates()
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [self.config_path, self.log_path, self.session_path, self.ssl_path]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
    def _initialize_templates(self) -> None:
        """Initialize configuration templates"""
        
        # Main XRDP configuration template
        self.config_templates["xrdp.ini"] = """[globals]
bitmap_cache=true
bitmap_compression=true
port={port}
crypt_level={crypt_level}
channel_code=1
max_bpp=24
use_fastpath=both
tcp_nodelay=true
tcp_keepalive=true

[security]
allow_root_login=false
max_login_attempts=3
login_timeout=60
ssl_protocols={ssl_protocols}
certificate_path={cert_path}
key_path={key_path}
require_certificate=true

[channels]
rdpdr=true
rdpsnd=true
drdynvc=true
cliprdr=true
rail=true
rdpsnd_priority=2

[logging]
log_file={log_file}
log_level=INFO
enable_syslog=false
log_audit=true

[display]
display_server={display_server}
session_path={session_path}
default_window_manager=weston
"""
        
        # Session configuration template
        self.config_templates["session.ini"] = """[session]
server_id={server_id}
user_id={user_id}
session_id={session_id}
port={port}
created_at={created_at}
display={display}

[environment]
DISPLAY={display}
WAYLAND_DISPLAY={wayland_display}
XDG_RUNTIME_DIR={runtime_dir}
XDG_SESSION_TYPE=wayland
XDG_CURRENT_DESKTOP=weston

[security]
session_timeout={session_timeout}
idle_timeout={idle_timeout}
max_connections={max_connections}
require_authentication=true

[display_config]
resolution={resolution}
color_depth={color_depth}
refresh_rate={refresh_rate}
hardware_acceleration={hardware_acceleration}
"""
        
        # SSL configuration template
        self.config_templates["ssl.conf"] = """[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = California
L = San Francisco
O = Lucid Blockchain
OU = RDP Services
CN = {hostname}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = {hostname}
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = {server_ip}
"""
    
    async def initialize(self) -> None:
        """Initialize XRDP config manager"""
        logger.info("Initializing XRDP Config Manager...")
        
        # Generate SSL certificates if needed
        await self._ensure_ssl_certificates()
        
        logger.info("XRDP Config Manager initialized")
    
    async def _ensure_ssl_certificates(self) -> None:
        """Ensure SSL certificates exist"""
        try:
            cert_file = self.ssl_path / "server.crt"
            key_file = self.ssl_path / "server.key"
            
            if not cert_file.exists() or not key_file.exists():
                await self._generate_ssl_certificates()
            
            logger.info("SSL certificates verified")
            
        except Exception as e:
            logger.error(f"SSL certificate setup failed: {e}")
    
    async def _generate_ssl_certificates(self) -> None:
        """Generate SSL certificates"""
        try:
            # Generate private key
            key_cmd = [
                "openssl", "genrsa", "-out", str(self.ssl_path / "server.key"), "2048"
            ]
            subprocess.run(key_cmd, check=True, capture_output=True)
            
            # Generate certificate signing request
            csr_file = self.ssl_path / "server.csr"
            conf_file = self.ssl_path / "ssl.conf"
            
            # Create SSL configuration
            hostname = os.getenv("XRDP_HOSTNAME", os.getenv("RDP_XRDP_HOST", "rdp-xrdp"))
            # For SSL cert, use actual bind address (0.0.0.0 maps to container's IP)
            # But for certificate, we include localhost and service name
            server_ip = os.getenv("XRDP_SERVER_IP", "127.0.0.1")  # Default to localhost for cert SAN (required for SSL cert)
            ssl_config = self.config_templates["ssl.conf"].format(
                hostname=hostname,
                server_ip=server_ip
            )
            
            with open(conf_file, 'w') as f:
                f.write(ssl_config)
            
            # Generate CSR
            csr_cmd = [
                "openssl", "req", "-new", "-key", str(self.ssl_path / "server.key"),
                "-out", str(csr_file), "-config", str(conf_file)
            ]
            subprocess.run(csr_cmd, check=True, capture_output=True)
            
            # Generate self-signed certificate
            cert_cmd = [
                "openssl", "x509", "-req", "-days", "365",
                "-in", str(csr_file), "-signkey", str(self.ssl_path / "server.key"),
                "-out", str(self.ssl_path / "server.crt"), "-extensions", "v3_req",
                "-extfile", str(conf_file)
            ]
            subprocess.run(cert_cmd, check=True, capture_output=True)
            
            # Set permissions
            os.chmod(self.ssl_path / "server.key", 0o600)
            os.chmod(self.ssl_path / "server.crt", 0o644)
            
            # Cleanup
            csr_file.unlink()
            conf_file.unlink()
            
            logger.info("SSL certificates generated")
            
        except Exception as e:
            logger.error(f"SSL certificate generation failed: {e}")
            raise
    
    async def create_server_config(self, 
                                  server_id: str,
                                  port: int,
                                  user_id: str,
                                  session_id: str,
                                  display_config: Optional[Dict[str, Any]] = None,
                                  security_level: SecurityLevel = SecurityLevel.HIGH) -> XRDPConfig:
        """Create XRDP configuration for server"""
        try:
            # Create server-specific directories
            server_config_path = self.config_path / server_id
            server_log_path = self.log_path / server_id
            server_session_path = self.session_path / server_id
            
            for path in [server_config_path, server_log_path, server_session_path]:
                path.mkdir(parents=True, exist_ok=True)
            
            # Create XRDP configuration
            xrdp_config = XRDPConfig(
                port=port,
                config_path=server_config_path,
                log_path=server_log_path,
                session_path=server_session_path,
                security_level=security_level,
                ssl_enabled=True,
                ssl_cert_path=self.ssl_path / "server.crt",
                ssl_key_path=self.ssl_path / "server.key",
                display_server=display_config.get("display_server", "wayland") if display_config else "wayland",
                hardware_acceleration=display_config.get("hardware_acceleration", True) if display_config else True,
                max_connections=1,  # Single user per server
                session_timeout=3600,
                idle_timeout=1800
            )
            
            # Generate configuration files
            await self._generate_xrdp_ini(xrdp_config)
            await self._generate_session_ini(xrdp_config, user_id, session_id, display_config)
            
            logger.info(f"Created XRDP configuration for server: {server_id}")
            
            return xrdp_config
            
        except Exception as e:
            logger.error(f"XRDP configuration creation failed: {e}")
            raise
    
    async def _generate_xrdp_ini(self, config: XRDPConfig) -> None:
        """Generate XRDP INI configuration"""
        try:
            # Map security levels
            crypt_levels = {
                SecurityLevel.LOW: "low",
                SecurityLevel.MEDIUM: "medium", 
                SecurityLevel.HIGH: "high",
                SecurityLevel.MAXIMUM: "maximum"
            }
            
            ssl_protocols = {
                SecurityLevel.LOW: "TLSv1.0,TLSv1.1,TLSv1.2",
                SecurityLevel.MEDIUM: "TLSv1.2",
                SecurityLevel.HIGH: "TLSv1.2,TLSv1.3",
                SecurityLevel.MAXIMUM: "TLSv1.3"
            }
            
            # Generate configuration content
            config_content = self.config_templates["xrdp.ini"].format(
                port=config.port,
                crypt_level=crypt_levels[config.security_level],
                ssl_protocols=ssl_protocols[config.security_level],
                cert_path=config.ssl_cert_path,
                key_path=config.ssl_key_path,
                log_file=config.log_path / "xrdp.log",
                display_server=config.display_server,
                session_path=config.session_path
            )
            
            # Add hardware acceleration section if enabled
            if config.hardware_acceleration:
                config_content += """
[hardware_acceleration]
enable_gpu=true
enable_v4l2=true
enable_vaapi=true
"""
            
            # Write configuration file
            config_file = config.config_path / "xrdp.ini"
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            # Set permissions
            os.chmod(config_file, 0o644)
            
            logger.info(f"Generated XRDP configuration: {config_file}")
            
        except Exception as e:
            logger.error(f"XRDP INI generation failed: {e}")
            raise
    
    async def _generate_session_ini(self, 
                                   config: XRDPConfig,
                                   user_id: str,
                                   session_id: str,
                                   display_config: Optional[Dict[str, Any]] = None) -> None:
        """Generate session configuration"""
        try:
            # Default display settings
            resolution = "1920x1080"
            color_depth = "24"
            refresh_rate = "60"
            hardware_acceleration = "true"
            
            if display_config:
                resolution = display_config.get("resolution", resolution)
                color_depth = display_config.get("color_depth", color_depth)
                refresh_rate = display_config.get("refresh_rate", refresh_rate)
                hardware_acceleration = str(display_config.get("hardware_acceleration", True)).lower()
            
            # Generate session content
            session_content = self.config_templates["session.ini"].format(
                server_id=config.port,  # Use port as server identifier
                user_id=user_id,
                session_id=session_id,
                port=config.port,
                created_at=datetime.now(timezone.utc).isoformat(),
                display=f":{config.port % 1000}",
                wayland_display=f"wayland-{config.port % 1000}",
                runtime_dir=f"/tmp/runtime-{config.port}",
                session_timeout=config.session_timeout,
                idle_timeout=config.idle_timeout,
                max_connections=config.max_connections,
                resolution=resolution,
                color_depth=color_depth,
                refresh_rate=refresh_rate,
                hardware_acceleration=hardware_acceleration
            )
            
            # Write session file
            session_file = config.config_path / "session.ini"
            with open(session_file, 'w') as f:
                f.write(session_content)
            
            # Set permissions
            os.chmod(session_file, 0o644)
            
            logger.info(f"Generated session configuration: {session_file}")
            
        except Exception as e:
            logger.error(f"Session configuration generation failed: {e}")
            raise
    
    async def validate_config(self, config_path: Path) -> bool:
        """Validate XRDP configuration"""
        try:
            xrdp_ini = config_path / "xrdp.ini"
            session_ini = config_path / "session.ini"
            
            # Check if files exist
            if not xrdp_ini.exists() or not session_ini.exists():
                logger.error("Configuration files missing")
                return False
            
            # Basic file validation
            if xrdp_ini.stat().st_size == 0 or session_ini.stat().st_size == 0:
                logger.error("Configuration files are empty")
                return False
            
            # TODO: Add more detailed validation
            # - INI format validation
            # - Required sections check
            # - Value range validation
            
            logger.info(f"Configuration validation passed: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def cleanup_config(self, config_path: Path) -> None:
        """Cleanup server configuration"""
        try:
            import shutil
            
            if config_path.exists():
                shutil.rmtree(config_path)
                logger.info(f"Cleaned up configuration: {config_path}")
            
        except Exception as e:
            logger.error(f"Configuration cleanup failed: {e}")
    
    async def get_configuration_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics"""
        try:
            # Count configuration directories
            config_dirs = [d for d in self.config_path.iterdir() if d.is_dir()]
            log_dirs = [d for d in self.log_path.iterdir() if d.is_dir()]
            session_dirs = [d for d in self.session_path.iterdir() if d.is_dir()]
            
            return {
                "total_configurations": len(config_dirs),
                "active_logs": len(log_dirs),
                "active_sessions": len(session_dirs),
                "config_path": str(self.config_path),
                "log_path": str(self.log_path),
                "session_path": str(self.session_path),
                "ssl_path": str(self.ssl_path)
            }
            
        except Exception as e:
            logger.error(f"Configuration statistics failed: {e}")
            return {}

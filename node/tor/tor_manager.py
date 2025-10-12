"""
LUCID Node Tor - Tor Service Management
Manages Tor proxy connections, onion services, and network routing
Distroless container: pickme/lucid:node-worker:latest
"""

import asyncio
import json
import logging
import os
import time
import hashlib
import base64
import subprocess
import signal
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import aiohttp
import stem
from stem import Signal
from stem.control import Controller
from stem.process import launch_tor_with_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TorServiceStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class OnionServiceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    EXPIRED = "expired"

class TorConnectionType(str, Enum):
    DIRECT = "direct"
    SOCKS5 = "socks5"
    HTTP_PROXY = "http_proxy"
    ONION = "onion"

@dataclass
class OnionService:
    """Onion service configuration"""
    service_id: str
    service_name: str
    port: int
    target_host: str
    target_port: int
    private_key: str
    public_key: str
    onion_address: str
    status: OnionServiceStatus
    created_at: datetime
    last_seen: Optional[datetime] = None

@dataclass
class TorConnection:
    """Tor connection information"""
    connection_id: str
    connection_type: TorConnectionType
    proxy_host: str
    proxy_port: int
    target_host: str
    target_port: int
    onion_address: Optional[str] = None
    status: str = "active"
    created_at: datetime = None
    last_used: Optional[datetime] = None

class TorServiceRequest(BaseModel):
    """Pydantic model for Tor service requests"""
    service_name: str = Field(..., description="Name of the service")
    port: int = Field(..., description="Port to expose")
    target_host: str = Field(..., description="Target host to forward to")
    target_port: int = Field(..., description="Target port to forward to")
    private_key: Optional[str] = Field(default=None, description="Private key for onion service")

class TorConnectionRequest(BaseModel):
    """Pydantic model for Tor connection requests"""
    connection_type: TorConnectionType = Field(..., description="Type of connection")
    target_host: str = Field(..., description="Target host to connect to")
    target_port: int = Field(..., description="Target port to connect to")
    onion_address: Optional[str] = Field(default=None, description="Onion address for onion connections")

class TorServiceResponse(BaseModel):
    """Response model for Tor service operations"""
    service_id: str
    onion_address: str
    status: str
    message: str
    port: int

class TorManager:
    """Manages Tor proxy services and onion routing"""
    
    def __init__(self):
        self.data_dir = Path("/data/node/tor")
        self.config_dir = Path("/data/node/tor/config")
        self.logs_dir = Path("/data/node/tor/logs")
        self.keys_dir = Path("/data/node/tor/keys")
        
        # Ensure directories exist
        for directory in [self.data_dir, self.config_dir, self.logs_dir, self.keys_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.node_id = os.getenv("LUCID_NODE_ID", "node-001")
        self.tor_control_port = int(os.getenv("LUCID_TOR_CONTROL_PORT", "9051"))
        self.tor_socks_port = int(os.getenv("LUCID_TOR_SOCKS_PORT", "9050"))
        self.tor_data_dir = self.data_dir / "tor_data"
        self.tor_config_file = self.config_dir / "torrc"
        
        # Tor service management
        self.tor_process: Optional[subprocess.Popen] = None
        self.tor_controller: Optional[Controller] = None
        self.tor_status = TorServiceStatus.STOPPED
        
        # Onion services
        self.onion_services: Dict[str, OnionService] = {}
        self.tor_connections: Dict[str, TorConnection] = {}
        
        # Load existing configuration
        asyncio.create_task(self._load_tor_config())
        
        # Start Tor service
        asyncio.create_task(self._start_tor_service())
    
    async def _load_tor_config(self):
        """Load existing Tor configuration"""
        try:
            # Load onion services
            services_file = self.data_dir / "onion_services.json"
            if services_file.exists():
                async with aiofiles.open(services_file, "r") as f:
                    data = await f.read()
                    services_data = json.loads(data)
                    
                    for service_id, service_data in services_data.items():
                        service = OnionService(**service_data)
                        self.onion_services[service_id] = service
                    
                logger.info(f"Loaded {len(self.onion_services)} onion services")
            
            # Load connections
            connections_file = self.data_dir / "tor_connections.json"
            if connections_file.exists():
                async with aiofiles.open(connections_file, "r") as f:
                    data = await f.read()
                    connections_data = json.loads(data)
                    
                    for connection_id, connection_data in connections_data.items():
                        connection = TorConnection(**connection_data)
                        self.tor_connections[connection_id] = connection
                    
                logger.info(f"Loaded {len(self.tor_connections)} Tor connections")
                
        except Exception as e:
            logger.error(f"Error loading Tor configuration: {e}")
    
    async def _save_tor_config(self):
        """Save Tor configuration to disk"""
        try:
            # Save onion services
            services_data = {k: asdict(v) for k, v in self.onion_services.items()}
            services_file = self.data_dir / "onion_services.json"
            async with aiofiles.open(services_file, "w") as f:
                await f.write(json.dumps(services_data, indent=2, default=str))
            
            # Save connections
            connections_data = {k: asdict(v) for k, v in self.tor_connections.items()}
            connections_file = self.data_dir / "tor_connections.json"
            async with aiofiles.open(connections_file, "w") as f:
                await f.write(json.dumps(connections_data, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Error saving Tor configuration: {e}")
    
    async def _create_tor_config(self):
        """Create Tor configuration file"""
        try:
            config_content = f"""
# Tor configuration for LUCID Node
DataDirectory {self.tor_data_dir}
ControlPort {self.tor_control_port}
SocksPort {self.tor_socks_port}
CookieAuthentication 1
CookieAuthFile {self.tor_data_dir}/control_auth_cookie
HashedControlPassword {self._generate_hashed_password()}
Log notice file {self.logs_dir}/tor.log
Log info file {self.logs_dir}/tor.log
Log debug file {self.logs_dir}/tor.log
"""
            
            # Add onion service configurations
            for service in self.onion_services.values():
                if service.status == OnionServiceStatus.ACTIVE:
                    config_content += f"""
HiddenServiceDir {self.keys_dir}/{service.service_id}
HiddenServicePort {service.port} {service.target_host}:{service.target_port}
"""
            
            # Write configuration file
            async with aiofiles.open(self.tor_config_file, "w") as f:
                await f.write(config_content)
            
            logger.info("Created Tor configuration file")
            
        except Exception as e:
            logger.error(f"Error creating Tor configuration: {e}")
            raise
    
    def _generate_hashed_password(self) -> str:
        """Generate hashed password for Tor control"""
        import hashlib
        import secrets
        
        # Generate random password
        password = secrets.token_hex(16)
        
        # Hash password using Tor's method
        salt = secrets.token_hex(8)
        hashed = hashlib.sha1((password + salt).encode()).hexdigest()
        
        return f"16:{hashed}{salt}"
    
    async def _start_tor_service(self):
        """Start Tor service"""
        try:
            logger.info("Starting Tor service")
            self.tor_status = TorServiceStatus.STARTING
            
            # Create configuration
            await self._create_tor_config()
            
            # Start Tor process
            tor_config = {
                'SocksPort': str(self.tor_socks_port),
                'ControlPort': str(self.tor_control_port),
                'DataDirectory': str(self.tor_data_dir),
                'CookieAuthentication': '1',
                'Log': [
                    'notice file ' + str(self.logs_dir / 'tor.log'),
                    'info file ' + str(self.logs_dir / 'tor.log'),
                ],
            }
            
            # Launch Tor
            self.tor_process = launch_tor_with_config(
                config=tor_config,
                init_msg_handler=self._tor_init_handler,
                timeout=30
            )
            
            # Connect to Tor controller
            await self._connect_controller()
            
            self.tor_status = TorServiceStatus.RUNNING
            logger.info("Tor service started successfully")
            
            # Start monitoring task
            asyncio.create_task(self._monitor_tor_service())
            
        except Exception as e:
            logger.error(f"Error starting Tor service: {e}")
            self.tor_status = TorServiceStatus.ERROR
            raise
    
    def _tor_init_handler(self, line):
        """Handle Tor initialization messages"""
        if "Bootstrapped 100%" in line:
            logger.info("Tor bootstrapped successfully")
        elif "Opening Socks listener" in line:
            logger.info("Tor SOCKS listener opened")
        elif "Opening Control listener" in line:
            logger.info("Tor control listener opened")
        elif "ERROR" in line:
            logger.error(f"Tor error: {line}")
    
    async def _connect_controller(self):
        """Connect to Tor controller"""
        try:
            self.tor_controller = Controller.from_port(port=self.tor_control_port)
            self.tor_controller.authenticate()
            
            logger.info("Connected to Tor controller")
            
        except Exception as e:
            logger.error(f"Error connecting to Tor controller: {e}")
            raise
    
    async def _monitor_tor_service(self):
        """Monitor Tor service health"""
        try:
            while self.tor_status == TorServiceStatus.RUNNING:
                try:
                    # Check if Tor process is still running
                    if self.tor_process and self.tor_process.poll() is not None:
                        logger.error("Tor process has stopped")
                        self.tor_status = TorServiceStatus.ERROR
                        break
                    
                    # Check controller connection
                    if self.tor_controller:
                        try:
                            # Get Tor info
                            info = self.tor_controller.get_info("version")
                            logger.debug(f"Tor version: {info}")
                        except:
                            logger.warning("Tor controller connection lost, reconnecting")
                            await self._connect_controller()
                    
                    # Update onion service statuses
                    await self._update_onion_service_statuses()
                    
                except Exception as e:
                    logger.error(f"Error in Tor monitoring: {e}")
                
                # Wait before next check
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Tor monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in Tor monitoring loop: {e}")
    
    async def _update_onion_service_statuses(self):
        """Update onion service statuses"""
        try:
            if not self.tor_controller:
                return
            
            # Get active onion services
            active_services = self.tor_controller.get_hidden_services()
            
            for service_id, service in self.onion_services.items():
                if service_id in active_services:
                    service.status = OnionServiceStatus.ACTIVE
                    service.last_seen = datetime.now()
                else:
                    if service.status == OnionServiceStatus.ACTIVE:
                        service.status = OnionServiceStatus.INACTIVE
            
        except Exception as e:
            logger.error(f"Error updating onion service statuses: {e}")
    
    async def create_onion_service(self, request: TorServiceRequest) -> TorServiceResponse:
        """Create a new onion service"""
        try:
            if self.tor_status != TorServiceStatus.RUNNING:
                raise RuntimeError("Tor service is not running")
            
            # Generate service ID
            service_id = await self._generate_service_id(request.service_name)
            
            # Generate or load private key
            private_key, public_key = await self._generate_or_load_key(service_id, request.private_key)
            
            # Create onion service directory
            service_dir = self.keys_dir / service_id
            service_dir.mkdir(exist_ok=True)
            
            # Save private key
            private_key_file = service_dir / "private_key"
            async with aiofiles.open(private_key_file, "w") as f:
                await f.write(private_key)
            
            # Create onion service
            onion_service = OnionService(
                service_id=service_id,
                service_name=request.service_name,
                port=request.port,
                target_host=request.target_host,
                target_port=request.target_port,
                private_key=private_key,
                public_key=public_key,
                onion_address="",  # Will be set after Tor creates the service
                status=OnionServiceStatus.ACTIVE,
                created_at=datetime.now()
            )
            
            # Add to controller
            if self.tor_controller:
                self.tor_controller.create_hidden_service(
                    service_dir,
                    request.port,
                    target=f"{request.target_host}:{request.target_port}"
                )
                
                # Get onion address
                onion_address = self.tor_controller.get_hidden_service_descriptor(service_id).address
                onion_service.onion_address = onion_address
            
            # Store service
            self.onion_services[service_id] = onion_service
            
            # Save configuration
            await self._save_tor_config()
            
            # Log service creation
            await self._log_tor_event(service_id, "onion_service_created", {
                "service_name": request.service_name,
                "port": request.port,
                "target_host": request.target_host,
                "target_port": request.target_port,
                "onion_address": onion_service.onion_address
            })
            
            logger.info(f"Created onion service: {service_id} -> {onion_service.onion_address}")
            
            return TorServiceResponse(
                service_id=service_id,
                onion_address=onion_service.onion_address,
                status="active",
                message="Onion service created successfully",
                port=request.port
            )
            
        except Exception as e:
            logger.error(f"Error creating onion service: {e}")
            raise
    
    async def _generate_service_id(self, service_name: str) -> str:
        """Generate unique service ID"""
        timestamp = int(time.time())
        name_hash = hashlib.sha256(service_name.encode()).hexdigest()[:8]
        return f"service_{timestamp}_{name_hash}"
    
    async def _generate_or_load_key(self, service_id: str, private_key: Optional[str] = None) -> Tuple[str, str]:
        """Generate or load private/public key pair"""
        try:
            if private_key:
                # Use provided private key
                return private_key, self._derive_public_key(private_key)
            else:
                # Generate new key pair
                import cryptography
                from cryptography.hazmat.primitives.asymmetric import ed25519
                
                private_key_obj = ed25519.Ed25519PrivateKey.generate()
                public_key_obj = private_key_obj.public_key()
                
                # Convert to strings
                private_key_str = base64.b64encode(
                    private_key_obj.private_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PrivateFormat.Raw,
                        encryption_algorithm=serialization.NoEncryption()
                    )
                ).decode()
                
                public_key_str = base64.b64encode(
                    public_key_obj.public_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw
                    )
                ).decode()
                
                return private_key_str, public_key_str
                
        except Exception as e:
            logger.error(f"Error generating/loading key: {e}")
            raise
    
    def _derive_public_key(self, private_key: str) -> str:
        """Derive public key from private key"""
        try:
            # This would implement proper key derivation
            return "derived_public_key"
        except Exception as e:
            logger.error(f"Error deriving public key: {e}")
            return "error"
    
    async def create_tor_connection(self, request: TorConnectionRequest) -> str:
        """Create a new Tor connection"""
        try:
            connection_id = await self._generate_connection_id(request)
            
            connection = TorConnection(
                connection_id=connection_id,
                connection_type=request.connection_type,
                proxy_host="127.0.0.1",
                proxy_port=self.tor_socks_port,
                target_host=request.target_host,
                target_port=request.target_port,
                onion_address=request.onion_address,
                status="active",
                created_at=datetime.now()
            )
            
            # Store connection
            self.tor_connections[connection_id] = connection
            
            # Save configuration
            await self._save_tor_config()
            
            # Log connection creation
            await self._log_tor_event(connection_id, "tor_connection_created", {
                "connection_type": request.connection_type,
                "target_host": request.target_host,
                "target_port": request.target_port,
                "onion_address": request.onion_address
            })
            
            logger.info(f"Created Tor connection: {connection_id}")
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Error creating Tor connection: {e}")
            raise
    
    async def _generate_connection_id(self, request: TorConnectionRequest) -> str:
        """Generate unique connection ID"""
        timestamp = int(time.time())
        target_hash = hashlib.sha256(f"{request.target_host}:{request.target_port}".encode()).hexdigest()[:8]
        type_hash = hashlib.sha256(request.connection_type.value.encode()).hexdigest()[:8]
        
        return f"conn_{timestamp}_{target_hash}_{type_hash}"
    
    async def make_tor_request(self, connection_id: str, url: str, method: str = "GET", 
                             data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request through Tor"""
        try:
            if connection_id not in self.tor_connections:
                raise ValueError(f"Connection not found: {connection_id}")
            
            connection = self.tor_connections[connection_id]
            
            # Configure proxy
            proxy_url = f"socks5://{connection.proxy_host}:{connection.proxy_port}"
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    proxy=proxy_url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content": await response.text()
                    }
                    
                    # Update connection last used
                    connection.last_used = datetime.now()
                    await self._save_tor_config()
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Error making Tor request: {e}")
            raise
    
    async def get_tor_status(self) -> Dict[str, Any]:
        """Get Tor service status"""
        try:
            status_info = {
                "tor_status": self.tor_status.value,
                "tor_process_running": self.tor_process is not None and self.tor_process.poll() is None,
                "controller_connected": self.tor_controller is not None,
                "socks_port": self.tor_socks_port,
                "control_port": self.tor_control_port,
                "onion_services_count": len(self.onion_services),
                "active_connections_count": len(self.tor_connections),
                "uptime": "unknown"  # This would be calculated from start time
            }
            
            # Add Tor version if controller is connected
            if self.tor_controller:
                try:
                    version = self.tor_controller.get_info("version")
                    status_info["tor_version"] = version
                except:
                    status_info["tor_version"] = "unknown"
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting Tor status: {e}")
            return {"error": str(e)}
    
    async def get_onion_services(self) -> List[Dict[str, Any]]:
        """Get list of onion services"""
        try:
            services = []
            for service in self.onion_services.values():
                services.append({
                    "service_id": service.service_id,
                    "service_name": service.service_name,
                    "onion_address": service.onion_address,
                    "port": service.port,
                    "target_host": service.target_host,
                    "target_port": service.target_port,
                    "status": service.status.value,
                    "created_at": service.created_at.isoformat(),
                    "last_seen": service.last_seen.isoformat() if service.last_seen else None
                })
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting onion services: {e}")
            return []
    
    async def get_tor_connections(self) -> List[Dict[str, Any]]:
        """Get list of Tor connections"""
        try:
            connections = []
            for connection in self.tor_connections.values():
                connections.append({
                    "connection_id": connection.connection_id,
                    "connection_type": connection.connection_type.value,
                    "target_host": connection.target_host,
                    "target_port": connection.target_port,
                    "onion_address": connection.onion_address,
                    "status": connection.status,
                    "created_at": connection.created_at.isoformat(),
                    "last_used": connection.last_used.isoformat() if connection.last_used else None
                })
            
            return connections
            
        except Exception as e:
            logger.error(f"Error getting Tor connections: {e}")
            return []
    
    async def stop_tor_service(self):
        """Stop Tor service"""
        try:
            logger.info("Stopping Tor service")
            self.tor_status = TorServiceStatus.STOPPING
            
            # Disconnect controller
            if self.tor_controller:
                self.tor_controller.close()
                self.tor_controller = None
            
            # Stop Tor process
            if self.tor_process:
                self.tor_process.terminate()
                self.tor_process.wait(timeout=10)
                self.tor_process = None
            
            self.tor_status = TorServiceStatus.STOPPED
            logger.info("Tor service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Tor service: {e}")
            self.tor_status = TorServiceStatus.ERROR
            raise
    
    async def _log_tor_event(self, event_id: str, event_type: str, data: Dict[str, Any]):
        """Log Tor event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_id": event_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"tor_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging Tor event: {e}")
    
    async def cleanup_old_connections(self, max_age_hours: int = 24):
        """Clean up old Tor connections"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            to_remove = []
            for connection_id, connection in self.tor_connections.items():
                if connection.created_at < cutoff_time:
                    to_remove.append(connection_id)
            
            for connection_id in to_remove:
                del self.tor_connections[connection_id]
            
            if to_remove:
                await self._save_tor_config()
                logger.info(f"Cleaned up {len(to_remove)} old Tor connections")
                
        except Exception as e:
            logger.error(f"Error cleaning up old connections: {e}")

# Global Tor manager instance
tor_manager = TorManager()

# Convenience functions for external use
async def create_onion_service(request: TorServiceRequest) -> TorServiceResponse:
    """Create a new onion service"""
    return await tor_manager.create_onion_service(request)

async def create_tor_connection(request: TorConnectionRequest) -> str:
    """Create a new Tor connection"""
    return await tor_manager.create_tor_connection(request)

async def make_tor_request(connection_id: str, url: str, method: str = "GET", 
                         data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make a request through Tor"""
    return await tor_manager.make_tor_request(connection_id, url, method, data)

async def get_tor_status() -> Dict[str, Any]:
    """Get Tor service status"""
    return await tor_manager.get_tor_status()

async def get_onion_services() -> List[Dict[str, Any]]:
    """Get list of onion services"""
    return await tor_manager.get_onion_services()

async def get_tor_connections() -> List[Dict[str, Any]]:
    """Get list of Tor connections"""
    return await tor_manager.get_tor_connections()

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create an onion service
        service_request = TorServiceRequest(
            service_name="lucid-api",
            port=8080,
            target_host="127.0.0.1",
            target_port=8081
        )
        
        service_response = await create_onion_service(service_request)
        print(f"Onion service created: {service_response}")
        
        # Create a Tor connection
        connection_request = TorConnectionRequest(
            connection_type=TorConnectionType.SOCKS5,
            target_host="example.com",
            target_port=80
        )
        
        connection_id = await create_tor_connection(connection_request)
        print(f"Tor connection created: {connection_id}")
        
        # Make a request through Tor
        response = await make_tor_request(connection_id, "http://example.com")
        print(f"Tor request response: {response['status_code']}")
    
    asyncio.run(main())

"""
LUCID Node Tor - Onion Service Creation and Management
Handles dynamic .onion address creation, key management, and service lifecycle
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
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OnionServiceType(str, Enum):
    """Types of onion services"""
    DYNAMIC = "dynamic"           # Ephemeral, created on-demand
    STATIC = "static"             # Persistent, with saved keys
    WALLET = "wallet"             # Optimized for wallet operations
    API_GATEWAY = "api_gateway"   # API gateway service
    TUNNEL = "tunnel"             # SOCKS/HTTP tunnel
    MONGO_PROXY = "mongo_proxy"   # MongoDB proxy
    TOR_CONTROL = "tor_control"   # Tor control interface

class OnionKeyType(str, Enum):
    """Onion service key types"""
    ED25519_V3 = "ED25519-V3"     # Modern, recommended
    RSA1024 = "RSA1024"           # Legacy, not recommended
    NEW = "NEW"                   # Let Tor choose

class OnionServiceStatus(str, Enum):
    """Onion service status"""
    CREATING = "creating"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    EXPIRED = "expired"
    REMOVED = "removed"

@dataclass
class OnionServiceConfig:
    """Onion service configuration"""
    service_name: str
    service_type: OnionServiceType
    onion_port: int
    target_host: str
    target_port: int
    key_type: OnionKeyType = OnionKeyType.ED25519_V3
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    cookie_auth: bool = True
    ephemeral: bool = False
    is_wallet: bool = False
    max_streams: Optional[int] = None
    client_auth: Optional[str] = None

@dataclass
class OnionServiceInfo:
    """Onion service information"""
    service_id: str
    onion_address: str
    config: OnionServiceConfig
    status: OnionServiceStatus
    created_at: datetime
    last_seen: Optional[datetime] = None
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class OnionServiceRequest(BaseModel):
    """Request model for creating onion services"""
    service_name: str = Field(..., description="Name of the service")
    service_type: OnionServiceType = Field(default=OnionServiceType.DYNAMIC, description="Type of onion service")
    onion_port: int = Field(default=80, description="Onion service port")
    target_host: str = Field(default="127.0.0.1", description="Target host")
    target_port: int = Field(default=8080, description="Target port")
    key_type: OnionKeyType = Field(default=OnionKeyType.ED25519_V3, description="Key type")
    private_key: Optional[str] = Field(default=None, description="Private key (for static services)")
    ephemeral: bool = Field(default=True, description="Whether service is ephemeral")
    is_wallet: bool = Field(default=False, description="Optimize for wallet operations")
    max_streams: Optional[int] = Field(default=None, description="Maximum concurrent streams")
    client_auth: Optional[str] = Field(default=None, description="Client authorization")

class OnionServiceResponse(BaseModel):
    """Response model for onion service operations"""
    service_id: str
    onion_address: str
    status: str
    message: str
    onion_port: int
    target_host: str
    target_port: int
    created_at: str
    private_key_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class OnionServiceManager:
    """Manages onion service creation and lifecycle"""
    
    def __init__(self, tor_controller: Controller, data_dir: Path):
        self.tor_controller = tor_controller
        self.data_dir = data_dir
        self.services_dir = data_dir / "onion_services"
        self.keys_dir = data_dir / "keys"
        self.logs_dir = data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.services_dir, self.keys_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Service registry
        self.services: Dict[str, OnionServiceInfo] = {}
        
        # Load existing services
        asyncio.create_task(self._load_existing_services())
    
    async def _load_existing_services(self):
        """Load existing onion services from disk"""
        try:
            services_file = self.services_dir / "services_registry.json"
            if services_file.exists():
                async with aiofiles.open(services_file, "r") as f:
                    data = await f.read()
                    services_data = json.loads(data)
                    
                    for service_id, service_data in services_data.items():
                        # Convert datetime strings back to datetime objects
                        if 'created_at' in service_data:
                            service_data['created_at'] = datetime.fromisoformat(service_data['created_at'])
                        if 'last_seen' in service_data and service_data['last_seen']:
                            service_data['last_seen'] = datetime.fromisoformat(service_data['last_seen'])
                        
                        service_info = OnionServiceInfo(**service_data)
                        self.services[service_id] = service_info
                    
                logger.info(f"Loaded {len(self.services)} existing onion services")
                
        except Exception as e:
            logger.error(f"Error loading existing services: {e}")
    
    async def _save_services_registry(self):
        """Save services registry to disk"""
        try:
            services_data = {}
            for service_id, service_info in self.services.items():
                # Convert to dict and handle datetime serialization
                service_dict = asdict(service_info)
                if service_dict['created_at']:
                    service_dict['created_at'] = service_dict['created_at'].isoformat()
                if service_dict['last_seen']:
                    service_dict['last_seen'] = service_dict['last_seen'].isoformat()
                services_data[service_id] = service_dict
            
            services_file = self.services_dir / "services_registry.json"
            async with aiofiles.open(services_file, "w") as f:
                await f.write(json.dumps(services_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving services registry: {e}")
    
    async def create_onion_service(self, request: OnionServiceRequest) -> OnionServiceResponse:
        """Create a new onion service"""
        try:
            logger.info(f"Creating onion service: {request.service_name}")
            
            # Generate service ID
            service_id = await self._generate_service_id(request.service_name)
            
            # Create service configuration
            config = OnionServiceConfig(
                service_name=request.service_name,
                service_type=request.service_type,
                onion_port=request.onion_port,
                target_host=request.target_host,
                target_port=request.target_port,
                key_type=request.key_type,
                private_key=request.private_key,
                ephemeral=request.ephemeral,
                is_wallet=request.is_wallet,
                max_streams=request.max_streams,
                client_auth=request.client_auth
            )
            
            # Create service directory
            service_dir = self.services_dir / service_id
            service_dir.mkdir(exist_ok=True)
            
            # Generate or load keys
            private_key_path, public_key_path = await self._handle_keys(
                service_id, config, service_dir
            )
            
            # Create onion service via Tor controller
            onion_address = await self._create_tor_onion_service(
                service_id, config, service_dir
            )
            
            # Create service info
            service_info = OnionServiceInfo(
                service_id=service_id,
                onion_address=onion_address,
                config=config,
                status=OnionServiceStatus.ACTIVE,
                created_at=datetime.now(),
                private_key_path=private_key_path,
                public_key_path=public_key_path,
                metadata={
                    "service_type": config.service_type.value,
                    "is_wallet": config.is_wallet,
                    "ephemeral": config.ephemeral,
                    "key_type": config.key_type.value
                }
            )
            
            # Store service
            self.services[service_id] = service_info
            
            # Save registry
            await self._save_services_registry()
            
            # Create metadata file
            await self._create_service_metadata(service_info)
            
            # Log service creation
            await self._log_onion_event(service_id, "onion_service_created", {
                "service_name": request.service_name,
                "onion_address": onion_address,
                "onion_port": request.onion_port,
                "target_host": request.target_host,
                "target_port": request.target_port,
                "service_type": request.service_type.value,
                "is_wallet": request.is_wallet
            })
            
            logger.info(f"Created onion service: {service_id} -> {onion_address}")
            
            return OnionServiceResponse(
                service_id=service_id,
                onion_address=onion_address,
                status="active",
                message="Onion service created successfully",
                onion_port=request.onion_port,
                target_host=request.target_host,
                target_port=request.target_port,
                created_at=service_info.created_at.isoformat(),
                private_key_path=private_key_path,
                metadata=service_info.metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating onion service: {e}")
            raise
    
    async def _generate_service_id(self, service_name: str) -> str:
        """Generate unique service ID"""
        timestamp = int(time.time())
        name_hash = hashlib.sha256(service_name.encode()).hexdigest()[:8]
        return f"onion_{timestamp}_{name_hash}"
    
    async def _handle_keys(self, service_id: str, config: OnionServiceConfig, 
                          service_dir: Path) -> Tuple[str, str]:
        """Handle key generation or loading"""
        try:
            private_key_path = service_dir / "private_key"
            public_key_path = service_dir / "public_key"
            
            if config.private_key:
                # Use provided private key
                async with aiofiles.open(private_key_path, "w") as f:
                    await f.write(config.private_key)
                
                # Derive public key
                public_key = await self._derive_public_key(config.private_key)
                async with aiofiles.open(public_key_path, "w") as f:
                    await f.write(public_key)
                
                return str(private_key_path), str(public_key_path)
            else:
                # Generate new key pair
                if config.key_type == OnionKeyType.ED25519_V3:
                    private_key, public_key = await self._generate_ed25519_keys()
                else:
                    # For other key types, let Tor generate them
                    private_key = None
                    public_key = None
                
                if private_key:
                    async with aiofiles.open(private_key_path, "w") as f:
                        await f.write(private_key)
                
                if public_key:
                    async with aiofiles.open(public_key_path, "w") as f:
                        await f.write(public_key)
                
                return str(private_key_path), str(public_key_path)
                
        except Exception as e:
            logger.error(f"Error handling keys: {e}")
            raise
    
    async def _generate_ed25519_keys(self) -> Tuple[str, str]:
        """Generate ED25519 key pair"""
        try:
            # Generate private key
            private_key_obj = ed25519.Ed25519PrivateKey.generate()
            public_key_obj = private_key_obj.public_key()
            
            # Convert to PEM format
            private_key_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            
            public_key_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            return private_key_pem, public_key_pem
            
        except Exception as e:
            logger.error(f"Error generating ED25519 keys: {e}")
            raise
    
    async def _derive_public_key(self, private_key: str) -> str:
        """Derive public key from private key"""
        try:
            # Load private key
            private_key_obj = serialization.load_pem_private_key(
                private_key.encode(), password=None
            )
            
            # Get public key
            public_key_obj = private_key_obj.public_key()
            
            # Convert to PEM format
            public_key_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            return public_key_pem
            
        except Exception as e:
            logger.error(f"Error deriving public key: {e}")
            return "error"
    
    async def _create_tor_onion_service(self, service_id: str, config: OnionServiceConfig,
                                      service_dir: Path) -> str:
        """Create onion service via Tor controller"""
        try:
            # Build ADD_ONION command
            if config.key_type == OnionKeyType.NEW:
                # Let Tor generate the key
                add_onion_cmd = f"ADD_ONION NEW:ED25519-V3"
            elif config.private_key:
                # Use existing private key
                add_onion_cmd = f"ADD_ONION {config.private_key}"
            else:
                # Generate new key
                add_onion_cmd = f"ADD_ONION NEW:{config.key_type.value}"
            
            # Add port mapping
            add_onion_cmd += f" Port={config.onion_port},{config.target_host}:{config.target_port}"
            
            # Add client authorization if specified
            if config.client_auth:
                add_onion_cmd += f" ClientAuth={config.client_auth}"
            
            # Send command to Tor
            response = self.tor_controller.msg(add_onion_cmd)
            
            # Parse response
            if response.is_ok():
                # Extract service ID and create onion address
                for line in response:
                    if line.startswith("250-ServiceID="):
                        service_id_hex = line.split("=", 1)[1].strip()
                        onion_address = f"{service_id_hex}.onion"
                        
                        # Save service ID
                        service_id_file = service_dir / "service_id"
                        async with aiofiles.open(service_id_file, "w") as f:
                            await f.write(service_id_hex)
                        
                        return onion_address
                
                raise RuntimeError("Failed to parse ServiceID from Tor response")
            else:
                raise RuntimeError(f"Tor ADD_ONION failed: {response}")
                
        except Exception as e:
            logger.error(f"Error creating Tor onion service: {e}")
            raise
    
    async def _create_service_metadata(self, service_info: OnionServiceInfo):
        """Create service metadata file"""
        try:
            metadata = {
                "service_id": service_info.service_id,
                "service_name": service_info.config.service_name,
                "onion_address": service_info.onion_address,
                "onion_port": service_info.config.onion_port,
                "target_host": service_info.config.target_host,
                "target_port": service_info.config.target_port,
                "service_type": service_info.config.service_type.value,
                "key_type": service_info.config.key_type.value,
                "is_wallet": service_info.config.is_wallet,
                "ephemeral": service_info.config.ephemeral,
                "created_at": service_info.created_at.isoformat(),
                "status": service_info.status.value,
                "metadata": service_info.metadata or {}
            }
            
            metadata_file = self.services_dir / service_info.service_id / "metadata.json"
            async with aiofiles.open(metadata_file, "w") as f:
                await f.write(json.dumps(metadata, indent=2))
                
        except Exception as e:
            logger.error(f"Error creating service metadata: {e}")
    
    async def remove_onion_service(self, service_id: str) -> bool:
        """Remove an onion service"""
        try:
            if service_id not in self.services:
                return False
            
            service_info = self.services[service_id]
            
            # Remove from Tor controller
            try:
                # Extract service ID hex from onion address
                service_id_hex = service_info.onion_address.replace(".onion", "")
                del_onion_cmd = f"DEL_ONION {service_id_hex}"
                
                response = self.tor_controller.msg(del_onion_cmd)
                if not response.is_ok():
                    logger.warning(f"Failed to remove onion from Tor: {response}")
                
            except Exception as e:
                logger.warning(f"Error removing onion from Tor: {e}")
            
            # Update status
            service_info.status = OnionServiceStatus.REMOVED
            
            # Remove from registry
            del self.services[service_id]
            
            # Save registry
            await self._save_services_registry()
            
            # Log removal
            await self._log_onion_event(service_id, "onion_service_removed", {
                "service_name": service_info.config.service_name,
                "onion_address": service_info.onion_address
            })
            
            logger.info(f"Removed onion service: {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing onion service: {e}")
            return False
    
    async def list_onion_services(self) -> List[Dict[str, Any]]:
        """List all onion services"""
        try:
            services = []
            for service_info in self.services.values():
                if service_info.status != OnionServiceStatus.REMOVED:
                    services.append({
                        "service_id": service_info.service_id,
                        "service_name": service_info.config.service_name,
                        "onion_address": service_info.onion_address,
                        "onion_port": service_info.config.onion_port,
                        "target_host": service_info.config.target_host,
                        "target_port": service_info.config.target_port,
                        "service_type": service_info.config.service_type.value,
                        "key_type": service_info.config.key_type.value,
                        "status": service_info.status.value,
                        "is_wallet": service_info.config.is_wallet,
                        "ephemeral": service_info.config.ephemeral,
                        "created_at": service_info.created_at.isoformat(),
                        "last_seen": service_info.last_seen.isoformat() if service_info.last_seen else None,
                        "metadata": service_info.metadata
                    })
            
            return services
            
        except Exception as e:
            logger.error(f"Error listing onion services: {e}")
            return []
    
    async def get_onion_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get specific onion service info"""
        try:
            if service_id not in self.services:
                return None
            
            service_info = self.services[service_id]
            
            return {
                "service_id": service_info.service_id,
                "service_name": service_info.config.service_name,
                "onion_address": service_info.onion_address,
                "onion_port": service_info.config.onion_port,
                "target_host": service_info.config.target_host,
                "target_port": service_info.config.target_port,
                "service_type": service_info.config.service_type.value,
                "key_type": service_info.config.key_type.value,
                "status": service_info.status.value,
                "is_wallet": service_info.config.is_wallet,
                "ephemeral": service_info.config.ephemeral,
                "created_at": service_info.created_at.isoformat(),
                "last_seen": service_info.last_seen.isoformat() if service_info.last_seen else None,
                "private_key_path": service_info.private_key_path,
                "public_key_path": service_info.public_key_path,
                "metadata": service_info.metadata
            }
            
        except Exception as e:
            logger.error(f"Error getting onion service: {e}")
            return None
    
    async def rotate_onion_service(self, service_id: str) -> Optional[OnionServiceResponse]:
        """Rotate (recreate) an onion service with new address"""
        try:
            if service_id not in self.services:
                return None
            
            old_service = self.services[service_id]
            
            # Create new service with same configuration
            new_request = OnionServiceRequest(
                service_name=old_service.config.service_name,
                service_type=old_service.config.service_type,
                onion_port=old_service.config.onion_port,
                target_host=old_service.config.target_host,
                target_port=old_service.config.target_port,
                key_type=old_service.config.key_type,
                ephemeral=old_service.config.ephemeral,
                is_wallet=old_service.config.is_wallet,
                max_streams=old_service.config.max_streams,
                client_auth=old_service.config.client_auth
            )
            
            # Remove old service
            await self.remove_onion_service(service_id)
            
            # Create new service
            new_response = await self.create_onion_service(new_request)
            
            # Log rotation
            await self._log_onion_event(service_id, "onion_service_rotated", {
                "old_onion_address": old_service.onion_address,
                "new_onion_address": new_response.onion_address,
                "service_name": old_service.config.service_name
            })
            
            logger.info(f"Rotated onion service: {old_service.onion_address} -> {new_response.onion_address}")
            
            return new_response
            
        except Exception as e:
            logger.error(f"Error rotating onion service: {e}")
            return None
    
    async def _log_onion_event(self, service_id: str, event_type: str, data: Dict[str, Any]):
        """Log onion service event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "service_id": service_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"onion_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging onion event: {e}")

# Convenience functions for external use
async def create_onion_service(request: OnionServiceRequest, 
                             tor_controller: Controller, 
                             data_dir: Path) -> OnionServiceResponse:
    """Create a new onion service"""
    manager = OnionServiceManager(tor_controller, data_dir)
    return await manager.create_onion_service(request)

async def remove_onion_service(service_id: str, 
                             tor_controller: Controller, 
                             data_dir: Path) -> bool:
    """Remove an onion service"""
    manager = OnionServiceManager(tor_controller, data_dir)
    return await manager.remove_onion_service(service_id)

async def list_onion_services(tor_controller: Controller, 
                            data_dir: Path) -> List[Dict[str, Any]]:
    """List all onion services"""
    manager = OnionServiceManager(tor_controller, data_dir)
    return await manager.list_onion_services()

async def rotate_onion_service(service_id: str, 
                             tor_controller: Controller, 
                             data_dir: Path) -> Optional[OnionServiceResponse]:
    """Rotate an onion service"""
    manager = OnionServiceManager(tor_controller, data_dir)
    return await manager.rotate_onion_service(service_id)

if __name__ == "__main__":
    # Example usage
    async def main():
        # This would be used with an actual Tor controller
        # For demonstration purposes only
        
        # Create a wallet onion service
        wallet_request = OnionServiceRequest(
            service_name="lucid-wallet",
            service_type=OnionServiceType.WALLET,
            onion_port=80,
            target_host="127.0.0.1",
            target_port=8080,
            is_wallet=True,
            ephemeral=False
        )
        
        print(f"Wallet onion service request: {wallet_request}")
        
        # Create an API gateway onion service
        api_request = OnionServiceRequest(
            service_name="lucid-api",
            service_type=OnionServiceType.API_GATEWAY,
            onion_port=80,
            target_host="127.0.0.1",
            target_port=8081,
            ephemeral=True
        )
        
        print(f"API gateway onion service request: {api_request}")
    
    asyncio.run(main())

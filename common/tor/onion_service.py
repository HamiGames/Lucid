"""
Onion service management for Lucid RDP.

This module provides comprehensive .onion service creation, management,
key handling, and integration with the LUCID-STRICT security model.
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import aiofiles
import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519
import cryptography.hazmat.primitives.serialization as serialization

from ..security.trust_nothing_engine import (
    TrustNothingEngine, SecurityContext, SecurityAssessment,
    TrustLevel, RiskLevel, ActionType, PolicyLevel
)


class OnionServiceStatus(Enum):
    """Onion service status states"""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    EXPIRED = "expired"


class OnionServiceType(Enum):
    """Types of onion services"""
    V2 = "v2"
    V3 = "v3"
    STEALTH = "stealth"
    EPHEMERAL = "ephemeral"


class KeyType(Enum):
    """Types of cryptographic keys"""
    ED25519 = "ed25519"
    RSA = "rsa"
    X25519 = "x25519"


@dataclass
class OnionServiceKey:
    """Onion service cryptographic key"""
    key_id: str
    key_type: KeyType
    private_key: bytes
    public_key: bytes
    key_version: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_ephemeral: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OnionServiceConfig:
    """Onion service configuration"""
    service_id: str
    service_type: OnionServiceType
    key: OnionServiceKey
    directory: str
    ports: List[Dict[str, Union[str, int]]]
    max_streams: int = 1000
    max_streams_per_circuit: int = 10
    allow_unknown_ports: bool = False
    client_auth: Optional[Dict[str, str]] = None  # client_name -> auth_key
    stealth_auth: Optional[Dict[str, str]] = None  # client_name -> stealth_key
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OnionServiceInfo:
    """Information about onion service"""
    service_id: str
    onion_address: str
    status: OnionServiceStatus
    service_type: OnionServiceType
    key_id: str
    directory: str
    ports: List[Dict[str, Union[str, int]]]
    created_at: datetime
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    client_count: int = 0
    stream_count: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OnionServiceClient:
    """Onion service client information"""
    client_id: str
    client_name: str
    auth_key: str
    stealth_key: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    connection_count: int = 0
    is_active: bool = True


class OnionService:
    """
    Comprehensive onion service management for Lucid RDP.
    
    Provides service creation, key management, client authentication,
    and integration with the LUCID-STRICT security model.
    """
    
    def __init__(self, trust_engine: Optional[TrustNothingEngine] = None):
        self.trust_engine = trust_engine or TrustNothingEngine()
        self.logger = logging.getLogger(__name__)
        
        # Service state
        self.services: Dict[str, OnionServiceInfo] = {}
        self.service_configs: Dict[str, OnionServiceConfig] = {}
        self.service_keys: Dict[str, OnionServiceKey] = {}
        self.service_clients: Dict[str, List[OnionServiceClient]] = {}
        
        # Key management
        self.key_storage_path = Path.home() / ".lucid" / "onion_keys"
        self.key_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Service directories
        self.service_base_path = Path.home() / ".lucid" / "onion_services"
        self.service_base_path.mkdir(parents=True, exist_ok=True)
        
        # Security integration
        self.security_context_cache: Dict[str, SecurityContext] = {}
        self.rate_limits: Dict[str, Tuple[datetime, int]] = {}
        
        self.logger.info("OnionService initialized")
    
    async def create_service(
        self,
        service_type: OnionServiceType = OnionServiceType.V3,
        ports: List[Dict[str, Union[str, int]]] = None,
        client_auth: Optional[Dict[str, str]] = None,
        stealth_auth: Optional[Dict[str, str]] = None,
        max_streams: int = 1000,
        max_streams_per_circuit: int = 10,
        allow_unknown_ports: bool = False,
        ephemeral: bool = False,
        key_expiry_days: Optional[int] = None
    ) -> Tuple[bool, Optional[OnionServiceInfo]]:
        """Create a new onion service"""
        try:
            # Security assessment
            context = SecurityContext(
                request_id=f"onion_create_{int(datetime.now().timestamp())}",
                service_name="onion_service",
                component_name="service_creation",
                operation="create_service",
                resource_path="/onion/service"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.HIGH)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False, None
            
            # Generate service ID
            service_id = f"onion_{secrets.token_hex(8)}"
            
            # Create service key
            key = await self._generate_service_key(
                service_type=service_type,
                ephemeral=ephemeral,
                expiry_days=key_expiry_days
            )
            
            # Create service directory
            service_dir = self.service_base_path / service_id
            service_dir.mkdir(parents=True, exist_ok=True)
            
            # Default ports if none provided
            if ports is None:
                ports = [{"port": 80, "target": "127.0.0.1:8080"}]
            
            # Create service configuration
            config = OnionServiceConfig(
                service_id=service_id,
                service_type=service_type,
                key=key,
                directory=str(service_dir),
                ports=ports,
                max_streams=max_streams,
                max_streams_per_circuit=max_streams_per_circuit,
                allow_unknown_ports=allow_unknown_ports,
                client_auth=client_auth,
                stealth_auth=stealth_auth
            )
            
            # Generate onion address
            onion_address = await self._generate_onion_address(key, service_type)
            
            # Create service info
            service_info = OnionServiceInfo(
                service_id=service_id,
                onion_address=onion_address,
                status=OnionServiceStatus.CREATED,
                service_type=service_type,
                key_id=key.key_id,
                directory=str(service_dir),
                ports=ports,
                created_at=datetime.now(timezone.utc)
            )
            
            # Store service data
            self.services[service_id] = service_info
            self.service_configs[service_id] = config
            self.service_keys[key.key_id] = key
            
            # Initialize client list
            self.service_clients[service_id] = []
            
            # Save service configuration
            await self._save_service_config(config)
            
            # Save key to disk
            await self._save_service_key(key)
            
            self.logger.info(f"Created onion service {service_id} with address {onion_address}")
            return True, service_info
            
        except Exception as e:
            self.logger.error(f"Failed to create onion service: {e}")
            return False, None
    
    async def start_service(self, service_id: str) -> bool:
        """Start an onion service"""
        try:
            if service_id not in self.services:
                self.logger.error(f"Service {service_id} not found")
                return False
            
            service_info = self.services[service_id]
            config = self.service_configs[service_id]
            
            # Security assessment
            context = SecurityContext(
                request_id=f"onion_start_{service_id}_{int(datetime.now().timestamp())}",
                service_name="onion_service",
                component_name="service_management",
                operation="start_service",
                resource_path=f"/onion/service/{service_id}"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.HIGH)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Update service status
            service_info.status = OnionServiceStatus.STARTING
            
            # Generate Tor configuration for this service
            tor_config = await self._generate_tor_config(config)
            
            # Write configuration to service directory
            config_file = Path(config.directory) / "torrc"
            async with aiofiles.open(config_file, 'w') as f:
                await f.write(tor_config)
            
            # Update service status
            service_info.status = OnionServiceStatus.RUNNING
            service_info.last_heartbeat = datetime.now(timezone.utc)
            
            self.logger.info(f"Started onion service {service_id}")
            return True
            
        except Exception as e:
            if service_id in self.services:
                self.services[service_id].status = OnionServiceStatus.ERROR
                self.services[service_id].error_message = str(e)
            
            self.logger.error(f"Failed to start onion service {service_id}: {e}")
            return False
    
    async def stop_service(self, service_id: str) -> bool:
        """Stop an onion service"""
        try:
            if service_id not in self.services:
                self.logger.error(f"Service {service_id} not found")
                return False
            
            service_info = self.services[service_id]
            
            # Security assessment
            context = SecurityContext(
                request_id=f"onion_stop_{service_id}_{int(datetime.now().timestamp())}",
                service_name="onion_service",
                component_name="service_management",
                operation="stop_service",
                resource_path=f"/onion/service/{service_id}"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.HIGH)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Update service status
            service_info.status = OnionServiceStatus.STOPPING
            
            # Remove Tor configuration
            config = self.service_configs[service_id]
            config_file = Path(config.directory) / "torrc"
            if config_file.exists():
                config_file.unlink()
            
            # Update service status
            service_info.status = OnionServiceStatus.STOPPED
            
            self.logger.info(f"Stopped onion service {service_id}")
            return True
            
        except Exception as e:
            if service_id in self.services:
                self.services[service_id].status = OnionServiceStatus.ERROR
                self.services[service_id].error_message = str(e)
            
            self.logger.error(f"Failed to stop onion service {service_id}: {e}")
            return False
    
    async def delete_service(self, service_id: str, delete_keys: bool = False) -> bool:
        """Delete an onion service"""
        try:
            if service_id not in self.services:
                self.logger.error(f"Service {service_id} not found")
                return False
            
            # Security assessment
            context = SecurityContext(
                request_id=f"onion_delete_{service_id}_{int(datetime.now().timestamp())}",
                service_name="onion_service",
                component_name="service_management",
                operation="delete_service",
                resource_path=f"/onion/service/{service_id}"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.CRITICAL)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Stop service first
            await self.stop_service(service_id)
            
            # Get service data
            service_info = self.services[service_id]
            config = self.service_configs[service_id]
            key = self.service_keys[config.key.key_id]
            
            # Delete service directory
            service_dir = Path(config.directory)
            if service_dir.exists():
                import shutil
                shutil.rmtree(service_dir)
            
            # Delete key if requested
            if delete_keys:
                await self._delete_service_key(key)
            
            # Remove from memory
            del self.services[service_id]
            del self.service_configs[service_id]
            if service_id in self.service_clients:
                del self.service_clients[service_id]
            
            self.logger.info(f"Deleted onion service {service_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete onion service {service_id}: {e}")
            return False
    
    async def get_service_info(self, service_id: str) -> Optional[OnionServiceInfo]:
        """Get information about an onion service"""
        return self.services.get(service_id)
    
    async def list_services(self) -> List[OnionServiceInfo]:
        """List all onion services"""
        return list(self.services.values())
    
    async def add_client_auth(
        self,
        service_id: str,
        client_name: str,
        auth_key: Optional[str] = None,
        stealth_key: Optional[str] = None
    ) -> bool:
        """Add client authentication to an onion service"""
        try:
            if service_id not in self.services:
                self.logger.error(f"Service {service_id} not found")
                return False
            
            config = self.service_configs[service_id]
            
            # Generate keys if not provided
            if auth_key is None:
                auth_key = await self._generate_client_auth_key()
            
            if stealth_key is None and config.service_type == OnionServiceType.STEALTH:
                stealth_key = await self._generate_stealth_key()
            
            # Create client
            client = OnionServiceClient(
                client_id=f"client_{secrets.token_hex(4)}",
                client_name=client_name,
                auth_key=auth_key,
                stealth_key=stealth_key
            )
            
            # Add to service clients
            if service_id not in self.service_clients:
                self.service_clients[service_id] = []
            
            self.service_clients[service_id].append(client)
            
            # Update service configuration
            if config.client_auth is None:
                config.client_auth = {}
            config.client_auth[client_name] = auth_key
            
            if stealth_key and config.stealth_auth is None:
                config.stealth_auth = {}
            if stealth_key:
                config.stealth_auth[client_name] = stealth_key
            
            # Save updated configuration
            await self._save_service_config(config)
            
            self.logger.info(f"Added client {client_name} to service {service_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add client auth to service {service_id}: {e}")
            return False
    
    async def remove_client_auth(self, service_id: str, client_name: str) -> bool:
        """Remove client authentication from an onion service"""
        try:
            if service_id not in self.services:
                self.logger.error(f"Service {service_id} not found")
                return False
            
            config = self.service_configs[service_id]
            
            # Remove from service clients
            if service_id in self.service_clients:
                self.service_clients[service_id] = [
                    client for client in self.service_clients[service_id]
                    if client.client_name != client_name
                ]
            
            # Update service configuration
            if config.client_auth and client_name in config.client_auth:
                del config.client_auth[client_name]
            
            if config.stealth_auth and client_name in config.stealth_auth:
                del config.stealth_auth[client_name]
            
            # Save updated configuration
            await self._save_service_config(config)
            
            self.logger.info(f"Removed client {client_name} from service {service_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove client auth from service {service_id}: {e}")
            return False
    
    async def get_service_clients(self, service_id: str) -> List[OnionServiceClient]:
        """Get clients for an onion service"""
        return self.service_clients.get(service_id, [])
    
    async def rotate_service_key(self, service_id: str) -> Tuple[bool, Optional[str]]:
        """Rotate the key for an onion service"""
        try:
            if service_id not in self.services:
                self.logger.error(f"Service {service_id} not found")
                return False, None
            
            service_info = self.services[service_id]
            config = self.service_configs[service_id]
            
            # Security assessment
            context = SecurityContext(
                request_id=f"onion_rotate_{service_id}_{int(datetime.now().timestamp())}",
                service_name="onion_service",
                component_name="key_management",
                operation="rotate_key",
                resource_path=f"/onion/service/{service_id}/key"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.CRITICAL)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False, None
            
            # Generate new key
            new_key = await self._generate_service_key(
                service_type=config.service_type,
                ephemeral=config.key.is_ephemeral
            )
            
            # Generate new onion address
            new_onion_address = await self._generate_onion_address(new_key, config.service_type)
            
            # Update service configuration
            old_key_id = config.key.key_id
            config.key = new_key
            config.updated_at = datetime.now(timezone.utc)
            
            # Update service info
            service_info.onion_address = new_onion_address
            service_info.key_id = new_key.key_id
            
            # Save updated configuration
            await self._save_service_config(config)
            await self._save_service_key(new_key)
            
            # Delete old key
            await self._delete_service_key(self.service_keys[old_key_id])
            del self.service_keys[old_key_id]
            
            self.logger.info(f"Rotated key for service {service_id}, new address: {new_onion_address}")
            return True, new_onion_address
            
        except Exception as e:
            self.logger.error(f"Failed to rotate key for service {service_id}: {e}")
            return False, None
    
    async def _generate_service_key(
        self,
        service_type: OnionServiceType,
        ephemeral: bool = False,
        expiry_days: Optional[int] = None
    ) -> OnionServiceKey:
        """Generate a new service key"""
        key_id = f"key_{secrets.token_hex(8)}"
        
        if service_type == OnionServiceType.V3:
            # Generate Ed25519 key pair
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Serialize keys
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
        else:
            # For V2 services, generate RSA key (simplified)
            private_bytes = secrets.token_bytes(32)
            public_bytes = secrets.token_bytes(32)
        
        # Calculate expiry
        expires_at = None
        if expiry_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        
        return OnionServiceKey(
            key_id=key_id,
            key_type=KeyType.ED25519 if service_type == OnionServiceType.V3 else KeyType.RSA,
            private_key=private_bytes,
            public_key=public_bytes,
            key_version=3 if service_type == OnionServiceType.V3 else 2,
            expires_at=expires_at,
            is_ephemeral=ephemeral
        )
    
    async def _generate_onion_address(self, key: OnionServiceKey, service_type: OnionServiceType) -> str:
        """Generate onion address from service key"""
        if service_type == OnionServiceType.V3:
            # For V3 services, use the public key to generate the address
            # This is a simplified version - real implementation would use proper Tor v3 address generation
            hash_obj = hashlib.sha3_256()
            hash_obj.update(key.public_key)
            address_hash = hash_obj.digest()[:16]  # First 16 bytes
            onion_address = base64.b32encode(address_hash).decode().lower()
            return f"{onion_address}.onion"
        
        else:
            # For V2 services, generate a random address (simplified)
            random_bytes = secrets.token_bytes(10)
            onion_address = base64.b32encode(random_bytes).decode().lower()
            return f"{onion_address}.onion"
    
    async def _generate_client_auth_key(self) -> str:
        """Generate client authentication key"""
        # Generate a random 32-byte key and encode as base32
        key_bytes = secrets.token_bytes(32)
        return base64.b32encode(key_bytes).decode().lower()
    
    async def _generate_stealth_key(self) -> str:
        """Generate stealth authentication key"""
        # Generate a random 32-byte key and encode as base32
        key_bytes = secrets.token_bytes(32)
        return base64.b32encode(key_bytes).decode().lower()
    
    async def _generate_tor_config(self, config: OnionServiceConfig) -> str:
        """Generate Tor configuration for onion service"""
        config_lines = [
            f"HiddenServiceDir {config.directory}",
        ]
        
        # Add port configurations
        for port_config in config.ports:
            port = port_config.get("port", 80)
            target = port_config.get("target", "127.0.0.1:8080")
            config_lines.append(f"HiddenServicePort {port} {target}")
        
        # Add client authentication
        if config.client_auth:
            for client_name, auth_key in config.client_auth.items():
                config_lines.append(f"HiddenServiceAuthorizeClient stealth {client_name}:{auth_key}")
        
        # Add stealth authentication
        if config.stealth_auth:
            for client_name, stealth_key in config.stealth_auth.items():
                config_lines.append(f"HiddenServiceAuthorizeClient stealth {client_name}:{stealth_key}")
        
        # Add stream limits
        config_lines.extend([
            f"HiddenServiceMaxStreams {config.max_streams}",
            f"HiddenServiceMaxStreamsCloseCircuit {config.max_streams_per_circuit}"
        ])
        
        if config.allow_unknown_ports:
            config_lines.append("HiddenServiceAllowUnknownPorts 1")
        else:
            config_lines.append("HiddenServiceAllowUnknownPorts 0")
        
        return '\n'.join(config_lines)
    
    async def _save_service_config(self, config: OnionServiceConfig) -> None:
        """Save service configuration to disk"""
        config_file = Path(config.directory) / "service_config.json"
        
        config_data = {
            "service_id": config.service_id,
            "service_type": config.service_type.value,
            "key_id": config.key.key_id,
            "directory": config.directory,
            "ports": config.ports,
            "max_streams": config.max_streams,
            "max_streams_per_circuit": config.max_streams_per_circuit,
            "allow_unknown_ports": config.allow_unknown_ports,
            "client_auth": config.client_auth,
            "stealth_auth": config.stealth_auth,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
            "metadata": config.metadata
        }
        
        async with aiofiles.open(config_file, 'w') as f:
            await f.write(json.dumps(config_data, indent=2))
    
    async def _save_service_key(self, key: OnionServiceKey) -> None:
        """Save service key to disk"""
        key_file = self.key_storage_path / f"{key.key_id}.key"
        
        key_data = {
            "key_id": key.key_id,
            "key_type": key.key_type.value,
            "private_key": base64.b64encode(key.private_key).decode(),
            "public_key": base64.b64encode(key.public_key).decode(),
            "key_version": key.key_version,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "is_ephemeral": key.is_ephemeral,
            "metadata": key.metadata
        }
        
        async with aiofiles.open(key_file, 'w') as f:
            await f.write(json.dumps(key_data, indent=2))
    
    async def _delete_service_key(self, key: OnionServiceKey) -> None:
        """Delete service key from disk"""
        key_file = self.key_storage_path / f"{key.key_id}.key"
        if key_file.exists():
            key_file.unlink()


# Global instance management
_onion_service_instance: Optional[OnionService] = None


def get_onion_service() -> Optional[OnionService]:
    """Get the global OnionService instance"""
    return _onion_service_instance


def create_onion_service(trust_engine: Optional[TrustNothingEngine] = None) -> OnionService:
    """Create a new OnionService instance"""
    global _onion_service_instance
    _onion_service_instance = OnionService(trust_engine)
    return _onion_service_instance


async def main():
    """Example usage of OnionService"""
    # Create onion service manager
    onion_service = create_onion_service()
    
    # Create a new V3 onion service
    success, service_info = await onion_service.create_service(
        service_type=OnionServiceType.V3,
        ports=[{"port": 80, "target": "127.0.0.1:8080"}],
        max_streams=1000
    )
    
    if success and service_info:
        print(f"Created onion service: {service_info.onion_address}")
        
        # Start the service
        await onion_service.start_service(service_info.service_id)
        
        # Add client authentication
        await onion_service.add_client_auth(
            service_info.service_id,
            "test_client",
            auth_key="test_auth_key"
        )
        
        # Get service info
        info = await onion_service.get_service_info(service_info.service_id)
        print(f"Service status: {info.status}")
        
        # List all services
        services = await onion_service.list_services()
        print(f"Total services: {len(services)}")
        
        # Stop and delete service
        await onion_service.stop_service(service_info.service_id)
        await onion_service.delete_service(service_info.service_id, delete_keys=True)


if __name__ == "__main__":
    asyncio.run(main())

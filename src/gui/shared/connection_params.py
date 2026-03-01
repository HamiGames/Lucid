# Connection Parameters Module for Lucid GUI
# Core parameters module for GUI connection management
# Implements SPEC-2 connection parameter specifications

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionType(Enum):
    """Connection type enumeration"""
    RDP = "rdp"
    SSH = "ssh"
    VNC = "vnc"
    WEBSOCKET = "websocket"
    BLOCKCHAIN = "blockchain"
    NODE = "node"

class SecurityLevel(Enum):
    """Security level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"

class AuthenticationMethod(Enum):
    """Authentication method enumeration"""
    PASSWORD = "password"
    KEY = "key"
    CERTIFICATE = "certificate"
    TOKEN = "token"
    HARDWARE_WALLET = "hardware_wallet"

@dataclass
class ConnectionCredentials:
    """Connection credentials data structure"""
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None
    certificate: Optional[str] = None
    token: Optional[str] = None
    wallet_address: Optional[str] = None
    encrypted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionCredentials':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class NetworkConfig:
    """Network configuration data structure"""
    host: str
    port: int
    protocol: str = "tcp"
    timeout: int = 30
    keepalive: bool = True
    compression: bool = False
    encryption: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkConfig':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class SecurityConfig:
    """Security configuration data structure"""
    level: SecurityLevel = SecurityLevel.MEDIUM
    authentication_method: AuthenticationMethod = AuthenticationMethod.PASSWORD
    encryption_algorithm: str = "AES-256-GCM"
    key_exchange: str = "ECDH"
    certificate_validation: bool = True
    require_mfa: bool = False
    session_timeout: int = 3600
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityConfig':
        """Create from dictionary"""
        # Convert string enums back to enum objects
        if isinstance(data.get('level'), str):
            data['level'] = SecurityLevel(data['level'])
        if isinstance(data.get('authentication_method'), str):
            data['authentication_method'] = AuthenticationMethod(data['authentication_method'])
        return cls(**data)

@dataclass
class ConnectionParameters:
    """Core connection parameters data structure"""
    connection_id: str
    name: str
    connection_type: ConnectionType
    network_config: NetworkConfig
    credentials: ConnectionCredentials
    security_config: SecurityConfig
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert enums to strings for JSON serialization
        data['connection_type'] = self.connection_type.value
        data['network_config'] = self.network_config.to_dict()
        data['credentials'] = self.credentials.to_dict()
        data['security_config'] = self.security_config.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionParameters':
        """Create from dictionary"""
        # Convert string enums back to enum objects
        data['connection_type'] = ConnectionType(data['connection_type'])
        data['network_config'] = NetworkConfig.from_dict(data['network_config'])
        data['credentials'] = ConnectionCredentials.from_dict(data['credentials'])
        data['security_config'] = SecurityConfig.from_dict(data['security_config'])
        return cls(**data)

class ConnectionParameterManager:
    """Manager class for connection parameters"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize connection parameter manager"""
        self.config_dir = config_dir or os.path.join(os.path.expanduser("~"), ".lucid", "connections")
        self.encryption_key = self._get_or_create_encryption_key()
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists"""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credentials"""
        key_file = os.path.join(self.config_dir, ".encryption_key")
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            return key
    
    def _encrypt_credentials(self, credentials: ConnectionCredentials) -> ConnectionCredentials:
        """Encrypt sensitive credential data"""
        if credentials.encrypted:
            return credentials
        
        fernet = Fernet(self.encryption_key)
        encrypted_creds = ConnectionCredentials(
            username=credentials.username,
            password=fernet.encrypt(credentials.password.encode()).decode() if credentials.password else None,
            private_key=fernet.encrypt(credentials.private_key.encode()).decode() if credentials.private_key else None,
            certificate=fernet.encrypt(credentials.certificate.encode()).decode() if credentials.certificate else None,
            token=fernet.encrypt(credentials.token.encode()).decode() if credentials.token else None,
            wallet_address=credentials.wallet_address,
            encrypted=True
        )
        return encrypted_creds
    
    def _decrypt_credentials(self, credentials: ConnectionCredentials) -> ConnectionCredentials:
        """Decrypt sensitive credential data"""
        if not credentials.encrypted:
            return credentials
        
        fernet = Fernet(self.encryption_key)
        decrypted_creds = ConnectionCredentials(
            username=credentials.username,
            password=fernet.decrypt(credentials.password.encode()).decode() if credentials.password else None,
            private_key=fernet.decrypt(credentials.private_key.encode()).decode() if credentials.private_key else None,
            certificate=fernet.decrypt(credentials.certificate.encode()).decode() if credentials.certificate else None,
            token=fernet.decrypt(credentials.token.encode()).decode() if credentials.token else None,
            wallet_address=credentials.wallet_address,
            encrypted=False
        )
        return decrypted_creds
    
    def save_connection(self, connection: ConnectionParameters, encrypt: bool = True) -> bool:
        """Save connection parameters to file"""
        try:
            # Encrypt credentials if requested
            if encrypt:
                connection.credentials = self._encrypt_credentials(connection.credentials)
            
            # Update timestamps
            import datetime
            now = datetime.datetime.utcnow().isoformat()
            if not connection.created_at:
                connection.created_at = now
            connection.updated_at = now
            
            # Save to file
            filename = f"{connection.connection_id}.json"
            filepath = os.path.join(self.config_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(connection.to_dict(), f, indent=2)
            
            logger.info(f"Connection saved: {connection.connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save connection {connection.connection_id}: {e}")
            return False
    
    def load_connection(self, connection_id: str, decrypt: bool = True) -> Optional[ConnectionParameters]:
        """Load connection parameters from file"""
        try:
            filename = f"{connection_id}.json"
            filepath = os.path.join(self.config_dir, filename)
            
            if not os.path.exists(filepath):
                logger.warning(f"Connection file not found: {connection_id}")
                return None
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            connection = ConnectionParameters.from_dict(data)
            
            # Decrypt credentials if requested
            if decrypt:
                connection.credentials = self._decrypt_credentials(connection.credentials)
            
            logger.info(f"Connection loaded: {connection_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to load connection {connection_id}: {e}")
            return None
    
    def list_connections(self) -> List[str]:
        """List all available connection IDs"""
        try:
            connections = []
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.json'):
                    connection_id = filename[:-5]  # Remove .json extension
                    connections.append(connection_id)
            return connections
        except Exception as e:
            logger.error(f"Failed to list connections: {e}")
            return []
    
    def delete_connection(self, connection_id: str) -> bool:
        """Delete connection parameters"""
        try:
            filename = f"{connection_id}.json"
            filepath = os.path.join(self.config_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Connection deleted: {connection_id}")
                return True
            else:
                logger.warning(f"Connection file not found: {connection_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete connection {connection_id}: {e}")
            return False
    
    def create_connection(
        self,
        name: str,
        connection_type: ConnectionType,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        **kwargs
    ) -> ConnectionParameters:
        """Create new connection parameters"""
        
        # Generate unique connection ID
        connection_id = self._generate_connection_id(name, host, port)
        
        # Create network config
        network_config = NetworkConfig(
            host=host,
            port=port,
            **kwargs.get('network_config', {})
        )
        
        # Create credentials
        credentials = ConnectionCredentials(
            username=username,
            password=password,
            **kwargs.get('credentials', {})
        )
        
        # Create security config
        security_config = SecurityConfig(
            level=security_level,
            **kwargs.get('security_config', {})
        )
        
        # Create connection parameters
        connection = ConnectionParameters(
            connection_id=connection_id,
            name=name,
            connection_type=connection_type,
            network_config=network_config,
            credentials=credentials,
            security_config=security_config,
            metadata=kwargs.get('metadata', {})
        )
        
        return connection
    
    def _generate_connection_id(self, name: str, host: str, port: int) -> str:
        """Generate unique connection ID"""
        # Create a hash of name, host, port, and timestamp
        timestamp = str(int(datetime.datetime.utcnow().timestamp()))
        data = f"{name}:{host}:{port}:{timestamp}"
        hash_object = hashlib.sha256(data.encode())
        return hash_object.hexdigest()[:16]  # Use first 16 characters
    
    def validate_connection(self, connection: ConnectionParameters) -> List[str]:
        """Validate connection parameters"""
        errors = []
        
        # Validate required fields
        if not connection.name:
            errors.append("Connection name is required")
        
        if not connection.network_config.host:
            errors.append("Host is required")
        
        if not connection.network_config.port or connection.network_config.port <= 0:
            errors.append("Valid port is required")
        
        if not connection.credentials.username:
            errors.append("Username is required")
        
        # Validate port ranges
        if connection.network_config.port > 65535:
            errors.append("Port must be between 1 and 65535")
        
        # Validate security configuration
        if connection.security_config.session_timeout <= 0:
            errors.append("Session timeout must be positive")
        
        return errors

# Import datetime at module level
import datetime

# Factory functions for common connection types
def create_rdp_connection(
    name: str,
    host: str,
    username: str,
    password: str,
    port: int = 3389,
    security_level: SecurityLevel = SecurityLevel.MEDIUM
) -> ConnectionParameters:
    """Create RDP connection parameters"""
    manager = ConnectionParameterManager()
    return manager.create_connection(
        name=name,
        connection_type=ConnectionType.RDP,
        host=host,
        port=port,
        username=username,
        password=password,
        security_level=security_level,
        network_config={
            'protocol': 'tcp',
            'timeout': 30,
            'keepalive': True,
            'compression': True,
            'encryption': True
        },
        security_config={
            'authentication_method': AuthenticationMethod.PASSWORD,
            'encryption_algorithm': 'AES-256-GCM',
            'certificate_validation': True,
            'session_timeout': 3600
        }
    )

def create_blockchain_connection(
    name: str,
    host: str,
    wallet_address: str,
    port: int = 8545,
    security_level: SecurityLevel = SecurityLevel.HIGH
) -> ConnectionParameters:
    """Create blockchain connection parameters"""
    manager = ConnectionParameterManager()
    return manager.create_connection(
        name=name,
        connection_type=ConnectionType.BLOCKCHAIN,
        host=host,
        port=port,
        username="blockchain_user",  # Placeholder
        password=None,
        security_level=security_level,
        credentials={
            'wallet_address': wallet_address
        },
        network_config={
            'protocol': 'tcp',
            'timeout': 60,
            'keepalive': True,
            'compression': False,
            'encryption': True
        },
        security_config={
            'authentication_method': AuthenticationMethod.HARDWARE_WALLET,
            'encryption_algorithm': 'AES-256-GCM',
            'certificate_validation': True,
            'session_timeout': 7200
        }
    )

def create_node_connection(
    name: str,
    host: str,
    port: int = 8080,
    security_level: SecurityLevel = SecurityLevel.HIGH
) -> ConnectionParameters:
    """Create node connection parameters"""
    manager = ConnectionParameterManager()
    return manager.create_connection(
        name=name,
        connection_type=ConnectionType.NODE,
        host=host,
        port=port,
        username="node_user",  # Placeholder
        password=None,
        security_level=security_level,
        network_config={
            'protocol': 'tcp',
            'timeout': 30,
            'keepalive': True,
            'compression': True,
            'encryption': True
        },
        security_config={
            'authentication_method': AuthenticationMethod.TOKEN,
            'encryption_algorithm': 'AES-256-GCM',
            'certificate_validation': True,
            'session_timeout': 1800
        }
    )

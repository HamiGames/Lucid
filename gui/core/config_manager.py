# Path: gui/core/config_manager.py
"""
Encrypted configuration management for Lucid RDP GUI.
Provides secure storage and retrieval of configuration data with encryption.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
import hashlib

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import blake3

logger = logging.getLogger(__name__)


class ConfigScope(Enum):
    """Configuration scope levels"""
    GLOBAL = "global"          # System-wide configuration
    USER = "user"             # User-specific configuration
    APPLICATION = "application"  # Application-specific configuration
    SESSION = "session"       # Session-specific configuration


class ConfigEncryption(Enum):
    """Encryption methods for configuration"""
    FERNET = "fernet"         # Fernet symmetric encryption
    CHACHA20 = "chacha20"     # ChaCha20-Poly1305 AEAD
    NONE = "none"             # No encryption (for non-sensitive data)


@dataclass
class ConfigMetadata:
    """Configuration metadata"""
    version: str = "1.0.0"
    created_at: str = ""
    updated_at: str = ""
    scope: ConfigScope = ConfigScope.USER
    encryption: ConfigEncryption = ConfigEncryption.FERNET
    checksum: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            from datetime import datetime, timezone
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class GuiConfig:
    """Main GUI configuration structure"""
    # Window settings
    window_width: int = 1200
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100
    window_maximized: bool = False
    
    # Theme settings
    theme: str = "default"
    dark_mode: bool = False
    font_family: str = "Arial"
    font_size: int = 10
    
    # Network settings
    node_api_url: str = "http://localhost:8080"
    tor_socks_port: int = 9150
    tor_control_port: int = 9151
    connection_timeout: int = 30
    read_timeout: int = 60
    
    # Security settings
    certificate_pinning: bool = True
    allowed_onions: List[str] = None
    verify_ssl: bool = True
    
    # Update settings
    update_interval: int = 5000  # milliseconds
    auto_refresh: bool = True
    log_level: str = "INFO"
    
    # Advanced settings
    debug_mode: bool = False
    experimental_features: bool = False
    telemetry_enabled: bool = False
    
    def __post_init__(self):
        if self.allowed_onions is None:
            self.allowed_onions = []


class ConfigEncryptionManager:
    """Manages encryption for configuration data"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or self._generate_master_key()
        self._fernet_key: Optional[Fernet] = None
        self._chacha20_key: Optional[bytes] = None
        
    def _generate_master_key(self) -> bytes:
        """Generate a secure master key"""
        return secrets.token_bytes(32)
    
    def _derive_fernet_key(self, salt: bytes) -> Fernet:
        """Derive Fernet key from master key"""
        if self._fernet_key is None:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
            self._fernet_key = Fernet(key)
        return self._fernet_key
    
    def _derive_chacha20_key(self, salt: bytes) -> bytes:
        """Derive ChaCha20 key from master key"""
        if self._chacha20_key is None:
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                info=b'chacha20-config-key'
            )
            self._chacha20_key = hkdf.derive(self.master_key)
        return self._chacha20_key
    
    def encrypt_data(self, data: bytes, encryption: ConfigEncryption, salt: bytes) -> bytes:
        """Encrypt configuration data"""
        if encryption == ConfigEncryption.FERNET:
            fernet = self._derive_fernet_key(salt)
            return fernet.encrypt(data)
        
        elif encryption == ConfigEncryption.CHACHA20:
            key = self._derive_chacha20_key(salt)
            nonce = secrets.token_bytes(12)  # ChaCha20-Poly1305 nonce
            cipher = ChaCha20Poly1305(key)
            encrypted = cipher.encrypt(nonce, data, None)
            return nonce + encrypted
        
        elif encryption == ConfigEncryption.NONE:
            return data
        
        else:
            raise ValueError(f"Unsupported encryption: {encryption}")
    
    def decrypt_data(self, encrypted_data: bytes, encryption: ConfigEncryption, salt: bytes) -> bytes:
        """Decrypt configuration data"""
        if encryption == ConfigEncryption.FERNET:
            fernet = self._derive_fernet_key(salt)
            return fernet.decrypt(encrypted_data)
        
        elif encryption == ConfigEncryption.CHACHA20:
            key = self._derive_chacha20_key(salt)
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            cipher = ChaCha20Poly1305(key)
            return cipher.decrypt(nonce, ciphertext, None)
        
        elif encryption == ConfigEncryption.NONE:
            return encrypted_data
        
        else:
            raise ValueError(f"Unsupported encryption: {encryption}")


class ConfigManager:
    """
    Encrypted configuration manager for Lucid RDP GUI.
    
    Provides secure storage and retrieval of configuration data with:
    - Multiple encryption methods (Fernet, ChaCha20-Poly1305)
    - Configuration scoping (global, user, application, session)
    - Integrity verification with checksums
    - Automatic backup and recovery
    """
    
    def __init__(self, 
                 config_dir: Optional[Path] = None,
                 master_key: Optional[bytes] = None,
                 default_encryption: ConfigEncryption = ConfigEncryption.FERNET):
        self.config_dir = config_dir or Path.home() / ".lucid" / "gui"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryption_manager = ConfigEncryptionManager(master_key)
        self.default_encryption = default_encryption
        
        # Configuration cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._metadata_cache: Dict[str, ConfigMetadata] = {}
        
        logger.info(f"ConfigManager initialized with directory: {self.config_dir}")
    
    def _get_config_path(self, config_name: str, scope: ConfigScope) -> Path:
        """Get configuration file path"""
        scope_dir = self.config_dir / scope.value
        scope_dir.mkdir(parents=True, exist_ok=True)
        return scope_dir / f"{config_name}.json"
    
    def _get_backup_path(self, config_path: Path) -> Path:
        """Get backup configuration file path"""
        return config_path.with_suffix('.json.backup')
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate BLAKE3 checksum of data"""
        return blake3.blake3(data).hexdigest()
    
    def _generate_salt(self) -> bytes:
        """Generate random salt for encryption"""
        return secrets.token_bytes(16)
    
    def save_config(self, 
                   config_name: str, 
                   config_data: Dict[str, Any],
                   scope: ConfigScope = ConfigScope.USER,
                   encryption: Optional[ConfigEncryption] = None) -> bool:
        """
        Save configuration data with encryption.
        
        Args:
            config_name: Name of the configuration
            config_data: Configuration data to save
            scope: Configuration scope
            encryption: Encryption method (defaults to instance default)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            encryption = encryption or self.default_encryption
            config_path = self._get_config_path(config_name, scope)
            backup_path = self._get_backup_path(config_path)
            
            # Create backup of existing config
            if config_path.exists():
                config_path.rename(backup_path)
            
            # Prepare data
            json_data = json.dumps(config_data, indent=2, sort_keys=True)
            data_bytes = json_data.encode('utf-8')
            
            # Calculate checksum
            checksum = self._calculate_checksum(data_bytes)
            
            # Generate salt for encryption
            salt = self._generate_salt()
            
            # Encrypt data
            encrypted_data = self.encryption_manager.encrypt_data(data_bytes, encryption, salt)
            
            # Create metadata
            metadata = ConfigMetadata(
                scope=scope,
                encryption=encryption,
                checksum=checksum,
                updated_at=self._get_current_timestamp()
            )
            
            # Prepare final config structure
            final_config = {
                "metadata": asdict(metadata),
                "salt": base64.b64encode(salt).decode('ascii'),
                "data": base64.b64encode(encrypted_data).decode('ascii')
            }
            
            # Write to file
            with open(config_path, 'w') as f:
                json.dump(final_config, f, indent=2, sort_keys=True)
            
            # Update cache
            self._cache[f"{scope.value}:{config_name}"] = config_data
            self._metadata_cache[f"{scope.value}:{config_name}"] = metadata
            
            # Clean up backup if save was successful
            if backup_path.exists():
                backup_path.unlink()
            
            logger.debug(f"Saved config '{config_name}' with scope '{scope.value}' and encryption '{encryption.value}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config '{config_name}': {e}")
            
            # Restore backup if save failed
            if backup_path.exists() and not config_path.exists():
                backup_path.rename(config_path)
            
            return False
    
    def load_config(self, 
                   config_name: str,
                   scope: ConfigScope = ConfigScope.USER,
                   default_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load configuration data with decryption.
        
        Args:
            config_name: Name of the configuration
            scope: Configuration scope
            default_data: Default data to return if config doesn't exist
            
        Returns:
            Configuration data dictionary
        """
        cache_key = f"{scope.value}:{config_name}"
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            config_path = self._get_config_path(config_name, scope)
            
            if not config_path.exists():
                if default_data is not None:
                    logger.debug(f"Config '{config_name}' not found, using defaults")
                    return default_data
                else:
                    logger.warning(f"Config '{config_name}' not found and no defaults provided")
                    return {}
            
            # Read config file
            with open(config_path, 'r') as f:
                config_structure = json.load(f)
            
            # Extract components
            metadata_dict = config_structure.get("metadata", {})
            salt_b64 = config_structure.get("salt", "")
            encrypted_data_b64 = config_structure.get("data", "")
            
            if not salt_b64 or not encrypted_data_b64:
                raise ValueError("Invalid config structure: missing salt or data")
            
            # Decode components
            salt = base64.b64decode(salt_b64)
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Get encryption method from metadata
            encryption_str = metadata_dict.get("encryption", self.default_encryption.value)
            encryption = ConfigEncryption(encryption_str)
            
            # Decrypt data
            decrypted_data = self.encryption_manager.decrypt_data(encrypted_data, encryption, salt)
            
            # Verify checksum
            expected_checksum = metadata_dict.get("checksum", "")
            if expected_checksum:
                actual_checksum = self._calculate_checksum(decrypted_data)
                if actual_checksum != expected_checksum:
                    logger.error(f"Checksum mismatch for config '{config_name}'")
                    raise ValueError("Configuration integrity check failed")
            
            # Parse JSON
            config_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Create metadata object
            metadata = ConfigMetadata(**metadata_dict)
            
            # Update cache
            self._cache[cache_key] = config_data
            self._metadata_cache[cache_key] = metadata
            
            logger.debug(f"Loaded config '{config_name}' with scope '{scope.value}'")
            return config_data
            
        except Exception as e:
            logger.error(f"Failed to load config '{config_name}': {e}")
            
            # Try to restore from backup
            backup_path = self._get_backup_path(config_path)
            if backup_path.exists():
                try:
                    logger.info(f"Attempting to restore config '{config_name}' from backup")
                    backup_path.rename(config_path)
                    return self.load_config(config_name, scope, default_data)
                except Exception as backup_e:
                    logger.error(f"Failed to restore from backup: {backup_e}")
            
            if default_data is not None:
                logger.info(f"Using default data for config '{config_name}'")
                return default_data
            else:
                return {}
    
    def delete_config(self, config_name: str, scope: ConfigScope = ConfigScope.USER) -> bool:
        """
        Delete configuration file.
        
        Args:
            config_name: Name of the configuration
            scope: Configuration scope
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            config_path = self._get_config_path(config_name, scope)
            backup_path = self._get_backup_path(config_path)
            
            # Remove from cache
            cache_key = f"{scope.value}:{config_name}"
            self._cache.pop(cache_key, None)
            self._metadata_cache.pop(cache_key, None)
            
            # Delete file
            if config_path.exists():
                config_path.unlink()
            
            # Delete backup if exists
            if backup_path.exists():
                backup_path.unlink()
            
            logger.debug(f"Deleted config '{config_name}' with scope '{scope.value}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete config '{config_name}': {e}")
            return False
    
    def list_configs(self, scope: ConfigScope = ConfigScope.USER) -> List[str]:
        """
        List available configurations for a scope.
        
        Args:
            scope: Configuration scope
            
        Returns:
            List of configuration names
        """
        try:
            scope_dir = self.config_dir / scope.value
            if not scope_dir.exists():
                return []
            
            configs = []
            for config_file in scope_dir.glob("*.json"):
                if not config_file.name.endswith('.backup'):
                    config_name = config_file.stem
                    configs.append(config_name)
            
            return sorted(configs)
            
        except Exception as e:
            logger.error(f"Failed to list configs for scope '{scope.value}': {e}")
            return []
    
    def get_config_metadata(self, config_name: str, scope: ConfigScope = ConfigScope.USER) -> Optional[ConfigMetadata]:
        """
        Get configuration metadata.
        
        Args:
            config_name: Name of the configuration
            scope: Configuration scope
            
        Returns:
            Configuration metadata or None if not found
        """
        cache_key = f"{scope.value}:{config_name}"
        
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key]
        
        # Try to load metadata from file without full decryption
        try:
            config_path = self._get_config_path(config_name, scope)
            
            if not config_path.exists():
                return None
            
            with open(config_path, 'r') as f:
                config_structure = json.load(f)
            
            metadata_dict = config_structure.get("metadata", {})
            if metadata_dict:
                metadata = ConfigMetadata(**metadata_dict)
                self._metadata_cache[cache_key] = metadata
                return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for config '{config_name}': {e}")
        
        return None
    
    def clear_cache(self) -> None:
        """Clear configuration cache"""
        self._cache.clear()
        self._metadata_cache.clear()
        logger.debug("Configuration cache cleared")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def export_config(self, config_name: str, scope: ConfigScope = ConfigScope.USER) -> Optional[Dict[str, Any]]:
        """
        Export configuration data (unencrypted) for backup or migration.
        
        Args:
            config_name: Name of the configuration
            scope: Configuration scope
            
        Returns:
            Exported configuration data or None if not found
        """
        try:
            config_data = self.load_config(config_name, scope)
            metadata = self.get_config_metadata(config_name, scope)
            
            if not config_data and not metadata:
                return None
            
            return {
                "name": config_name,
                "scope": scope.value,
                "metadata": asdict(metadata) if metadata else {},
                "data": config_data
            }
            
        except Exception as e:
            logger.error(f"Failed to export config '{config_name}': {e}")
            return None
    
    def import_config(self, exported_data: Dict[str, Any]) -> bool:
        """
        Import configuration data from export.
        
        Args:
            exported_data: Exported configuration data
            
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            config_name = exported_data.get("name")
            scope_str = exported_data.get("scope", ConfigScope.USER.value)
            metadata_dict = exported_data.get("metadata", {})
            config_data = exported_data.get("data", {})
            
            if not config_name or not config_data:
                raise ValueError("Invalid export data: missing name or data")
            
            scope = ConfigScope(scope_str)
            
            # Import with original encryption if available
            encryption_str = metadata_dict.get("encryption")
            encryption = ConfigEncryption(encryption_str) if encryption_str else None
            
            return self.save_config(config_name, config_data, scope, encryption)
            
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[Path] = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    
    return _config_manager


def cleanup_config_manager() -> None:
    """Cleanup global configuration manager"""
    global _config_manager
    
    if _config_manager:
        _config_manager.clear_cache()
        _config_manager = None


# Convenience functions for common operations
def save_gui_config(config: GuiConfig, scope: ConfigScope = ConfigScope.USER) -> bool:
    """Save GUI configuration"""
    manager = get_config_manager()
    return manager.save_config("gui", asdict(config), scope)


def load_gui_config(scope: ConfigScope = ConfigScope.USER) -> GuiConfig:
    """Load GUI configuration"""
    manager = get_config_manager()
    config_data = manager.load_config("gui", scope, asdict(GuiConfig()))
    return GuiConfig(**config_data)


def get_config_value(key: str, default: Any = None, scope: ConfigScope = ConfigScope.USER) -> Any:
    """Get a specific configuration value"""
    manager = get_config_manager()
    config_data = manager.load_config("gui", scope, {})
    return config_data.get(key, default)


def set_config_value(key: str, value: Any, scope: ConfigScope = ConfigScope.USER) -> bool:
    """Set a specific configuration value"""
    manager = get_config_manager()
    config_data = manager.load_config("gui", scope, {})
    config_data[key] = value
    return manager.save_config("gui", config_data, scope)

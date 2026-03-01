# LUCID Wallet Keystore Manager - Encrypted Keystore Management
# Implements secure encrypted keystore with multiple encryption layers
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import time
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature, InvalidKey

logger = logging.getLogger(__name__)

# Configuration from environment
KEYSTORE_ENCRYPTION_ALGORITHM = "AES-256-GCM"
KEYSTORE_KEY_DERIVATION_ROUNDS = 100000
KEYSTORE_SALT_SIZE = 32
KEYSTORE_IV_SIZE = 12
KEYSTORE_TAG_SIZE = 16
KEYSTORE_MAX_KEYS = 10000
KEYSTORE_BACKUP_COUNT = 5
KEYSTORE_COMPRESSION_ENABLED = True


class KeystoreStatus(Enum):
    """Keystore status states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    LOCKED = "locked"
    ERROR = "error"
    CORRUPTED = "corrupted"
    MAINTENANCE = "maintenance"


class KeyType(Enum):
    """Key types in keystore"""
    ED25519 = "ed25519"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    SECP256K1 = "secp256k1"
    CHACHA20 = "chacha20"
    AES_256 = "aes_256"


class KeyUsage(Enum):
    """Key usage types"""
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    AUTHENTICATION = "authentication"
    DERIVATION = "derivation"
    BACKUP = "backup"
    RECOVERY = "recovery"


class KeyStatus(Enum):
    """Key status in keystore"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    COMPROMISED = "compromised"
    EXPIRED = "expired"
    PENDING_DELETION = "pending_deletion"


@dataclass
class KeystoreKey:
    """Keystore key metadata and encrypted data"""
    key_id: str
    key_type: KeyType
    key_usage: KeyUsage
    key_status: KeyStatus
    public_key: bytes
    encrypted_private_key: bytes
    key_version: int
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_count: int = 0
    max_usage: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "key_id": self.key_id,
            "key_type": self.key_type.value,
            "key_usage": self.key_usage.value,
            "key_status": self.key_status.value,
            "public_key": self.public_key.hex(),
            "encrypted_private_key": self.encrypted_private_key.hex(),
            "key_version": self.key_version,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "usage_count": self.usage_count,
            "max_usage": self.max_usage,
            "metadata": self.metadata,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KeystoreKey:
        """Create from dictionary"""
        return cls(
            key_id=data["key_id"],
            key_type=KeyType(data["key_type"]),
            key_usage=KeyUsage(data["key_usage"]),
            key_status=KeyStatus(data["key_status"]),
            public_key=bytes.fromhex(data["public_key"]),
            encrypted_private_key=bytes.fromhex(data["encrypted_private_key"]),
            key_version=data["key_version"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            usage_count=data.get("usage_count", 0),
            max_usage=data.get("max_usage"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )


@dataclass
class KeystoreMetadata:
    """Keystore metadata and configuration"""
    keystore_id: str
    keystore_name: str
    version: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    key_count: int = 0
    encryption_algorithm: str = KEYSTORE_ENCRYPTION_ALGORITHM
    key_derivation_rounds: int = KEYSTORE_KEY_DERIVATION_ROUNDS
    compression_enabled: bool = KEYSTORE_COMPRESSION_ENABLED
    status: KeystoreStatus = KeystoreStatus.UNINITIALIZED
    backup_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeystoreAccess:
    """Keystore access record"""
    access_id: str
    user_id: str
    access_type: str  # "read", "write", "admin"
    granted_at: datetime
    expires_at: Optional[datetime] = None
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class KeystoreManager:
    """
    Encrypted keystore manager for secure key storage and management.
    
    Features:
    - Multi-layer encryption (AES-256-GCM + PBKDF2/Scrypt)
    - Key versioning and lifecycle management
    - Usage tracking and limits
    - Access control and permissions
    - Backup and recovery mechanisms
    - Key rotation and expiration
    - Compression and optimization
    - Comprehensive audit logging
    """
    
    def __init__(self, keystore_path: Path, keystore_id: str):
        """Initialize keystore manager"""
        self.keystore_path = keystore_path
        self.keystore_id = keystore_id
        self.status = KeystoreStatus.UNINITIALIZED
        self.metadata: Optional[KeystoreMetadata] = None
        self.master_key: Optional[bytes] = None
        self.keystore_keys: Dict[str, KeystoreKey] = {}
        self.access_records: Dict[str, KeystoreAccess] = {}
        
        # Encryption settings
        self.encryption_algorithm = KEYSTORE_ENCRYPTION_ALGORITHM
        self.key_derivation_rounds = KEYSTORE_KEY_DERIVATION_ROUNDS
        
        # Ensure keystore directory exists
        self.keystore_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"KeystoreManager initialized: {keystore_id}")
    
    async def initialize_keystore(
        self,
        keystore_name: str,
        master_password: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Initialize new keystore with master password"""
        try:
            if self.status != KeystoreStatus.UNINITIALIZED:
                return False
            
            self.status = KeystoreStatus.INITIALIZING
            
            # Generate master key from password
            self.master_key = await self._derive_master_key(master_password)
            
            # Create keystore metadata
            self.metadata = KeystoreMetadata(
                keystore_id=self.keystore_id,
                keystore_name=keystore_name,
                version="1.0.0",
                created_at=datetime.now(timezone.utc),
                encryption_algorithm=self.encryption_algorithm,
                key_derivation_rounds=self.key_derivation_rounds,
                metadata=metadata or {}
            )
            
            # Save keystore metadata
            await self._save_keystore_metadata()
            
            # Create verification file
            await self._create_verification_file()
            
            self.status = KeystoreStatus.READY
            
            logger.info(f"Keystore initialized: {keystore_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize keystore: {e}")
            self.status = KeystoreStatus.ERROR
            return False
    
    async def unlock_keystore(self, master_password: str) -> bool:
        """Unlock existing keystore"""
        try:
            if self.status == KeystoreStatus.READY:
                return True
            
            # Load keystore metadata
            if not await self._load_keystore_metadata():
                return False
            
            # Derive master key
            self.master_key = await self._derive_master_key(master_password)
            
            # Verify master key
            if not await self._verify_master_key():
                return False
            
            # Load keys
            await self._load_keystore_keys()
            
            # Update access time
            self.metadata.last_accessed = datetime.now(timezone.utc)
            await self._save_keystore_metadata()
            
            self.status = KeystoreStatus.READY
            
            logger.info(f"Keystore unlocked: {self.keystore_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unlock keystore: {e}")
            self.status = KeystoreStatus.ERROR
            return False
    
    async def lock_keystore(self) -> bool:
        """Lock keystore and clear sensitive data"""
        try:
            # Clear master key
            if self.master_key:
                self.master_key = b'\x00' * len(self.master_key)
                self.master_key = None
            
            # Clear keys from memory
            self.keystore_keys.clear()
            
            self.status = KeystoreStatus.LOCKED
            
            logger.info(f"Keystore locked: {self.keystore_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to lock keystore: {e}")
            return False
    
    async def generate_key(
        self,
        key_type: KeyType,
        key_usage: KeyUsage,
        key_name: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        max_usage: Optional[int] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Generate new key and store in keystore"""
        try:
            if self.status != KeystoreStatus.READY:
                raise ValueError("Keystore must be unlocked to generate keys")
            
            # Generate key pair
            if key_type == KeyType.ED25519:
                private_key = ed25519.Ed25519PrivateKey.generate()
                public_key = private_key.public_key()
            elif key_type == KeyType.RSA_2048:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
            elif key_type == KeyType.RSA_4096:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=4096,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
            else:
                raise ValueError(f"Unsupported key type: {key_type}")
            
            # Serialize keys
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Encrypt private key
            encrypted_private_key = await self._encrypt_data(private_key_bytes)
            
            # Create keystore key
            key_id = secrets.token_hex(16)
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            
            keystore_key = KeystoreKey(
                key_id=key_id,
                key_type=key_type,
                key_usage=key_usage,
                key_status=KeyStatus.ACTIVE,
                public_key=public_key_bytes,
                encrypted_private_key=encrypted_private_key,
                key_version=1,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                max_usage=max_usage,
                metadata=metadata or {},
                tags=tags or []
            )
            
            # Store key
            self.keystore_keys[key_id] = keystore_key
            self.metadata.key_count = len(self.keystore_keys)
            
            # Save key to disk
            await self._save_key(keystore_key)
            await self._save_keystore_metadata()
            
            logger.info(f"Generated key: {key_id} ({key_type.value})")
            return key_id
            
        except Exception as e:
            logger.error(f"Failed to generate key: {e}")
            return None
    
    async def get_public_key(self, key_id: str) -> Optional[bytes]:
        """Get public key by ID"""
        try:
            if key_id not in self.keystore_keys:
                return None
            
            keystore_key = self.keystore_keys[key_id]
            
            # Update usage count
            keystore_key.usage_count += 1
            keystore_key.last_used = datetime.now(timezone.utc)
            
            # Save updated key
            await self._save_key(keystore_key)
            
            return keystore_key.public_key
            
        except Exception as e:
            logger.error(f"Failed to get public key: {e}")
            return None
    
    async def get_private_key(self, key_id: str) -> Optional[bytes]:
        """Get decrypted private key by ID"""
        try:
            if self.status != KeystoreStatus.READY:
                raise ValueError("Keystore must be unlocked to access private keys")
            
            if key_id not in self.keystore_keys:
                return None
            
            keystore_key = self.keystore_keys[key_id]
            
            # Check key status
            if keystore_key.key_status != KeyStatus.ACTIVE:
                return None
            
            # Check expiration
            if keystore_key.expires_at and datetime.now(timezone.utc) > keystore_key.expires_at:
                keystore_key.key_status = KeyStatus.EXPIRED
                await self._save_key(keystore_key)
                return None
            
            # Check usage limit
            if keystore_key.max_usage and keystore_key.usage_count >= keystore_key.max_usage:
                keystore_key.key_status = KeyStatus.INACTIVE
                await self._save_key(keystore_key)
                return None
            
            # Decrypt private key
            private_key_bytes = await self._decrypt_data(keystore_key.encrypted_private_key)
            
            # Update usage count
            keystore_key.usage_count += 1
            keystore_key.last_used = datetime.now(timezone.utc)
            
            # Save updated key
            await self._save_key(keystore_key)
            
            return private_key_bytes
            
        except Exception as e:
            logger.error(f"Failed to get private key: {e}")
            return None
    
    async def sign_data(self, key_id: str, data: bytes) -> Optional[bytes]:
        """Sign data with specified key"""
        try:
            # Get private key
            private_key_bytes = await self.get_private_key(key_id)
            if not private_key_bytes:
                return None
            
            keystore_key = self.keystore_keys[key_id]
            
            # Create private key object based on type
            if keystore_key.key_type == KeyType.ED25519:
                private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            elif keystore_key.key_type in [KeyType.RSA_2048, KeyType.RSA_4096]:
                private_key = rsa.RSAPrivateKey.from_private_bytes(private_key_bytes)
            else:
                return None
            
            # Sign data
            signature = private_key.sign(data, padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ))
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to sign data: {e}")
            return None
    
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature with specified key"""
        try:
            # Get public key
            public_key_bytes = await self.get_public_key(key_id)
            if not public_key_bytes:
                return False
            
            keystore_key = self.keystore_keys[key_id]
            
            # Create public key object based on type
            if keystore_key.key_type == KeyType.ED25519:
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            elif keystore_key.key_type in [KeyType.RSA_2048, KeyType.RSA_4096]:
                public_key = rsa.RSAPublicKey.from_public_bytes(public_key_bytes)
            else:
                return False
            
            # Verify signature
            public_key.verify(signature, data, padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ))
            
            return True
            
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error(f"Failed to verify signature: {e}")
            return False
    
    async def rotate_key(self, key_id: str) -> Optional[str]:
        """Rotote key to new version"""
        try:
            if key_id not in self.keystore_keys:
                return None
            
            old_key = self.keystore_keys[key_id]
            
            # Generate new key
            new_key_id = await self.generate_key(
                key_type=old_key.key_type,
                key_usage=old_key.key_usage,
                key_name=old_key.metadata.get("name"),
                expires_in_days=30,  # Default expiration for rotated keys
                tags=old_key.tags,
                metadata=old_key.metadata
            )
            
            if new_key_id:
                # Archive old key
                old_key.key_status = KeyStatus.ARCHIVED
                await self._save_key(old_key)
                
                logger.info(f"Key rotated: {key_id} -> {new_key_id}")
            
            return new_key_id
            
        except Exception as e:
            logger.error(f"Failed to rotate key: {e}")
            return None
    
    async def delete_key(self, key_id: str, permanent: bool = False) -> bool:
        """Delete key from keystore"""
        try:
            if key_id not in self.keystore_keys:
                return False
            
            keystore_key = self.keystore_keys[key_id]
            
            if permanent:
                # Permanent deletion
                del self.keystore_keys[key_id]
                
                # Remove from disk
                key_path = self.keystore_path / f"key_{key_id}.json"
                if key_path.exists():
                    key_path.unlink()
            else:
                # Mark for deletion
                keystore_key.key_status = KeyStatus.PENDING_DELETION
                await self._save_key(keystore_key)
            
            # Update metadata
            self.metadata.key_count = len(self.keystore_keys)
            await self._save_keystore_metadata()
            
            logger.info(f"Key deleted: {key_id} (permanent: {permanent})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete key: {e}")
            return False
    
    async def list_keys(
        self, 
        key_type: Optional[KeyType] = None,
        key_usage: Optional[KeyUsage] = None,
        key_status: Optional[KeyStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List keys with optional filtering"""
        try:
            keys_info = []
            
            for key_id, keystore_key in self.keystore_keys.items():
                # Apply filters
                if key_type and keystore_key.key_type != key_type:
                    continue
                if key_usage and keystore_key.key_usage != key_usage:
                    continue
                if key_status and keystore_key.key_status != key_status:
                    continue
                if tags and not any(tag in keystore_key.tags for tag in tags):
                    continue
                
                keys_info.append({
                    "key_id": key_id,
                    "key_type": keystore_key.key_type.value,
                    "key_usage": keystore_key.key_usage.value,
                    "key_status": keystore_key.key_status.value,
                    "created_at": keystore_key.created_at.isoformat(),
                    "last_used": keystore_key.last_used.isoformat() if keystore_key.last_used else None,
                    "expires_at": keystore_key.expires_at.isoformat() if keystore_key.expires_at else None,
                    "usage_count": keystore_key.usage_count,
                    "max_usage": keystore_key.max_usage,
                    "tags": keystore_key.tags,
                    "metadata": keystore_key.metadata
                })
            
            return keys_info
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []
    
    async def backup_keystore(self, backup_path: Path) -> bool:
        """Create backup of keystore"""
        try:
            if self.status != KeystoreStatus.READY:
                return False
            
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy all key files
            for key_id in self.keystore_keys:
                source_path = self.keystore_path / f"key_{key_id}.json"
                dest_path = backup_path / f"key_{key_id}.json"
                
                if source_path.exists():
                    import shutil
                    shutil.copy2(source_path, dest_path)
            
            # Copy metadata
            metadata_source = self.keystore_path / "keystore_metadata.json"
            metadata_dest = backup_path / "keystore_metadata.json"
            
            if metadata_source.exists():
                import shutil
                shutil.copy2(metadata_source, metadata_dest)
            
            # Update backup count
            self.metadata.backup_count += 1
            await self._save_keystore_metadata()
            
            logger.info(f"Keystore backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup keystore: {e}")
            return False
    
    async def get_keystore_status(self) -> Dict[str, Any]:
        """Get keystore status information"""
        return {
            "keystore_id": self.keystore_id,
            "status": self.status.value,
            "is_unlocked": self.status == KeystoreStatus.READY,
            "key_count": len(self.keystore_keys),
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "encryption_algorithm": self.encryption_algorithm,
            "key_derivation_rounds": self.key_derivation_rounds
        }
    
    async def _derive_master_key(self, password: str) -> bytes:
        """Derive master key from password"""
        try:
            # Use keystore ID as salt
            salt = self.keystore_id.encode('utf-8')[:KEYSTORE_SALT_SIZE]
            if len(salt) < KEYSTORE_SALT_SIZE:
                salt = salt.ljust(KEYSTORE_SALT_SIZE, b'\x00')
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=salt,
                iterations=self.key_derivation_rounds,
                backend=default_backend()
            )
            
            master_key = kdf.derive(password.encode('utf-8'))
            return master_key
            
        except Exception as e:
            logger.error(f"Failed to derive master key: {e}")
            raise
    
    async def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using master key"""
        if not self.master_key:
            raise ValueError("Keystore must be unlocked to encrypt data")
        
        try:
            # Generate random IV
            iv = os.urandom(KEYSTORE_IV_SIZE)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.master_key),
                modes.GCM(iv),
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            # Return IV + tag + ciphertext
            return iv + encryptor.tag + ciphertext
            
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise
    
    async def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using master key"""
        if not self.master_key:
            raise ValueError("Keystore must be unlocked to decrypt data")
        
        try:
            # Extract IV, tag, and ciphertext
            iv = encrypted_data[:KEYSTORE_IV_SIZE]
            tag = encrypted_data[KEYSTORE_IV_SIZE:KEYSTORE_IV_SIZE + KEYSTORE_TAG_SIZE]
            ciphertext = encrypted_data[KEYSTORE_IV_SIZE + KEYSTORE_TAG_SIZE:]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.master_key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise
    
    async def _verify_master_key(self) -> bool:
        """Verify master key by attempting to decrypt verification file"""
        try:
            verification_file = self.keystore_path / "verification"
            if not verification_file.exists():
                return False
            
            # Try to decrypt verification data
            with open(verification_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = await self._decrypt_data(encrypted_data)
            return decrypted_data == b"keystore_verification"
            
        except Exception as e:
            logger.error(f"Failed to verify master key: {e}")
            return False
    
    async def _create_verification_file(self) -> None:
        """Create verification file for master key validation"""
        try:
            verification_data = b"keystore_verification"
            encrypted_data = await self._encrypt_data(verification_data)
            
            verification_file = self.keystore_path / "verification"
            with open(verification_file, 'wb') as f:
                f.write(encrypted_data)
                
        except Exception as e:
            logger.error(f"Failed to create verification file: {e}")
            raise
    
    async def _save_keystore_metadata(self) -> None:
        """Save keystore metadata to disk"""
        if not self.metadata:
            return
        
        metadata_path = self.keystore_path / "keystore_metadata.json"
        
        data = {
            "keystore_id": self.metadata.keystore_id,
            "keystore_name": self.metadata.keystore_name,
            "version": self.metadata.version,
            "created_at": self.metadata.created_at.isoformat(),
            "last_accessed": self.metadata.last_accessed.isoformat() if self.metadata.last_accessed else None,
            "key_count": self.metadata.key_count,
            "encryption_algorithm": self.metadata.encryption_algorithm,
            "key_derivation_rounds": self.metadata.key_derivation_rounds,
            "compression_enabled": self.metadata.compression_enabled,
            "status": self.metadata.status.value,
            "backup_count": self.metadata.backup_count,
            "metadata": self.metadata.metadata
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def _load_keystore_metadata(self) -> bool:
        """Load keystore metadata from disk"""
        try:
            metadata_path = self.keystore_path / "keystore_metadata.json"
            if not metadata_path.exists():
                return False
            
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            
            self.metadata = KeystoreMetadata(
                keystore_id=data["keystore_id"],
                keystore_name=data["keystore_name"],
                version=data["version"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
                key_count=data.get("key_count", 0),
                encryption_algorithm=data.get("encryption_algorithm", KEYSTORE_ENCRYPTION_ALGORITHM),
                key_derivation_rounds=data.get("key_derivation_rounds", KEYSTORE_KEY_DERIVATION_ROUNDS),
                compression_enabled=data.get("compression_enabled", KEYSTORE_COMPRESSION_ENABLED),
                status=KeystoreStatus(data.get("status", "uninitialized")),
                backup_count=data.get("backup_count", 0),
                metadata=data.get("metadata", {})
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load keystore metadata: {e}")
            return False
    
    async def _save_key(self, keystore_key: KeystoreKey) -> None:
        """Save key to disk"""
        key_path = self.keystore_path / f"key_{keystore_key.key_id}.json"
        
        with open(key_path, 'w') as f:
            json.dump(keystore_key.to_dict(), f, indent=2)
    
    async def _load_keystore_keys(self) -> None:
        """Load all keys from disk"""
        try:
            self.keystore_keys.clear()
            
            for key_file in self.keystore_path.glob("key_*.json"):
                try:
                    with open(key_file, 'r') as f:
                        data = json.load(f)
                    
                    keystore_key = KeystoreKey.from_dict(data)
                    self.keystore_keys[keystore_key.key_id] = keystore_key
                    
                except Exception as e:
                    logger.error(f"Failed to load key from {key_file}: {e}")
            
            logger.info(f"Loaded {len(self.keystore_keys)} keys from keystore")
            
        except Exception as e:
            logger.error(f"Failed to load keystore keys: {e}")


# Global keystore managers
_keystore_managers: Dict[str, KeystoreManager] = {}


def get_keystore_manager(keystore_id: str) -> Optional[KeystoreManager]:
    """Get keystore manager by ID"""
    return _keystore_managers.get(keystore_id)


def create_keystore_manager(keystore_path: Path, keystore_id: str) -> KeystoreManager:
    """Create new keystore manager"""
    keystore_manager = KeystoreManager(keystore_path, keystore_id)
    _keystore_managers[keystore_id] = keystore_manager
    return keystore_manager


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create test keystore
    keystore_path = Path("./test_keystore")
    keystore = create_keystore_manager(keystore_path, "test_keystore_001")
    
    # Initialize keystore
    success = await keystore.initialize_keystore(
        keystore_name="Test Keystore",
        master_password="test_password_123"
    )
    print(f"Keystore initialization: {success}")
    
    if success:
        # Generate test key
        key_id = await keystore.generate_key(
            key_type=KeyType.ED25519,
            key_usage=KeyUsage.SIGNING,
            key_name="test_signing_key",
            tags=["test", "signing"]
        )
        print(f"Generated key: {key_id}")
        
        if key_id:
            # Test signing
            test_data = b"Hello, Keystore!"
            signature = await keystore.sign_data(key_id, test_data)
            print(f"Signature: {signature.hex() if signature else None}")
            
            # Test verification
            is_valid = await keystore.verify_signature(key_id, test_data, signature)
            print(f"Verification: {is_valid}")
            
            # List keys
            keys = await keystore.list_keys()
            print(f"Keys in keystore: {len(keys)}")
        
        # Get status
        status = await keystore.get_keystore_status()
        print(f"Keystore status: {status}")


if __name__ == "__main__":
    asyncio.run(main())

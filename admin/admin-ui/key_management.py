# Path: admin/admin-ui/key_management.py
# Lucid Admin UI - Key Management Interface
# Provides secure key rotation and management capabilities
# LUCID-STRICT Layer 1 Core Infrastructure

from __future__ import annotations

import asyncio
import logging
import os
import json
import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import aiofiles

logger = logging.getLogger(__name__)

# Configuration from environment
KEY_STORAGE_PATH = Path(os.getenv("KEY_STORAGE_PATH", "/secrets/keys"))
KEY_ROTATION_INTERVAL = int(os.getenv("KEY_ROTATION_INTERVAL", "86400"))  # 24 hours
KEY_BACKUP_COUNT = int(os.getenv("KEY_BACKUP_COUNT", "5"))
MASTER_KEY_PATH = Path(os.getenv("MASTER_KEY_PATH", "/secrets/master.key"))
KEY_ENCRYPTION_ALGORITHM = os.getenv("KEY_ENCRYPTION_ALGORITHM", "AES-256-GCM")


class KeyType(Enum):
    """Types of cryptographic keys"""
    RSA_PRIVATE = "rsa_private"
    RSA_PUBLIC = "rsa_public"
    AES_SYMMETRIC = "aes_symmetric"
    ECDSA_PRIVATE = "ecdsa_private"
    ECDSA_PUBLIC = "ecdsa_public"
    MASTER_KEY = "master_key"
    SESSION_KEY = "session_key"
    WALLET_KEY = "wallet_key"


class KeyStatus(Enum):
    """Key status states"""
    ACTIVE = "active"
    ROTATING = "rotating"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class KeyUsage(Enum):
    """Key usage purposes"""
    ENCRYPTION = "encryption"
    SIGNING = "signing"
    AUTHENTICATION = "authentication"
    SESSION_MANAGEMENT = "session_management"
    WALLET_OPERATIONS = "wallet_operations"
    BLOCKCHAIN_SIGNING = "blockchain_signing"


@dataclass
class KeyMetadata:
    """Metadata for a cryptographic key"""
    key_id: str
    key_type: KeyType
    usage: KeyUsage
    status: KeyStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    rotation_count: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeyRotationPolicy:
    """Key rotation policy configuration"""
    key_type: KeyType
    rotation_interval_hours: int
    max_key_age_hours: int
    auto_rotation: bool = True
    require_manual_approval: bool = False
    backup_retention_count: int = 5
    notification_before_hours: int = 24


@dataclass
class KeyRotationResult:
    """Result of a key rotation operation"""
    success: bool
    old_key_id: str
    new_key_id: str
    rotation_timestamp: datetime
    backup_location: Optional[str] = None
    error_message: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)


class KeyManager:
    """Secure key management and rotation service"""
    
    def __init__(self):
        self.key_storage_path = KEY_STORAGE_PATH
        self.master_key_path = MASTER_KEY_PATH
        self.rotation_policies: Dict[KeyType, KeyRotationPolicy] = {}
        self._initialize_storage()
        self._load_rotation_policies()
        self._ensure_master_key()
    
    def _initialize_storage(self):
        """Initialize key storage directories"""
        try:
            self.key_storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.master_key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            logger.info(f"Key storage initialized at {self.key_storage_path}")
        except Exception as e:
            logger.error(f"Failed to initialize key storage: {e}")
            raise
    
    def _load_rotation_policies(self):
        """Load key rotation policies"""
        default_policies = {
            KeyType.RSA_PRIVATE: KeyRotationPolicy(
                key_type=KeyType.RSA_PRIVATE,
                rotation_interval_hours=24 * 7,  # 7 days
                max_key_age_hours=24 * 30,  # 30 days
                auto_rotation=True,
                require_manual_approval=False,
                backup_retention_count=5
            ),
            KeyType.AES_SYMMETRIC: KeyRotationPolicy(
                key_type=KeyType.AES_SYMMETRIC,
                rotation_interval_hours=24,  # 1 day
                max_key_age_hours=24 * 7,  # 7 days
                auto_rotation=True,
                require_manual_approval=False,
                backup_retention_count=3
            ),
            KeyType.SESSION_KEY: KeyRotationPolicy(
                key_type=KeyType.SESSION_KEY,
                rotation_interval_hours=1,  # 1 hour
                max_key_age_hours=24,  # 1 day
                auto_rotation=True,
                require_manual_approval=False,
                backup_retention_count=2
            ),
            KeyType.WALLET_KEY: KeyRotationPolicy(
                key_type=KeyType.WALLET_KEY,
                rotation_interval_hours=24 * 30,  # 30 days
                max_key_age_hours=24 * 90,  # 90 days
                auto_rotation=False,
                require_manual_approval=True,
                backup_retention_count=10
            )
        }
        
        self.rotation_policies = default_policies
        logger.info("Key rotation policies loaded")
    
    def _ensure_master_key(self):
        """Ensure master key exists for encrypting other keys"""
        if not self.master_key_path.exists():
            logger.info("Creating new master key")
            master_key = self._generate_aes_key()
            self._save_master_key(master_key)
        else:
            logger.info("Master key already exists")
    
    def _generate_aes_key(self) -> bytes:
        """Generate a new AES-256 key"""
        return secrets.token_bytes(32)  # 256 bits
    
    def _generate_rsa_keypair(self, key_size: int = 2048) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Generate a new RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    def _save_master_key(self, master_key: bytes):
        """Save the master key securely"""
        try:
            # In production, this should be stored in a hardware security module
            with open(self.master_key_path, 'wb') as f:
                f.write(master_key)
            self.master_key_path.chmod(0o600)
            logger.info("Master key saved securely")
        except Exception as e:
            logger.error(f"Failed to save master key: {e}")
            raise
    
    def _load_master_key(self) -> bytes:
        """Load the master key"""
        try:
            with open(self.master_key_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load master key: {e}")
            raise
    
    def _encrypt_key(self, key_data: bytes, key_id: str) -> bytes:
        """Encrypt key data using the master key"""
        try:
            master_key = self._load_master_key()
            
            # Generate a random IV
            iv = secrets.token_bytes(12)  # 96 bits for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(master_key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt the key data
            ciphertext = encryptor.update(key_data) + encryptor.finalize()
            
            # Combine IV, tag, and ciphertext
            encrypted_data = iv + encryptor.tag + ciphertext
            
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Failed to encrypt key {key_id}: {e}")
            raise
    
    def _decrypt_key(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt key data using the master key"""
        try:
            master_key = self._load_master_key()
            
            # Extract IV, tag, and ciphertext
            iv = encrypted_data[:12]
            tag = encrypted_data[12:28]
            ciphertext = encrypted_data[28:]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(master_key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt the key data
            key_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            return key_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt key {key_id}: {e}")
            raise
    
    async def generate_key(self, key_type: KeyType, usage: KeyUsage, 
                          description: str = "", tags: List[str] = None,
                          expires_in_hours: Optional[int] = None) -> str:
        """Generate a new cryptographic key"""
        try:
            key_id = self._generate_key_id(key_type, usage)
            
            # Generate key based on type
            if key_type in [KeyType.RSA_PRIVATE, KeyType.RSA_PUBLIC]:
                private_key, public_key = self._generate_rsa_keypair()
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            elif key_type == KeyType.AES_SYMMETRIC:
                key_data = self._generate_aes_key()
            else:
                raise ValueError(f"Unsupported key type: {key_type}")
            
            # Create metadata
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            
            metadata = KeyMetadata(
                key_id=key_id,
                key_type=key_type,
                usage=usage,
                status=KeyStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                description=description,
                tags=tags or []
            )
            
            # Encrypt and save key
            encrypted_key = self._encrypt_key(key_data, key_id)
            await self._save_key(key_id, encrypted_key, metadata)
            
            logger.info(f"Generated new key: {key_id} ({key_type.value})")
            return key_id
            
        except Exception as e:
            logger.error(f"Failed to generate key: {e}")
            raise
    
    def _generate_key_id(self, key_type: KeyType, usage: KeyUsage) -> str:
        """Generate a unique key ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"{key_type.value}_{usage.value}_{timestamp}_{random_suffix}"
    
    async def _save_key(self, key_id: str, encrypted_key: bytes, metadata: KeyMetadata):
        """Save encrypted key and metadata"""
        try:
            # Save encrypted key
            key_file = self.key_storage_path / f"{key_id}.key"
            async with aiofiles.open(key_file, 'wb') as f:
                await f.write(encrypted_key)
            key_file.chmod(0o600)
            
            # Save metadata
            metadata_file = self.key_storage_path / f"{key_id}.meta"
            metadata_dict = {
                "key_id": metadata.key_id,
                "key_type": metadata.key_type.value,
                "usage": metadata.usage.value,
                "status": metadata.status.value,
                "created_at": metadata.created_at.isoformat(),
                "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
                "last_used": metadata.last_used.isoformat() if metadata.last_used else None,
                "rotation_count": metadata.rotation_count,
                "description": metadata.description,
                "tags": metadata.tags,
                "metadata": metadata.metadata
            }
            
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(metadata_dict, indent=2))
            metadata_file.chmod(0o600)
            
        except Exception as e:
            logger.error(f"Failed to save key {key_id}: {e}")
            raise
    
    async def get_key(self, key_id: str) -> Tuple[bytes, KeyMetadata]:
        """Retrieve and decrypt a key"""
        try:
            # Load metadata
            metadata_file = self.key_storage_path / f"{key_id}.meta"
            if not metadata_file.exists():
                raise FileNotFoundError(f"Key metadata not found: {key_id}")
            
            async with aiofiles.open(metadata_file, 'r') as f:
                metadata_dict = json.loads(await f.read())
            
            metadata = KeyMetadata(
                key_id=metadata_dict["key_id"],
                key_type=KeyType(metadata_dict["key_type"]),
                usage=KeyUsage(metadata_dict["usage"]),
                status=KeyStatus(metadata_dict["status"]),
                created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                expires_at=datetime.fromisoformat(metadata_dict["expires_at"]) if metadata_dict["expires_at"] else None,
                last_used=datetime.fromisoformat(metadata_dict["last_used"]) if metadata_dict["last_used"] else None,
                rotation_count=metadata_dict["rotation_count"],
                description=metadata_dict["description"],
                tags=metadata_dict["tags"],
                metadata=metadata_dict["metadata"]
            )
            
            # Load and decrypt key
            key_file = self.key_storage_path / f"{key_id}.key"
            if not key_file.exists():
                raise FileNotFoundError(f"Key file not found: {key_id}")
            
            async with aiofiles.open(key_file, 'rb') as f:
                encrypted_key = await f.read()
            
            key_data = self._decrypt_key(encrypted_key, key_id)
            
            # Update last used timestamp
            metadata.last_used = datetime.now(timezone.utc)
            await self._save_key(key_id, encrypted_key, metadata)
            
            return key_data, metadata
            
        except Exception as e:
            logger.error(f"Failed to get key {key_id}: {e}")
            raise
    
    async def list_keys(self, key_type: Optional[KeyType] = None, 
                       usage: Optional[KeyUsage] = None,
                       status: Optional[KeyStatus] = None) -> List[KeyMetadata]:
        """List all keys matching the criteria"""
        try:
            keys = []
            
            for metadata_file in self.key_storage_path.glob("*.meta"):
                try:
                    async with aiofiles.open(metadata_file, 'r') as f:
                        metadata_dict = json.loads(await f.read())
                    
                    metadata = KeyMetadata(
                        key_id=metadata_dict["key_id"],
                        key_type=KeyType(metadata_dict["key_type"]),
                        usage=KeyUsage(metadata_dict["usage"]),
                        status=KeyStatus(metadata_dict["status"]),
                        created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                        expires_at=datetime.fromisoformat(metadata_dict["expires_at"]) if metadata_dict["expires_at"] else None,
                        last_used=datetime.fromisoformat(metadata_dict["last_used"]) if metadata_dict["last_used"] else None,
                        rotation_count=metadata_dict["rotation_count"],
                        description=metadata_dict["description"],
                        tags=metadata_dict["tags"],
                        metadata=metadata_dict["metadata"]
                    )
                    
                    # Apply filters
                    if key_type and metadata.key_type != key_type:
                        continue
                    if usage and metadata.usage != usage:
                        continue
                    if status and metadata.status != status:
                        continue
                    
                    keys.append(metadata)
                    
                except Exception as e:
                    logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
                    continue
            
            return sorted(keys, key=lambda k: k.created_at, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            raise
    
    async def rotate_key(self, key_id: str, force: bool = False) -> KeyRotationResult:
        """Rotate a cryptographic key"""
        try:
            # Get current key and metadata
            old_key_data, old_metadata = await self.get_key(key_id)
            
            # Check if rotation is needed
            if not force and not self._should_rotate_key(old_metadata):
                return KeyRotationResult(
                    success=False,
                    old_key_id=key_id,
                    new_key_id="",
                    rotation_timestamp=datetime.now(timezone.utc),
                    error_message="Key rotation not needed"
                )
            
            # Generate new key
            new_key_id = await self.generate_key(
                key_type=old_metadata.key_type,
                usage=old_metadata.usage,
                description=f"Rotated from {key_id}",
                tags=old_metadata.tags + ["rotated"],
                expires_in_hours=None  # Use default expiration
            )
            
            # Backup old key
            backup_location = await self._backup_key(key_id)
            
            # Update old key status
            old_metadata.status = KeyStatus.ROTATING
            await self._save_key(key_id, old_key_data, old_metadata)
            
            # Notify affected services
            affected_services = await self._notify_key_rotation(key_id, new_key_id)
            
            logger.info(f"Successfully rotated key {key_id} to {new_key_id}")
            
            return KeyRotationResult(
                success=True,
                old_key_id=key_id,
                new_key_id=new_key_id,
                rotation_timestamp=datetime.now(timezone.utc),
                backup_location=backup_location,
                affected_services=affected_services
            )
            
        except Exception as e:
            logger.error(f"Failed to rotate key {key_id}: {e}")
            return KeyRotationResult(
                success=False,
                old_key_id=key_id,
                new_key_id="",
                rotation_timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    def _should_rotate_key(self, metadata: KeyMetadata) -> bool:
        """Check if a key should be rotated based on policy"""
        if metadata.status != KeyStatus.ACTIVE:
            return False
        
        policy = self.rotation_policies.get(metadata.key_type)
        if not policy:
            return False
        
        # Check if key is expired
        if metadata.expires_at and metadata.expires_at <= datetime.now(timezone.utc):
            return True
        
        # Check rotation interval
        if policy.auto_rotation:
            last_rotation = metadata.created_at
            if metadata.last_used:
                last_rotation = max(last_rotation, metadata.last_used)
            
            rotation_threshold = datetime.now(timezone.utc) - timedelta(hours=policy.rotation_interval_hours)
            if last_rotation <= rotation_threshold:
                return True
        
        return False
    
    async def _backup_key(self, key_id: str) -> str:
        """Create a backup of a key"""
        try:
            backup_dir = self.key_storage_path / "backups" / key_id
            backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{key_id}_{timestamp}"
            
            # Copy key files
            key_file = self.key_storage_path / f"{key_id}.key"
            metadata_file = self.key_storage_path / f"{key_id}.meta"
            
            if key_file.exists():
                async with aiofiles.open(key_file, 'rb') as src, aiofiles.open(f"{backup_path}.key", 'wb') as dst:
                    await dst.write(await src.read())
            
            if metadata_file.exists():
                async with aiofiles.open(metadata_file, 'r') as src, aiofiles.open(f"{backup_path}.meta", 'w') as dst:
                    await dst.write(await src.read())
            
            # Clean up old backups
            await self._cleanup_old_backups(key_id)
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to backup key {key_id}: {e}")
            raise
    
    async def _cleanup_old_backups(self, key_id: str):
        """Clean up old key backups based on retention policy"""
        try:
            backup_dir = self.key_storage_path / "backups" / key_id
            if not backup_dir.exists():
                return
            
            # Get all backup files
            backup_files = list(backup_dir.glob(f"{key_id}_*"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Get retention count from policy
            policy = self.rotation_policies.get(KeyType.RSA_PRIVATE)  # Default policy
            retention_count = policy.backup_retention_count if policy else 5
            
            # Remove old backups
            for backup_file in backup_files[retention_count:]:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups for {key_id}: {e}")
    
    async def _notify_key_rotation(self, old_key_id: str, new_key_id: str) -> List[str]:
        """Notify services about key rotation"""
        affected_services = []
        
        try:
            # In a real implementation, this would notify actual services
            # For now, we'll just log the rotation
            logger.info(f"Key rotation notification: {old_key_id} -> {new_key_id}")
            
            # Simulate service notifications
            services = ["authentication", "wallet", "blockchain", "sessions"]
            for service in services:
                # In production, this would send actual notifications
                affected_services.append(service)
                logger.info(f"Notified service {service} about key rotation")
            
        except Exception as e:
            logger.error(f"Failed to notify services about key rotation: {e}")
        
        return affected_services
    
    async def revoke_key(self, key_id: str, reason: str = "") -> bool:
        """Revoke a key"""
        try:
            key_data, metadata = await self.get_key(key_id)
            
            metadata.status = KeyStatus.REVOKED
            metadata.metadata["revocation_reason"] = reason
            metadata.metadata["revoked_at"] = datetime.now(timezone.utc).isoformat()
            
            await self._save_key(key_id, key_data, metadata)
            
            logger.info(f"Revoked key {key_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke key {key_id}: {e}")
            return False
    
    async def get_rotation_schedule(self) -> List[Dict[str, Any]]:
        """Get upcoming key rotations"""
        try:
            schedule = []
            keys = await self.list_keys(status=KeyStatus.ACTIVE)
            
            for key_metadata in keys:
                policy = self.rotation_policies.get(key_metadata.key_type)
                if not policy:
                    continue
                
                # Calculate next rotation time
                last_rotation = key_metadata.created_at
                if key_metadata.last_used:
                    last_rotation = max(last_rotation, key_metadata.last_used)
                
                next_rotation = last_rotation + timedelta(hours=policy.rotation_interval_hours)
                
                schedule.append({
                    "key_id": key_metadata.key_id,
                    "key_type": key_metadata.key_type.value,
                    "usage": key_metadata.usage.value,
                    "next_rotation": next_rotation.isoformat(),
                    "days_until_rotation": (next_rotation - datetime.now(timezone.utc)).days,
                    "auto_rotation": policy.auto_rotation,
                    "requires_approval": policy.require_manual_approval
                })
            
            return sorted(schedule, key=lambda x: x["next_rotation"])
            
        except Exception as e:
            logger.error(f"Failed to get rotation schedule: {e}")
            raise
    
    async def auto_rotate_keys(self) -> List[KeyRotationResult]:
        """Automatically rotate keys that need rotation"""
        try:
            results = []
            keys = await self.list_keys(status=KeyStatus.ACTIVE)
            
            for key_metadata in keys:
                if self._should_rotate_key(key_metadata):
                    policy = self.rotation_policies.get(key_metadata.key_type)
                    if policy and policy.auto_rotation and not policy.require_manual_approval:
                        result = await self.rotate_key(key_metadata.key_id)
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to auto-rotate keys: {e}")
            raise


# Global key manager instance
key_manager = KeyManager()


async def generate_new_key(key_type: KeyType, usage: KeyUsage, 
                          description: str = "", tags: List[str] = None) -> str:
    """Generate a new cryptographic key"""
    return await key_manager.generate_key(key_type, usage, description, tags)


async def get_key_data(key_id: str) -> Tuple[bytes, KeyMetadata]:
    """Get key data and metadata"""
    return await key_manager.get_key(key_id)


async def list_all_keys(key_type: Optional[KeyType] = None, 
                       usage: Optional[KeyUsage] = None) -> List[KeyMetadata]:
    """List all keys"""
    return await key_manager.list_keys(key_type, usage)


async def rotate_key_now(key_id: str, force: bool = False) -> KeyRotationResult:
    """Rotate a key immediately"""
    return await key_manager.rotate_key(key_id, force)


async def get_rotation_schedule() -> List[Dict[str, Any]]:
    """Get upcoming key rotations"""
    return await key_manager.get_rotation_schedule()


async def auto_rotate_all_keys() -> List[KeyRotationResult]:
    """Automatically rotate all keys that need rotation"""
    return await key_manager.auto_rotate_keys()


if __name__ == "__main__":
    # Test the key management service
    async def test_key_management():
        # Generate a test key
        key_id = await generate_new_key(
            KeyType.RSA_PRIVATE,
            KeyUsage.ENCRYPTION,
            "Test encryption key",
            ["test", "demo"]
        )
        print(f"Generated key: {key_id}")
        
        # List all keys
        keys = await list_all_keys()
        print(f"Total keys: {len(keys)}")
        
        # Get rotation schedule
        schedule = await get_rotation_schedule()
        print(f"Rotation schedule: {len(schedule)} keys")
        
        # Clean up test key
        await key_manager.revoke_key(key_id, "Test cleanup")
        print("Test key revoked")
    
    asyncio.run(test_key_management())

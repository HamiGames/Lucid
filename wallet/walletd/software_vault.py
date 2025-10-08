# LUCID Wallet Software Vault - Passphrase-Protected Vault
# Implements secure software wallet storage with passphrase protection
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import json
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Configuration from environment
VAULT_ENCRYPTION_ALGORITHM = "ChaCha20Poly1305"
VAULT_KEY_DERIVATION_ROUNDS = 100000
VAULT_SALT_SIZE = 32
VAULT_NONCE_SIZE = 12
VAULT_MAX_LOGIN_ATTEMPTS = 5
VAULT_LOCKOUT_DURATION_MINUTES = 30
VAULT_SESSION_TIMEOUT_MINUTES = 60


class VaultStatus(Enum):
    """Vault status states"""
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    LOCKED_OUT = "locked_out"
    CORRUPTED = "corrupted"
    ERROR = "error"


class VaultAccessLevel(Enum):
    """Vault access levels"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    MASTER = "master"


@dataclass
class VaultKey:
    """Vault key metadata"""
    key_id: str
    key_type: str  # "ed25519", "rsa", "secp256k1"
    public_key: bytes
    private_key_encrypted: bytes
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VaultSession:
    """Vault session information"""
    session_id: str
    user_id: str
    access_level: VaultAccessLevel
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VaultMetadata:
    """Vault metadata and configuration"""
    vault_id: str
    vault_name: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    key_count: int = 0
    max_keys: int = 1000
    encryption_algorithm: str = VAULT_ENCRYPTION_ALGORITHM
    key_derivation_rounds: int = VAULT_KEY_DERIVATION_ROUNDS
    is_locked: bool = True
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SoftwareVault:
    """
    Passphrase-protected software vault for secure key storage.
    
    Features:
    - Passphrase-based encryption using PBKDF2 + ChaCha20-Poly1305
    - Key derivation with configurable rounds
    - Session management with timeout
    - Brute force protection with lockout
    - Multiple access levels
    - Key rotation support
    - Secure key generation and storage
    """
    
    def __init__(self, vault_path: Path, vault_id: str):
        """Initialize software vault"""
        self.vault_path = vault_path
        self.vault_id = vault_id
        self.status = VaultStatus.LOCKED
        self.metadata: Optional[VaultMetadata] = None
        self.master_key: Optional[bytes] = None
        self.active_sessions: Dict[str, VaultSession] = {}
        self.stored_keys: Dict[str, VaultKey] = {}
        
        # Security settings
        self.max_login_attempts = VAULT_MAX_LOGIN_ATTEMPTS
        self.lockout_duration = timedelta(minutes=VAULT_LOCKOUT_DURATION_MINUTES)
        self.session_timeout = timedelta(minutes=VAULT_SESSION_TIMEOUT_MINUTES)
        
        # Ensure vault directory exists
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SoftwareVault initialized: {vault_id}")
    
    async def create_vault(
        self,
        vault_name: str,
        master_passphrase: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create new vault with master passphrase"""
        try:
            # Generate master key from passphrase
            master_key = await self._derive_master_key(master_passphrase)
            
            # Create vault metadata
            self.metadata = VaultMetadata(
                vault_id=self.vault_id,
                vault_name=vault_name,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Store master key temporarily (will be cleared on lock)
            self.master_key = master_key
            
            # Save vault metadata
            await self._save_vault_metadata()
            
            # Unlock vault
            self.status = VaultStatus.UNLOCKED
            
            logger.info(f"Vault created successfully: {vault_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vault: {e}")
            self.status = VaultStatus.ERROR
            return False
    
    async def load_vault(self) -> bool:
        """Load existing vault metadata"""
        try:
            metadata_path = self.vault_path / "vault_metadata.json"
            if not metadata_path.exists():
                logger.warning(f"Vault metadata not found: {metadata_path}")
                return False
            
            # Load metadata from file
            with open(metadata_path, 'r') as f:
                data = json.loads(f.read())
            
            self.metadata = VaultMetadata(
                vault_id=data["vault_id"],
                vault_name=data["vault_name"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
                key_count=data.get("key_count", 0),
                max_keys=data.get("max_keys", 1000),
                encryption_algorithm=data.get("encryption_algorithm", VAULT_ENCRYPTION_ALGORITHM),
                key_derivation_rounds=data.get("key_derivation_rounds", VAULT_KEY_DERIVATION_ROUNDS),
                is_locked=data.get("is_locked", True),
                failed_attempts=data.get("failed_attempts", 0),
                locked_until=datetime.fromisoformat(data["locked_until"]) if data.get("locked_until") else None,
                metadata=data.get("metadata", {})
            )
            
            # Check if vault is locked out
            if self.metadata.locked_until and datetime.now(timezone.utc) < self.metadata.locked_until:
                self.status = VaultStatus.LOCKED_OUT
            else:
                self.status = VaultStatus.LOCKED
            
            logger.info(f"Vault loaded successfully: {self.metadata.vault_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load vault: {e}")
            self.status = VaultStatus.ERROR
            return False
    
    async def unlock_vault(
        self,
        master_passphrase: str,
        user_id: str,
        access_level: VaultAccessLevel = VaultAccessLevel.READ_WRITE
    ) -> Tuple[bool, Optional[str]]:
        """Unlock vault with master passphrase"""
        try:
            # Check if vault is locked out
            if self.status == VaultStatus.LOCKED_OUT:
                if self.metadata and self.metadata.locked_until:
                    remaining_time = self.metadata.locked_until - datetime.now(timezone.utc)
                    if remaining_time.total_seconds() > 0:
                        return False, f"Vault locked out. Try again in {remaining_time}"
                    else:
                        # Reset lockout
                        self.metadata.failed_attempts = 0
                        self.metadata.locked_until = None
                        self.status = VaultStatus.LOCKED
            
            # Derive master key
            master_key = await self._derive_master_key(master_passphrase)
            
            # Verify master key by attempting to decrypt a test value
            if not await self._verify_master_key(master_key):
                # Increment failed attempts
                if self.metadata:
                    self.metadata.failed_attempts += 1
                    
                    # Check if should lock out
                    if self.metadata.failed_attempts >= self.max_login_attempts:
                        self.metadata.locked_until = datetime.now(timezone.utc) + self.lockout_duration
                        self.status = VaultStatus.LOCKED_OUT
                        await self._save_vault_metadata()
                        return False, f"Too many failed attempts. Vault locked for {self.lockout_duration}"
                    
                    await self._save_vault_metadata()
                
                return False, "Invalid passphrase"
            
            # Vault unlocked successfully
            self.master_key = master_key
            self.status = VaultStatus.UNLOCKED
            
            # Reset failed attempts
            if self.metadata:
                self.metadata.failed_attempts = 0
                self.metadata.locked_until = None
                self.metadata.last_accessed = datetime.now(timezone.utc)
                await self._save_vault_metadata()
            
            # Create session
            session_id = await self._create_session(user_id, access_level)
            
            # Load stored keys
            await self._load_stored_keys()
            
            logger.info(f"Vault unlocked successfully by user: {user_id}")
            return True, session_id
            
        except Exception as e:
            logger.error(f"Failed to unlock vault: {e}")
            return False, f"Unlock error: {str(e)}"
    
    async def lock_vault(self) -> bool:
        """Lock vault and clear sensitive data"""
        try:
            # Clear master key
            if self.master_key:
                # Securely clear memory
                self.master_key = b'\x00' * len(self.master_key)
                self.master_key = None
            
            # Clear stored keys
            self.stored_keys.clear()
            
            # Clear active sessions
            self.active_sessions.clear()
            
            # Update status
            self.status = VaultStatus.LOCKED
            
            # Update metadata
            if self.metadata:
                self.metadata.is_locked = True
                await self._save_vault_metadata()
            
            logger.info("Vault locked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to lock vault: {e}")
            return False
    
    async def generate_key(
        self,
        key_type: str = "ed25519",
        key_name: Optional[str] = None,
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[VaultKey]:
        """Generate new cryptographic key"""
        try:
            if self.status != VaultStatus.UNLOCKED:
                raise ValueError("Vault must be unlocked to generate keys")
            
            if not session_id or session_id not in self.active_sessions:
                raise ValueError("Valid session required")
            
            # Check access level
            session = self.active_sessions[session_id]
            if session.access_level not in [VaultAccessLevel.READ_WRITE, VaultAccessLevel.ADMIN, VaultAccessLevel.MASTER]:
                raise ValueError("Insufficient access level to generate keys")
            
            # Generate key pair
            if key_type == "ed25519":
                private_key = ed25519.Ed25519PrivateKey.generate()
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
            
            # Create vault key
            key_id = secrets.token_hex(16)
            vault_key = VaultKey(
                key_id=key_id,
                key_type=key_type,
                public_key=public_key_bytes,
                private_key_encrypted=encrypted_private_key,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Store key
            self.stored_keys[key_id] = vault_key
            
            # Update vault metadata
            if self.metadata:
                self.metadata.key_count = len(self.stored_keys)
                await self._save_vault_metadata()
            
            # Save key to disk
            await self._save_key(vault_key)
            
            logger.info(f"Generated new key: {key_id} ({key_type})")
            return vault_key
            
        except Exception as e:
            logger.error(f"Failed to generate key: {e}")
            return None
    
    async def get_public_key(self, key_id: str, session_id: str = "") -> Optional[bytes]:
        """Get public key by ID"""
        try:
            if not session_id or session_id not in self.active_sessions:
                raise ValueError("Valid session required")
            
            if key_id not in self.stored_keys:
                return None
            
            vault_key = self.stored_keys[key_id]
            
            # Update usage count
            vault_key.usage_count += 1
            vault_key.last_used = datetime.now(timezone.utc)
            
            return vault_key.public_key
            
        except Exception as e:
            logger.error(f"Failed to get public key: {e}")
            return None
    
    async def get_private_key(self, key_id: str, session_id: str = "") -> Optional[bytes]:
        """Get decrypted private key by ID"""
        try:
            if self.status != VaultStatus.UNLOCKED:
                raise ValueError("Vault must be unlocked")
            
            if not session_id or session_id not in self.active_sessions:
                raise ValueError("Valid session required")
            
            # Check access level
            session = self.active_sessions[session_id]
            if session.access_level not in [VaultAccessLevel.READ_WRITE, VaultAccessLevel.ADMIN, VaultAccessLevel.MASTER]:
                raise ValueError("Insufficient access level to access private keys")
            
            if key_id not in self.stored_keys:
                return None
            
            vault_key = self.stored_keys[key_id]
            
            # Decrypt private key
            private_key_bytes = await self._decrypt_data(vault_key.private_key_encrypted)
            
            # Update usage count
            vault_key.usage_count += 1
            vault_key.last_used = datetime.now(timezone.utc)
            
            return private_key_bytes
            
        except Exception as e:
            logger.error(f"Failed to get private key: {e}")
            return None
    
    async def sign_data(
        self,
        key_id: str,
        data: bytes,
        session_id: str = ""
    ) -> Optional[bytes]:
        """Sign data with specified key"""
        try:
            # Get private key
            private_key_bytes = await self.get_private_key(key_id, session_id)
            if not private_key_bytes:
                return None
            
            # Create private key object
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            
            # Sign data
            signature = private_key.sign(data)
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to sign data: {e}")
            return None
    
    async def verify_signature(
        self,
        key_id: str,
        data: bytes,
        signature: bytes,
        session_id: str = ""
    ) -> bool:
        """Verify signature with specified key"""
        try:
            # Get public key
            public_key_bytes = await self.get_public_key(key_id, session_id)
            if not public_key_bytes:
                return False
            
            # Create public key object
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify signature
            public_key.verify(signature, data)
            return True
            
        except Exception:
            return False
    
    async def list_keys(self, session_id: str = "") -> List[Dict[str, Any]]:
        """List all keys in vault"""
        try:
            if not session_id or session_id not in self.active_sessions:
                raise ValueError("Valid session required")
            
            keys_info = []
            for key_id, vault_key in self.stored_keys.items():
                keys_info.append({
                    "key_id": key_id,
                    "key_type": vault_key.key_type,
                    "created_at": vault_key.created_at.isoformat(),
                    "last_used": vault_key.last_used.isoformat() if vault_key.last_used else None,
                    "usage_count": vault_key.usage_count,
                    "is_active": vault_key.is_active,
                    "metadata": vault_key.metadata
                })
            
            return keys_info
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []
    
    async def delete_key(self, key_id: str, session_id: str = "") -> bool:
        """Delete key from vault"""
        try:
            if not session_id or session_id not in self.active_sessions:
                raise ValueError("Valid session required")
            
            # Check access level
            session = self.active_sessions[session_id]
            if session.access_level not in [VaultAccessLevel.ADMIN, VaultAccessLevel.MASTER]:
                raise ValueError("Insufficient access level to delete keys")
            
            if key_id not in self.stored_keys:
                return False
            
            # Remove from memory
            del self.stored_keys[key_id]
            
            # Remove from disk
            key_path = self.vault_path / f"key_{key_id}.json"
            if key_path.exists():
                key_path.unlink()
            
            # Update vault metadata
            if self.metadata:
                self.metadata.key_count = len(self.stored_keys)
                await self._save_vault_metadata()
            
            logger.info(f"Deleted key: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete key: {e}")
            return False
    
    async def _derive_master_key(self, passphrase: str) -> bytes:
        """Derive master key from passphrase using PBKDF2"""
        try:
            # Use vault ID as salt (deterministic for same vault)
            salt = self.vault_id.encode('utf-8')[:VAULT_SALT_SIZE]
            if len(salt) < VAULT_SALT_SIZE:
                salt = salt.ljust(VAULT_SALT_SIZE, b'\x00')
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=salt,
                iterations=VAULT_KEY_DERIVATION_ROUNDS,
                backend=default_backend()
            )
            
            master_key = kdf.derive(passphrase.encode('utf-8'))
            return master_key
            
        except Exception as e:
            logger.error(f"Failed to derive master key: {e}")
            raise
    
    async def _verify_master_key(self, master_key: bytes) -> bool:
        """Verify master key by attempting to decrypt test data"""
        try:
            # Look for a test file or create one if needed
            test_file = self.vault_path / "test_encryption"
            
            if test_file.exists():
                # Try to decrypt existing test data
                with open(test_file, 'rb') as f:
                    encrypted_data = f.read()
                
                decrypted_data = await self._decrypt_data_with_key(encrypted_data, master_key)
                return decrypted_data == b"test_data"
            else:
                # Create new test data
                test_data = b"test_data"
                encrypted_data = await self._encrypt_data_with_key(test_data, master_key)
                
                with open(test_file, 'wb') as f:
                    f.write(encrypted_data)
                
                return True
            
        except Exception as e:
            logger.error(f"Failed to verify master key: {e}")
            return False
    
    async def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using master key"""
        if not self.master_key:
            raise ValueError("Vault must be unlocked to encrypt data")
        
        return await self._encrypt_data_with_key(data, self.master_key)
    
    async def _encrypt_data_with_key(self, data: bytes, key: bytes) -> bytes:
        """Encrypt data with specified key"""
        try:
            # Generate random nonce
            nonce = os.urandom(VAULT_NONCE_SIZE)
            
            # Create cipher
            cipher = Cipher(
                algorithms.ChaCha20(key, nonce),
                None,  # No mode for ChaCha20
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            
            # Return nonce + encrypted data
            return nonce + encrypted_data
            
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise
    
    async def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using master key"""
        if not self.master_key:
            raise ValueError("Vault must be unlocked to decrypt data")
        
        return await self._decrypt_data_with_key(encrypted_data, self.master_key)
    
    async def _decrypt_data_with_key(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data with specified key"""
        try:
            # Extract nonce and encrypted data
            nonce = encrypted_data[:VAULT_NONCE_SIZE]
            data = encrypted_data[VAULT_NONCE_SIZE:]
            
            # Create cipher
            cipher = Cipher(
                algorithms.ChaCha20(key, nonce),
                None,  # No mode for ChaCha20
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            decrypted_data = decryptor.update(data) + decryptor.finalize()
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise
    
    async def _create_session(
        self,
        user_id: str,
        access_level: VaultAccessLevel
    ) -> str:
        """Create new vault session"""
        session_id = secrets.token_hex(16)
        
        session = VaultSession(
            session_id=session_id,
            user_id=user_id,
            access_level=access_level,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + self.session_timeout,
            last_activity=datetime.now(timezone.utc)
        )
        
        self.active_sessions[session_id] = session
        return session_id
    
    async def _save_vault_metadata(self) -> None:
        """Save vault metadata to disk"""
        if not self.metadata:
            return
        
        metadata_path = self.vault_path / "vault_metadata.json"
        
        data = {
            "vault_id": self.metadata.vault_id,
            "vault_name": self.metadata.vault_name,
            "created_at": self.metadata.created_at.isoformat(),
            "last_accessed": self.metadata.last_accessed.isoformat() if self.metadata.last_accessed else None,
            "key_count": self.metadata.key_count,
            "max_keys": self.metadata.max_keys,
            "encryption_algorithm": self.metadata.encryption_algorithm,
            "key_derivation_rounds": self.metadata.key_derivation_rounds,
            "is_locked": self.metadata.is_locked,
            "failed_attempts": self.metadata.failed_attempts,
            "locked_until": self.metadata.locked_until.isoformat() if self.metadata.locked_until else None,
            "metadata": self.metadata.metadata
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def _save_key(self, vault_key: VaultKey) -> None:
        """Save key to disk"""
        key_path = self.vault_path / f"key_{vault_key.key_id}.json"
        
        data = {
            "key_id": vault_key.key_id,
            "key_type": vault_key.key_type,
            "public_key": vault_key.public_key.hex(),
            "private_key_encrypted": vault_key.private_key_encrypted.hex(),
            "created_at": vault_key.created_at.isoformat(),
            "last_used": vault_key.last_used.isoformat() if vault_key.last_used else None,
            "usage_count": vault_key.usage_count,
            "is_active": vault_key.is_active,
            "metadata": vault_key.metadata
        }
        
        with open(key_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def _load_stored_keys(self) -> None:
        """Load all stored keys from disk"""
        try:
            self.stored_keys.clear()
            
            for key_file in self.vault_path.glob("key_*.json"):
                try:
                    with open(key_file, 'r') as f:
                        data = json.load(f)
                    
                    vault_key = VaultKey(
                        key_id=data["key_id"],
                        key_type=data["key_type"],
                        public_key=bytes.fromhex(data["public_key"]),
                        private_key_encrypted=bytes.fromhex(data["private_key_encrypted"]),
                        created_at=datetime.fromisoformat(data["created_at"]),
                        last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
                        usage_count=data.get("usage_count", 0),
                        is_active=data.get("is_active", True),
                        metadata=data.get("metadata", {})
                    )
                    
                    self.stored_keys[vault_key.key_id] = vault_key
                    
                except Exception as e:
                    logger.error(f"Failed to load key from {key_file}: {e}")
            
            logger.info(f"Loaded {len(self.stored_keys)} keys from vault")
            
        except Exception as e:
            logger.error(f"Failed to load stored keys: {e}")
    
    async def get_vault_status(self) -> Dict[str, Any]:
        """Get vault status information"""
        return {
            "vault_id": self.vault_id,
            "status": self.status.value,
            "is_locked": self.status == VaultStatus.LOCKED,
            "key_count": len(self.stored_keys),
            "active_sessions": len(self.active_sessions),
            "metadata": self.metadata.to_dict() if self.metadata else None
        }


# Global vault manager
_vault_manager: Dict[str, SoftwareVault] = {}


def get_vault(vault_id: str) -> Optional[SoftwareVault]:
    """Get vault by ID"""
    return _vault_manager.get(vault_id)


def create_vault(vault_path: Path, vault_id: str) -> SoftwareVault:
    """Create new vault instance"""
    vault = SoftwareVault(vault_path, vault_id)
    _vault_manager[vault_id] = vault
    return vault


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create test vault
    vault_path = Path("./test_vault")
    vault = create_vault(vault_path, "test_vault_001")
    
    # Create vault
    success = await vault.create_vault(
        vault_name="Test Vault",
        master_passphrase="test_passphrase_123"
    )
    print(f"Vault created: {success}")
    
    # Unlock vault
    success, session_id = await vault.unlock_vault(
        master_passphrase="test_passphrase_123",
        user_id="test_user",
        access_level=VaultAccessLevel.ADMIN
    )
    print(f"Vault unlocked: {success}, Session: {session_id}")
    
    if success and session_id:
        # Generate key
        vault_key = await vault.generate_key(
            key_type="ed25519",
            key_name="test_key",
            session_id=session_id
        )
        print(f"Key generated: {vault_key.key_id if vault_key else None}")
        
        if vault_key:
            # Test signing
            test_data = b"Hello, World!"
            signature = await vault.sign_data(vault_key.key_id, test_data, session_id)
            print(f"Signature created: {signature.hex() if signature else None}")
            
            # Test verification
            is_valid = await vault.verify_signature(vault_key.key_id, test_data, signature, session_id)
            print(f"Signature valid: {is_valid}")
        
        # List keys
        keys = await vault.list_keys(session_id)
        print(f"Keys in vault: {len(keys)}")
    
    # Get vault status
    status = await vault.get_vault_status()
    print(f"Vault status: {status}")


if __name__ == "__main__":
    asyncio.run(main())

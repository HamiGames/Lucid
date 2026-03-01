"""
Chunk Encryption Module
Implements AES-256-GCM encryption for session chunks.

This module provides secure encryption functionality for session chunks using
AES-256-GCM (Galois/Counter Mode) encryption. It ensures data confidentiality,
integrity, and authenticity for all processed chunks.

Features:
- AES-256-GCM encryption with authentication
- Secure key management
- Nonce generation and management
- Encryption/decryption with integrity verification
- Performance optimization for large chunks
- Error handling and validation
"""

import os
import secrets
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption-related errors."""
    pass


class KeyDerivationError(EncryptionError):
    """Raised when key derivation fails."""
    pass


class EncryptionValidationError(EncryptionError):
    """Raised when encryption validation fails."""
    pass


class ChunkEncryptor:
    """
    AES-256-GCM chunk encryptor with secure key management.
    
    This class provides secure encryption and decryption of session chunks
    using AES-256-GCM mode, which provides both confidentiality and authenticity.
    """
    
    # AES-256-GCM constants
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits (recommended for GCM)
    TAG_SIZE = 16  # 128 bits authentication tag
    SALT_SIZE = 32  # 256 bits for PBKDF2 salt
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the chunk encryptor.
        
        Args:
            master_key: Master key for encryption. If None, will be generated.
        """
        self.master_key = master_key or self._generate_master_key()
        self._derived_key = None
        self._encryption_count = 0
        self._decryption_count = 0
        
        logger.info("ChunkEncryptor initialized")
    
    def _generate_master_key(self) -> str:
        """Generate a secure master key."""
        return secrets.token_urlsafe(32)
    
    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive encryption key from master key using PBKDF2.
        
        Args:
            salt: Salt for key derivation
            
        Returns:
            Derived encryption key
            
        Raises:
            KeyDerivationError: If key derivation fails
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.KEY_SIZE,
                salt=salt,
                iterations=100000,  # OWASP recommended minimum
                backend=default_backend()
            )
            
            master_key_bytes = self.master_key.encode('utf-8')
            derived_key = kdf.derive(master_key_bytes)
            
            return derived_key
            
        except Exception as e:
            raise KeyDerivationError(f"Failed to derive encryption key: {str(e)}")
    
    def _generate_nonce(self) -> bytes:
        """
        Generate a cryptographically secure nonce.
        
        Returns:
            Random nonce bytes
        """
        return secrets.token_bytes(self.NONCE_SIZE)
    
    def _generate_salt(self) -> bytes:
        """
        Generate a cryptographically secure salt.
        
        Returns:
            Random salt bytes
        """
        return secrets.token_bytes(self.SALT_SIZE)
    
    async def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt plaintext data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Encrypted data with metadata (salt + nonce + ciphertext + tag)
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            raise EncryptionError("Plaintext cannot be empty")
        
        try:
            # Generate salt and nonce
            salt = self._generate_salt()
            nonce = self._generate_nonce()
            
            # Derive key from master key and salt
            key = self._derive_key(salt)
            
            # Create AES-GCM cipher
            aesgcm = AESGCM(key)
            
            # Encrypt data
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            
            # Combine salt + nonce + ciphertext
            encrypted_data = salt + nonce + ciphertext
            
            # Update encryption count
            self._encryption_count += 1
            
            logger.debug(f"Encrypted {len(plaintext)} bytes to {len(encrypted_data)} bytes")
            
            return encrypted_data
            
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    async def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt encrypted data using AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted data with metadata
            
        Returns:
            Decrypted plaintext data
            
        Raises:
            EncryptionError: If decryption fails
            EncryptionValidationError: If authentication fails
        """
        if not encrypted_data:
            raise EncryptionError("Encrypted data cannot be empty")
        
        try:
            # Validate minimum size
            min_size = self.SALT_SIZE + self.NONCE_SIZE + self.TAG_SIZE
            if len(encrypted_data) < min_size:
                raise EncryptionError(f"Encrypted data too small: {len(encrypted_data)} < {min_size}")
            
            # Extract components
            salt = encrypted_data[:self.SALT_SIZE]
            nonce = encrypted_data[self.SALT_SIZE:self.SALT_SIZE + self.NONCE_SIZE]
            ciphertext = encrypted_data[self.SALT_SIZE + self.NONCE_SIZE:]
            
            # Derive key from master key and salt
            key = self._derive_key(salt)
            
            # Create AES-GCM cipher
            aesgcm = AESGCM(key)
            
            # Decrypt data
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Update decryption count
            self._decryption_count += 1
            
            logger.debug(f"Decrypted {len(encrypted_data)} bytes to {len(plaintext)} bytes")
            
            return plaintext
            
        except Exception as e:
            if "authentication" in str(e).lower() or "tag" in str(e).lower():
                raise EncryptionValidationError(f"Authentication failed: {str(e)}")
            else:
                raise EncryptionError(f"Decryption failed: {str(e)}")
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """
        Get encryption statistics.
        
        Returns:
            Dictionary containing encryption statistics
        """
        return {
            "encryption_count": self._encryption_count,
            "decryption_count": self._decryption_count,
            "key_size": self.KEY_SIZE,
            "nonce_size": self.NONCE_SIZE,
            "tag_size": self.TAG_SIZE,
            "salt_size": self.SALT_SIZE
        }
    
    async def validate_encryption(self, plaintext: bytes) -> bool:
        """
        Validate encryption/decryption round trip.
        
        Args:
            plaintext: Data to test encryption with
            
        Returns:
            True if encryption/decryption works correctly
        """
        try:
            # Encrypt
            encrypted = await self.encrypt(plaintext)
            
            # Decrypt
            decrypted = await self.decrypt(encrypted)
            
            # Compare
            return plaintext == decrypted
            
        except Exception as e:
            logger.error(f"Encryption validation failed: {str(e)}")
            return False


class EncryptionManager:
    """
    High-level encryption manager for session chunks.
    
    This class provides a higher-level interface for encryption operations,
    including batch processing, key rotation, and performance optimization.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the encryption manager.
        
        Args:
            master_key: Master key for encryption. If None, will be generated.
        """
        self.encryptor = ChunkEncryptor(master_key)
        self._session_keys: Dict[str, ChunkEncryptor] = {}
        self._key_rotation_interval = 3600  # 1 hour in seconds
        self._last_key_rotation = datetime.utcnow()
        
        logger.info("EncryptionManager initialized")
    
    async def encrypt_chunk(
        self, 
        session_id: str, 
        chunk_id: str, 
        chunk_data: bytes
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Encrypt a chunk with session-specific key management.
        
        Args:
            session_id: ID of the session
            chunk_id: ID of the chunk
            chunk_data: Raw chunk data
            
        Returns:
            Tuple of (encrypted_data, metadata)
        """
        try:
            # Get or create session-specific encryptor
            session_encryptor = self._get_session_encryptor(session_id)
            
            # Encrypt chunk
            encrypted_data = await session_encryptor.encrypt(chunk_data)
            
            # Create metadata
            metadata = {
                "session_id": session_id,
                "chunk_id": chunk_id,
                "original_size": len(chunk_data),
                "encrypted_size": len(encrypted_data),
                "compression_ratio": len(encrypted_data) / len(chunk_data),
                "encryption_algorithm": "AES-256-GCM",
                "timestamp": datetime.utcnow().isoformat(),
                "key_version": self._get_key_version(session_id)
            }
            
            logger.debug(f"Encrypted chunk {chunk_id} for session {session_id}")
            
            return encrypted_data, metadata
            
        except Exception as e:
            logger.error(f"Failed to encrypt chunk {chunk_id}: {str(e)}")
            raise EncryptionError(f"Chunk encryption failed: {str(e)}")
    
    async def decrypt_chunk(
        self, 
        session_id: str, 
        chunk_id: str, 
        encrypted_data: bytes
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Decrypt a chunk with session-specific key management.
        
        Args:
            session_id: ID of the session
            chunk_id: ID of the chunk
            encrypted_data: Encrypted chunk data
            
        Returns:
            Tuple of (decrypted_data, metadata)
        """
        try:
            # Get session-specific encryptor
            session_encryptor = self._get_session_encryptor(session_id)
            
            # Decrypt chunk
            decrypted_data = await session_encryptor.decrypt(encrypted_data)
            
            # Create metadata
            metadata = {
                "session_id": session_id,
                "chunk_id": chunk_id,
                "encrypted_size": len(encrypted_data),
                "decrypted_size": len(decrypted_data),
                "decryption_algorithm": "AES-256-GCM",
                "timestamp": datetime.utcnow().isoformat(),
                "key_version": self._get_key_version(session_id)
            }
            
            logger.debug(f"Decrypted chunk {chunk_id} for session {session_id}")
            
            return decrypted_data, metadata
            
        except Exception as e:
            logger.error(f"Failed to decrypt chunk {chunk_id}: {str(e)}")
            raise EncryptionError(f"Chunk decryption failed: {str(e)}")
    
    async def encrypt_chunks_batch(
        self, 
        session_id: str, 
        chunks: Dict[str, bytes]
    ) -> Dict[str, Tuple[bytes, Dict[str, Any]]]:
        """
        Encrypt multiple chunks in batch.
        
        Args:
            session_id: ID of the session
            chunks: Dictionary of chunk_id -> chunk_data
            
        Returns:
            Dictionary of chunk_id -> (encrypted_data, metadata)
        """
        results = {}
        
        for chunk_id, chunk_data in chunks.items():
            try:
                encrypted_data, metadata = await self.encrypt_chunk(
                    session_id, chunk_id, chunk_data
                )
                results[chunk_id] = (encrypted_data, metadata)
            except Exception as e:
                logger.error(f"Failed to encrypt chunk {chunk_id} in batch: {str(e)}")
                results[chunk_id] = (None, {"error": str(e)})
        
        logger.info(f"Batch encrypted {len(chunks)} chunks for session {session_id}")
        return results
    
    def _get_session_encryptor(self, session_id: str) -> ChunkEncryptor:
        """
        Get or create a session-specific encryptor.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Session-specific encryptor
        """
        if session_id not in self._session_keys:
            # Create new session-specific encryptor
            session_key = self._generate_session_key(session_id)
            self._session_keys[session_id] = ChunkEncryptor(session_key)
            
            logger.debug(f"Created new encryptor for session {session_id}")
        
        return self._session_keys[session_id]
    
    def _generate_session_key(self, session_id: str) -> str:
        """
        Generate a session-specific encryption key.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Session-specific encryption key
        """
        # Combine master key with session ID for uniqueness
        combined = f"{self.encryptor.master_key}:{session_id}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _get_key_version(self, session_id: str) -> str:
        """
        Get the current key version for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Key version string
        """
        # For now, return a simple version based on session creation time
        # In production, this would be more sophisticated
        return "1.0"
    
    async def rotate_keys(self):
        """Rotate encryption keys for all sessions."""
        current_time = datetime.utcnow()
        
        if (current_time - self._last_key_rotation).total_seconds() < self._key_rotation_interval:
            return  # Too soon for rotation
        
        logger.info("Starting key rotation for all sessions")
        
        # Clear existing session keys (they will be regenerated on next use)
        self._session_keys.clear()
        
        # Update rotation time
        self._last_key_rotation = current_time
        
        logger.info("Key rotation completed")
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive encryption statistics.
        
        Returns:
            Dictionary containing encryption statistics
        """
        stats = self.encryptor.get_encryption_stats()
        stats.update({
            "active_sessions": len(self._session_keys),
            "key_rotation_interval": self._key_rotation_interval,
            "last_key_rotation": self._last_key_rotation.isoformat(),
            "session_encryptors": list(self._session_keys.keys())
        })
        
        return stats
    
    def cleanup_session(self, session_id: str):
        """
        Clean up encryption resources for a session.
        
        Args:
            session_id: ID of the session to clean up
        """
        if session_id in self._session_keys:
            del self._session_keys[session_id]
            logger.debug(f"Cleaned up encryption resources for session {session_id}")


# Utility functions for encryption operations

def generate_encryption_key() -> str:
    """
    Generate a secure encryption key.
    
    Returns:
        Base64-encoded encryption key
    """
    key = secrets.token_bytes(32)  # 256 bits
    return base64.b64encode(key).decode('utf-8')


def validate_encryption_key(key: str) -> bool:
    """
    Validate an encryption key format.
    
    Args:
        key: Encryption key to validate
        
    Returns:
        True if key is valid
    """
    try:
        decoded = base64.b64decode(key)
        return len(decoded) == 32  # 256 bits
    except Exception:
        return False


def calculate_encryption_overhead(original_size: int) -> int:
    """
    Calculate the encryption overhead for a given data size.
    
    Args:
        original_size: Original data size in bytes
        
    Returns:
        Additional bytes needed for encryption
    """
    # AES-256-GCM overhead: salt (32) + nonce (12) + tag (16) = 60 bytes
    return 60


def estimate_encrypted_size(original_size: int) -> int:
    """
    Estimate the size of data after encryption.
    
    Args:
        original_size: Original data size in bytes
        
    Returns:
        Estimated encrypted data size
    """
    return original_size + calculate_encryption_overhead(original_size)

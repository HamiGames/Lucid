# Path: session/encryption_manager.py

from __future__ import annotations
import os
import logging
from typing import Optional, Tuple, Dict, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import secrets
import base64

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages XChaCha20-Poly1305 encryption for session data.
    Provides per-chunk encryption with derived keys.
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        master_key_env = os.getenv("LUCID_ENCRYPTION_MASTER_KEY")
        if master_key_env:
            self.master_key = bytes.fromhex(master_key_env)
        else:
            self.master_key = master_key or self._generate_master_key()
        self.backend = default_backend()
        
    def _generate_master_key(self) -> bytes:
        """Generate a secure master key."""
        return secrets.token_bytes(32)  # 256-bit key
        
    def derive_chunk_key(self, session_id: str, chunk_index: int) -> bytes:
        """Derive encryption key for a specific chunk using HKDF-BLAKE2b."""
        info = f"chunk:{session_id}:{chunk_index}".encode()
        hkdf = HKDF(
            algorithm=hashes.BLAKE2b(32),
            length=32,
            salt=None,
            info=info,
            backend=self.backend
        )
        return hkdf.derive(self.master_key)
        
    def encrypt_chunk(
        self, 
        session_id: str, 
        chunk_index: int, 
        data: bytes
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt chunk data with XChaCha20-Poly1305.
        Returns (encrypted_data, nonce).
        """
        try:
            # Derive chunk-specific key
            key = self.derive_chunk_key(session_id, chunk_index)
            
            # Generate nonce (24 bytes for XChaCha20)
            nonce = secrets.token_bytes(24)
            
            # Create cipher
            cipher = Cipher(
                algorithms.ChaCha20(key, nonce),
                mode=None,
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # Encrypt data
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            
            return encrypted_data, nonce
            
        except Exception as e:
            logger.error(f"Failed to encrypt chunk: {e}")
            raise
            
    def decrypt_chunk(
        self,
        session_id: str,
        chunk_index: int,
        encrypted_data: bytes,
        nonce: bytes
    ) -> bytes:
        """Decrypt chunk data."""
        try:
            # Derive chunk-specific key
            key = self.derive_chunk_key(session_id, chunk_index)
            
            # Create cipher
            cipher = Cipher(
                algorithms.ChaCha20(key, nonce),
                mode=None,
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt chunk: {e}")
            raise
            
    def export_key(self) -> str:
        """Export master key as base64 string."""
        return base64.b64encode(self.master_key).decode()
        
    @classmethod
    def from_exported_key(cls, key_str: str) -> EncryptionManager:
        """Create encryption manager from exported key."""
        key_bytes = base64.b64decode(key_str.encode())
        return cls(master_key=key_bytes)

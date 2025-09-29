# Path: apps/encryptor/encryptor.py
# Lucid RDP Chunk Encryptor - XChaCha20-Poly1305 with per-chunk nonces
# Based on LUCID-STRICT requirements per Spec-1b

from __future__ import annotations

import os
import secrets
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import hashlib

from apps.chunker.chunker import ChunkMetadata

logger = logging.getLogger(__name__)

# Encryption constants per specification
NONCE_SIZE = 12  # ChaCha20Poly1305 nonce size
KEY_SIZE = 32    # 256-bit key
SESSION_KEY_INFO = b"lucid-session-key"
CHUNK_KEY_INFO = b"lucid-chunk-key"


@dataclass(frozen=True)
class EncryptedChunk:
    """Metadata for an encrypted chunk"""
    chunk_id: str
    session_id: str
    sequence_number: int
    original_size: int
    compressed_size: int
    encrypted_size: int
    nonce: bytes
    ciphertext_sha256: str
    local_path: Path
    created_at: datetime
    
    def to_dict(self) -> dict:
        """Convert to MongoDB document format per Spec-1b collections schema"""
        return {
            "_id": self.chunk_id,
            "session_id": self.session_id,
            "idx": self.sequence_number,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "encrypted_size": self.encrypted_size,
            "nonce": self.nonce.hex(),
            "ciphertext_sha256": self.ciphertext_sha256,
            "local_path": str(self.local_path),
            "created_at": self.created_at
        }


class LucidEncryptor:
    """
    XChaCha20-Poly1305 encryption for Lucid RDP chunks.
    
    Per Spec-1b:
    - Per-chunk nonces with XChaCha20-Poly1305
    - Key derived from session key via HKDF-BLAKE2b
    - Encrypted chunks stored locally for On-System Chain anchoring
    """
    
    def __init__(self, session_id: str, master_key: bytes):
        if len(master_key) != KEY_SIZE:
            raise ValueError(f"Master key must be {KEY_SIZE} bytes")
            
        self.session_id = session_id
        self.master_key = master_key
        
        # Derive session key using HKDF-BLAKE2b per specification
        self.session_key = self._derive_session_key(session_id, master_key)
        
        # Initialize ChaCha20Poly1305 cipher
        self.cipher = ChaCha20Poly1305(self.session_key)
        
        # Set up encrypted chunk storage
        self.storage_dir = Path(f"/tmp/lucid/encrypted/{session_id}")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Encryptor initialized for session {session_id}")
    
    @classmethod
    def _derive_session_key(cls, session_id: str, master_key: bytes) -> bytes:
        """
        Derive session key using HKDF-BLAKE2b per Spec-1b.
        
        Args:
            session_id: Unique session identifier
            master_key: Master encryption key
            
        Returns:
            32-byte session key
        """
        hkdf = HKDF(
            algorithm=hashes.BLAKE2b(64),  # Use BLAKE2b as specified
            length=KEY_SIZE,
            salt=None,  # No salt per spec
            info=SESSION_KEY_INFO + session_id.encode('utf-8')
        )
        return hkdf.derive(master_key)
    
    def _derive_chunk_key(self, chunk_index: int) -> bytes:
        """
        Derive per-chunk key using HKDF-BLAKE2b.
        
        Args:
            chunk_index: Sequential chunk number
            
        Returns:
            32-byte chunk key
        """
        hkdf = HKDF(
            algorithm=hashes.BLAKE2b(64),
            length=KEY_SIZE,
            salt=None,
            info=CHUNK_KEY_INFO + f"{self.session_id}-{chunk_index}".encode('utf-8')
        )
        return hkdf.derive(self.session_key)
    
    def encrypt_chunk(self, chunk_meta: ChunkMetadata, compressed_data: bytes) -> EncryptedChunk:
        """
        Encrypt compressed chunk data with per-chunk nonce.
        
        Args:
            chunk_meta: Chunk metadata from chunker
            compressed_data: Zstd compressed chunk data
            
        Returns:
            Encrypted chunk metadata with storage info
        """
        try:
            # Generate unique nonce for this chunk
            nonce = secrets.token_bytes(NONCE_SIZE)
            
            # Encrypt compressed data
            ciphertext = self.cipher.encrypt(nonce, compressed_data, None)
            encrypted_size = len(ciphertext)
            
            # Calculate ciphertext hash for integrity verification
            ciphertext_sha256 = hashlib.sha256(ciphertext).hexdigest()
            
            # Store encrypted chunk with nonce prepended
            chunk_path = self._store_encrypted_chunk(chunk_meta.chunk_id, nonce, ciphertext)
            
            encrypted_chunk = EncryptedChunk(
                chunk_id=chunk_meta.chunk_id,
                session_id=chunk_meta.session_id,
                sequence_number=chunk_meta.sequence_number,
                original_size=chunk_meta.original_size,
                compressed_size=chunk_meta.compressed_size,
                encrypted_size=encrypted_size,
                nonce=nonce,
                ciphertext_sha256=ciphertext_sha256,
                local_path=chunk_path,
                created_at=datetime.now(timezone.utc)
            )
            
            logger.debug(f"Encrypted chunk {chunk_meta.chunk_id}: "
                        f"{chunk_meta.compressed_size}→{encrypted_size} bytes")
            
            return encrypted_chunk
            
        except Exception as e:
            logger.error(f"Chunk encryption failed for {chunk_meta.chunk_id}: {e}")
            raise
    
    def decrypt_chunk(self, encrypted_chunk: EncryptedChunk) -> bytes:
        """
        Decrypt an encrypted chunk back to compressed data.
        
        Args:
            encrypted_chunk: Encrypted chunk metadata
            
        Returns:
            Original compressed data
        """
        try:
            # Read encrypted chunk from storage
            stored_data = encrypted_chunk.local_path.read_bytes()
            
            # Extract nonce and ciphertext (nonce is prepended)
            stored_nonce = stored_data[:NONCE_SIZE]
            ciphertext = stored_data[NONCE_SIZE:]
            
            # Verify nonce matches metadata
            if stored_nonce != encrypted_chunk.nonce:
                raise ValueError("Nonce mismatch in stored chunk")
            
            # Decrypt ciphertext
            compressed_data = self.cipher.decrypt(encrypted_chunk.nonce, ciphertext, None)
            
            logger.debug(f"Decrypted chunk {encrypted_chunk.chunk_id}: "
                        f"{len(compressed_data)} bytes")
            
            return compressed_data
            
        except Exception as e:
            logger.error(f"Chunk decryption failed for {encrypted_chunk.chunk_id}: {e}")
            raise
    
    def _store_encrypted_chunk(self, chunk_id: str, nonce: bytes, ciphertext: bytes) -> Path:
        """
        Store encrypted chunk with nonce prepended.
        
        Args:
            chunk_id: Unique chunk identifier
            nonce: Encryption nonce
            ciphertext: Encrypted chunk data
            
        Returns:
            Path to stored encrypted chunk
        """
        chunk_file = self.storage_dir / f"{chunk_id}.enc"
        
        # Store nonce + ciphertext
        chunk_data = nonce + ciphertext
        chunk_file.write_bytes(chunk_data)
        
        logger.debug(f"Stored encrypted chunk: {chunk_file}")
        return chunk_file
    
    def verify_chunk_integrity(self, encrypted_chunk: EncryptedChunk) -> bool:
        """
        Verify encrypted chunk integrity using stored hash.
        
        Args:
            encrypted_chunk: Encrypted chunk to verify
            
        Returns:
            True if chunk integrity is valid
        """
        try:
            # Read stored chunk
            stored_data = encrypted_chunk.local_path.read_bytes()
            ciphertext = stored_data[NONCE_SIZE:]  # Skip nonce
            
            # Calculate hash of stored ciphertext
            calculated_hash = hashlib.sha256(ciphertext).hexdigest()
            
            return calculated_hash == encrypted_chunk.ciphertext_sha256
            
        except Exception as e:
            logger.error(f"Chunk integrity verification failed: {e}")
            return False
    
    def cleanup_session(self) -> None:
        """Remove all encrypted chunks for this session."""
        try:
            import shutil
            if self.storage_dir.exists():
                shutil.rmtree(self.storage_dir)
                logger.info(f"Cleaned up encrypted chunks for session {self.session_id}")
        except Exception as e:
            logger.error(f"Cleanup failed for session {self.session_id}: {e}")


class SessionEncryptionManager:
    """
    Manages encryption for multiple active sessions.
    Interfaces with chunker and merkle builder services.
    """
    
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.active_encryptors: dict[str, LucidEncryptor] = {}
        logger.info("Session encryption manager initialized")
    
    def start_encryption(self, session_id: str) -> None:
        """Start encryption for a new session."""
        if session_id in self.active_encryptors:
            logger.warning(f"Encryptor already exists for session {session_id}")
            return
        
        encryptor = LucidEncryptor(session_id, self.master_key)
        self.active_encryptors[session_id] = encryptor
        
        logger.info(f"Started encryption for session {session_id}")
    
    def encrypt_chunk(self, session_id: str, chunk_meta: ChunkMetadata, 
                     compressed_data: bytes) -> EncryptedChunk:
        """Encrypt a chunk for the specified session."""
        encryptor = self.active_encryptors.get(session_id)
        if not encryptor:
            raise ValueError(f"No encryptor found for session {session_id}")
        
        return encryptor.encrypt_chunk(chunk_meta, compressed_data)
    
    def decrypt_chunk(self, session_id: str, encrypted_chunk: EncryptedChunk) -> bytes:
        """Decrypt a chunk for the specified session."""
        encryptor = self.active_encryptors.get(session_id)
        if not encryptor:
            raise ValueError(f"No encryptor found for session {session_id}")
        
        return encryptor.decrypt_chunk(encrypted_chunk)
    
    def finalize_session(self, session_id: str) -> None:
        """Finalize encryption for a session and clean up."""
        encryptor = self.active_encryptors.get(session_id)
        if not encryptor:
            logger.warning(f"No encryptor found for session {session_id}")
            return
        
        # Keep encrypted chunks but remove encryptor
        del self.active_encryptors[session_id]
        
        logger.info(f"Finalized encryption for session {session_id}")
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up all encrypted data for a session."""
        encryptor = self.active_encryptors.get(session_id)
        if encryptor:
            encryptor.cleanup_session()
            del self.active_encryptors[session_id]
    
    def get_active_sessions(self) -> List[str]:
        """Get list of all sessions with active encryptors."""
        return list(self.active_encryptors.keys())


def generate_master_key() -> bytes:
    """Generate a cryptographically secure master key."""
    return secrets.token_bytes(KEY_SIZE)


def load_master_key_from_env() -> bytes:
    """
    Load master key from environment variable.
    
    Returns:
        32-byte master key
        
    Raises:
        ValueError: If key is not found or invalid
    """
    key_hex = os.getenv("LUCID_MASTER_KEY")
    if not key_hex:
        raise ValueError("LUCID_MASTER_KEY environment variable not set")
    
    try:
        key_bytes = bytes.fromhex(key_hex)
        if len(key_bytes) != KEY_SIZE:
            raise ValueError(f"Master key must be {KEY_SIZE} bytes, got {len(key_bytes)}")
        return key_bytes
    except ValueError as e:
        raise ValueError(f"Invalid master key format: {e}")


if __name__ == "__main__":
    # Test encryptor functionality
    import sys
    from apps.chunker.chunker import ChunkMetadata
    
    if len(sys.argv) < 2:
        print("Usage: python encryptor.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    master_key = generate_master_key()
    
    encryptor = LucidEncryptor(session_id, master_key)
    
    # Create test chunk metadata
    test_chunk = ChunkMetadata(
        chunk_id=f"{session_id}-chunk-000001",
        session_id=session_id,
        sequence_number=0,
        original_size=1000,
        compressed_size=800,
        compression_ratio=0.8,
        chunk_hash="test_hash",
        created_at=datetime.now(timezone.utc)
    )
    
    # Test encrypt/decrypt cycle
    test_data = b"Test compressed chunk data" * 50  # ~1.3KB
    encrypted = encryptor.encrypt_chunk(test_chunk, test_data)
    decrypted = encryptor.decrypt_chunk(encrypted)
    
    print(f"Test completed for session {session_id}")
    print(f"Original size: {len(test_data)} bytes")
    print(f"Encrypted size: {encrypted.encrypted_size} bytes")
    print(f"Decryption successful: {decrypted == test_data}")
    print(f"Integrity check: {encryptor.verify_chunk_integrity(encrypted)}")
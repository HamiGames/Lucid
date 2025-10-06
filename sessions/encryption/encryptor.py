#!/usr/bin/env python3
"""
LUCID Session Encryptor - SPEC-1B Implementation
XChaCha20-Poly1305 per-chunk encryption with HKDF-BLAKE2b key derivation
"""

import asyncio
import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import blake3

logger = logging.getLogger(__name__)

@dataclass
class EncryptedChunk:
    """Encrypted chunk data structure"""
    chunk_id: str
    session_id: str
    encrypted_data: bytes
    nonce: bytes
    tag: bytes
    key_id: str
    timestamp: float
    file_path: str

class SessionEncryptor:
    """
    XChaCha20-Poly1305 per-chunk encryption per SPEC-1b
    """
    
    CIPHER_ALGORITHM = "XChaCha20-Poly1305"
    KEY_DERIVATION = "HKDF-BLAKE2b"
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 24  # 192 bits for XChaCha20
    SALT_SIZE = 32  # 256 bits for HKDF salt
    
    def __init__(self, output_dir: str = "/data/encrypted", master_key: Optional[bytes] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate or use provided master key
        self.master_key = master_key or secrets.token_bytes(self.KEY_SIZE)
        
        # Key derivation context
        self._key_cache: Dict[str, bytes] = {}
        
        logger.info("SessionEncryptor initialized with XChaCha20-Poly1305 encryption")
    
    def _derive_chunk_key(self, session_id: str, chunk_id: str, salt: bytes) -> bytes:
        """Derive encryption key for a specific chunk using HKDF-BLAKE2b"""
        
        # Create key cache key
        cache_key = f"{session_id}:{chunk_id}:{salt.hex()}"
        
        if cache_key in self._key_cache:
            return self._key_cache[cache_key]
        
        # Create HKDF context
        info = f"lucid-chunk-encryption:{session_id}:{chunk_id}".encode()
        
        # Use BLAKE2b for HKDF
        hkdf = HKDF(
            algorithm=hashes.BLAKE2b(64),  # BLAKE2b with 512-bit output
            length=self.KEY_SIZE,
            salt=salt,
            info=info,
        )
        
        # Derive key from master key
        chunk_key = hkdf.derive(self.master_key)
        
        # Cache the key
        self._key_cache[cache_key] = chunk_key
        
        return chunk_key
    
    async def encrypt_chunk(
        self, 
        chunk_data: bytes, 
        chunk_id: str, 
        session_id: str,
        key_id: Optional[str] = None
    ) -> EncryptedChunk:
        """
        Encrypt a chunk with XChaCha20-Poly1305
        
        Args:
            chunk_data: Raw chunk data to encrypt
            chunk_id: Unique chunk identifier
            session_id: Session identifier
            key_id: Optional key identifier for key rotation
            
        Returns:
            EncryptedChunk object with encrypted data and metadata
        """
        if key_id is None:
            key_id = f"key_{int(time.time())}"
        
        # Generate random salt for key derivation
        salt = secrets.token_bytes(self.SALT_SIZE)
        
        # Derive chunk-specific key
        chunk_key = self._derive_chunk_key(session_id, chunk_id, salt)
        
        # Generate random nonce
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        
        # Create cipher
        cipher = ChaCha20Poly1305(chunk_key)
        
        # Encrypt the data
        encrypted_data = cipher.encrypt(nonce, chunk_data, None)
        
        # Extract tag (last 16 bytes)
        tag = encrypted_data[-16:]
        encrypted_content = encrypted_data[:-16]
        
        # Save encrypted chunk to disk
        chunk_filename = f"{chunk_id}.enc"
        chunk_path = self.output_dir / chunk_filename
        
        # Write encrypted data with metadata
        with open(chunk_path, 'wb') as f:
            f.write(salt)  # 32 bytes salt
            f.write(nonce)  # 24 bytes nonce
            f.write(tag)  # 16 bytes tag
            f.write(encrypted_content)  # encrypted data
        
        # Create metadata
        encrypted_chunk = EncryptedChunk(
            chunk_id=chunk_id,
            session_id=session_id,
            encrypted_data=encrypted_content,
            nonce=nonce,
            tag=tag,
            key_id=key_id,
            timestamp=time.time(),
            file_path=str(chunk_path)
        )
        
        logger.debug(f"Encrypted chunk {chunk_id}: {len(chunk_data)} -> {len(encrypted_content)} bytes")
        
        return encrypted_chunk
    
    async def decrypt_chunk(self, encrypted_chunk: EncryptedChunk) -> bytes:
        """
        Decrypt a chunk using XChaCha20-Poly1305
        
        Args:
            encrypted_chunk: EncryptedChunk object to decrypt
            
        Returns:
            Decrypted chunk data
        """
        if not os.path.exists(encrypted_chunk.file_path):
            raise FileNotFoundError(f"Encrypted chunk file not found: {encrypted_chunk.file_path}")
        
        # Read encrypted file
        with open(encrypted_chunk.file_path, 'rb') as f:
            file_data = f.read()
        
        # Extract components
        salt = file_data[:self.SALT_SIZE]
        nonce = file_data[self.SALT_SIZE:self.SALT_SIZE + self.NONCE_SIZE]
        tag = file_data[self.SALT_SIZE + self.NONCE_SIZE:self.SALT_SIZE + self.NONCE_SIZE + 16]
        encrypted_content = file_data[self.SALT_SIZE + self.NONCE_SIZE + 16:]
        
        # Derive the same key used for encryption
        chunk_key = self._derive_chunk_key(
            encrypted_chunk.session_id, 
            encrypted_chunk.chunk_id, 
            salt
        )
        
        # Create cipher
        cipher = ChaCha20Poly1305(chunk_key)
        
        # Reconstruct encrypted data with tag
        encrypted_data = encrypted_content + tag
        
        # Decrypt the data
        try:
            decrypted_data = cipher.decrypt(nonce, encrypted_data, None)
            return decrypted_data
        except Exception as e:
            raise ValueError(f"Failed to decrypt chunk {encrypted_chunk.chunk_id}: {e}")
    
    async def encrypt_session_chunks(
        self, 
        chunks: List[Tuple[str, bytes]], 
        session_id: str
    ) -> List[EncryptedChunk]:
        """
        Encrypt multiple chunks for a session
        
        Args:
            chunks: List of (chunk_id, chunk_data) tuples
            session_id: Session identifier
            
        Returns:
            List of EncryptedChunk objects
        """
        encrypted_chunks = []
        
        logger.info(f"Encrypting {len(chunks)} chunks for session {session_id}")
        
        for chunk_id, chunk_data in chunks:
            encrypted_chunk = await self.encrypt_chunk(
                chunk_data, chunk_id, session_id
            )
            encrypted_chunks.append(encrypted_chunk)
        
        logger.info(f"Encryption complete: {len(encrypted_chunks)} encrypted chunks")
        return encrypted_chunks
    
    async def decrypt_session_chunks(
        self, 
        encrypted_chunks: List[EncryptedChunk]
    ) -> List[Tuple[str, bytes]]:
        """
        Decrypt multiple chunks for a session
        
        Args:
            encrypted_chunks: List of EncryptedChunk objects
            
        Returns:
            List of (chunk_id, decrypted_data) tuples
        """
        decrypted_chunks = []
        
        logger.info(f"Decrypting {len(encrypted_chunks)} chunks")
        
        for encrypted_chunk in encrypted_chunks:
            try:
                decrypted_data = await self.decrypt_chunk(encrypted_chunk)
                decrypted_chunks.append((encrypted_chunk.chunk_id, decrypted_data))
            except Exception as e:
                logger.error(f"Failed to decrypt chunk {encrypted_chunk.chunk_id}: {e}")
                raise
        
        logger.info(f"Decryption complete: {len(decrypted_chunks)} chunks decrypted")
        return decrypted_chunks
    
    def rotate_master_key(self, new_master_key: Optional[bytes] = None) -> bytes:
        """
        Rotate the master key for enhanced security
        
        Args:
            new_master_key: Optional new master key (generated if None)
            
        Returns:
            New master key
        """
        old_master_key = self.master_key
        self.master_key = new_master_key or secrets.token_bytes(self.KEY_SIZE)
        
        # Clear key cache to force re-derivation
        self._key_cache.clear()
        
        logger.info("Master key rotated, key cache cleared")
        return self.master_key
    
    def get_encryption_stats(self, session_id: str) -> dict:
        """Get encryption statistics for a session"""
        
        encrypted_files = list(self.output_dir.glob(f"*_chunk_*.enc"))
        session_files = [f for f in encrypted_files if session_id in f.name]
        
        if not session_files:
            return {
                "session_id": session_id,
                "total_encrypted_chunks": 0,
                "total_encrypted_size": 0,
                "average_overhead": 0.0
            }
        
        total_encrypted_size = sum(f.stat().st_size for f in session_files)
        
        return {
            "session_id": session_id,
            "total_encrypted_chunks": len(session_files),
            "total_encrypted_size": total_encrypted_size,
            "average_overhead": 0.0  # Would need to compare with original sizes
        }
    
    async def cleanup_session_encrypted_chunks(self, session_id: str) -> int:
        """Clean up all encrypted chunks for a session"""
        
        encrypted_files = list(self.output_dir.glob(f"*_chunk_*.enc"))
        session_files = [f for f in encrypted_files if session_id in f.name]
        removed_count = 0
        
        for encrypted_file in session_files:
            try:
                encrypted_file.unlink()
                removed_count += 1
            except OSError as e:
                logger.error(f"Failed to remove encrypted file {encrypted_file}: {e}")
        
        logger.info(f"Cleaned up {removed_count} encrypted chunks for session {session_id}")
        return removed_count

# CLI interface for testing
async def main():
    """Test the encryptor with sample data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID Session Encryptor")
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--input-file", required=True, help="Input file to encrypt")
    parser.add_argument("--output-dir", default="/data/encrypted", help="Output directory")
    parser.add_argument("--decrypt", action="store_true", help="Decrypt instead of encrypt")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create encryptor
    encryptor = SessionEncryptor(args.output_dir)
    
    if args.decrypt:
        # Decrypt mode (would need encrypted chunk metadata)
        print("Decrypt mode not implemented in CLI")
    else:
        # Encrypt mode
        with open(args.input_file, 'rb') as f:
            data = f.read()
        
        # Create a single chunk
        chunk_id = f"{args.session_id}_chunk_000000"
        
        # Encrypt the chunk
        encrypted_chunk = await encryptor.encrypt_chunk(
            data, chunk_id, args.session_id
        )
        
        print(f"Encrypted chunk: {chunk_id}")
        print(f"Original size: {len(data)} bytes")
        print(f"Encrypted size: {len(encrypted_chunk.encrypted_data)} bytes")
        print(f"File path: {encrypted_chunk.file_path}")

if __name__ == "__main__":
    asyncio.run(main())
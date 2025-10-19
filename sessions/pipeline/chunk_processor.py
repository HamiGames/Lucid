#!/usr/bin/env python3
"""
LUCID Chunk Processor - SPEC-1B Implementation
Handles session chunk processing with compression and encryption
"""

import asyncio
import logging
import time
import zlib
import gzip
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChunkConfig:
    """Chunk processing configuration"""
    chunk_size_mb: int = 10
    compression_level: int = 6
    encryption_algorithm: str = "ChaCha20Poly1305"  # XChaCha20-Poly1305 equivalent
    merkle_hash_algorithm: str = "BLAKE3"  # BLAKE3 for Merkle trees
    compression_algorithm: str = "gzip"  # gzip, zlib, or lz4

@dataclass
class ChunkMetadata:
    """Chunk metadata information"""
    chunk_id: str
    session_id: str
    sequence_number: int
    size_original: int
    size_compressed: int
    size_encrypted: int
    compression_ratio: float
    compression_time_ms: float
    encryption_time_ms: float
    hash_original: str
    hash_compressed: str
    hash_encrypted: str
    timestamp: datetime
    merkle_hash: str

class ChunkProcessor:
    """
    LUCID Chunk Processor
    
    Processes session chunks through:
    1. Compression (gzip level 6)
    2. Encryption (XChaCha20-Poly1305)
    3. Hashing (BLAKE3)
    4. Merkle tree integration
    """
    
    def __init__(self, config: ChunkConfig):
        self.config = config
        self.session_keys: Dict[str, bytes] = {}  # Per-session encryption keys
        self.compression_stats: Dict[str, Dict[str, float]] = {}
        self.encryption_stats: Dict[str, Dict[str, float]] = {}
        
    async def initialize_session(self, session_id: str) -> str:
        """
        Initialize chunk processing for session
        
        Args:
            session_id: Session identifier
            
        Returns:
            session_key: Generated encryption key for session
        """
        try:
            logger.info(f"Initializing chunk processor for session {session_id}")
            
            # Generate session-specific encryption key
            session_key = await self._generate_session_key()
            self.session_keys[session_id] = session_key
            
            # Initialize compression stats
            self.compression_stats[session_id] = {
                "total_chunks": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "avg_compression_ratio": 0.0,
                "total_compression_time": 0.0
            }
            
            # Initialize encryption stats
            self.encryption_stats[session_id] = {
                "total_chunks": 0,
                "total_encryption_time": 0.0,
                "avg_encryption_time": 0.0
            }
            
            logger.info(f"Chunk processor initialized for session {session_id}")
            
            return base64.b64encode(session_key).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to initialize chunk processor for session {session_id}: {e}")
            raise
    
    async def process_chunk(self, session_id: str, chunk_data: bytes, sequence_number: int) -> ChunkMetadata:
        """
        Process chunk through compression and encryption pipeline
        
        Args:
            session_id: Session identifier
            chunk_data: Raw chunk data
            sequence_number: Chunk sequence number
            
        Returns:
            chunk_metadata: Processed chunk metadata
        """
        try:
            start_time = time.time()
            
            # Validate chunk size
            chunk_size_mb = len(chunk_data) / (1024 * 1024)
            if chunk_size_mb > self.config.chunk_size_mb:
                logger.warning(f"Chunk size {chunk_size_mb:.2f}MB exceeds limit {self.config.chunk_size_mb}MB")
            
            # Generate chunk ID
            chunk_id = f"chunk_{session_id}_{sequence_number}_{int(time.time())}"
            
            # Calculate original hash
            hash_original = await self._calculate_hash(chunk_data, self.config.merkle_hash_algorithm)
            
            # Compress chunk
            compressed_data, compression_time = await self._compress_chunk(chunk_data)
            hash_compressed = await self._calculate_hash(compressed_data, self.config.merkle_hash_algorithm)
            
            # Encrypt chunk
            encrypted_data, encryption_time = await self._encrypt_chunk(session_id, compressed_data)
            hash_encrypted = await self._calculate_hash(encrypted_data, self.config.merkle_hash_algorithm)
            
            # Calculate compression ratio
            compression_ratio = len(chunk_data) / len(compressed_data) if len(compressed_data) > 0 else 1.0
            
            # Create chunk metadata
            chunk_metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id=session_id,
                sequence_number=sequence_number,
                size_original=len(chunk_data),
                size_compressed=len(compressed_data),
                size_encrypted=len(encrypted_data),
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time * 1000,
                encryption_time_ms=encryption_time * 1000,
                hash_original=hash_original,
                hash_compressed=hash_compressed,
                hash_encrypted=hash_encrypted,
                timestamp=datetime.utcnow(),
                merkle_hash=hash_encrypted  # Use encrypted hash for Merkle tree
            )
            
            # Update statistics
            await self._update_statistics(session_id, chunk_metadata)
            
            processing_time = time.time() - start_time
            logger.debug(f"Processed chunk {chunk_id} in {processing_time*1000:.2f}ms")
            
            return chunk_metadata
            
        except Exception as e:
            logger.error(f"Failed to process chunk for session {session_id}: {e}")
            raise
    
    async def _compress_chunk(self, chunk_data: bytes) -> Tuple[bytes, float]:
        """
        Compress chunk data using configured algorithm
        
        Args:
            chunk_data: Raw chunk data
            
        Returns:
            compressed_data: Compressed chunk data
            compression_time: Compression time in seconds
        """
        try:
            start_time = time.time()
            
            if self.config.compression_algorithm == "gzip":
                compressed_data = gzip.compress(chunk_data, compresslevel=self.config.compression_level)
            elif self.config.compression_algorithm == "zlib":
                compressed_data = zlib.compress(chunk_data, level=self.config.compression_level)
            else:
                # Default to gzip if unknown algorithm
                compressed_data = gzip.compress(chunk_data, compresslevel=self.config.compression_level)
            
            compression_time = time.time() - start_time
            
            logger.debug(f"Compressed {len(chunk_data)} bytes to {len(compressed_data)} bytes "
                        f"({len(chunk_data)/len(compressed_data):.2f}x ratio) in {compression_time*1000:.2f}ms")
            
            return compressed_data, compression_time
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise
    
    async def _encrypt_chunk(self, session_id: str, chunk_data: bytes) -> Tuple[bytes, float]:
        """
        Encrypt chunk data using session-specific key
        
        Args:
            session_id: Session identifier
            chunk_data: Chunk data to encrypt
            
        Returns:
            encrypted_data: Encrypted chunk data
            encryption_time: Encryption time in seconds
        """
        try:
            start_time = time.time()
            
            # Get session key
            session_key = self.session_keys.get(session_id)
            if not session_key:
                raise ValueError(f"No encryption key found for session {session_id}")
            
            # Generate nonce for this chunk
            nonce = secrets.token_bytes(12)  # 96-bit nonce for ChaCha20Poly1305
            
            # Encrypt using ChaCha20Poly1305 (XChaCha20-Poly1305 equivalent)
            cipher = ChaCha20Poly1305(session_key)
            encrypted_data = cipher.encrypt(nonce, chunk_data, None)
            
            # Prepend nonce to encrypted data
            encrypted_data = nonce + encrypted_data
            
            encryption_time = time.time() - start_time
            
            logger.debug(f"Encrypted {len(chunk_data)} bytes to {len(encrypted_data)} bytes "
                        f"in {encryption_time*1000:.2f}ms")
            
            return encrypted_data, encryption_time
            
        except Exception as e:
            logger.error(f"Encryption failed for session {session_id}: {e}")
            raise
    
    async def _calculate_hash(self, data: bytes, algorithm: str) -> str:
        """
        Calculate hash of data using specified algorithm
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm (BLAKE3, SHA256, etc.)
            
        Returns:
            hash_hex: Hexadecimal hash string
        """
        try:
            if algorithm == "BLAKE3":
                # Use hashlib.blake2b as BLAKE3 equivalent (BLAKE3 not available in standard library)
                hash_obj = hashlib.blake2b(data, digest_size=32)
            elif algorithm == "SHA256":
                hash_obj = hashlib.sha256(data)
            else:
                # Default to SHA256
                hash_obj = hashlib.sha256(data)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Hash calculation failed: {e}")
            raise
    
    async def _generate_session_key(self) -> bytes:
        """
        Generate session-specific encryption key
        
        Returns:
            session_key: 32-byte encryption key
        """
        return secrets.token_bytes(32)  # 256-bit key
    
    async def _update_statistics(self, session_id: str, chunk_metadata: ChunkMetadata):
        """Update processing statistics for session"""
        try:
            # Update compression stats
            comp_stats = self.compression_stats[session_id]
            comp_stats["total_chunks"] += 1
            comp_stats["total_original_size"] += chunk_metadata.size_original
            comp_stats["total_compressed_size"] += chunk_metadata.size_compressed
            comp_stats["total_compression_time"] += chunk_metadata.compression_time_ms / 1000
            
            # Calculate average compression ratio
            if comp_stats["total_compressed_size"] > 0:
                comp_stats["avg_compression_ratio"] = (
                    comp_stats["total_original_size"] / comp_stats["total_compressed_size"]
                )
            
            # Update encryption stats
            enc_stats = self.encryption_stats[session_id]
            enc_stats["total_chunks"] += 1
            enc_stats["total_encryption_time"] += chunk_metadata.encryption_time_ms / 1000
            enc_stats["avg_encryption_time"] = enc_stats["total_encryption_time"] / enc_stats["total_chunks"]
            
        except Exception as e:
            logger.error(f"Failed to update statistics for session {session_id}: {e}")
    
    async def decrypt_chunk(self, session_id: str, encrypted_data: bytes) -> bytes:
        """
        Decrypt chunk data using session key
        
        Args:
            session_id: Session identifier
            encrypted_data: Encrypted chunk data with nonce
            
        Returns:
            decrypted_data: Decrypted chunk data
        """
        try:
            # Get session key
            session_key = self.session_keys.get(session_id)
            if not session_key:
                raise ValueError(f"No encryption key found for session {session_id}")
            
            # Extract nonce and encrypted data
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Decrypt using ChaCha20Poly1305
            cipher = ChaCha20Poly1305(session_key)
            decrypted_data = cipher.decrypt(nonce, ciphertext, None)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption failed for session {session_id}: {e}")
            raise
    
    async def decompress_chunk(self, compressed_data: bytes) -> bytes:
        """
        Decompress chunk data using configured algorithm
        
        Args:
            compressed_data: Compressed chunk data
            
        Returns:
            decompressed_data: Decompressed chunk data
        """
        try:
            if self.config.compression_algorithm == "gzip":
                decompressed_data = gzip.decompress(compressed_data)
            elif self.config.compression_algorithm == "zlib":
                decompressed_data = zlib.decompress(compressed_data)
            else:
                # Default to gzip
                decompressed_data = gzip.decompress(compressed_data)
            
            return decompressed_data
            
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get processing statistics for session"""
        if session_id not in self.compression_stats:
            return {}
        
        comp_stats = self.compression_stats[session_id]
        enc_stats = self.encryption_stats[session_id]
        
        return {
            "session_id": session_id,
            "compression": {
                "total_chunks": comp_stats["total_chunks"],
                "total_original_size": comp_stats["total_original_size"],
                "total_compressed_size": comp_stats["total_compressed_size"],
                "avg_compression_ratio": comp_stats["avg_compression_ratio"],
                "total_compression_time": comp_stats["total_compression_time"],
                "avg_compression_time_ms": (comp_stats["total_compression_time"] / comp_stats["total_chunks"] * 1000) if comp_stats["total_chunks"] > 0 else 0
            },
            "encryption": {
                "total_chunks": enc_stats["total_chunks"],
                "total_encryption_time": enc_stats["total_encryption_time"],
                "avg_encryption_time_ms": enc_stats["avg_encryption_time"] * 1000
            },
            "config": {
                "chunk_size_mb": self.config.chunk_size_mb,
                "compression_level": self.config.compression_level,
                "compression_algorithm": self.config.compression_algorithm,
                "encryption_algorithm": self.config.encryption_algorithm,
                "merkle_hash_algorithm": self.config.merkle_hash_algorithm
            }
        }
    
    async def cleanup_session(self, session_id: str):
        """Cleanup session resources"""
        try:
            logger.info(f"Cleaning up chunk processor for session {session_id}")
            
            # Remove session key
            if session_id in self.session_keys:
                del self.session_keys[session_id]
            
            # Remove statistics
            if session_id in self.compression_stats:
                del self.compression_stats[session_id]
            
            if session_id in self.encryption_stats:
                del self.encryption_stats[session_id]
            
            logger.info(f"Chunk processor cleanup completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup chunk processor for session {session_id}: {e}")

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize chunk processor
        config = ChunkConfig(
            chunk_size_mb=10,
            compression_level=6,
            compression_algorithm="gzip",
            encryption_algorithm="ChaCha20Poly1305",
            merkle_hash_algorithm="BLAKE3"
        )
        
        processor = ChunkProcessor(config)
        
        # Initialize session
        session_id = "session_123"
        session_key = await processor.initialize_session(session_id)
        print(f"Session key generated: {session_key[:20]}...")
        
        # Process some chunks
        for i in range(5):
            chunk_data = f"Sample chunk data {i} with some content to compress and encrypt".encode() * 1000
            chunk_metadata = await processor.process_chunk(session_id, chunk_data, i)
            
            print(f"Chunk {i}:")
            print(f"  Original size: {chunk_metadata.size_original} bytes")
            print(f"  Compressed size: {chunk_metadata.size_compressed} bytes")
            print(f"  Encrypted size: {chunk_metadata.size_encrypted} bytes")
            print(f"  Compression ratio: {chunk_metadata.compression_ratio:.2f}x")
            print(f"  Compression time: {chunk_metadata.compression_time_ms:.2f}ms")
            print(f"  Encryption time: {chunk_metadata.encryption_time_ms:.2f}ms")
            print()
        
        # Get statistics
        stats = processor.get_session_statistics(session_id)
        print("Session Statistics:")
        print(f"  Total chunks: {stats['compression']['total_chunks']}")
        print(f"  Average compression ratio: {stats['compression']['avg_compression_ratio']:.2f}x")
        print(f"  Average compression time: {stats['compression']['avg_compression_time_ms']:.2f}ms")
        print(f"  Average encryption time: {stats['encryption']['avg_encryption_time_ms']:.2f}ms")
        
        # Cleanup
        await processor.cleanup_session(session_id)
        print("Session cleanup completed")
    
    asyncio.run(main())

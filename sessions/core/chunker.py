# Path: apps/chunker/chunker.py
# Lucid RDP Data Chunker - 8-16MB chunks with Zstd compression
# Based on LUCID-STRICT requirements per Spec-1b

from __future__ import annotations

import os
import zstandard as zstd
import logging
from pathlib import Path
from typing import List, Iterator, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import uuid

logger = logging.getLogger(__name__)

# Runtime variables per specification
CHUNK_MIN_SIZE = int(os.getenv("LUCID_CHUNK_MIN_SIZE", "8388608"))    # 8MB
CHUNK_MAX_SIZE = int(os.getenv("LUCID_CHUNK_MAX_SIZE", "16777216"))   # 16MB
COMPRESSION_LEVEL = int(os.getenv("LUCID_COMPRESSION_LEVEL", "3"))    # Zstd level 3
BASE_MB_PER_SESSION = int(os.getenv("BASE_MB_PER_SESSION", "5"))      # Per Spec-1c


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadata for a compressed chunk"""
    chunk_id: str
    session_id: str
    sequence_number: int
    original_size: int
    compressed_size: int
    compression_ratio: float
    chunk_hash: str
    created_at: datetime
    
    def to_dict(self) -> dict:
        """Convert to MongoDB document format"""
        return {
            "_id": self.chunk_id,
            "session_id": self.session_id,
            "idx": self.sequence_number,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "chunk_hash": self.chunk_hash,
            "created_at": self.created_at
        }


class LucidChunker:
    """
    Handles data chunking with Zstd compression for Lucid RDP sessions.
    
    Per Spec-1b: 8-16 MB chunks before compression, Zstd level 3
    Chunks are prepared for XChaCha20-Poly1305 encryption by encryptor service.
    """
    
    def __init__(self, session_id: str, compression_level: int = COMPRESSION_LEVEL):
        self.session_id = session_id
        self.compression_level = compression_level
        self.chunk_counter = 0
        
        # Initialize Zstd compressor with specified level
        self.compressor = zstd.ZstdCompressor(level=compression_level)
        self.decompressor = zstd.ZstdDecompressor()
        
        # Buffer for accumulating data before chunking
        self.buffer = bytearray()
        
        logger.info(f"Chunker initialized for session {session_id}, level {compression_level}")
    
    def add_data(self, data: bytes) -> List[ChunkMetadata]:
        """
        Add data to buffer and return completed chunks.
        
        Args:
            data: Raw RDP session data from recorder
            
        Returns:
            List of completed chunk metadata
        """
        self.buffer.extend(data)
        completed_chunks = []
        
        # Process complete chunks
        while len(self.buffer) >= CHUNK_MIN_SIZE:
            # Determine chunk boundary (min to max size)
            chunk_size = min(len(self.buffer), CHUNK_MAX_SIZE)
            
            # Extract chunk data
            chunk_data = bytes(self.buffer[:chunk_size])
            self.buffer = self.buffer[chunk_size:]
            
            # Create chunk metadata
            chunk_meta = self._create_chunk(chunk_data)
            completed_chunks.append(chunk_meta)
            
        return completed_chunks
    
    def finalize_buffer(self) -> Optional[ChunkMetadata]:
        """
        Process remaining buffer data as final chunk.
        
        Returns:
            Final chunk metadata if buffer has data
        """
        if not self.buffer:
            return None
        
        final_data = bytes(self.buffer)
        self.buffer.clear()
        
        return self._create_chunk(final_data)
    
    def _create_chunk(self, data: bytes) -> ChunkMetadata:
        """
        Compress data and create chunk metadata.
        
        Args:
            data: Raw chunk data
            
        Returns:
            Chunk metadata with compression info
        """
        original_size = len(data)
        
        # Compress with Zstd
        try:
            compressed_data = self.compressor.compress(data)
            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size
            
            # Calculate chunk hash for integrity verification
            chunk_hash = hashlib.blake3(compressed_data).hexdigest()
            
            # Generate chunk ID
            chunk_id = f"{self.session_id}-chunk-{self.chunk_counter:06d}"
            self.chunk_counter += 1
            
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id=self.session_id,
                sequence_number=self.chunk_counter - 1,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                chunk_hash=chunk_hash,
                created_at=datetime.now(timezone.utc)
            )
            
            # Store compressed data for encryptor service
            self._store_compressed_chunk(chunk_id, compressed_data)
            
            logger.debug(f"Created chunk {chunk_id}: {original_size}→{compressed_size} bytes "
                        f"({compression_ratio:.2f} ratio)")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Chunk compression failed: {e}")
            raise
    
    def _store_compressed_chunk(self, chunk_id: str, compressed_data: bytes) -> None:
        """
        Store compressed chunk data for encryptor service.
        
        Args:
            chunk_id: Unique chunk identifier
            compressed_data: Zstd compressed data
        """
        # Create session chunk directory
        chunk_dir = Path(f"/tmp/lucid/chunks/{self.session_id}")
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        # Store compressed chunk
        chunk_file = chunk_dir / f"{chunk_id}.zst"
        chunk_file.write_bytes(compressed_data)
        
        logger.debug(f"Stored compressed chunk: {chunk_file}")
    
    def decompress_chunk(self, chunk_id: str) -> bytes:
        """
        Decompress a stored chunk for verification or recovery.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Original uncompressed data
        """
        try:
            chunk_file = Path(f"/tmp/lucid/chunks/{self.session_id}/{chunk_id}.zst")
            
            if not chunk_file.exists():
                raise FileNotFoundError(f"Chunk file not found: {chunk_file}")
            
            compressed_data = chunk_file.read_bytes()
            original_data = self.decompressor.decompress(compressed_data)
            
            logger.debug(f"Decompressed chunk {chunk_id}: {len(original_data)} bytes")
            return original_data
            
        except Exception as e:
            logger.error(f"Chunk decompression failed for {chunk_id}: {e}")
            raise
    
    def get_chunk_stats(self) -> dict:
        """Get chunker statistics for session monitoring."""
        return {
            "session_id": self.session_id,
            "chunks_created": self.chunk_counter,
            "buffer_size": len(self.buffer),
            "compression_level": self.compression_level
        }


class SessionChunkManager:
    """
    Manages chunking for multiple sessions.
    Interfaces with session recorder and encryptor services.
    """
    
    def __init__(self):
        self.active_chunkers: dict[str, LucidChunker] = {}
        logger.info("Session chunk manager initialized")
    
    def start_chunking(self, session_id: str, compression_level: int = COMPRESSION_LEVEL) -> None:
        """Start chunking for a new session."""
        if session_id in self.active_chunkers:
            logger.warning(f"Chunker already exists for session {session_id}")
            return
        
        chunker = LucidChunker(session_id, compression_level)
        self.active_chunkers[session_id] = chunker
        
        logger.info(f"Started chunking for session {session_id}")
    
    def process_session_data(self, session_id: str, data: bytes) -> List[ChunkMetadata]:
        """Process data for a session and return completed chunks."""
        chunker = self.active_chunkers.get(session_id)
        if not chunker:
            raise ValueError(f"No chunker found for session {session_id}")
        
        return chunker.add_data(data)
    
    def finalize_session(self, session_id: str) -> Optional[ChunkMetadata]:
        """Finalize chunking for a session and clean up."""
        chunker = self.active_chunkers.get(session_id)
        if not chunker:
            logger.warning(f"No chunker found for session {session_id}")
            return None
        
        # Process final chunk
        final_chunk = chunker.finalize_buffer()
        
        # Remove from active chunkers
        del self.active_chunkers[session_id]
        
        logger.info(f"Finalized chunking for session {session_id}")
        return final_chunk
    
    def get_session_stats(self, session_id: str) -> Optional[dict]:
        """Get statistics for a specific session."""
        chunker = self.active_chunkers.get(session_id)
        return chunker.get_chunk_stats() if chunker else None
    
    def get_all_sessions(self) -> List[str]:
        """Get list of all active chunking sessions."""
        return list(self.active_chunkers.keys())


# Module-level instance for service integration
chunk_manager = SessionChunkManager()


def calculate_work_units(total_bytes: int) -> int:
    """
    Calculate work units for PoOT consensus per Spec-1c.
    
    Args:
        total_bytes: Total compressed bytes processed
        
    Returns:
        Work units for consensus calculation
    """
    base_mb = BASE_MB_PER_SESSION * 1024 * 1024  # Convert to bytes
    return max(1, total_bytes // base_mb)


def validate_chunk_integrity(chunk_meta: ChunkMetadata, stored_data: bytes) -> bool:
    """
    Validate chunk integrity using stored hash.
    
    Args:
        chunk_meta: Chunk metadata with hash
        stored_data: Stored compressed chunk data
        
    Returns:
        True if chunk is valid
    """
    calculated_hash = hashlib.blake3(stored_data).hexdigest()
    return calculated_hash == chunk_meta.chunk_hash


if __name__ == "__main__":
    # Test chunker functionality
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python chunker.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    chunker = LucidChunker(session_id)
    
    # Test with sample data
    test_data = b"X" * (10 * 1024 * 1024)  # 10MB test data
    chunks = chunker.add_data(test_data)
    
    print(f"Created {len(chunks)} chunks for session {session_id}")
    for chunk in chunks:
        print(f"  {chunk.chunk_id}: {chunk.original_size}→{chunk.compressed_size} "
              f"({chunk.compression_ratio:.2f} ratio)")
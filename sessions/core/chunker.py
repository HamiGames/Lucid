#!/usr/bin/env python3
"""
LUCID Session Chunker - SPEC-1B Implementation
8-16MB chunking with Zstd compression (level 3)
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple
import zstd

logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Metadata for a session chunk"""
    chunk_id: str
    session_id: str
    chunk_index: int
    chunk_size: int
    compressed_size: int
    compression_ratio: float
    checksum: str
    timestamp: float
    file_path: str

class SessionChunker:
    """
    Implements 8-16MB chunking with Zstd level 3 compression per SPEC-1b
    """
    
    CHUNK_SIZE_MIN = int(os.getenv("LUCID_CHUNK_SIZE_MIN", "8388608"))   # 8MB default
    CHUNK_SIZE_MAX = int(os.getenv("LUCID_CHUNK_SIZE_MAX", "16777216"))  # 16MB default
    COMPRESSION_LEVEL = int(os.getenv("LUCID_COMPRESSION_LEVEL", "3"))   # Zstd level 3 default
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or os.getenv("LUCID_CHUNKER_OUTPUT_DIR", "/data/chunks"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def chunk_session_data(
        self, 
        session_id: str, 
        data_stream: bytes,
        target_chunk_size: Optional[int] = None
    ) -> List[ChunkMetadata]:
        """
        Chunk session data with optimal compression
        
        Args:
            session_id: Unique session identifier
            data_stream: Raw session data to chunk
            target_chunk_size: Optional target chunk size (defaults to 8MB)
            
        Returns:
            List of ChunkMetadata objects
        """
        if target_chunk_size is None:
            target_chunk_size = self.CHUNK_SIZE_MIN
            
        # Ensure target size is within bounds
        target_chunk_size = max(
            self.CHUNK_SIZE_MIN,
            min(target_chunk_size, self.CHUNK_SIZE_MAX)
        )
        
        chunks = []
        chunk_index = 0
        offset = 0
        
        logger.info(f"Starting chunking for session {session_id}, target size: {target_chunk_size}")
        
        while offset < len(data_stream):
            # Calculate chunk boundaries
            chunk_end = min(offset + target_chunk_size, len(data_stream))
            chunk_data = data_stream[offset:chunk_end]
            
            # Create chunk metadata
            chunk_id = f"{session_id}_chunk_{chunk_index:06d}"
            chunk_metadata = await self._process_chunk(
                chunk_id, session_id, chunk_index, chunk_data
            )
            
            chunks.append(chunk_metadata)
            
            logger.debug(f"Created chunk {chunk_index}: {chunk_metadata.chunk_size} bytes -> {chunk_metadata.compressed_size} bytes")
            
            offset = chunk_end
            chunk_index += 1
            
        logger.info(f"Chunking complete: {len(chunks)} chunks created for session {session_id}")
        return chunks
    
    async def _process_chunk(
        self, 
        chunk_id: str, 
        session_id: str, 
        chunk_index: int, 
        chunk_data: bytes
    ) -> ChunkMetadata:
        """Process a single chunk with compression and metadata"""
        
        # Calculate checksum before compression
        checksum = hashlib.sha256(chunk_data).hexdigest()
        
        # Compress with Zstd level 3
        compressed_data = zstd.compress(chunk_data, level=self.COMPRESSION_LEVEL)
        
        # Calculate compression ratio
        compression_ratio = len(compressed_data) / len(chunk_data) if chunk_data else 0
        
        # Save compressed chunk to disk
        chunk_filename = f"{chunk_id}.zst"
        chunk_path = self.output_dir / chunk_filename
        
        with open(chunk_path, 'wb') as f:
            f.write(compressed_data)
        
        # Create metadata
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            session_id=session_id,
            chunk_index=chunk_index,
            chunk_size=len(chunk_data),
            compressed_size=len(compressed_data),
            compression_ratio=compression_ratio,
            checksum=checksum,
            timestamp=time.time(),
            file_path=str(chunk_path)
        )
        
        return metadata
    
    async def stream_chunk_session_data(
        self, 
        session_id: str, 
        data_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ChunkMetadata, None]:
        """
        Stream chunking for large session data
        
        Args:
            session_id: Unique session identifier
            data_stream: Async generator yielding data chunks
            
        Yields:
            ChunkMetadata objects as chunks are processed
        """
        chunk_index = 0
        current_chunk = b""
        target_size = self.CHUNK_SIZE_MIN
        
        logger.info(f"Starting stream chunking for session {session_id}")
        
        async for data_chunk in data_stream:
            current_chunk += data_chunk
            
            # Process chunk when we reach target size
            while len(current_chunk) >= target_size:
                # Extract chunk data
                chunk_data = current_chunk[:target_size]
                current_chunk = current_chunk[target_size:]
                
                # Create chunk metadata
                chunk_id = f"{session_id}_chunk_{chunk_index:06d}"
                metadata = await self._process_chunk(
                    chunk_id, session_id, chunk_index, chunk_data
                )
                
                yield metadata
                chunk_index += 1
        
        # Process remaining data
        if current_chunk:
            chunk_id = f"{session_id}_chunk_{chunk_index:06d}"
            metadata = await self._process_chunk(
                chunk_id, session_id, chunk_index, current_chunk
            )
            yield metadata
        
        logger.info(f"Stream chunking complete: {chunk_index + 1} chunks for session {session_id}")
    
    async def get_chunk_data(self, chunk_metadata: ChunkMetadata) -> bytes:
        """Retrieve and decompress chunk data"""
        
        if not os.path.exists(chunk_metadata.file_path):
            raise FileNotFoundError(f"Chunk file not found: {chunk_metadata.file_path}")
        
        with open(chunk_metadata.file_path, 'rb') as f:
            compressed_data = f.read()
        
        # Decompress with Zstd
        decompressed_data = zstd.decompress(compressed_data)
        
        # Verify checksum
        calculated_checksum = hashlib.sha256(decompressed_data).hexdigest()
        if calculated_checksum != chunk_metadata.checksum:
            raise ValueError(f"Checksum mismatch for chunk {chunk_metadata.chunk_id}")
        
        return decompressed_data
    
    async def cleanup_session_chunks(self, session_id: str) -> int:
        """Clean up all chunks for a session"""
        
        chunk_files = list(self.output_dir.glob(f"{session_id}_chunk_*.zst"))
        removed_count = 0
        
        for chunk_file in chunk_files:
            try:
                chunk_file.unlink()
                removed_count += 1
            except OSError as e:
                logger.error(f"Failed to remove chunk file {chunk_file}: {e}")
        
        logger.info(f"Cleaned up {removed_count} chunks for session {session_id}")
        return removed_count
    
    def get_chunking_stats(self, session_id: str) -> dict:
        """Get chunking statistics for a session"""
        
        chunk_files = list(self.output_dir.glob(f"{session_id}_chunk_*.zst"))
        
        if not chunk_files:
            return {
                "session_id": session_id,
                "total_chunks": 0,
                "total_size": 0,
                "total_compressed_size": 0,
                "average_compression_ratio": 0.0
            }
        
        total_size = 0
        total_compressed_size = 0
        
        for chunk_file in chunk_files:
            total_compressed_size += chunk_file.stat().st_size
        
        return {
            "session_id": session_id,
            "total_chunks": len(chunk_files),
            "total_size": total_size,  # Would need to read metadata for accurate size
            "total_compressed_size": total_compressed_size,
            "average_compression_ratio": total_compressed_size / total_size if total_size > 0 else 0.0
        }

# CLI interface for testing
async def main():
    """Test the chunker with sample data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID Session Chunker")
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--input-file", required=True, help="Input file to chunk")
    parser.add_argument("--output-dir", default="/data/chunks", help="Output directory")
    parser.add_argument("--chunk-size", type=int, default=8*1024*1024, help="Target chunk size")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create chunker
    chunker = SessionChunker(args.output_dir)
    
    # Read input file
    with open(args.input_file, 'rb') as f:
        data = f.read()
    
    # Chunk the data
    chunks = await chunker.chunk_session_data(
        args.session_id, 
        data, 
        args.chunk_size
    )
    
    print(f"Created {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"  {chunk.chunk_id}: {chunk.chunk_size} -> {chunk.compressed_size} bytes (ratio: {chunk.compression_ratio:.3f})")

if __name__ == "__main__":
    asyncio.run(main())
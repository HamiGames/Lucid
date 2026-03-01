#!/usr/bin/env python3
"""
Lucid Session Management Chunk Generator
Generates 10MB chunks from session recordings with compression
"""

import asyncio
import hashlib
import gzip
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from dataclasses import dataclass
import uuid
import os

from .session_recorder import ChunkMetadata

logger = logging.getLogger(__name__)

@dataclass
class ChunkConfig:
    """Chunk generation configuration for Step 15 requirements"""
    chunk_size_mb: int = 10  # 10MB chunks as required
    compression_level: int = 6  # gzip level 6 as required
    output_path: Path = Path("/data/chunks")
    enable_compression: bool = True
    quality_threshold: float = 0.8

class ChunkGenerator:
    """
    Generates chunks from session recordings
    Creates 10MB chunks with gzip compression level 6 as required by Step 15
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        self.session_id: Optional[str] = None
        self.chunk_index = 0
        self.current_chunk_data = bytearray()
        self.chunk_metadata: List[ChunkMetadata] = []
        
        # Create output directory
        self.config.output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Chunk Generator initialized")
    
    async def initialize_session(self, session_id: str) -> None:
        """Initialize chunk generation for a session"""
        self.session_id = session_id
        self.chunk_index = 0
        self.current_chunk_data = bytearray()
        self.chunk_metadata = []
        
        logger.info(f"Initialized chunk generation for session {session_id}")
    
    async def add_data(self, data: bytes) -> List[ChunkMetadata]:
        """
        Add data to current chunk and generate chunks when size limit is reached
        
        Args:
            data: Raw data to add to chunk
            
        Returns:
            List of completed chunk metadata
        """
        if not self.session_id:
            raise ValueError("Session not initialized")
        
        self.current_chunk_data.extend(data)
        completed_chunks = []
        
        # Check if current chunk exceeds size limit
        chunk_size_limit = self.config.chunk_size_mb * 1024 * 1024
        
        while len(self.current_chunk_data) >= chunk_size_limit:
            # Extract chunk data
            chunk_data = bytes(self.current_chunk_data[:chunk_size_limit])
            self.current_chunk_data = self.current_chunk_data[chunk_size_limit:]
            
            # Generate chunk
            chunk_metadata = await self._generate_chunk(chunk_data)
            completed_chunks.append(chunk_metadata)
            self.chunk_metadata.append(chunk_metadata)
            
            self.chunk_index += 1
        
        return completed_chunks
    
    async def finalize_session(self) -> List[ChunkMetadata]:
        """
        Finalize session by processing remaining data
        
        Returns:
            List of final chunk metadata
        """
        if not self.session_id:
            raise ValueError("Session not initialized")
        
        completed_chunks = []
        
        # Process remaining data if any
        if len(self.current_chunk_data) > 0:
            chunk_data = bytes(self.current_chunk_data)
            chunk_metadata = await self._generate_chunk(chunk_data)
            completed_chunks.append(chunk_metadata)
            self.chunk_metadata.append(chunk_metadata)
            self.chunk_index += 1
        
        logger.info(f"Finalized chunk generation for session {self.session_id}: {len(completed_chunks)} chunks")
        return completed_chunks
    
    async def _generate_chunk(self, chunk_data: bytes) -> ChunkMetadata:
        """Generate a single chunk with metadata"""
        chunk_id = f"{self.session_id}-chunk-{self.chunk_index:06d}"
        
        # Calculate hash
        hash_sha256 = hashlib.sha256(chunk_data).hexdigest()
        
        # Compress data if enabled
        if self.config.enable_compression:
            compressed_data = gzip.compress(chunk_data, compresslevel=self.config.compression_level)
            compression_ratio = len(chunk_data) / len(compressed_data) if len(compressed_data) > 0 else 1.0
            final_data = compressed_data
            compressed = True
        else:
            final_data = chunk_data
            compression_ratio = 1.0
            compressed = False
        
        # Calculate quality score (placeholder implementation)
        quality_score = await self._calculate_quality_score(chunk_data)
        
        # Create chunk metadata
        chunk_metadata = ChunkMetadata(
            chunk_id=chunk_id,
            session_id=self.session_id,
            chunk_index=self.chunk_index,
            size_bytes=len(final_data),
            hash_sha256=hash_sha256,
            timestamp=datetime.now(timezone.utc),
            compressed=compressed,
            compression_ratio=compression_ratio,
            quality_score=quality_score
        )
        
        # Write chunk to disk
        await self._write_chunk(chunk_id, final_data, chunk_metadata)
        
        logger.debug(f"Generated chunk {chunk_id}: {len(final_data)} bytes, compression ratio: {compression_ratio:.2f}")
        
        return chunk_metadata
    
    async def _write_chunk(self, chunk_id: str, chunk_data: bytes, metadata: ChunkMetadata) -> None:
        """Write chunk data and metadata to disk"""
        try:
            # Write chunk data
            chunk_file = self.config.output_path / f"{chunk_id}.chunk"
            chunk_file.write_bytes(chunk_data)
            
            # Write metadata
            metadata_file = self.config.output_path / f"{chunk_id}.meta"
            metadata_dict = {
                "chunk_id": metadata.chunk_id,
                "session_id": metadata.session_id,
                "chunk_index": metadata.chunk_index,
                "size_bytes": metadata.size_bytes,
                "hash_sha256": metadata.hash_sha256,
                "timestamp": metadata.timestamp.isoformat(),
                "compressed": metadata.compressed,
                "compression_ratio": metadata.compression_ratio,
                "quality_score": metadata.quality_score
            }
            
            import json
            metadata_file.write_text(json.dumps(metadata_dict, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to write chunk {chunk_id}: {str(e)}")
            raise
    
    async def _calculate_quality_score(self, chunk_data: bytes) -> float:
        """Calculate quality score for chunk data (placeholder implementation)"""
        # This is a placeholder implementation
        # In a real implementation, this would analyze video quality metrics
        # such as PSNR, SSIM, or other quality indicators
        
        # For now, return a random score between 0.7 and 1.0
        import random
        return random.uniform(0.7, 1.0)
    
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Get metadata for a specific chunk"""
        for metadata in self.chunk_metadata:
            if metadata.chunk_id == chunk_id:
                return metadata
        return None
    
    async def get_session_chunks(self, session_id: str) -> List[ChunkMetadata]:
        """Get all chunks for a session"""
        if session_id == self.session_id:
            return self.chunk_metadata.copy()
        return []
    
    async def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk and its metadata"""
        try:
            # Find chunk metadata
            chunk_metadata = await self.get_chunk_metadata(chunk_id)
            if not chunk_metadata:
                return False
            
            # Delete chunk file
            chunk_file = self.config.output_path / f"{chunk_id}.chunk"
            if chunk_file.exists():
                chunk_file.unlink()
            
            # Delete metadata file
            metadata_file = self.config.output_path / f"{chunk_id}.meta"
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Remove from metadata list
            self.chunk_metadata = [m for m in self.chunk_metadata if m.chunk_id != chunk_id]
            
            logger.info(f"Deleted chunk {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id}: {str(e)}")
            return False
    
    async def cleanup_session(self, session_id: str) -> int:
        """Clean up all chunks for a session"""
        if session_id != self.session_id:
            return 0
        
        deleted_count = 0
        for metadata in self.chunk_metadata:
            if await self.delete_chunk(metadata.chunk_id):
                deleted_count += 1
        
        # Reset session state
        self.session_id = None
        self.chunk_index = 0
        self.current_chunk_data = bytearray()
        self.chunk_metadata = []
        
        logger.info(f"Cleaned up {deleted_count} chunks for session {session_id}")
        return deleted_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get chunk generation statistics"""
        total_size = sum(metadata.size_bytes for metadata in self.chunk_metadata)
        avg_compression_ratio = sum(metadata.compression_ratio for metadata in self.chunk_metadata) / len(self.chunk_metadata) if self.chunk_metadata else 0
        avg_quality_score = sum(metadata.quality_score for metadata in self.chunk_metadata) / len(self.chunk_metadata) if self.chunk_metadata else 0
        
        return {
            "session_id": self.session_id,
            "total_chunks": len(self.chunk_metadata),
            "total_size_bytes": total_size,
            "average_compression_ratio": avg_compression_ratio,
            "average_quality_score": avg_quality_score,
            "current_chunk_size": len(self.current_chunk_data),
            "chunk_size_limit_mb": self.config.chunk_size_mb,
            "compression_enabled": self.config.enable_compression,
            "compression_level": self.config.compression_level
        }

class ChunkProcessor:
    """
    Processes chunks from multiple sessions
    Manages chunk generation across multiple recording sessions
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        self.generators: Dict[str, ChunkGenerator] = {}
        
        logger.info("Chunk Processor initialized")
    
    async def get_or_create_generator(self, session_id: str) -> ChunkGenerator:
        """Get or create a chunk generator for a session"""
        if session_id not in self.generators:
            generator = ChunkGenerator(self.config)
            await generator.initialize_session(session_id)
            self.generators[session_id] = generator
            
            logger.info(f"Created chunk generator for session {session_id}")
        
        return self.generators[session_id]
    
    async def process_session_data(self, session_id: str, data: bytes) -> List[ChunkMetadata]:
        """Process data for a specific session"""
        generator = await self.get_or_create_generator(session_id)
        return await generator.add_data(data)
    
    async def finalize_session(self, session_id: str) -> List[ChunkMetadata]:
        """Finalize chunk generation for a session"""
        if session_id in self.generators:
            generator = self.generators[session_id]
            final_chunks = await generator.finalize_session()
            return final_chunks
        return []
    
    async def cleanup_session(self, session_id: str) -> int:
        """Clean up chunks for a session"""
        if session_id in self.generators:
            generator = self.generators[session_id]
            deleted_count = await generator.cleanup_session(session_id)
            del self.generators[session_id]
            return deleted_count
        return 0
    
    async def get_session_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a session"""
        if session_id in self.generators:
            return self.generators[session_id].get_statistics()
        return None
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all sessions"""
        return {
            session_id: generator.get_statistics()
            for session_id, generator in self.generators.items()
        }
    
    async def cleanup_all_sessions(self) -> int:
        """Clean up all sessions"""
        total_deleted = 0
        for session_id in list(self.generators.keys()):
            deleted_count = await self.cleanup_session(session_id)
            total_deleted += deleted_count
        
        logger.info(f"Cleaned up {total_deleted} chunks from all sessions")
        return total_deleted

#!/usr/bin/env python3
"""
LUCID Chunk Store Service - Step 17 Implementation
Handles chunk storage operations and file management
"""

import asyncio
import hashlib
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, BinaryIO
import aiofiles
import aiofiles.os
from dataclasses import dataclass
import zstd
import lz4.frame

logger = logging.getLogger(__name__)

# Optional import from recorder (lazy loading to avoid module initialization issues)
# Note: Module-level initialization in recorder tries to create directories which fails in read-only containers
try:
    from ..recorder.session_recorder import ChunkMetadata
except (ImportError, OSError) as e:
    # Define minimal type if recorder module is not available or initialization fails
    logger.warning(f"Failed to import recorder module (will use graceful degradation): {e}")
    ChunkMetadata = None

@dataclass
class ChunkStoreConfig:
    """Chunk store configuration"""
    base_path: str = "/app/data/chunks"  # Default should match config default (volume mount: /app/data)
    compression_algorithm: str = "zstd"  # zstd, lz4, gzip, none
    compression_level: int = 6
    chunk_size_mb: int = 10
    max_chunks_per_session: int = 100000
    cleanup_interval_hours: int = 24
    backup_enabled: bool = True
    backup_retention_days: int = 7

class ChunkStore:
    """
    Chunk store service for managing chunk files.
    
    Handles chunk storage, compression, retrieval, and cleanup operations.
    Implements efficient chunk storage for Step 17 requirements.
    """
    
    def __init__(self, config: ChunkStoreConfig):
        self.config = config
        self.base_path = Path(config.base_path)
        # In read-only containers, parent directory (e.g., /app/data) should exist via volume mount
        # Check that parent directory exists (from volume mount), then create base_path if needed
        parent_path = self.base_path.parent
        if not parent_path.exists():
            raise OSError(
                f"Parent directory does not exist: {parent_path}. "
                f"This directory should be provided via a volume mount in docker-compose. "
                f"Check that the volume is mounted correctly at {parent_path}. "
                f"Chunk store base path would be: {self.base_path}"
            )
        # Create base_path if it doesn't exist (parent already exists from volume mount)
        # Handle permission errors gracefully (user 65532:65532 needs write access)
        try:
            self.base_path.mkdir(exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied creating directory: {self.base_path}. "
                f"The container runs as user 65532:65532 and needs write access to the volume mount. "
                f"On the host, ensure the directory has correct permissions: "
                f"sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api && "
                f"sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/data/session-api. "
                f"Original error: {e}"
            )
        
        # Create directory structure (subdirectories within mounted volume)
        self._initialize_directories()
        
        # Compression functions
        self._compression_funcs = {
            "zstd": self._compress_zstd,
            "lz4": self._compress_lz4,
            "gzip": self._compress_gzip,
            "none": self._compress_none
        }
        
        self._decompression_funcs = {
            "zstd": self._decompress_zstd,
            "lz4": self._decompress_lz4,
            "gzip": self._decompress_gzip,
            "none": self._decompress_none
        }
        
        logger.info(f"ChunkStore initialized with base path: {self.base_path}")
    
    def _initialize_directories(self):
        """Initialize chunk store directory structure"""
        directories = [
            "active",
            "archived", 
            "temp",
            "backup",
            "metadata"
        ]
        
        for directory in directories:
            try:
                (self.base_path / directory).mkdir(exist_ok=True)
            except PermissionError as e:
                raise PermissionError(
                    f"Permission denied creating directory: {self.base_path / directory}. "
                    f"The container runs as user 65532:65532 and needs write access to the volume mount. "
                    f"On the host, ensure the directory has correct permissions: "
                    f"sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api && "
                    f"sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/data/session-api. "
                    f"Original error: {e}"
                )
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get session-specific directory path"""
        return self.base_path / "active" / session_id
    
    def _get_chunk_path(self, session_id: str, chunk_id: str) -> Path:
        """Get chunk file path"""
        session_path = self._get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path / f"{chunk_id}.{self.config.compression_algorithm}"
    
    def _get_metadata_path(self, session_id: str, chunk_id: str) -> Path:
        """Get chunk metadata file path"""
        metadata_path = self.base_path / "metadata" / session_id
        metadata_path.mkdir(parents=True, exist_ok=True)
        return metadata_path / f"{chunk_id}.json"
    
    async def _compress_zstd(self, data: bytes) -> bytes:
        """Compress data using Zstandard"""
        return zstd.compress(data, level=self.config.compression_level)
    
    async def _compress_lz4(self, data: bytes) -> bytes:
        """Compress data using LZ4"""
        return lz4.frame.compress(data, compression_level=self.config.compression_level)
    
    async def _compress_gzip(self, data: bytes) -> bytes:
        """Compress data using gzip"""
        import gzip
        return gzip.compress(data, compresslevel=self.config.compression_level)
    
    async def _compress_none(self, data: bytes) -> bytes:
        """No compression"""
        return data
    
    async def _decompress_zstd(self, data: bytes) -> bytes:
        """Decompress Zstandard data"""
        return zstd.decompress(data)
    
    async def _decompress_lz4(self, data: bytes) -> bytes:
        """Decompress LZ4 data"""
        return lz4.frame.decompress(data)
    
    async def _decompress_gzip(self, data: bytes) -> bytes:
        """Decompress gzip data"""
        import gzip
        return gzip.decompress(data)
    
    async def _decompress_none(self, data: bytes) -> bytes:
        """No decompression"""
        return data
    
    async def store_chunk(
        self, 
        session_id: str, 
        chunk: ChunkMetadata, 
        chunk_data: bytes
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Store chunk data with compression and metadata
        
        Returns:
            Tuple[bool, str, Dict]: (success, storage_path, metadata)
        """
        try:
            # Get compression function
            compress_func = self._compression_funcs.get(self.config.compression_algorithm)
            if not compress_func:
                raise ValueError(f"Unsupported compression algorithm: {self.config.compression_algorithm}")
            
            # Compress data
            start_time = time.time()
            compressed_data = await compress_func(chunk_data)
            compression_time = time.time() - start_time
            
            # Calculate compression ratio
            compression_ratio = len(compressed_data) / len(chunk_data) if chunk_data else 0.0
            
            # Get storage paths
            chunk_path = self._get_chunk_path(session_id, chunk.chunk_id)
            metadata_path = self._get_metadata_path(session_id, chunk.chunk_id)
            
            # Write compressed data
            async with aiofiles.open(chunk_path, 'wb') as f:
                await f.write(compressed_data)
            
            # Create metadata
            metadata = {
                "chunk_id": chunk.chunk_id,
                "session_id": session_id,
                "chunk_index": chunk.chunk_index,
                "timestamp": chunk.timestamp.isoformat(),
                "size_bytes": len(chunk_data),
                "compressed_size_bytes": len(compressed_data),
                "compression_algorithm": self.config.compression_algorithm,
                "compression_level": self.config.compression_level,
                "compression_ratio": compression_ratio,
                "compression_time_ms": compression_time * 1000,
                "hash_sha256": chunk.hash_sha256,
                "quality_score": chunk.quality_score,
                "compressed": chunk.compressed,
                "created_at": datetime.utcnow().isoformat(),
                "storage_path": str(chunk_path)
            }
            
            # Write metadata
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
            
            logger.info(f"Chunk stored: {chunk.chunk_id} -> {chunk_path}")
            return True, str(chunk_path), metadata
            
        except Exception as e:
            logger.error(f"Failed to store chunk {chunk.chunk_id}: {e}")
            return False, "", {}
    
    async def retrieve_chunk(
        self, 
        session_id: str, 
        chunk_id: str
    ) -> Tuple[bool, bytes, Dict[str, Any]]:
        """
        Retrieve chunk data with decompression
        
        Returns:
            Tuple[bool, bytes, Dict]: (success, chunk_data, metadata)
        """
        try:
            # Get paths
            chunk_path = self._get_chunk_path(session_id, chunk_id)
            metadata_path = self._get_metadata_path(session_id, chunk_id)
            
            # Check if files exist
            if not chunk_path.exists() or not metadata_path.exists():
                logger.warning(f"Chunk files not found: {chunk_id}")
                return False, b"", {}
            
            # Read metadata
            async with aiofiles.open(metadata_path, 'r') as f:
                metadata = json.loads(await f.read())
            
            # Read compressed data
            async with aiofiles.open(chunk_path, 'rb') as f:
                compressed_data = await f.read()
            
            # Get decompression function
            decompress_func = self._decompression_funcs.get(metadata["compression_algorithm"])
            if not decompress_func:
                raise ValueError(f"Unsupported compression algorithm: {metadata['compression_algorithm']}")
            
            # Decompress data
            start_time = time.time()
            chunk_data = await decompress_func(compressed_data)
            decompression_time = time.time() - start_time
            
            # Update metadata with decompression info
            metadata["decompression_time_ms"] = decompression_time * 1000
            
            logger.info(f"Chunk retrieved: {chunk_id}")
            return True, chunk_data, metadata
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return False, b"", {}
    
    async def get_chunk_metadata(
        self, 
        session_id: str, 
        chunk_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get chunk metadata without retrieving data"""
        try:
            metadata_path = self._get_metadata_path(session_id, chunk_id)
            
            if not metadata_path.exists():
                return None
            
            async with aiofiles.open(metadata_path, 'r') as f:
                return json.loads(await f.read())
                
        except Exception as e:
            logger.error(f"Failed to get chunk metadata {chunk_id}: {e}")
            return None
    
    async def list_session_chunks(
        self, 
        session_id: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List chunks for a session with pagination"""
        try:
            session_path = self._get_session_path(session_id)
            metadata_path = self.base_path / "metadata" / session_id
            
            if not session_path.exists() or not metadata_path.exists():
                return []
            
            # Get all metadata files
            metadata_files = list(metadata_path.glob("*.json"))
            metadata_files.sort(key=lambda x: x.stem)  # Sort by chunk_id
            
            # Apply pagination
            paginated_files = metadata_files[offset:offset + limit]
            
            chunks = []
            for metadata_file in paginated_files:
                try:
                    async with aiofiles.open(metadata_file, 'r') as f:
                        metadata = json.loads(await f.read())
                    chunks.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read metadata {metadata_file}: {e}")
                    continue
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to list session chunks: {e}")
            return []
    
    async def delete_chunk(self, session_id: str, chunk_id: str) -> bool:
        """Delete chunk and its metadata"""
        try:
            chunk_path = self._get_chunk_path(session_id, chunk_id)
            metadata_path = self._get_metadata_path(session_id, chunk_id)
            
            # Delete chunk file
            if chunk_path.exists():
                await aiofiles.os.remove(chunk_path)
            
            # Delete metadata file
            if metadata_path.exists():
                await aiofiles.os.remove(metadata_path)
            
            logger.info(f"Chunk deleted: {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id}: {e}")
            return False
    
    async def delete_session_chunks(self, session_id: str) -> int:
        """Delete all chunks for a session"""
        try:
            session_path = self._get_session_path(session_id)
            metadata_path = self.base_path / "metadata" / session_id
            
            deleted_count = 0
            
            # Delete chunk files
            if session_path.exists():
                for chunk_file in session_path.iterdir():
                    if chunk_file.is_file():
                        await aiofiles.os.remove(chunk_file)
                        deleted_count += 1
                await aiofiles.os.rmdir(session_path)
            
            # Delete metadata files
            if metadata_path.exists():
                for metadata_file in metadata_path.iterdir():
                    if metadata_file.is_file():
                        await aiofiles.os.remove(metadata_file)
                await aiofiles.os.rmdir(metadata_path)
            
            logger.info(f"Session chunks deleted: {session_id} ({deleted_count} chunks)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete session chunks {session_id}: {e}")
            return 0
    
    async def archive_session(self, session_id: str) -> bool:
        """Archive session chunks to archive directory"""
        try:
            session_path = self._get_session_path(session_id)
            metadata_path = self.base_path / "metadata" / session_id
            archive_path = self.base_path / "archived" / session_id
            
            if not session_path.exists():
                logger.warning(f"Session path not found: {session_path}")
                return False
            
            # Create archive directory
            archive_path.mkdir(parents=True, exist_ok=True)
            
            # Move session directory
            shutil.move(str(session_path), str(archive_path / "chunks"))
            
            # Move metadata directory
            if metadata_path.exists():
                shutil.move(str(metadata_path), str(archive_path / "metadata"))
            
            logger.info(f"Session archived: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive session {session_id}: {e}")
            return False
    
    async def restore_session(self, session_id: str) -> bool:
        """Restore session from archive"""
        try:
            archive_path = self.base_path / "archived" / session_id
            session_path = self._get_session_path(session_id)
            metadata_path = self.base_path / "metadata" / session_id
            
            if not archive_path.exists():
                logger.warning(f"Archive not found: {archive_path}")
                return False
            
            # Create active directories
            session_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move chunks back
            if (archive_path / "chunks").exists():
                shutil.move(str(archive_path / "chunks"), str(session_path))
            
            # Move metadata back
            if (archive_path / "metadata").exists():
                shutil.move(str(archive_path / "metadata"), str(metadata_path))
            
            # Remove archive directory
            shutil.rmtree(archive_path)
            
            logger.info(f"Session restored: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {e}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                "total_sessions": 0,
                "total_chunks": 0,
                "total_size_bytes": 0,
                "compressed_size_bytes": 0,
                "compression_ratio": 0.0,
                "active_sessions": 0,
                "archived_sessions": 0
            }
            
            # Count active sessions
            active_path = self.base_path / "active"
            if active_path.exists():
                stats["active_sessions"] = len([d for d in active_path.iterdir() if d.is_dir()])
            
            # Count archived sessions
            archived_path = self.base_path / "archived"
            if archived_path.exists():
                stats["archived_sessions"] = len([d for d in archived_path.iterdir() if d.is_dir()])
            
            stats["total_sessions"] = stats["active_sessions"] + stats["archived_sessions"]
            
            # Calculate total size and chunks
            for session_dir in active_path.iterdir():
                if session_dir.is_dir():
                    for chunk_file in session_dir.iterdir():
                        if chunk_file.is_file():
                            stats["total_chunks"] += 1
                            stats["compressed_size_bytes"] += chunk_file.stat().st_size
            
            # Calculate compression ratio
            if stats["total_size_bytes"] > 0:
                stats["compression_ratio"] = stats["compressed_size_bytes"] / stats["total_size_bytes"]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    async def cleanup_temp_files(self) -> int:
        """Cleanup temporary files"""
        try:
            temp_path = self.base_path / "temp"
            if not temp_path.exists():
                return 0
            
            deleted_count = 0
            for temp_file in temp_path.iterdir():
                if temp_file.is_file():
                    await aiofiles.os.remove(temp_file)
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Check if base directory is accessible
            accessible = self.base_path.exists() and self.base_path.is_dir()
            
            # Check available space
            statvfs = os.statvfs(self.base_path)
            available_space = statvfs.f_frsize * statvfs.f_bavail
            space_healthy = available_space > 1024 * 1024 * 1024  # 1GB minimum
            
            # Check compression functions
            compression_healthy = self.config.compression_algorithm in self._compression_funcs
            
            return {
                "status": "healthy" if all([accessible, space_healthy, compression_healthy]) else "unhealthy",
                "accessible": accessible,
                "space_healthy": space_healthy,
                "compression_healthy": compression_healthy,
                "available_space_bytes": available_space,
                "compression_algorithm": self.config.compression_algorithm,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

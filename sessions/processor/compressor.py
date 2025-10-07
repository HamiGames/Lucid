# Path: sessions/processor/compressor.py
# LUCID Session Data Compression - Zstd Compression Engine
# Professional data compression with Zstd algorithm for session data
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

import zstandard as zstd
import lz4.frame
import brotli

logger = logging.getLogger(__name__)

# Configuration from environment
COMPRESSION_PATH = Path(os.getenv("COMPRESSION_PATH", "/data/compression"))
DEFAULT_COMPRESSION_LEVEL = int(os.getenv("DEFAULT_COMPRESSION_LEVEL", "3"))
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1048576"))  # 1MB
COMPRESSION_THRESHOLD = int(os.getenv("COMPRESSION_THRESHOLD", "1024"))  # 1KB


class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    ZSTD = "zstd"
    LZ4 = "lz4"
    BROTLI = "brotli"
    NONE = "none"


class CompressionStatus(Enum):
    """Compression operation status"""
    PENDING = "pending"
    COMPRESSING = "compressing"
    COMPRESSED = "compressed"
    DECOMPRESSING = "decompressing"
    DECOMPRESSED = "decompressed"
    ERROR = "error"


@dataclass
class CompressionResult:
    """Compression operation result"""
    operation_id: str
    algorithm: CompressionAlgorithm
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time: float
    status: CompressionStatus
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompressionTask:
    """Compression task metadata"""
    task_id: str
    session_id: str
    owner_address: str
    algorithm: CompressionAlgorithm
    compression_level: int
    status: CompressionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    input_path: Optional[Path] = None
    output_path: Optional[Path] = None
    result: Optional[CompressionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionCompressor:
    """
    Professional data compression engine for Lucid RDP sessions.
    
    Supports multiple compression algorithms with Zstd as primary.
    Optimized for session data compression with hardware acceleration.
    """
    
    def __init__(self):
        """Initialize compression engine"""
        # Task tracking
        self.active_tasks: Dict[str, CompressionTask] = {}
        self.compression_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        # Compression settings
        self.compression_levels = {
            CompressionAlgorithm.ZSTD: DEFAULT_COMPRESSION_LEVEL,
            CompressionAlgorithm.LZ4: 1,
            CompressionAlgorithm.BROTLI: 4
        }
        
        # Performance metrics
        self.compression_stats = {
            "total_compressed": 0,
            "total_decompressed": 0,
            "total_savings": 0,
            "average_ratio": 0.0
        }
        
        # Create directories
        self._create_directories()
        
        # Initialize compressors
        self._initialize_compressors()
        
        logger.info("Session compressor initialized")
        logger.info(f"Default compression level: {DEFAULT_COMPRESSION_LEVEL}")
        logger.info(f"Max chunk size: {MAX_CHUNK_SIZE}")
    
    def _create_directories(self) -> None:
        """Create required directories"""
        COMPRESSION_PATH.mkdir(parents=True, exist_ok=True)
        (COMPRESSION_PATH / "temp").mkdir(exist_ok=True)
        (COMPRESSION_PATH / "compressed").mkdir(exist_ok=True)
        logger.info(f"Created compression directories: {COMPRESSION_PATH}")
    
    def _initialize_compressors(self) -> None:
        """Initialize compression engines"""
        try:
            # Test Zstd availability
            test_data = b"test compression data"
            zstd_compressor = zstd.ZstdCompressor(level=DEFAULT_COMPRESSION_LEVEL)
            zstd_compressor.compress(test_data)
            logger.info("Zstd compressor initialized successfully")
            
            # Test LZ4 availability
            lz4.frame.compress(test_data)
            logger.info("LZ4 compressor initialized successfully")
            
            # Test Brotli availability
            brotli.compress(test_data)
            logger.info("Brotli compressor initialized successfully")
            
        except Exception as e:
            logger.warning(f"Compressor initialization warning: {e}")
    
    async def compress_data(self,
                           session_id: str,
                           owner_address: str,
                           data: Union[bytes, Path],
                           algorithm: CompressionAlgorithm = CompressionAlgorithm.ZSTD,
                           compression_level: Optional[int] = None) -> CompressionResult:
        """Compress session data"""
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Determine compression level
            if compression_level is None:
                compression_level = self.compression_levels.get(algorithm, DEFAULT_COMPRESSION_LEVEL)
            
            # Create compression task
            task = CompressionTask(
                task_id=task_id,
                session_id=session_id,
                owner_address=owner_address,
                algorithm=algorithm,
                compression_level=compression_level,
                status=CompressionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                metadata={}
            )
            
            # Store task
            self.active_tasks[task_id] = task
            
            # Read input data
            if isinstance(data, Path):
                input_data = data.read_bytes()
                task.input_path = data
            else:
                input_data = data
            
            # Check if compression is beneficial
            if len(input_data) < COMPRESSION_THRESHOLD:
                logger.info(f"Data too small for compression: {len(input_data)} bytes")
                return CompressionResult(
                    operation_id=task_id,
                    algorithm=CompressionAlgorithm.NONE,
                    original_size=len(input_data),
                    compressed_size=len(input_data),
                    compression_ratio=1.0,
                    compression_time=0.0,
                    status=CompressionStatus.COMPRESSED,
                    checksum=hashlib.sha256(input_data).hexdigest()
                )
            
            # Update status
            task.status = CompressionStatus.COMPRESSING
            start_time = time.time()
            
            # Perform compression
            compressed_data = await self._compress_bytes(input_data, algorithm, compression_level)
            
            # Calculate metrics
            compression_time = time.time() - start_time
            compression_ratio = len(compressed_data) / len(input_data)
            
            # Generate checksum
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Create result
            result = CompressionResult(
                operation_id=task_id,
                algorithm=algorithm,
                original_size=len(input_data),
                compressed_size=len(compressed_data),
                compression_ratio=compression_ratio,
                compression_time=compression_time,
                status=CompressionStatus.COMPRESSED,
                checksum=checksum,
                metadata={
                    "session_id": session_id,
                    "owner_address": owner_address,
                    "compression_level": compression_level
                }
            )
            
            # Update task
            task.status = CompressionStatus.COMPRESSED
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            
            # Update statistics
            self._update_stats(result)
            
            logger.info(f"Compression completed: {task_id} - Ratio: {compression_ratio:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = CompressionStatus.ERROR
            
            raise Exception(f"Compression failed: {str(e)}")
    
    async def decompress_data(self,
                             compressed_data: bytes,
                             algorithm: CompressionAlgorithm,
                             original_size: Optional[int] = None) -> bytes:
        """Decompress session data"""
        try:
            start_time = time.time()
            
            # Perform decompression
            decompressed_data = await self._decompress_bytes(compressed_data, algorithm)
            
            decompression_time = time.time() - start_time
            
            logger.info(f"Decompression completed in {decompression_time:.3f}s")
            
            return decompressed_data
            
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise Exception(f"Decompression failed: {str(e)}")
    
    async def _compress_bytes(self,
                             data: bytes,
                             algorithm: CompressionAlgorithm,
                             level: int) -> bytes:
        """Compress bytes using specified algorithm"""
        try:
            if algorithm == CompressionAlgorithm.ZSTD:
                return await self._compress_zstd(data, level)
            elif algorithm == CompressionAlgorithm.LZ4:
                return await self._compress_lz4(data, level)
            elif algorithm == CompressionAlgorithm.BROTLI:
                return await self._compress_brotli(data, level)
            else:
                raise ValueError(f"Unsupported compression algorithm: {algorithm}")
                
        except Exception as e:
            logger.error(f"Compression algorithm error: {e}")
            raise
    
    async def _decompress_bytes(self,
                               data: bytes,
                               algorithm: CompressionAlgorithm) -> bytes:
        """Decompress bytes using specified algorithm"""
        try:
            if algorithm == CompressionAlgorithm.ZSTD:
                return await self._decompress_zstd(data)
            elif algorithm == CompressionAlgorithm.LZ4:
                return await self._decompress_lz4(data)
            elif algorithm == CompressionAlgorithm.BROTLI:
                return await self._decompress_brotli(data)
            else:
                raise ValueError(f"Unsupported compression algorithm: {algorithm}")
                
        except Exception as e:
            logger.error(f"Decompression algorithm error: {e}")
            raise
    
    async def _compress_zstd(self, data: bytes, level: int) -> bytes:
        """Compress using Zstd algorithm"""
        try:
            # Run compression in executor to avoid blocking
            loop = asyncio.get_event_loop()
            compressed = await loop.run_in_executor(
                None,
                self._zstd_compress_sync,
                data,
                level
            )
            return compressed
        except Exception as e:
            logger.error(f"Zstd compression error: {e}")
            raise
    
    def _zstd_compress_sync(self, data: bytes, level: int) -> bytes:
        """Synchronous Zstd compression"""
        compressor = zstd.ZstdCompressor(level=level)
        return compressor.compress(data)
    
    async def _decompress_zstd(self, data: bytes) -> bytes:
        """Decompress using Zstd algorithm"""
        try:
            loop = asyncio.get_event_loop()
            decompressed = await loop.run_in_executor(
                None,
                self._zstd_decompress_sync,
                data
            )
            return decompressed
        except Exception as e:
            logger.error(f"Zstd decompression error: {e}")
            raise
    
    def _zstd_decompress_sync(self, data: bytes) -> bytes:
        """Synchronous Zstd decompression"""
        decompressor = zstd.ZstdDecompressor()
        return decompressor.decompress(data)
    
    async def _compress_lz4(self, data: bytes, level: int) -> bytes:
        """Compress using LZ4 algorithm"""
        try:
            loop = asyncio.get_event_loop()
            compressed = await loop.run_in_executor(
                None,
                lz4.frame.compress,
                data,
                {"compression_level": level}
            )
            return compressed
        except Exception as e:
            logger.error(f"LZ4 compression error: {e}")
            raise
    
    async def _decompress_lz4(self, data: bytes) -> bytes:
        """Decompress using LZ4 algorithm"""
        try:
            loop = asyncio.get_event_loop()
            decompressed = await loop.run_in_executor(
                None,
                lz4.frame.decompress,
                data
            )
            return decompressed
        except Exception as e:
            logger.error(f"LZ4 decompression error: {e}")
            raise
    
    async def _compress_brotli(self, data: bytes, level: int) -> bytes:
        """Compress using Brotli algorithm"""
        try:
            loop = asyncio.get_event_loop()
            compressed = await loop.run_in_executor(
                None,
                brotli.compress,
                data,
                {"quality": level}
            )
            return compressed
        except Exception as e:
            logger.error(f"Brotli compression error: {e}")
            raise
    
    async def _decompress_brotli(self, data: bytes) -> bytes:
        """Decompress using Brotli algorithm"""
        try:
            loop = asyncio.get_event_loop()
            decompressed = await loop.run_in_executor(
                None,
                brotli.decompress,
                data
            )
            return decompressed
        except Exception as e:
            logger.error(f"Brotli decompression error: {e}")
            raise
    
    def _update_stats(self, result: CompressionResult) -> None:
        """Update compression statistics"""
        self.compression_stats["total_compressed"] += 1
        self.compression_stats["total_savings"] += (result.original_size - result.compressed_size)
        
        # Calculate average ratio
        if self.compression_stats["total_compressed"] > 0:
            total_ratio = self.compression_stats["average_ratio"] * (self.compression_stats["total_compressed"] - 1)
            self.compression_stats["average_ratio"] = (total_ratio + result.compression_ratio) / self.compression_stats["total_compressed"]
    
    async def compress_file(self,
                           input_path: Path,
                           output_path: Optional[Path] = None,
                           algorithm: CompressionAlgorithm = CompressionAlgorithm.ZSTD,
                           compression_level: Optional[int] = None,
                           chunk_size: int = MAX_CHUNK_SIZE) -> CompressionResult:
        """Compress file in chunks"""
        try:
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            # Generate output path if not provided
            if output_path is None:
                output_path = input_path.with_suffix(f"{input_path.suffix}.{algorithm.value}")
            
            # Determine compression level
            if compression_level is None:
                compression_level = self.compression_levels.get(algorithm, DEFAULT_COMPRESSION_LEVEL)
            
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create compression task
            task = CompressionTask(
                task_id=task_id,
                session_id="file_compression",
                owner_address="system",
                algorithm=algorithm,
                compression_level=compression_level,
                status=CompressionStatus.COMPRESSING,
                created_at=datetime.now(timezone.utc),
                input_path=input_path,
                output_path=output_path,
                metadata={"chunk_size": chunk_size}
            )
            
            # Store task
            self.active_tasks[task_id] = task
            
            # Read file size
            original_size = input_path.stat().st_size
            
            start_time = time.time()
            
            # Compress file in chunks
            with open(input_path, 'rb') as input_file, open(output_path, 'wb') as output_file:
                compressor = self._get_file_compressor(algorithm, compression_level)
                
                while True:
                    chunk = input_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    compressed_chunk = await self._compress_bytes(chunk, algorithm, compression_level)
                    
                    # Write chunk size and compressed data
                    output_file.write(len(compressed_chunk).to_bytes(4, 'big'))
                    output_file.write(compressed_chunk)
            
            # Calculate metrics
            compression_time = time.time() - start_time
            compressed_size = output_path.stat().st_size
            compression_ratio = compressed_size / original_size
            
            # Generate checksum
            with open(output_path, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            # Create result
            result = CompressionResult(
                operation_id=task_id,
                algorithm=algorithm,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                compression_time=compression_time,
                status=CompressionStatus.COMPRESSED,
                checksum=checksum,
                metadata={
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                    "chunk_size": chunk_size
                }
            )
            
            # Update task
            task.status = CompressionStatus.COMPRESSED
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            
            logger.info(f"File compression completed: {input_path} -> {output_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"File compression failed: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = CompressionStatus.ERROR
            
            raise Exception(f"File compression failed: {str(e)}")
    
    def _get_file_compressor(self, algorithm: CompressionAlgorithm, level: int):
        """Get file compressor instance"""
        if algorithm == CompressionAlgorithm.ZSTD:
            return zstd.ZstdCompressor(level=level)
        elif algorithm == CompressionAlgorithm.LZ4:
            return lz4.frame.LZ4FrameCompressor(compression_level=level)
        else:
            raise ValueError(f"Unsupported file compression algorithm: {algorithm}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get compression task status"""
        if task_id not in self.active_tasks:
            raise Exception("Task not found")
        
        task = self.active_tasks[task_id]
        return {
            "task_id": task.task_id,
            "session_id": task.session_id,
            "algorithm": task.algorithm.value,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result.__dict__ if task.result else None
        }
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return {
            "stats": self.compression_stats.copy(),
            "active_tasks": len(self.active_tasks),
            "supported_algorithms": [alg.value for alg in CompressionAlgorithm],
            "compression_levels": self.compression_levels.copy()
        }


# Global compressor instance
session_compressor = SessionCompressor()

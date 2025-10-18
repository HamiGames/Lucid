#!/usr/bin/env python3
"""
Lucid Session Management Compression Module
Handles compression of session chunks with gzip level 6
"""

import asyncio
import gzip
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)

class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"

@dataclass
class CompressionResult:
    """Result of compression operation"""
    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time_ms: float
    algorithm: CompressionAlgorithm

@dataclass
class DecompressionResult:
    """Result of decompression operation"""
    decompressed_data: bytes
    compressed_size: int
    decompressed_size: int
    decompression_time_ms: float
    algorithm: CompressionAlgorithm

class CompressionEngine:
    """
    Compression engine for session chunks
    Supports multiple compression algorithms with gzip level 6 as default (Step 15 requirement)
    """
    
    def __init__(self, default_level: int = 6):  # gzip level 6 as required by Step 15
        self.default_level = default_level
        self.compression_stats = {
            "total_compressions": 0,
            "total_decompressions": 0,
            "total_time_ms": 0.0,
            "total_bytes_compressed": 0,
            "total_bytes_decompressed": 0
        }
        
        logger.info(f"Compression engine initialized with level {default_level}")
    
    async def compress(
        self, 
        data: bytes, 
        algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP,
        level: Optional[int] = None
    ) -> CompressionResult:
        """
        Compress data using specified algorithm
        
        Args:
            data: Raw data to compress
            algorithm: Compression algorithm to use
            level: Compression level (if applicable)
            
        Returns:
            CompressionResult with compressed data and metadata
        """
        start_time = time.time()
        
        try:
            if algorithm == CompressionAlgorithm.GZIP:
                compressed_data = await self._compress_gzip(data, level or self.default_level)
            elif algorithm == CompressionAlgorithm.LZ4:
                compressed_data = await self._compress_lz4(data, level or 1)
            elif algorithm == CompressionAlgorithm.ZSTD:
                compressed_data = await self._compress_zstd(data, level or 3)
            else:
                raise ValueError(f"Unsupported compression algorithm: {algorithm}")
            
            compression_time = (time.time() - start_time) * 1000
            compression_ratio = len(data) / len(compressed_data) if len(compressed_data) > 0 else 1.0
            
            # Update statistics
            self.compression_stats["total_compressions"] += 1
            self.compression_stats["total_time_ms"] += compression_time
            self.compression_stats["total_bytes_compressed"] += len(data)
            
            result = CompressionResult(
                compressed_data=compressed_data,
                original_size=len(data),
                compressed_size=len(compressed_data),
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time,
                algorithm=algorithm
            )
            
            logger.debug(
                f"Compressed {len(data)} bytes to {len(compressed_data)} bytes "
                f"(ratio: {compression_ratio:.2f}) in {compression_time:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Compression failed: {str(e)}")
            raise
    
    async def decompress(
        self, 
        compressed_data: bytes, 
        algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    ) -> DecompressionResult:
        """
        Decompress data using specified algorithm
        
        Args:
            compressed_data: Compressed data to decompress
            algorithm: Compression algorithm used
            
        Returns:
            DecompressionResult with decompressed data and metadata
        """
        start_time = time.time()
        
        try:
            if algorithm == CompressionAlgorithm.GZIP:
                decompressed_data = await self._decompress_gzip(compressed_data)
            elif algorithm == CompressionAlgorithm.LZ4:
                decompressed_data = await self._decompress_lz4(compressed_data)
            elif algorithm == CompressionAlgorithm.ZSTD:
                decompressed_data = await self._decompress_zstd(compressed_data)
            else:
                raise ValueError(f"Unsupported compression algorithm: {algorithm}")
            
            decompression_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self.compression_stats["total_decompressions"] += 1
            self.compression_stats["total_time_ms"] += decompression_time
            self.compression_stats["total_bytes_decompressed"] += len(decompressed_data)
            
            result = DecompressionResult(
                decompressed_data=decompressed_data,
                compressed_size=len(compressed_data),
                decompressed_size=len(decompressed_data),
                decompression_time_ms=decompression_time,
                algorithm=algorithm
            )
            
            logger.debug(
                f"Decompressed {len(compressed_data)} bytes to {len(decompressed_data)} bytes "
                f"in {decompression_time:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Decompression failed: {str(e)}")
            raise
    
    async def _compress_gzip(self, data: bytes, level: int) -> bytes:
        """Compress data using gzip"""
        # Run compression in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: gzip.compress(data, compresslevel=level)
        )
    
    async def _decompress_gzip(self, compressed_data: bytes) -> bytes:
        """Decompress data using gzip"""
        # Run decompression in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: gzip.decompress(compressed_data)
        )
    
    async def _compress_lz4(self, data: bytes, level: int) -> bytes:
        """Compress data using LZ4"""
        try:
            import lz4.frame
            
            # Run compression in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                lambda: lz4.frame.compress(data, compression_level=level)
            )
        except ImportError:
            logger.warning("LZ4 not available, falling back to gzip")
            return await self._compress_gzip(data, self.default_level)
    
    async def _decompress_lz4(self, compressed_data: bytes) -> bytes:
        """Decompress data using LZ4"""
        try:
            import lz4.frame
            
            # Run decompression in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                lambda: lz4.frame.decompress(compressed_data)
            )
        except ImportError:
            logger.warning("LZ4 not available, falling back to gzip")
            return await self._decompress_gzip(compressed_data)
    
    async def _compress_zstd(self, data: bytes, level: int) -> bytes:
        """Compress data using Zstandard"""
        try:
            import zstandard as zstd
            
            # Run compression in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            compressor = zstd.ZstdCompressor(level=level)
            return await loop.run_in_executor(
                None, 
                lambda: compressor.compress(data)
            )
        except ImportError:
            logger.warning("Zstandard not available, falling back to gzip")
            return await self._compress_gzip(data, self.default_level)
    
    async def _decompress_zstd(self, compressed_data: bytes) -> bytes:
        """Decompress data using Zstandard"""
        try:
            import zstandard as zstd
            
            # Run decompression in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            decompressor = zstd.ZstdDecompressor()
            return await loop.run_in_executor(
                None, 
                lambda: decompressor.decompress(compressed_data)
            )
        except ImportError:
            logger.warning("Zstandard not available, falling back to gzip")
            return await self._decompress_gzip(compressed_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compression statistics"""
        avg_compression_time = (
            self.compression_stats["total_time_ms"] / 
            max(1, self.compression_stats["total_compressions"] + self.compression_stats["total_decompressions"])
        )
        
        avg_compression_ratio = (
            self.compression_stats["total_bytes_compressed"] / 
            max(1, self.compression_stats["total_bytes_compressed"] - 
                (self.compression_stats["total_bytes_compressed"] - self.compression_stats["total_bytes_decompressed"]))
        )
        
        return {
            "total_compressions": self.compression_stats["total_compressions"],
            "total_decompressions": self.compression_stats["total_decompressions"],
            "total_time_ms": self.compression_stats["total_time_ms"],
            "average_compression_time_ms": avg_compression_time,
            "total_bytes_compressed": self.compression_stats["total_bytes_compressed"],
            "total_bytes_decompressed": self.compression_stats["total_bytes_decompressed"],
            "average_compression_ratio": avg_compression_ratio,
            "default_level": self.default_level
        }
    
    def reset_statistics(self):
        """Reset compression statistics"""
        self.compression_stats = {
            "total_compressions": 0,
            "total_decompressions": 0,
            "total_time_ms": 0.0,
            "total_bytes_compressed": 0,
            "total_bytes_decompressed": 0
        }
        logger.info("Compression statistics reset")

class CompressionManager:
    """
    Manages compression operations for session chunks
    Provides high-level compression interface with automatic algorithm selection
    Uses gzip level 6 as required by Step 15
    """
    
    def __init__(self, default_level: int = 6):  # gzip level 6 as required by Step 15
        self.engine = CompressionEngine(default_level)
        self.default_algorithm = CompressionAlgorithm.GZIP
        
        logger.info(f"Compression manager initialized with level {default_level}")
    
    async def compress_chunk(
        self, 
        chunk_data: bytes, 
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None
    ) -> CompressionResult:
        """
        Compress a session chunk
        
        Args:
            chunk_data: Raw chunk data
            algorithm: Compression algorithm (defaults to gzip)
            level: Compression level (defaults to 6)
            
        Returns:
            CompressionResult with compressed data
        """
        algorithm = algorithm or self.default_algorithm
        level = level or self.engine.default_level
        
        return await self.engine.compress(chunk_data, algorithm, level)
    
    async def decompress_chunk(
        self, 
        compressed_chunk: bytes, 
        algorithm: Optional[CompressionAlgorithm] = None
    ) -> DecompressionResult:
        """
        Decompress a session chunk
        
        Args:
            compressed_chunk: Compressed chunk data
            algorithm: Compression algorithm (defaults to gzip)
            
        Returns:
            DecompressionResult with decompressed data
        """
        algorithm = algorithm or self.default_algorithm
        
        return await self.engine.decompress(compressed_chunk, algorithm)
    
    async def batch_compress(
        self, 
        chunks: List[bytes], 
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None
    ) -> List[CompressionResult]:
        """
        Compress multiple chunks in parallel
        
        Args:
            chunks: List of raw chunk data
            algorithm: Compression algorithm (defaults to gzip)
            level: Compression level (defaults to 6)
            
        Returns:
            List of CompressionResults
        """
        algorithm = algorithm or self.default_algorithm
        level = level or self.engine.default_level
        
        # Compress chunks in parallel
        tasks = [
            self.engine.compress(chunk, algorithm, level)
            for chunk in chunks
        ]
        
        return await asyncio.gather(*tasks)
    
    async def batch_decompress(
        self, 
        compressed_chunks: List[bytes], 
        algorithm: Optional[CompressionAlgorithm] = None
    ) -> List[DecompressionResult]:
        """
        Decompress multiple chunks in parallel
        
        Args:
            compressed_chunks: List of compressed chunk data
            algorithm: Compression algorithm (defaults to gzip)
            
        Returns:
            List of DecompressionResults
        """
        algorithm = algorithm or self.default_algorithm
        
        # Decompress chunks in parallel
        tasks = [
            self.engine.decompress(chunk, algorithm)
            for chunk in compressed_chunks
        ]
        
        return await asyncio.gather(*tasks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compression manager statistics"""
        return self.engine.get_statistics()
    
    def reset_statistics(self):
        """Reset compression statistics"""
        self.engine.reset_statistics()
    
    def set_default_algorithm(self, algorithm: CompressionAlgorithm):
        """Set default compression algorithm"""
        self.default_algorithm = algorithm
        logger.info(f"Default compression algorithm set to {algorithm.value}")
    
    def set_default_level(self, level: int):
        """Set default compression level"""
        if level < 1 or level > 9:
            raise ValueError("Compression level must be between 1 and 9")
        
        self.engine.default_level = level
        logger.info(f"Default compression level set to {level}")
    
    def get_available_algorithms(self) -> List[CompressionAlgorithm]:
        """Get list of available compression algorithms"""
        algorithms = [CompressionAlgorithm.GZIP]  # gzip is always available
        
        try:
            import lz4.frame
            algorithms.append(CompressionAlgorithm.LZ4)
        except ImportError:
            pass
        
        try:
            import zstandard as zstd
            algorithms.append(CompressionAlgorithm.ZSTD)
        except ImportError:
            pass
        
        return algorithms

#!/usr/bin/env python3
"""
Native Chunker Addon for Lucid RDP
Provides high-performance chunking using native C extensions
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Union
import structlog
import numpy as np
from pathlib import Path
import ctypes
import os

logger = structlog.get_logger(__name__)

# Try to import native extension
try:
    import chunker_native
    NATIVE_AVAILABLE = True
    logger.info("Native chunker extension loaded successfully")
except ImportError:
    NATIVE_AVAILABLE = False
    logger.warning("Native chunker extension not available, using Python fallback")


class NativeChunker:
    """High-performance native chunker"""
    
    def __init__(self, chunk_size_mb: int = 8, compression_level: int = 3):
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.compression_level = compression_level
        self.native_chunker = None
        
        # Statistics
        self.stats = {
            'chunks_created': 0,
            'bytes_processed': 0,
            'compression_ratio': 0.0,
            'processing_time': 0.0,
            'native_calls': 0,
            'fallback_calls': 0
        }
        
        # Initialize native chunker if available
        if NATIVE_AVAILABLE:
            self._initialize_native()
    
    def _initialize_native(self):
        """Initialize native chunker"""
        try:
            self.native_chunker = chunker_native.Chunker(
                chunk_size=self.chunk_size_bytes,
                compression_level=self.compression_level
            )
            logger.info("Native chunker initialized", 
                       chunk_size_mb=self.chunk_size_bytes // (1024 * 1024),
                       compression_level=self.compression_level)
        except Exception as e:
            logger.error("Failed to initialize native chunker", error=str(e))
            self.native_chunker = None
    
    async def chunk_data(self, data: Union[bytes, np.ndarray], 
                        chunk_id: str = None) -> Optional[Dict[str, Any]]:
        """Chunk data using native implementation"""
        try:
            start_time = time.time()
            
            # Convert numpy array to bytes if necessary
            if isinstance(data, np.ndarray):
                data = data.tobytes()
            
            if NATIVE_AVAILABLE and self.native_chunker:
                # Use native implementation
                result = await self._chunk_native(data, chunk_id)
                self.stats['native_calls'] += 1
            else:
                # Use Python fallback
                result = await self._chunk_python(data, chunk_id)
                self.stats['fallback_calls'] += 1
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats['processing_time'] += processing_time
            self.stats['chunks_created'] += 1
            self.stats['bytes_processed'] += len(data)
            
            if result and 'compressed_size' in result:
                self.stats['compression_ratio'] = (
                    len(data) / result['compressed_size']
                )
            
            return result
            
        except Exception as e:
            logger.error("Failed to chunk data", error=str(e))
            return None
    
    async def _chunk_native(self, data: bytes, chunk_id: str = None) -> Optional[Dict[str, Any]]:
        """Chunk data using native implementation"""
        try:
            # Call native chunker
            result = self.native_chunker.chunk(data)
            
            if result:
                return {
                    'chunk_id': chunk_id or f"chunk_{int(time.time())}",
                    'data': result['data'],
                    'original_size': len(data),
                    'compressed_size': len(result['data']),
                    'compression_ratio': len(data) / len(result['data']),
                    'algorithm': result.get('algorithm', 'native'),
                    'checksum': result.get('checksum', ''),
                    'timestamp': time.time(),
                    'native': True
                }
            
            return None
            
        except Exception as e:
            logger.error("Native chunking failed", error=str(e))
            return None
    
    async def _chunk_python(self, data: bytes, chunk_id: str = None) -> Optional[Dict[str, Any]]:
        """Chunk data using Python fallback"""
        try:
            import zlib
            import hashlib
            
            # Simple compression fallback
            compressed_data = zlib.compress(data, level=self.compression_level)
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            return {
                'chunk_id': chunk_id or f"chunk_{int(time.time())}",
                'data': compressed_data,
                'original_size': len(data),
                'compressed_size': len(compressed_data),
                'compression_ratio': len(data) / len(compressed_data),
                'algorithm': 'zlib',
                'checksum': checksum,
                'timestamp': time.time(),
                'native': False
            }
            
        except Exception as e:
            logger.error("Python chunking failed", error=str(e))
            return None
    
    async def decompress_chunk(self, chunk_data: bytes, algorithm: str = 'native') -> Optional[bytes]:
        """Decompress a chunk"""
        try:
            if NATIVE_AVAILABLE and self.native_chunker and algorithm == 'native':
                # Use native decompression
                return self.native_chunker.decompress(chunk_data)
            else:
                # Use Python decompression
                import zlib
                return zlib.decompress(chunk_data)
                
        except Exception as e:
            logger.error("Failed to decompress chunk", error=str(e))
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chunker statistics"""
        return {
            **self.stats,
            'native_available': NATIVE_AVAILABLE,
            'native_initialized': self.native_chunker is not None,
            'chunk_size_mb': self.chunk_size_bytes // (1024 * 1024),
            'compression_level': self.compression_level
        }
    
    async def cleanup(self):
        """Cleanup chunker resources"""
        try:
            if self.native_chunker:
                self.native_chunker.cleanup()
            
            logger.info("Native chunker cleanup completed")
            
        except Exception as e:
            logger.error("Native chunker cleanup error", error=str(e))


class NativeChunkerService:
    """Service for managing multiple native chunkers"""
    
    def __init__(self):
        self.chunkers: Dict[str, NativeChunker] = {}
        self.is_running = False
    
    async def start(self):
        """Start the native chunker service"""
        self.is_running = True
        logger.info("Native chunker service started")
    
    async def stop(self):
        """Stop the native chunker service"""
        self.is_running = False
        
        # Cleanup all chunkers
        for chunker in self.chunkers.values():
            await chunker.cleanup()
        
        self.chunkers.clear()
        logger.info("Native chunker service stopped")
    
    async def create_chunker(self, session_id: str, config: Dict[str, Any] = None) -> NativeChunker:
        """Create a new chunker for a session"""
        try:
            if session_id in self.chunkers:
                logger.warning("Chunker already exists for session", session_id=session_id)
                return self.chunkers[session_id]
            
            # Default configuration
            default_config = {
                'chunk_size_mb': 8,
                'compression_level': 3
            }
            
            if config:
                default_config.update(config)
            
            # Create chunker
            chunker = NativeChunker(
                chunk_size_mb=default_config['chunk_size_mb'],
                compression_level=default_config['compression_level']
            )
            
            self.chunkers[session_id] = chunker
            logger.info("Created native chunker for session", session_id=session_id)
            
            return chunker
            
        except Exception as e:
            logger.error("Failed to create chunker", session_id=session_id, error=str(e))
            return None
    
    async def get_chunker(self, session_id: str) -> Optional[NativeChunker]:
        """Get chunker for a session"""
        return self.chunkers.get(session_id)
    
    async def remove_chunker(self, session_id: str):
        """Remove chunker for a session"""
        try:
            if session_id in self.chunkers:
                chunker = self.chunkers[session_id]
                await chunker.cleanup()
                del self.chunkers[session_id]
                logger.info("Removed chunker for session", session_id=session_id)
        except Exception as e:
            logger.error("Failed to remove chunker", session_id=session_id, error=str(e))
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service-wide statistics"""
        stats = {
            'is_running': self.is_running,
            'active_chunkers': len(self.chunkers),
            'sessions': list(self.chunkers.keys()),
            'native_available': NATIVE_AVAILABLE
        }
        
        # Aggregate chunker stats
        total_stats = {
            'chunks_created': 0,
            'bytes_processed': 0,
            'processing_time': 0.0,
            'native_calls': 0,
            'fallback_calls': 0
        }
        
        for chunker in self.chunkers.values():
            chunker_stats = chunker.get_stats()
            for key in total_stats:
                if key in chunker_stats:
                    total_stats[key] += chunker_stats[key]
        
        stats['aggregate_stats'] = total_stats
        return stats


async def main():
    """Main entry point for native chunker service"""
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and start service
    service = NativeChunkerService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Native chunker service running")
        while service.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())

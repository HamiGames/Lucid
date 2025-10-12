#!/usr/bin/env python3
"""
Lucid RDP Chunker Service
Handles data chunking, compression, and processing for session recordings
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum
import structlog
import zstandard as zstd
import lz4.frame
import brotli
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field
import aiofiles
from pathlib import Path

logger = structlog.get_logger(__name__)


class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    ZSTD = "zstd"
    LZ4 = "lz4"
    BROTLI = "brotli"
    NONE = "none"


class ChunkType(Enum):
    """Types of data chunks"""
    VIDEO_FRAME = "video_frame"
    AUDIO_FRAME = "audio_frame"
    METADATA = "metadata"
    CONTROL = "control"


@dataclass
class ChunkMetadata:
    """Metadata for a data chunk"""
    chunk_id: str
    chunk_type: ChunkType
    timestamp: float
    size: int
    compressed_size: int
    compression_ratio: float
    algorithm: CompressionAlgorithm
    checksum: str


class Chunk(BaseModel):
    """Data chunk model"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    chunk_type: ChunkType = Field(..., description="Type of chunk data")
    data: bytes = Field(..., description="Chunk data")
    metadata: ChunkMetadata = Field(..., description="Chunk metadata")
    compressed: bool = Field(default=True, description="Whether data is compressed")
    encrypted: bool = Field(default=False, description="Whether data is encrypted")


class ChunkProcessor:
    """Main chunk processing class"""
    
    def __init__(
        self,
        chunk_size_mb: int = 8,
        compression_level: int = 3,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.ZSTD,
        max_queue_size: int = 1000
    ):
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.compression_level = compression_level
        self.algorithm = algorithm
        self.max_queue_size = max_queue_size
        
        # Processing queues
        self.input_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.output_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # Compression contexts
        self.zstd_compressor = None
        self.zstd_decompressor = None
        
        # Statistics
        self.stats = {
            'chunks_processed': 0,
            'bytes_processed': 0,
            'bytes_compressed': 0,
            'compression_ratio': 0.0,
            'processing_time': 0.0,
            'queue_size': 0,
            'errors': 0
        }
        
        # Processing state
        self.is_processing = False
        self.current_chunk_data = b""
        self.current_chunk_metadata = []
    
    async def initialize(self) -> bool:
        """Initialize the chunk processor"""
        try:
            logger.info("Initializing chunk processor", 
                       algorithm=self.algorithm.value,
                       chunk_size_mb=self.chunk_size_bytes // (1024 * 1024))
            
            # Initialize compression contexts
            if self.algorithm == CompressionAlgorithm.ZSTD:
                self.zstd_compressor = zstd.ZstdCompressor(
                    level=self.compression_level,
                    threads=-1
                )
                self.zstd_decompressor = zstd.ZstdDecompressor()
            
            logger.info("Chunk processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize chunk processor", error=str(e))
            return False
    
    async def add_frame(self, frame_data: Union[np.ndarray, bytes], frame_type: ChunkType = ChunkType.VIDEO_FRAME):
        """Add a frame to the processing queue"""
        try:
            # Convert numpy array to bytes if necessary
            if isinstance(frame_data, np.ndarray):
                frame_data = frame_data.tobytes()
            
            # Add to input queue
            await self.input_queue.put({
                'data': frame_data,
                'type': frame_type,
                'timestamp': time.time()
            })
            
            self.stats['queue_size'] = self.input_queue.qsize()
            
        except Exception as e:
            logger.error("Failed to add frame to queue", error=str(e))
            self.stats['errors'] += 1
    
    async def add_audio(self, audio_data: bytes):
        """Add audio data to the processing queue"""
        await self.add_frame(audio_data, ChunkType.AUDIO_FRAME)
    
    async def add_metadata(self, metadata: Dict[str, Any]):
        """Add metadata to the processing queue"""
        import json
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        await self.add_frame(metadata_bytes, ChunkType.METADATA)
    
    async def get_next_chunk(self) -> Optional[Chunk]:
        """Get the next processed chunk"""
        try:
            chunk = await asyncio.wait_for(self.output_queue.get(), timeout=1.0)
            return chunk
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error("Failed to get next chunk", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def start_processing(self):
        """Start the chunk processing loop"""
        if self.is_processing:
            return
        
        self.is_processing = True
        logger.info("Starting chunk processing")
        
        # Start processing tasks
        asyncio.create_task(self._processing_loop())
        asyncio.create_task(self._chunk_assembly_loop())
    
    async def stop_processing(self):
        """Stop the chunk processing loop"""
        self.is_processing = False
        logger.info("Stopping chunk processing")
    
    async def _processing_loop(self):
        """Main processing loop for incoming data"""
        try:
            while self.is_processing:
                try:
                    # Get data from input queue
                    item = await asyncio.wait_for(self.input_queue.get(), timeout=1.0)
                    
                    # Process the data
                    await self._process_data_item(item)
                    
                    self.input_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No data available, continue
                    continue
                except Exception as e:
                    logger.error("Error processing data item", error=str(e))
                    self.stats['errors'] += 1
                    
        except Exception as e:
            logger.error("Error in processing loop", error=str(e))
            self.stats['errors'] += 1
    
    async def _process_data_item(self, item: Dict[str, Any]):
        """Process a single data item"""
        try:
            data = item['data']
            data_type = item['type']
            timestamp = item['timestamp']
            
            # Add to current chunk
            self.current_chunk_data += data
            self.current_chunk_metadata.append({
                'type': data_type,
                'timestamp': timestamp,
                'size': len(data)
            })
            
            # Check if we need to create a chunk
            if len(self.current_chunk_data) >= self.chunk_size_bytes:
                await self._create_chunk()
                
        except Exception as e:
            logger.error("Failed to process data item", error=str(e))
            self.stats['errors'] += 1
    
    async def _chunk_assembly_loop(self):
        """Loop to create chunks from accumulated data"""
        try:
            while self.is_processing:
                # Create chunk if we have data and enough time has passed
                if self.current_chunk_data and len(self.current_chunk_data) > 0:
                    # Check timeout or size threshold
                    if (len(self.current_chunk_data) >= self.chunk_size_bytes or 
                        self._should_flush_chunk()):
                        await self._create_chunk()
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
        except Exception as e:
            logger.error("Error in chunk assembly loop", error=str(e))
            self.stats['errors'] += 1
    
    def _should_flush_chunk(self) -> bool:
        """Determine if current chunk should be flushed"""
        if not self.current_chunk_metadata:
            return False
        
        # Flush if no new data for 5 seconds
        last_timestamp = max(item['timestamp'] for item in self.current_chunk_metadata)
        return time.time() - last_timestamp > 5.0
    
    async def _create_chunk(self):
        """Create a chunk from accumulated data"""
        try:
            if not self.current_chunk_data:
                return
            
            chunk_id = self._generate_chunk_id()
            original_size = len(self.current_chunk_data)
            
            # Compress the data
            start_time = time.time()
            compressed_data = await self._compress_data(self.current_chunk_data)
            compression_time = time.time() - start_time
            
            compressed_size = len(compressed_data)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            # Calculate checksum
            import hashlib
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Create chunk metadata
            chunk_metadata = ChunkMetadata(
                chunk_id=chunk_id,
                chunk_type=ChunkType.VIDEO_FRAME,  # Default type
                timestamp=time.time(),
                size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                algorithm=self.algorithm,
                checksum=checksum
            )
            
            # Create chunk
            chunk = Chunk(
                chunk_id=chunk_id,
                chunk_type=ChunkType.VIDEO_FRAME,
                data=compressed_data,
                metadata=chunk_metadata,
                compressed=True
            )
            
            # Add to output queue
            await self.output_queue.put(chunk)
            
            # Update statistics
            self.stats['chunks_processed'] += 1
            self.stats['bytes_processed'] += original_size
            self.stats['bytes_compressed'] += compressed_size
            self.stats['processing_time'] += compression_time
            self.stats['compression_ratio'] = (
                self.stats['bytes_processed'] / self.stats['bytes_compressed'] 
                if self.stats['bytes_compressed'] > 0 else 0
            )
            
            # Reset current chunk
            self.current_chunk_data = b""
            self.current_chunk_metadata = []
            
            logger.debug("Created chunk", 
                        chunk_id=chunk_id,
                        original_size=original_size,
                        compressed_size=compressed_size,
                        ratio=compression_ratio)
            
        except Exception as e:
            logger.error("Failed to create chunk", error=str(e))
            self.stats['errors'] += 1
    
    async def _compress_data(self, data: bytes) -> bytes:
        """Compress data using the configured algorithm"""
        try:
            if self.algorithm == CompressionAlgorithm.ZSTD:
                return self.zstd_compressor.compress(data)
            elif self.algorithm == CompressionAlgorithm.LZ4:
                return lz4.frame.compress(data, compression_level=self.compression_level)
            elif self.algorithm == CompressionAlgorithm.BROTLI:
                return brotli.compress(data, quality=self.compression_level)
            else:
                return data  # No compression
                
        except Exception as e:
            logger.error("Failed to compress data", error=str(e))
            self.stats['errors'] += 1
            return data
    
    async def decompress_data(self, data: bytes) -> bytes:
        """Decompress data using the configured algorithm"""
        try:
            if self.algorithm == CompressionAlgorithm.ZSTD:
                return self.zstd_decompressor.decompress(data)
            elif self.algorithm == CompressionAlgorithm.LZ4:
                return lz4.frame.decompress(data)
            elif self.algorithm == CompressionAlgorithm.BROTLI:
                return brotli.decompress(data)
            else:
                return data  # No compression
                
        except Exception as e:
            logger.error("Failed to decompress data", error=str(e))
            self.stats['errors'] += 1
            return data
    
    def _generate_chunk_id(self) -> str:
        """Generate a unique chunk ID"""
        import uuid
        return f"chunk_{uuid.uuid4().hex[:16]}_{int(time.time())}"
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'is_processing': self.is_processing,
            'stats': self.stats,
            'queue_sizes': {
                'input': self.input_queue.qsize(),
                'output': self.output_queue.qsize()
            }
        }
    
    async def flush(self):
        """Flush any remaining data as a chunk"""
        if self.current_chunk_data:
            await self._create_chunk()


class ChunkerService:
    """Main chunker service for handling multiple sessions"""
    
    def __init__(self):
        self.processors: Dict[str, ChunkProcessor] = {}
        self.is_running = False
    
    async def start(self):
        """Start the chunker service"""
        self.is_running = True
        logger.info("Chunker service started")
    
    async def stop(self):
        """Stop the chunker service"""
        self.is_running = False
        
        # Stop all processors
        for processor in self.processors.values():
            await processor.stop_processing()
        
        logger.info("Chunker service stopped")
    
    async def create_processor(self, session_id: str, config: Dict[str, Any] = None) -> ChunkProcessor:
        """Create a new chunk processor for a session"""
        try:
            if session_id in self.processors:
                logger.warning("Processor already exists for session", session_id=session_id)
                return self.processors[session_id]
            
            # Default configuration
            default_config = {
                'chunk_size_mb': 8,
                'compression_level': 3,
                'algorithm': CompressionAlgorithm.ZSTD,
                'max_queue_size': 1000
            }
            
            if config:
                default_config.update(config)
            
            # Create processor
            processor = ChunkProcessor(
                chunk_size_mb=default_config['chunk_size_mb'],
                compression_level=default_config['compression_level'],
                algorithm=default_config['algorithm'],
                max_queue_size=default_config['max_queue_size']
            )
            
            # Initialize processor
            if await processor.initialize():
                await processor.start_processing()
                self.processors[session_id] = processor
                logger.info("Created processor for session", session_id=session_id)
                return processor
            else:
                logger.error("Failed to initialize processor", session_id=session_id)
                return None
                
        except Exception as e:
            logger.error("Failed to create processor", session_id=session_id, error=str(e))
            return None
    
    async def get_processor(self, session_id: str) -> Optional[ChunkProcessor]:
        """Get processor for a session"""
        return self.processors.get(session_id)
    
    async def remove_processor(self, session_id: str):
        """Remove processor for a session"""
        try:
            if session_id in self.processors:
                processor = self.processors[session_id]
                await processor.stop_processing()
                del self.processors[session_id]
                logger.info("Removed processor for session", session_id=session_id)
        except Exception as e:
            logger.error("Failed to remove processor", session_id=session_id, error=str(e))
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service-wide statistics"""
        stats = {
            'is_running': self.is_running,
            'active_processors': len(self.processors),
            'sessions': list(self.processors.keys())
        }
        
        # Aggregate processor stats
        total_stats = {
            'chunks_processed': 0,
            'bytes_processed': 0,
            'bytes_compressed': 0,
            'errors': 0
        }
        
        for processor in self.processors.values():
            proc_stats = await processor.get_stats()
            for key in total_stats:
                total_stats[key] += proc_stats['stats'][key]
        
        stats['aggregate_stats'] = total_stats
        return stats


async def main():
    """Main entry point for chunker service"""
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
    service = ChunkerService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Chunker service running")
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

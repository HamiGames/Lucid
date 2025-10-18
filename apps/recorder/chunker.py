#!/usr/bin/env python3
"""
Chunk Processor Module for Lucid RDP Recorder
Handles video/audio chunking and compression
"""

import asyncio
import logging
import zlib
import time
from typing import Optional, Dict, Any, List
import numpy as np
import structlog
from dataclasses import dataclass
from datetime import datetime

logger = structlog.get_logger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a chunk"""
    chunk_id: str
    session_id: str
    timestamp: datetime
    size: int
    compressed_size: int
    frame_count: int
    audio_samples: int
    chunk_type: str  # 'video', 'audio', 'mixed'


@dataclass
class ProcessedChunk:
    """Processed chunk data"""
    data: bytes
    metadata: ChunkMetadata
    checksum: str


class ChunkProcessor:
    """Processes video and audio data into chunks"""
    
    def __init__(self, chunk_size_mb: int = 10, compression_level: int = 6):
        self.chunk_size_mb = chunk_size_mb
        self.compression_level = compression_level
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        
        # Buffers for incoming data
        self.video_buffer: List[np.ndarray] = []
        self.audio_buffer: List[bytes] = []
        self.current_chunk_size = 0
        
        # Output queue
        self.chunk_queue = asyncio.Queue(maxsize=20)
        
        # Statistics
        self.stats = {
            'chunks_created': 0,
            'total_bytes_processed': 0,
            'compression_ratio': 0.0,
            'average_chunk_size': 0.0,
            'last_chunk_time': None
        }
        
        # Chunk ID counter
        self.chunk_counter = 0
        
    async def add_frame(self, frame: np.ndarray):
        """Add a video frame to the current chunk"""
        try:
            # Calculate frame size
            frame_size = frame.nbytes
            
            # Check if adding this frame would exceed chunk size
            if self.current_chunk_size + frame_size > self.chunk_size_bytes:
                # Process current chunk
                await self._process_chunk()
            
            # Add frame to buffer
            self.video_buffer.append(frame)
            self.current_chunk_size += frame_size
            
            logger.debug("Added frame to chunk", 
                        frame_size=frame_size,
                        current_chunk_size=self.current_chunk_size)
            
        except Exception as e:
            logger.error("Error adding frame to chunk", error=str(e))
    
    async def add_audio(self, audio_data: bytes):
        """Add audio data to the current chunk"""
        try:
            audio_size = len(audio_data)
            
            # Check if adding this audio would exceed chunk size
            if self.current_chunk_size + audio_size > self.chunk_size_bytes:
                # Process current chunk
                await self._process_chunk()
            
            # Add audio to buffer
            self.audio_buffer.append(audio_data)
            self.current_chunk_size += audio_size
            
            logger.debug("Added audio to chunk", 
                        audio_size=audio_size,
                        current_chunk_size=self.current_chunk_size)
            
        except Exception as e:
            logger.error("Error adding audio to chunk", error=str(e))
    
    async def _process_chunk(self):
        """Process the current chunk"""
        try:
            if not self.video_buffer and not self.audio_buffer:
                return
            
            # Generate chunk ID
            self.chunk_counter += 1
            chunk_id = f"chunk_{self.chunk_counter}_{int(time.time())}"
            
            # Create chunk metadata
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id="",  # Will be set by caller
                timestamp=datetime.utcnow(),
                size=self.current_chunk_size,
                compressed_size=0,
                frame_count=len(self.video_buffer),
                audio_samples=len(self.audio_buffer),
                chunk_type=self._determine_chunk_type()
            )
            
            # Serialize chunk data
            chunk_data = await self._serialize_chunk_data()
            
            # Compress chunk data
            compressed_data = await self._compress_chunk(chunk_data)
            metadata.compressed_size = len(compressed_data)
            
            # Calculate checksum
            checksum = self._calculate_checksum(compressed_data)
            
            # Create processed chunk
            processed_chunk = ProcessedChunk(
                data=compressed_data,
                metadata=metadata,
                checksum=checksum
            )
            
            # Add to output queue
            try:
                self.chunk_queue.put_nowait(processed_chunk)
            except asyncio.QueueFull:
                logger.warning("Chunk queue is full, dropping chunk")
            
            # Update statistics
            self._update_stats(processed_chunk)
            
            # Clear buffers
            self._clear_buffers()
            
            logger.info("Processed chunk", 
                       chunk_id=chunk_id,
                       original_size=metadata.size,
                       compressed_size=metadata.compressed_size,
                       compression_ratio=metadata.size / metadata.compressed_size if metadata.compressed_size > 0 else 0)
            
        except Exception as e:
            logger.error("Error processing chunk", error=str(e))
    
    def _determine_chunk_type(self) -> str:
        """Determine chunk type based on content"""
        if self.video_buffer and self.audio_buffer:
            return "mixed"
        elif self.video_buffer:
            return "video"
        elif self.audio_buffer:
            return "audio"
        else:
            return "empty"
    
    async def _serialize_chunk_data(self) -> bytes:
        """Serialize chunk data for compression"""
        try:
            chunk_data = {
                'video_frames': [],
                'audio_data': [],
                'metadata': {
                    'frame_count': len(self.video_buffer),
                    'audio_samples': len(self.audio_buffer),
                    'total_size': self.current_chunk_size
                }
            }
            
            # Serialize video frames
            for frame in self.video_buffer:
                # Convert frame to bytes
                frame_bytes = frame.tobytes()
                chunk_data['video_frames'].append(frame_bytes)
            
            # Add audio data
            chunk_data['audio_data'] = self.audio_buffer.copy()
            
            # Serialize to JSON bytes
            import json
            serialized = json.dumps(chunk_data, default=str).encode('utf-8')
            
            return serialized
            
        except Exception as e:
            logger.error("Error serializing chunk data", error=str(e))
            return b''
    
    async def _compress_chunk(self, data: bytes) -> bytes:
        """Compress chunk data"""
        try:
            # Use zlib compression
            compressed = zlib.compress(data, level=self.compression_level)
            
            # Add compression header
            header = {
                'compression': 'zlib',
                'level': self.compression_level,
                'original_size': len(data),
                'compressed_size': len(compressed)
            }
            
            import json
            header_bytes = json.dumps(header).encode('utf-8')
            header_length = len(header_bytes).to_bytes(4, byteorder='big')
            
            # Combine header and compressed data
            return header_length + header_bytes + compressed
            
        except Exception as e:
            logger.error("Error compressing chunk", error=str(e))
            return data  # Return uncompressed data if compression fails
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate checksum for chunk data"""
        import hashlib
        return hashlib.sha256(data).hexdigest()
    
    def _update_stats(self, chunk: ProcessedChunk):
        """Update processing statistics"""
        self.stats['chunks_created'] += 1
        self.stats['total_bytes_processed'] += chunk.metadata.size
        
        # Update compression ratio
        if chunk.metadata.compressed_size > 0:
            ratio = chunk.metadata.size / chunk.metadata.compressed_size
            self.stats['compression_ratio'] = (
                (self.stats['compression_ratio'] * (self.stats['chunks_created'] - 1) + ratio) /
                self.stats['chunks_created']
            )
        
        # Update average chunk size
        self.stats['average_chunk_size'] = (
            self.stats['total_bytes_processed'] / self.stats['chunks_created']
        )
        
        self.stats['last_chunk_time'] = time.time()
    
    def _clear_buffers(self):
        """Clear current buffers"""
        self.video_buffer.clear()
        self.audio_buffer.clear()
        self.current_chunk_size = 0
    
    async def get_next_chunk(self) -> Optional[ProcessedChunk]:
        """Get the next processed chunk"""
        try:
            return await asyncio.wait_for(self.chunk_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
    
    async def finalize(self):
        """Finalize any remaining data"""
        try:
            if self.video_buffer or self.audio_buffer:
                await self._process_chunk()
            
            logger.info("Chunk processor finalized", stats=self.stats)
            
        except Exception as e:
            logger.error("Error finalizing chunk processor", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.stats,
            'current_buffer_size': self.current_chunk_size,
            'video_frames_buffered': len(self.video_buffer),
            'audio_samples_buffered': len(self.audio_buffer),
            'chunk_queue_size': self.chunk_queue.qsize()
        }
    
    async def cleanup(self):
        """Cleanup chunk processor resources"""
        try:
            # Clear all buffers
            self._clear_buffers()
            
            # Clear output queue
            while not self.chunk_queue.empty():
                try:
                    self.chunk_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info("Chunk processor cleanup completed")
            
        except Exception as e:
            logger.error("Chunk processor cleanup error", error=str(e))

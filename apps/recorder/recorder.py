#!/usr/bin/env python3
"""
Lucid RDP Session Recorder
Captures and processes remote desktop sessions with hardware-accelerated encoding
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
import time
from datetime import datetime

import cv2
import numpy as np
from pydantic import BaseModel, Field
import structlog
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp

from .capture import ScreenCapture, AudioCapture
from .encoder import HardwareEncoder
from .chunker import ChunkProcessor
from .encryptor import SessionEncryptor
from .merkle import MerkleBuilder
from .chain_client import ChainClient
from .config import RecorderConfig

logger = structlog.get_logger(__name__)


class SessionMetadata(BaseModel):
    """Session metadata for recording"""
    session_id: str = Field(..., description="Unique session identifier")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    chunks_count: int = 0
    total_bytes: int = 0
    merkle_root: Optional[str] = None
    policy_hash: Optional[str] = None
    client_ip: Optional[str] = None
    resolution: Optional[str] = None
    fps: float = 30.0
    bitrate: int = 2000000  # 2 Mbps


class SessionRecorder:
    """Main session recorder class"""
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.session_metadata: Optional[SessionMetadata] = None
        self.is_recording = False
        self.is_paused = False
        
        # Initialize components
        self.screen_capture: Optional[ScreenCapture] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.encoder: Optional[HardwareEncoder] = None
        self.chunker: Optional[ChunkProcessor] = None
        self.encryptor: Optional[SessionEncryptor] = None
        self.merkle_builder: Optional[MerkleBuilder] = None
        self.chain_client: Optional[ChainClient] = None
        
        # Database connection
        self.db_client: Optional[AsyncIOMotorClient] = None
        
        # Statistics
        self.stats = {
            'frames_captured': 0,
            'frames_encoded': 0,
            'chunks_created': 0,
            'bytes_processed': 0,
            'errors': 0,
            'start_time': None
        }
    
    async def initialize(self) -> bool:
        """Initialize all recorder components"""
        try:
            logger.info("Initializing session recorder components")
            
            # Initialize database connection
            self.db_client = AsyncIOMotorClient(self.config.mongo_url)
            await self.db_client.admin.command('ping')
            logger.info("Database connection established")
            
            # Initialize screen capture
            self.screen_capture = ScreenCapture(
                resolution=self.config.resolution,
                fps=self.config.fps
            )
            await self.screen_capture.initialize()
            
            # Initialize audio capture if enabled
            if self.config.capture_audio:
                self.audio_capture = AudioCapture(
                    sample_rate=self.config.audio_sample_rate,
                    channels=self.config.audio_channels
                )
                await self.audio_capture.initialize()
            
            # Initialize hardware encoder
            self.encoder = HardwareEncoder(
                codec='h264_v4l2m2m',  # Pi 5 hardware encoder
                bitrate=self.config.bitrate,
                fps=self.config.fps
            )
            await self.encoder.initialize()
            
            # Initialize chunker
            self.chunker = ChunkProcessor(
                chunk_size_mb=self.config.chunk_size_mb,
                compression_level=self.config.compression_level
            )
            
            # Initialize encryptor
            self.encryptor = SessionEncryptor(
                algorithm='XChaCha20-Poly1305'
            )
            await self.encryptor.generate_keys()
            
            # Initialize merkle builder
            self.merkle_builder = MerkleBuilder(
                hash_algorithm='BLAKE3'
            )
            
            # Initialize chain client
            self.chain_client = ChainClient(
                rpc_url=self.config.blockchain_rpc_url,
                contract_address=self.config.anchors_contract_address
            )
            await self.chain_client.initialize()
            
            logger.info("All recorder components initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize recorder components", error=str(e))
            return False
    
    async def start_session(self, session_id: str, policy_hash: str, client_ip: str = None) -> bool:
        """Start recording a new session"""
        try:
            if self.is_recording:
                logger.warning("Already recording a session")
                return False
            
            logger.info("Starting new session", session_id=session_id)
            
            # Create session metadata
            self.session_metadata = SessionMetadata(
                session_id=session_id,
                policy_hash=policy_hash,
                client_ip=client_ip,
                resolution=self.config.resolution,
                fps=self.config.fps,
                bitrate=self.config.bitrate
            )
            
            # Start recording
            self.is_recording = True
            self.is_paused = False
            self.stats['start_time'] = time.time()
            self.stats.update({
                'frames_captured': 0,
                'frames_encoded': 0,
                'chunks_created': 0,
                'bytes_processed': 0,
                'errors': 0
            })
            
            # Start capture tasks
            asyncio.create_task(self._capture_loop())
            asyncio.create_task(self._processing_loop())
            
            # Store session metadata in database
            await self._store_session_metadata()
            
            logger.info("Session recording started", session_id=session_id)
            return True
            
        except Exception as e:
            logger.error("Failed to start session", session_id=session_id, error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def stop_session(self) -> bool:
        """Stop recording the current session"""
        try:
            if not self.is_recording:
                logger.warning("No active session to stop")
                return False
            
            logger.info("Stopping session", session_id=self.session_metadata.session_id)
            
            # Stop recording
            self.is_recording = False
            
            # Finalize session
            await self._finalize_session()
            
            logger.info("Session recording stopped", session_id=self.session_metadata.session_id)
            return True
            
        except Exception as e:
            logger.error("Failed to stop session", error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def pause_session(self) -> bool:
        """Pause recording"""
        if not self.is_recording:
            return False
        
        self.is_paused = True
        logger.info("Session paused", session_id=self.session_metadata.session_id)
        return True
    
    async def resume_session(self) -> bool:
        """Resume recording"""
        if not self.is_recording or not self.is_paused:
            return False
        
        self.is_paused = False
        logger.info("Session resumed", session_id=self.session_metadata.session_id)
        return True
    
    async def _capture_loop(self):
        """Main capture loop for screen and audio"""
        try:
            while self.is_recording:
                if self.is_paused:
                    await asyncio.sleep(0.1)
                    continue
                
                # Capture screen frame
                frame = await self.screen_capture.capture_frame()
                if frame is not None:
                    self.stats['frames_captured'] += 1
                    
                    # Add to processing queue
                    await self.chunker.add_frame(frame)
                
                # Capture audio if enabled
                if self.audio_capture:
                    audio_data = await self.audio_capture.capture_audio()
                    if audio_data is not None:
                        await self.chunker.add_audio(audio_data)
                
                # Sleep to maintain FPS
                await asyncio.sleep(1.0 / self.config.fps)
                
        except Exception as e:
            logger.error("Error in capture loop", error=str(e))
            self.stats['errors'] += 1
    
    async def _processing_loop(self):
        """Main processing loop for encoding and chunking"""
        try:
            while self.is_recording:
                # Process chunks
                chunk = await self.chunker.get_next_chunk()
                if chunk is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Encode chunk
                encoded_chunk = await self.encoder.encode_chunk(chunk)
                if encoded_chunk is not None:
                    self.stats['frames_encoded'] += 1
                    
                    # Encrypt chunk
                    encrypted_chunk = await self.encryptor.encrypt_chunk(
                        encoded_chunk, 
                        self.session_metadata.session_id
                    )
                    
                    # Add to merkle tree
                    await self.merkle_builder.add_chunk(encrypted_chunk)
                    
                    # Store chunk
                    await self._store_chunk(encrypted_chunk)
                    
                    self.stats['chunks_created'] += 1
                    self.stats['bytes_processed'] += len(encrypted_chunk)
                    self.session_metadata.chunks_count += 1
                    self.session_metadata.total_bytes += len(encrypted_chunk)
                
        except Exception as e:
            logger.error("Error in processing loop", error=str(e))
            self.stats['errors'] += 1
    
    async def _finalize_session(self):
        """Finalize session and anchor to blockchain"""
        try:
            # Calculate session duration
            if self.session_metadata:
                self.session_metadata.end_time = datetime.utcnow()
                duration = (self.session_metadata.end_time - self.session_metadata.start_time).total_seconds()
                self.session_metadata.duration = duration
            
            # Finalize merkle tree
            merkle_root = await self.merkle_builder.finalize()
            if self.session_metadata:
                self.session_metadata.merkle_root = merkle_root
            
            # Anchor session to blockchain
            if self.chain_client and self.session_metadata:
                await self.chain_client.anchor_session(
                    session_id=self.session_metadata.session_id,
                    merkle_root=merkle_root,
                    chunk_count=self.session_metadata.chunks_count,
                    policy_hash=self.session_metadata.policy_hash
                )
            
            # Update session metadata in database
            await self._update_session_metadata()
            
            logger.info("Session finalized", 
                       session_id=self.session_metadata.session_id,
                       duration=duration,
                       chunks=self.session_metadata.chunks_count,
                       bytes=self.session_metadata.total_bytes)
            
        except Exception as e:
            logger.error("Failed to finalize session", error=str(e))
            self.stats['errors'] += 1
    
    async def _store_session_metadata(self):
        """Store session metadata in database"""
        if not self.db_client or not self.session_metadata:
            return
        
        try:
            db = self.db_client.lucid
            collection = db.sessions
            
            await collection.insert_one({
                'session_id': self.session_metadata.session_id,
                'start_time': self.session_metadata.start_time,
                'policy_hash': self.session_metadata.policy_hash,
                'client_ip': self.session_metadata.client_ip,
                'status': 'recording',
                'metadata': self.session_metadata.dict()
            })
            
        except Exception as e:
            logger.error("Failed to store session metadata", error=str(e))
    
    async def _update_session_metadata(self):
        """Update session metadata in database"""
        if not self.db_client or not self.session_metadata:
            return
        
        try:
            db = self.db_client.lucid
            collection = db.sessions
            
            await collection.update_one(
                {'session_id': self.session_metadata.session_id},
                {
                    '$set': {
                        'end_time': self.session_metadata.end_time,
                        'duration': self.session_metadata.duration,
                        'chunks_count': self.session_metadata.chunks_count,
                        'total_bytes': self.session_metadata.total_bytes,
                        'merkle_root': self.session_metadata.merkle_root,
                        'status': 'completed',
                        'stats': self.stats,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
        except Exception as e:
            logger.error("Failed to update session metadata", error=str(e))
    
    async def _store_chunk(self, chunk_data: bytes):
        """Store encrypted chunk"""
        if not self.db_client or not self.session_metadata:
            return
        
        try:
            db = self.db_client.lucid
            collection = db.chunks
            
            await collection.insert_one({
                'session_id': self.session_metadata.session_id,
                'chunk_data': chunk_data,
                'size': len(chunk_data),
                'timestamp': datetime.utcnow()
            })
            
        except Exception as e:
            logger.error("Failed to store chunk", error=str(e))
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get current recording statistics"""
        return {
            'is_recording': self.is_recording,
            'is_paused': self.is_paused,
            'session_id': self.session_metadata.session_id if self.session_metadata else None,
            'stats': self.stats,
            'uptime': time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.screen_capture:
                await self.screen_capture.cleanup()
            
            if self.audio_capture:
                await self.audio_capture.cleanup()
            
            if self.encoder:
                await self.encoder.cleanup()
            
            if self.db_client:
                self.db_client.close()
            
            logger.info("Recorder cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))


async def main():
    """Main entry point"""
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
    
    # Load configuration
    config = RecorderConfig()
    
    # Initialize recorder
    recorder = SessionRecorder(config)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("Received signal, shutting down", signal=signum)
        asyncio.create_task(recorder.cleanup())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize recorder
        if not await recorder.initialize():
            logger.error("Failed to initialize recorder")
            sys.exit(1)
        
        # Keep running
        logger.info("Recorder started, waiting for sessions")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await recorder.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

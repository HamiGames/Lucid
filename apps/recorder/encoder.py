#!/usr/bin/env python3
"""
Hardware Encoder Module for Lucid RDP Recorder
Provides hardware-accelerated encoding for Raspberry Pi 5
"""

import asyncio
import logging
import subprocess
import tempfile
from typing import Optional, Dict, Any
import numpy as np
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class HardwareEncoder:
    """Hardware-accelerated encoder for Pi 5"""
    
    def __init__(self, codec: str = "h264_v4l2m2m", bitrate: int = 2000000, fps: int = 30):
        self.codec = codec
        self.bitrate = bitrate
        self.fps = fps
        self.encoder_process: Optional[subprocess.Popen] = None
        self.temp_dir: Optional[Path] = None
        
        # Encoding parameters
        self.encoding_params = {
            'codec': codec,
            'bitrate': bitrate,
            'fps': fps,
            'profile': 'high',
            'level': '4.1',
            'preset': 'fast',
            'crf': 23,
            'pix_fmt': 'yuv420p'
        }
        
        # Buffer for encoded chunks
        self.encoded_buffer = asyncio.Queue(maxsize=10)
        
    async def initialize(self) -> bool:
        """Initialize hardware encoder"""
        try:
            logger.info("Initializing hardware encoder", 
                       codec=self.codec, 
                       bitrate=self.bitrate,
                       fps=self.fps)
            
            # Create temporary directory for encoding
            self.temp_dir = Path(tempfile.mkdtemp(prefix="lucid_encoder_"))
            
            # Check hardware encoder availability
            if not await self._check_hardware_encoder():
                logger.error("Hardware encoder not available")
                return False
            
            # Test encoding capability
            if not await self._test_encoding():
                logger.error("Encoding test failed")
                return False
            
            logger.info("Hardware encoder initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize hardware encoder", error=str(e))
            return False
    
    async def _check_hardware_encoder(self) -> bool:
        """Check if hardware encoder is available"""
        try:
            # Check for V4L2 M2M encoder
            if self.codec == "h264_v4l2m2m":
                # Check if V4L2 M2M encoder is available
                result = await asyncio.create_subprocess_exec(
                    'ffmpeg', '-hide_banner', '-encoders',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    encoders = stdout.decode()
                    if 'h264_v4l2m2m' in encoders:
                        logger.info("V4L2 M2M H.264 encoder available")
                        return True
                    else:
                        logger.warning("V4L2 M2M H.264 encoder not available")
                        # Fallback to software encoder
                        self.codec = "libx264"
                        return True
                
            # Check for other hardware encoders
            elif self.codec == "h264_omx":
                # Check for OpenMAX encoder
                result = await asyncio.create_subprocess_exec(
                    'ffmpeg', '-hide_banner', '-encoders',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    encoders = stdout.decode()
                    if 'h264_omx' in encoders:
                        logger.info("OpenMAX H.264 encoder available")
                        return True
                    else:
                        logger.warning("OpenMAX H.264 encoder not available")
                        # Fallback to software encoder
                        self.codec = "libx264"
                        return True
            
            return True
            
        except Exception as e:
            logger.error("Hardware encoder check error", error=str(e))
            return False
    
    async def _test_encoding(self) -> bool:
        """Test encoding capability"""
        try:
            # Create test frame
            test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Test encoding
            encoded_data = await self._encode_frame(test_frame)
            
            if encoded_data is not None and len(encoded_data) > 0:
                logger.info("Encoding test successful")
                return True
            else:
                logger.error("Encoding test failed")
                return False
                
        except Exception as e:
            logger.error("Encoding test error", error=str(e))
            return False
    
    async def _encode_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode a single frame"""
        try:
            # Save frame to temporary file
            input_file = self.temp_dir / "input.raw"
            output_file = self.temp_dir / "output.h264"
            
            # Write raw frame data
            with open(input_file, 'wb') as f:
                f.write(frame.tobytes())
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{frame.shape[1]}x{frame.shape[0]}',
                '-r', str(self.fps),
                '-i', str(input_file),
                '-c:v', self.codec,
                '-b:v', f'{self.bitrate}',
                '-r', str(self.fps),
                '-profile:v', self.encoding_params['profile'],
                '-level', self.encoding_params['level'],
                '-preset', self.encoding_params['preset'],
                '-pix_fmt', self.encoding_params['pix_fmt'],
                '-frames:v', '1',
                str(output_file)
            ]
            
            # Add hardware-specific parameters
            if self.codec == "h264_v4l2m2m":
                cmd.extend(['-device', '/dev/video11'])  # V4L2 M2M device
            elif self.codec == "h264_omx":
                cmd.extend(['-omx_libname', 'libOpenMAX.so'])
            
            # Run encoding
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and output_file.exists():
                # Read encoded data
                with open(output_file, 'rb') as f:
                    encoded_data = f.read()
                
                # Cleanup temporary files
                input_file.unlink(missing_ok=True)
                output_file.unlink(missing_ok=True)
                
                return encoded_data
            else:
                logger.warning("Frame encoding failed", stderr=stderr.decode())
                return None
                
        except Exception as e:
            logger.error("Frame encoding error", error=str(e))
            return None
    
    async def encode_chunk(self, chunk_data: bytes) -> Optional[bytes]:
        """Encode a chunk of data"""
        try:
            # For now, assume chunk_data is a frame
            # In a real implementation, this would handle video chunks
            
            # Convert bytes to numpy array (assuming BGR24 format)
            # This is a simplified implementation
            frame_size = len(chunk_data) // 3
            if frame_size * 3 != len(chunk_data):
                logger.error("Invalid chunk data size")
                return None
            
            # Assume 640x480 frame for now
            width, height = 640, 480
            if frame_size != width * height:
                logger.error("Unexpected frame size")
                return None
            
            frame = np.frombuffer(chunk_data, dtype=np.uint8)
            frame = frame.reshape((height, width, 3))
            
            # Encode frame
            encoded_data = await self._encode_frame(frame)
            
            return encoded_data
            
        except Exception as e:
            logger.error("Chunk encoding error", error=str(e))
            return None
    
    async def encode_video_stream(self, input_stream: asyncio.Queue) -> asyncio.Queue:
        """Encode a video stream"""
        try:
            output_queue = asyncio.Queue(maxsize=10)
            
            async def encode_worker():
                while True:
                    try:
                        # Get frame from input stream
                        frame = await input_stream.get()
                        if frame is None:
                            break
                        
                        # Encode frame
                        encoded_frame = await self._encode_frame(frame)
                        if encoded_frame is not None:
                            await output_queue.put(encoded_frame)
                        
                        # Mark task as done
                        input_stream.task_done()
                        
                    except Exception as e:
                        logger.error("Video stream encoding error", error=str(e))
                        break
            
            # Start encoding worker
            asyncio.create_task(encode_worker())
            
            return output_queue
            
        except Exception as e:
            logger.error("Video stream encoding setup error", error=str(e))
            return asyncio.Queue()
    
    async def get_encoding_stats(self) -> Dict[str, Any]:
        """Get encoding statistics"""
        return {
            'codec': self.codec,
            'bitrate': self.bitrate,
            'fps': self.fps,
            'buffer_size': self.encoded_buffer.qsize(),
            'max_buffer_size': self.encoded_buffer.maxsize
        }
    
    async def cleanup(self):
        """Cleanup encoder resources"""
        try:
            # Cleanup temporary directory
            if self.temp_dir and self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            # Clear encoded buffer
            while not self.encoded_buffer.empty():
                try:
                    self.encoded_buffer.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info("Hardware encoder cleanup completed")
            
        except Exception as e:
            logger.error("Hardware encoder cleanup error", error=str(e))

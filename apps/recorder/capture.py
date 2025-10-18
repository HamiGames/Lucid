#!/usr/bin/env python3
"""
Screen and Audio Capture Module for Lucid RDP Recorder
Provides hardware-accelerated capture for Raspberry Pi 5
"""

import asyncio
import logging
import subprocess
import time
from typing import Optional, Tuple
import numpy as np
import cv2
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)


class ScreenCapture:
    """Hardware-accelerated screen capture for Pi 5"""
    
    def __init__(self, resolution: str = "1920x1080", fps: int = 30):
        self.resolution = resolution
        self.fps = fps
        self.capture_process: Optional[subprocess.Popen] = None
        self.is_capturing = False
        
        # Parse resolution
        width, height = map(int, resolution.split('x'))
        self.width = width
        self.height = height
        
        # Buffer for frames
        self.frame_buffer = asyncio.Queue(maxsize=10)
        
    async def initialize(self) -> bool:
        """Initialize screen capture"""
        try:
            logger.info("Initializing screen capture", 
                       resolution=self.resolution, 
                       fps=self.fps)
            
            # Check if running in X11 environment
            if not self._check_display():
                logger.error("No display available for screen capture")
                return False
            
            # Test capture capability
            if not await self._test_capture():
                logger.error("Screen capture test failed")
                return False
            
            logger.info("Screen capture initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize screen capture", error=str(e))
            return False
    
    def _check_display(self) -> bool:
        """Check if display is available"""
        try:
            result = subprocess.run(
                ['xrandr', '--query'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def _test_capture(self) -> bool:
        """Test screen capture capability"""
        try:
            # Test with ffmpeg
            test_cmd = [
                'ffmpeg', '-f', 'x11grab',
                '-video_size', self.resolution,
                '-framerate', str(self.fps),
                '-i', ':0.0',
                '-vframes', '1',
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-'
            ]
            
            result = await asyncio.create_subprocess_exec(
                *test_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and len(stdout) > 0:
                logger.info("Screen capture test successful")
                return True
            else:
                logger.error("Screen capture test failed", stderr=stderr.decode())
                return False
                
        except Exception as e:
            logger.error("Screen capture test error", error=str(e))
            return False
    
    async def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame"""
        try:
            # Use ffmpeg for hardware-accelerated capture
            cmd = [
                'ffmpeg', '-f', 'x11grab',
                '-video_size', self.resolution,
                '-framerate', str(self.fps),
                '-i', ':0.0',
                '-vframes', '1',
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-'
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and len(stdout) > 0:
                # Convert raw video data to numpy array
                frame = np.frombuffer(stdout, dtype=np.uint8)
                frame = frame.reshape((self.height, self.width, 3))
                return frame
            else:
                logger.warning("Failed to capture frame", stderr=stderr.decode())
                return None
                
        except Exception as e:
            logger.error("Frame capture error", error=str(e))
            return None
    
    async def start_continuous_capture(self):
        """Start continuous capture process"""
        try:
            self.is_capturing = True
            
            while self.is_capturing:
                frame = await self.capture_frame()
                if frame is not None:
                    try:
                        self.frame_buffer.put_nowait(frame)
                    except asyncio.QueueFull:
                        # Remove oldest frame if buffer is full
                        try:
                            self.frame_buffer.get_nowait()
                            self.frame_buffer.put_nowait(frame)
                        except asyncio.QueueEmpty:
                            pass
                
                # Maintain frame rate
                await asyncio.sleep(1.0 / self.fps)
                
        except Exception as e:
            logger.error("Continuous capture error", error=str(e))
        finally:
            self.is_capturing = False
    
    async def get_frame(self) -> Optional[np.ndarray]:
        """Get next frame from buffer"""
        try:
            return await asyncio.wait_for(self.frame_buffer.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
    
    async def cleanup(self):
        """Cleanup capture resources"""
        try:
            self.is_capturing = False
            
            # Clear frame buffer
            while not self.frame_buffer.empty():
                try:
                    self.frame_buffer.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info("Screen capture cleanup completed")
            
        except Exception as e:
            logger.error("Screen capture cleanup error", error=str(e))


class AudioCapture:
    """Audio capture for Pi 5"""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.capture_process: Optional[subprocess.Popen] = None
        self.is_capturing = False
        
        # Buffer for audio data
        self.audio_buffer = asyncio.Queue(maxsize=50)
        
    async def initialize(self) -> bool:
        """Initialize audio capture"""
        try:
            logger.info("Initializing audio capture", 
                       sample_rate=self.sample_rate, 
                       channels=self.channels)
            
            # Check audio devices
            if not await self._check_audio_devices():
                logger.warning("No audio devices found")
                return False
            
            # Test audio capture
            if not await self._test_audio_capture():
                logger.error("Audio capture test failed")
                return False
            
            logger.info("Audio capture initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize audio capture", error=str(e))
            return False
    
    async def _check_audio_devices(self) -> bool:
        """Check available audio devices"""
        try:
            # Check ALSA devices
            result = await asyncio.create_subprocess_exec(
                'arecord', '-l',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and len(stdout) > 0:
                logger.info("Audio devices found")
                return True
            else:
                logger.warning("No audio devices found")
                return False
                
        except FileNotFoundError:
            logger.warning("arecord not found")
            return False
        except Exception as e:
            logger.error("Audio device check error", error=str(e))
            return False
    
    async def _test_audio_capture(self) -> bool:
        """Test audio capture capability"""
        try:
            # Test with arecord
            test_cmd = [
                'arecord', '-f', 'cd',  # 16-bit, 44.1kHz
                '-c', str(self.channels),
                '-d', '1',  # 1 second
                '-t', 'raw',
                '/dev/null'
            ]
            
            result = await asyncio.create_subprocess_exec(
                *test_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info("Audio capture test successful")
                return True
            else:
                logger.error("Audio capture test failed", stderr=stderr.decode())
                return False
                
        except Exception as e:
            logger.error("Audio capture test error", error=str(e))
            return False
    
    async def capture_audio(self) -> Optional[bytes]:
        """Capture audio data"""
        try:
            # Use arecord for audio capture
            cmd = [
                'arecord', '-f', 'cd',  # 16-bit, 44.1kHz
                '-c', str(self.channels),
                '-d', '0.1',  # 100ms chunks
                '-t', 'raw'
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and len(stdout) > 0:
                return stdout
            else:
                logger.warning("Failed to capture audio", stderr=stderr.decode())
                return None
                
        except Exception as e:
            logger.error("Audio capture error", error=str(e))
            return None
    
    async def start_continuous_capture(self):
        """Start continuous audio capture"""
        try:
            self.is_capturing = True
            
            while self.is_capturing:
                audio_data = await self.capture_audio()
                if audio_data is not None:
                    try:
                        self.audio_buffer.put_nowait(audio_data)
                    except asyncio.QueueFull:
                        # Remove oldest audio if buffer is full
                        try:
                            self.audio_buffer.get_nowait()
                            self.audio_buffer.put_nowait(audio_data)
                        except asyncio.QueueEmpty:
                            pass
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error("Continuous audio capture error", error=str(e))
        finally:
            self.is_capturing = False
    
    async def get_audio(self) -> Optional[bytes]:
        """Get next audio chunk from buffer"""
        try:
            return await asyncio.wait_for(self.audio_buffer.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    async def cleanup(self):
        """Cleanup audio capture resources"""
        try:
            self.is_capturing = False
            
            # Clear audio buffer
            while not self.audio_buffer.empty():
                try:
                    self.audio_buffer.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info("Audio capture cleanup completed")
            
        except Exception as e:
            logger.error("Audio capture cleanup error", error=str(e))

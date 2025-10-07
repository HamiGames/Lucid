# Path: sessions/recorder/video_capture.py
# LUCID Session Video Capture - Hardware Encoding Support
# Professional video capture with Pi 5 hardware acceleration
# Multi-platform build for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import threading
import queue

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Configuration from environment
VIDEO_CAPTURE_PATH = Path(os.getenv("VIDEO_CAPTURE_PATH", "/data/video_capture"))
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")
HARDWARE_ACCELERATION = os.getenv("HARDWARE_ACCELERATION", "true").lower() == "true"
VIDEO_CODEC = os.getenv("VIDEO_CODEC", "h264_v4l2m2m")
BITRATE = os.getenv("BITRATE", "2000k")
FPS = int(os.getenv("FPS", "30"))
RESOLUTION = os.getenv("RESOLUTION", "1920x1080")
XRDP_DISPLAY = os.getenv("XRDP_DISPLAY", ":10")


class CaptureStatus(Enum):
    """Video capture status states"""
    IDLE = "idle"
    STARTING = "starting"
    CAPTURING = "capturing"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class VideoFrame:
    """Video frame data structure"""
    frame_id: str
    timestamp: datetime
    data: bytes
    width: int
    height: int
    format: str = "BGR24"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CaptureSession:
    """Video capture session metadata"""
    session_id: str
    owner_address: str
    status: CaptureStatus
    started_at: datetime
    stopped_at: Optional[datetime] = None
    output_path: Optional[Path] = None
    ffmpeg_process: Optional[subprocess.Popen] = None
    frame_queue: Optional[queue.Queue] = None
    capture_thread: Optional[threading.Thread] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    frame_count: int = 0


class VideoCapture:
    """
    Hardware-accelerated video capture for Lucid RDP sessions.
    
    Supports Pi 5 hardware acceleration and multi-platform recording.
    Implements SPEC-1B session recording requirements with hardware encoding.
    """
    
    def __init__(self):
        """Initialize video capture system"""
        # Capture tracking
        self.active_captures: Dict[str, CaptureSession] = {}
        self.capture_tasks: Dict[str, asyncio.Task] = {}
        
        # Hardware detection
        self.hardware_codecs = self._detect_hardware_codecs()
        self.capture_devices = self._detect_capture_devices()
        
        # Create directories
        self._create_directories()
        
        logger.info(f"Video capture initialized - Hardware acceleration: {HARDWARE_ACCELERATION}")
        logger.info(f"Available codecs: {self.hardware_codecs}")
    
    def _create_directories(self) -> None:
        """Create required directories"""
        VIDEO_CAPTURE_PATH.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created video capture directory: {VIDEO_CAPTURE_PATH}")
    
    def _detect_hardware_codecs(self) -> List[str]:
        """Detect available hardware codecs"""
        codecs = []
        
        try:
            # Check FFmpeg hardware codecs
            result = subprocess.run(
                [FFMPEG_PATH, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Check for Pi 5 hardware codecs
                if "h264_v4l2m2m" in output:
                    codecs.append("h264_v4l2m2m")
                if "h264_omx" in output:
                    codecs.append("h264_omx")
                if "h264_v4l2m2m" in output:
                    codecs.append("h264_v4l2m2m")
                
                # Check for general hardware codecs
                if "h264_nvenc" in output:
                    codecs.append("h264_nvenc")
                if "h264_qsv" in output:
                    codecs.append("h264_qsv")
                if "h264_vaapi" in output:
                    codecs.append("h264_vaapi")
            
        except Exception as e:
            logger.warning(f"Hardware codec detection failed: {e}")
        
        # Fallback to software codecs
        if not codecs:
            codecs = ["libx264", "libx265"]
        
        return codecs
    
    def _detect_capture_devices(self) -> List[Dict[str, Any]]:
        """Detect available capture devices"""
        devices = []
        
        try:
            # Check for X11 display
            if os.getenv("DISPLAY") or XRDP_DISPLAY:
                devices.append({
                    "type": "x11grab",
                    "source": XRDP_DISPLAY,
                    "description": "X11 Display Capture"
                })
            
            # Check for V4L2 devices
            v4l2_path = Path("/dev")
            for device in v4l2_path.glob("video*"):
                devices.append({
                    "type": "v4l2",
                    "source": str(device),
                    "description": f"V4L2 Device {device.name}"
                })
            
            # Check for screen capture
            devices.append({
                "type": "screen",
                "source": "screen",
                "description": "Screen Capture"
            })
            
        except Exception as e:
            logger.warning(f"Capture device detection failed: {e}")
        
        return devices
    
    async def start_capture(self, 
                           session_id: str, 
                           owner_address: str,
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start video capture session"""
        try:
            # Check if already capturing
            if session_id in self.active_captures:
                raise Exception("Capture already in progress")
            
            # Create capture session
            capture = CaptureSession(
                session_id=session_id,
                owner_address=owner_address,
                status=CaptureStatus.STARTING,
                started_at=datetime.now(timezone.utc),
                output_path=VIDEO_CAPTURE_PATH / f"{session_id}.mp4",
                frame_queue=queue.Queue(maxsize=100),
                metadata=metadata or {}
            )
            
            # Store in memory
            self.active_captures[session_id] = capture
            
            # Start capture task
            task = asyncio.create_task(self._run_capture(capture))
            self.capture_tasks[session_id] = task
            
            logger.info(f"Started video capture session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": capture.status.value,
                "started_at": capture.started_at.isoformat(),
                "output_path": str(capture.output_path),
                "hardware_acceleration": HARDWARE_ACCELERATION,
                "codec": VIDEO_CODEC
            }
            
        except Exception as e:
            logger.error(f"Capture start failed: {e}")
            raise Exception(f"Capture start failed: {str(e)}")
    
    async def stop_capture(self, session_id: str) -> Dict[str, Any]:
        """Stop video capture session"""
        if session_id not in self.active_captures:
            raise Exception("Capture not found")
        
        capture = self.active_captures[session_id]
        
        try:
            # Update status
            capture.status = CaptureStatus.STOPPING
            capture.stopped_at = datetime.now(timezone.utc)
            
            # Stop capture thread
            if capture.capture_thread and capture.capture_thread.is_alive():
                # Signal stop to thread
                capture.frame_queue.put(None)  # Sentinel value
                capture.capture_thread.join(timeout=5)
            
            # Stop FFmpeg process
            if capture.ffmpeg_process:
                capture.ffmpeg_process.terminate()
                try:
                    capture.ffmpeg_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    capture.ffmpeg_process.kill()
                    capture.ffmpeg_process.wait()
                capture.ffmpeg_process = None
            
            # Cancel capture task
            if session_id in self.capture_tasks:
                self.capture_tasks[session_id].cancel()
                del self.capture_tasks[session_id]
            
            # Update status
            capture.status = CaptureStatus.STOPPED
            
            logger.info(f"Stopped video capture session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": capture.status.value,
                "stopped_at": capture.stopped_at.isoformat(),
                "output_path": str(capture.output_path),
                "frame_count": capture.frame_count
            }
            
        except Exception as e:
            logger.error(f"Capture stop failed: {e}")
            capture.status = CaptureStatus.ERROR
            raise Exception(f"Capture stop failed: {str(e)}")
    
    async def _run_capture(self, capture: CaptureSession) -> None:
        """Run video capture session"""
        try:
            logger.info(f"Running video capture session: {capture.session_id}")
            
            # Start capture thread
            capture.capture_thread = threading.Thread(
                target=self._capture_frames,
                args=(capture,),
                daemon=True
            )
            capture.capture_thread.start()
            
            # Update status
            capture.status = CaptureStatus.CAPTURING
            
            # Start FFmpeg encoding process
            await self._start_ffmpeg_encoding(capture)
            
            # Wait for capture to complete
            await asyncio.get_event_loop().run_in_executor(
                None, capture.capture_thread.join
            )
            
            # Check final status
            if capture.status == CaptureStatus.CAPTURING:
                capture.status = CaptureStatus.STOPPED
                logger.info(f"Video capture completed successfully: {capture.session_id}")
            
        except asyncio.CancelledError:
            logger.info(f"Video capture cancelled: {capture.session_id}")
            capture.status = CaptureStatus.STOPPED
        except Exception as e:
            logger.error(f"Video capture error: {e}")
            capture.status = CaptureStatus.ERROR
    
    def _capture_frames(self, capture: CaptureSession) -> None:
        """Capture video frames in separate thread"""
        try:
            # Initialize OpenCV capture
            if HARDWARE_ACCELERATION and self.capture_devices:
                # Use X11 grab for hardware acceleration
                cap = cv2.VideoCapture(0)  # Use first available device
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                cap.set(cv2.CAP_PROP_FPS, FPS)
            else:
                # Use screen capture
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                cap.set(cv2.CAP_PROP_FPS, FPS)
            
            if not cap.isOpened():
                raise Exception("Failed to open video capture device")
            
            logger.info(f"Video capture device opened for session: {capture.session_id}")
            
            frame_count = 0
            while capture.status == CaptureStatus.CAPTURING:
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"Failed to read frame for session: {capture.session_id}")
                    break
                
                # Create frame data
                frame_id = f"{capture.session_id}_frame_{frame_count:08d}"
                frame_data = cv2.imencode('.jpg', frame)[1].tobytes()
                
                video_frame = VideoFrame(
                    frame_id=frame_id,
                    timestamp=datetime.now(timezone.utc),
                    data=frame_data,
                    width=frame.shape[1],
                    height=frame.shape[0],
                    format="JPEG",
                    metadata={
                        "session_id": capture.session_id,
                        "frame_number": frame_count,
                        "compression": "JPEG"
                    }
                )
                
                # Add to queue
                try:
                    capture.frame_queue.put(video_frame, timeout=1.0)
                    frame_count += 1
                    capture.frame_count = frame_count
                except queue.Full:
                    logger.warning(f"Frame queue full, dropping frame: {capture.session_id}")
                    continue
            
            cap.release()
            logger.info(f"Video capture thread completed for session: {capture.session_id}")
            
        except Exception as e:
            logger.error(f"Video capture thread error: {e}")
            capture.status = CaptureStatus.ERROR
    
    async def _start_ffmpeg_encoding(self, capture: CaptureSession) -> None:
        """Start FFmpeg encoding process"""
        try:
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command(capture)
            
            # Start FFmpeg process
            capture.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(VIDEO_CAPTURE_PATH)
            )
            
            # Start frame feeding thread
            feed_thread = threading.Thread(
                target=self._feed_frames_to_ffmpeg,
                args=(capture,),
                daemon=True
            )
            feed_thread.start()
            
            logger.info(f"FFmpeg encoding started for session: {capture.session_id}")
            
        except Exception as e:
            logger.error(f"FFmpeg encoding start failed: {e}")
            capture.status = CaptureStatus.ERROR
    
    def _feed_frames_to_ffmpeg(self, capture: CaptureSession) -> None:
        """Feed frames to FFmpeg process"""
        try:
            while capture.status == CaptureStatus.CAPTURING and capture.ffmpeg_process:
                try:
                    frame = capture.frame_queue.get(timeout=1.0)
                    if frame is None:  # Sentinel value
                        break
                    
                    # Write frame data to FFmpeg stdin
                    if capture.ffmpeg_process.stdin:
                        capture.ffmpeg_process.stdin.write(frame.data)
                        capture.ffmpeg_process.stdin.flush()
                    
                    capture.frame_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Frame feeding error: {e}")
                    break
            
            # Close FFmpeg stdin
            if capture.ffmpeg_process and capture.ffmpeg_process.stdin:
                capture.ffmpeg_process.stdin.close()
            
            logger.info(f"Frame feeding completed for session: {capture.session_id}")
            
        except Exception as e:
            logger.error(f"Frame feeding thread error: {e}")
    
    def _build_ffmpeg_command(self, capture: CaptureSession) -> List[str]:
        """Build FFmpeg command for hardware encoding"""
        cmd = [FFMPEG_PATH]
        
        # Input from stdin (JPEG frames)
        cmd.extend([
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-i", "-"
        ])
        
        # Video encoding with hardware acceleration
        if HARDWARE_ACCELERATION and VIDEO_CODEC in self.hardware_codecs:
            if VIDEO_CODEC == "h264_v4l2m2m":
                # Pi 5 hardware acceleration
                cmd.extend([
                    "-c:v", "h264_v4l2m2m",
                    "-b:v", BITRATE,
                    "-maxrate", BITRATE,
                    "-bufsize", "4000k"
                ])
            elif VIDEO_CODEC == "h264_omx":
                # OpenMAX hardware acceleration
                cmd.extend([
                    "-c:v", "h264_omx",
                    "-b:v", BITRATE,
                    "-maxrate", BITRATE,
                    "-bufsize", "4000k"
                ])
            else:
                # Other hardware codecs
                cmd.extend([
                    "-c:v", VIDEO_CODEC,
                    "-b:v", BITRATE,
                    "-maxrate", BITRATE,
                    "-bufsize", "4000k"
                ])
        else:
            # Software encoding fallback
            cmd.extend([
                "-c:v", "libx264",
                "-b:v", BITRATE,
                "-maxrate", BITRATE,
                "-bufsize", "4000k",
                "-preset", "fast"
            ])
        
        # Output settings
        cmd.extend([
            "-r", str(FPS),
            "-f", "mp4",
            "-movflags", "+faststart",
            "-y",  # Overwrite output file
            str(capture.output_path)
        ])
        
        return cmd
    
    def get_capture_info(self, session_id: str) -> Dict[str, Any]:
        """Get capture session information"""
        if session_id not in self.active_captures:
            raise Exception("Capture not found")
        
        capture = self.active_captures[session_id]
        return {
            "session_id": capture.session_id,
            "owner_address": capture.owner_address,
            "status": capture.status.value,
            "started_at": capture.started_at.isoformat(),
            "stopped_at": capture.stopped_at.isoformat() if capture.stopped_at else None,
            "output_path": str(capture.output_path),
            "frame_count": capture.frame_count,
            "hardware_acceleration": HARDWARE_ACCELERATION,
            "codec": VIDEO_CODEC
        }
    
    def list_captures(self) -> Dict[str, Any]:
        """List all capture sessions"""
        return {
            "captures": [
                {
                    "session_id": capture.session_id,
                    "owner_address": capture.owner_address,
                    "status": capture.status.value,
                    "started_at": capture.started_at.isoformat(),
                    "frame_count": capture.frame_count
                }
                for capture in self.active_captures.values()
            ]
        }


# Global video capture instance
video_capture = VideoCapture()

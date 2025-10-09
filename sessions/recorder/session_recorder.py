# LUCID Session Recorder - SPEC-1B Session Recording
# Professional session recording with hardware acceleration for Pi 5
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration from environment
RECORDING_PATH = Path(os.getenv("RECORDING_PATH", "/data/recordings"))
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")
XRDP_DISPLAY = os.getenv("XRDP_DISPLAY", ":10")
HARDWARE_ACCELERATION = os.getenv("HARDWARE_ACCELERATION", "true").lower() == "true"
VIDEO_CODEC = os.getenv("VIDEO_CODEC", "h264_v4l2m2m")
AUDIO_CODEC = os.getenv("AUDIO_CODEC", "opus")
BITRATE = os.getenv("BITRATE", "2000k")
FPS = int(os.getenv("FPS", "30"))


class RecordingStatus(Enum):
    """Session recording status states"""
    IDLE = "idle"
    STARTING = "starting"
    RECORDING = "recording"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class RecordingSession:
    """Recording session metadata"""
    session_id: str
    owner_address: str
    status: RecordingStatus
    started_at: datetime
    stopped_at: Optional[datetime] = None
    output_path: Optional[Path] = None
    ffmpeg_process: Optional[subprocess.Popen] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionRecorder:
    """
    Session recorder for Lucid RDP system.
    
    Records RDP sessions with hardware acceleration support for Pi 5.
    Implements SPEC-1B session recording requirements.
    """
    
    def __init__(self):
        """Initialize session recorder"""
        self.app = FastAPI(
            title="Lucid Session Recorder",
            description="Session recording service for Lucid RDP system",
            version="1.0.0"
        )
        
        # Recording tracking
        self.active_recordings: Dict[str, RecordingSession] = {}
        self.recording_tasks: Dict[str, asyncio.Task] = {}
        
        # Setup routes
        self._setup_routes()
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        RECORDING_PATH.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created recording directory: {RECORDING_PATH}")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "session-recorder",
                "active_recordings": len(self.active_recordings),
                "hardware_acceleration": HARDWARE_ACCELERATION,
                "video_codec": VIDEO_CODEC
            }
        
        @self.app.post("/recordings/start")
        async def start_recording(request: StartRecordingRequest):
            """Start session recording"""
            return await self.start_recording(
                session_id=request.session_id,
                owner_address=request.owner_address,
                metadata=request.metadata
            )
        
        @self.app.post("/recordings/{session_id}/stop")
        async def stop_recording(session_id: str):
            """Stop session recording"""
            return await self.stop_recording(session_id)
        
        @self.app.get("/recordings/{session_id}")
        async def get_recording(session_id: str):
            """Get recording information"""
            if session_id not in self.active_recordings:
                raise HTTPException(404, "Recording not found")
            
            recording = self.active_recordings[session_id]
            return {
                "session_id": recording.session_id,
                "status": recording.status.value,
                "started_at": recording.started_at.isoformat(),
                "stopped_at": recording.stopped_at.isoformat() if recording.stopped_at else None,
                "output_path": str(recording.output_path) if recording.output_path else None
            }
        
        @self.app.get("/recordings")
        async def list_recordings():
            """List all recordings"""
            return {
                "recordings": [
                    {
                        "session_id": recording.session_id,
                        "owner_address": recording.owner_address,
                        "status": recording.status.value,
                        "started_at": recording.started_at.isoformat()
                    }
                    for recording in self.active_recordings.values()
                ]
            }
    
    async def start_recording(self, 
                            session_id: str, 
                            owner_address: str,
                            metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start session recording"""
        try:
            # Check if already recording
            if session_id in self.active_recordings:
                raise HTTPException(409, "Recording already in progress")
            
            # Create recording session
            recording = RecordingSession(
                session_id=session_id,
                owner_address=owner_address,
                status=RecordingStatus.STARTING,
                started_at=datetime.now(timezone.utc),
                output_path=RECORDING_PATH / f"{session_id}.mp4",
                metadata=metadata or {}
            )
            
            # Store in memory
            self.active_recordings[session_id] = recording
            
            # Start recording task
            task = asyncio.create_task(self._run_recording(recording))
            self.recording_tasks[session_id] = task
            
            logger.info(f"Started recording session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": recording.status.value,
                "started_at": recording.started_at.isoformat(),
                "output_path": str(recording.output_path)
            }
            
        except Exception as e:
            logger.error(f"Recording start failed: {e}")
            raise HTTPException(500, f"Recording start failed: {str(e)}")
    
    async def stop_recording(self, session_id: str) -> Dict[str, Any]:
        """Stop session recording"""
        if session_id not in self.active_recordings:
            raise HTTPException(404, "Recording not found")
        
        recording = self.active_recordings[session_id]
        
        try:
            # Update status
            recording.status = RecordingStatus.STOPPING
            recording.stopped_at = datetime.now(timezone.utc)
            
            # Stop FFmpeg process
            if recording.ffmpeg_process:
                recording.ffmpeg_process.terminate()
                try:
                    recording.ffmpeg_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    recording.ffmpeg_process.kill()
                    recording.ffmpeg_process.wait()
                recording.ffmpeg_process = None
            
            # Cancel recording task
            if session_id in self.recording_tasks:
                self.recording_tasks[session_id].cancel()
                del self.recording_tasks[session_id]
            
            # Update status
            recording.status = RecordingStatus.STOPPED
            
            logger.info(f"Stopped recording session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": recording.status.value,
                "stopped_at": recording.stopped_at.isoformat(),
                "output_path": str(recording.output_path)
            }
            
        except Exception as e:
            logger.error(f"Recording stop failed: {e}")
            recording.status = RecordingStatus.ERROR
            raise HTTPException(500, f"Recording stop failed: {str(e)}")
    
    async def _run_recording(self, recording: RecordingSession) -> None:
        """Run session recording with FFmpeg"""
        try:
            logger.info(f"Running recording session: {recording.session_id}")
            
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command(recording)
            
            # Start FFmpeg process
            recording.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(RECORDING_PATH)
            )
            
            # Update status
            recording.status = RecordingStatus.RECORDING
            
            # Wait for process to complete
            await asyncio.get_event_loop().run_in_executor(
                None, recording.ffmpeg_process.wait
            )
            
            # Check exit code
            if recording.ffmpeg_process.returncode == 0:
                recording.status = RecordingStatus.STOPPED
                logger.info(f"Recording completed successfully: {recording.session_id}")
            else:
                recording.status = RecordingStatus.ERROR
                logger.error(f"Recording failed: {recording.session_id}")
            
        except asyncio.CancelledError:
            logger.info(f"Recording cancelled: {recording.session_id}")
            recording.status = RecordingStatus.STOPPED
        except Exception as e:
            logger.error(f"Recording error: {e}")
            recording.status = RecordingStatus.ERROR
    
    def _build_ffmpeg_command(self, recording: RecordingSession) -> List[str]:
        """Build FFmpeg command for recording"""
        cmd = [FFMPEG_PATH]
        
        # Input sources
        if HARDWARE_ACCELERATION:
            # Hardware-accelerated video capture
            cmd.extend([
                "-f", "x11grab",
                "-display", XRDP_DISPLAY,
                "-video_size", "1920x1080",
                "-framerate", str(FPS)
            ])
        else:
            # Software video capture
            cmd.extend([
                "-f", "x11grab",
                "-display", XRDP_DISPLAY,
                "-video_size", "1920x1080",
                "-framerate", str(FPS)
            ])
        
        # Video encoding
        if HARDWARE_ACCELERATION and VIDEO_CODEC == "h264_v4l2m2m":
            # Pi 5 hardware acceleration
            cmd.extend([
                "-c:v", "h264_v4l2m2m",
                "-b:v", BITRATE,
                "-maxrate", BITRATE,
                "-bufsize", "4000k"
            ])
        else:
            # Software encoding
            cmd.extend([
                "-c:v", "libx264",
                "-b:v", BITRATE,
                "-maxrate", BITRATE,
                "-bufsize", "4000k",
                "-preset", "fast"
            ])
        
        # Audio capture and encoding
        cmd.extend([
            "-f", "pulse",
            "-ac", "2",
            "-ar", "44100",
            "-c:a", AUDIO_CODEC,
            "-b:a", "128k"
        ])
        
        # Output settings
        cmd.extend([
            "-f", "mp4",
            "-movflags", "+faststart",
            "-y",  # Overwrite output file
            str(recording.output_path)
        ])
        
        return cmd


# Pydantic models
class StartRecordingRequest(BaseModel):
    session_id: str
    owner_address: str
    metadata: Optional[Dict[str, Any]] = None


# Global recorder instance
session_recorder = SessionRecorder()

# FastAPI app instance
app = session_recorder.app

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Session Recorder...")
    logger.info("Session Recorder started")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Session Recorder...")
    
    # Stop all active recordings
    for session_id in list(session_recorder.active_recordings.keys()):
        await session_recorder.stop_recording(session_id)
    
    logger.info("Session Recorder stopped")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[session-recorder] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "session_recorder:app",
        host="0.0.0.0",
        port=8093,
        log_level="info"
    )


if __name__ == "__main__":
    main()

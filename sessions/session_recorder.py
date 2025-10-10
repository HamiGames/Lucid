# Path: session/session_recorder.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import json
import os
import tempfile
from pathlib import Path
import threading
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    """Metadata for a recorded session."""
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    host_info: Dict[str, Any] = field(default_factory=dict)
    client_info: Dict[str, Any] = field(default_factory=dict)
    participants: List[str] = field(default_factory=list)
    resource_access: List[str] = field(default_factory=list)  # clipboard, files, etc.
    total_size_bytes: int = 0
    chunk_count: int = 0
    codec_info: Dict[str, Any] = field(default_factory=dict)
    device_fingerprint: str = ""
    recorder_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "host_info": self.host_info,
            "client_info": self.client_info,
            "participants": self.participants,
            "resource_access": self.resource_access,
            "total_size_bytes": self.total_size_bytes,
            "chunk_count": self.chunk_count,
            "codec_info": self.codec_info,
            "device_fingerprint": self.device_fingerprint,
            "recorder_version": self.recorder_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionMetadata:
        return cls(
            session_id=data["session_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            host_info=data.get("host_info", {}),
            client_info=data.get("client_info", {}),
            participants=data.get("participants", []),
            resource_access=data.get("resource_access", []),
            total_size_bytes=data.get("total_size_bytes", 0),
            chunk_count=data.get("chunk_count", 0),
            codec_info=data.get("codec_info", {}),
            device_fingerprint=data.get("device_fingerprint", ""),
            recorder_version=data.get("recorder_version", "1.0.0")
        )


class SessionRecorder:
    """
    Records RDP sessions with video, audio, and metadata capture.
    Integrates with trust-nothing policy engine and resource access controls.
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        temp_dir: Optional[str] = None,
        max_chunk_size: Optional[int] = None,
        video_codec: Optional[str] = None,
        audio_enabled: Optional[bool] = None,
        keylog_enabled: Optional[bool] = None
    ):
        self.db = db
        self.temp_dir = Path(temp_dir or os.getenv("LUCID_RECORDER_TEMP_DIR", str(tempfile.gettempdir()))) / "lucid_sessions"
        self.max_chunk_size = max_chunk_size or int(os.getenv("LUCID_RECORDER_MAX_CHUNK_SIZE", "16777216"))  # 16MB
        self.video_codec = video_codec or os.getenv("LUCID_RECORDER_VIDEO_CODEC", "h264")
        self.audio_enabled = audio_enabled if audio_enabled is not None else os.getenv("LUCID_RECORDER_AUDIO_ENABLED", "true").lower() == "true"
        self.keylog_enabled = keylog_enabled if keylog_enabled is not None else os.getenv("LUCID_RECORDER_KEYLOG_ENABLED", "false").lower() == "true"
        
        # Create temp directory
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Recording state
        self.active_sessions: Dict[str, SessionMetadata] = {}
        self.recording_processes: Dict[str, Any] = {}  # Would contain actual recording processes
        self.event_callbacks: List[Callable] = []
        
        # Resource access tracking
        self.resource_monitors: Dict[str, Dict[str, Any]] = {}
        
    async def start_session(
        self,
        host_addr: str,
        client_addr: str,
        user_id: Optional[str] = None,
        policy_config: Optional[Dict] = None
    ) -> str:
        """Start recording a new RDP session."""
        session_id = str(uuid.uuid4())
        
        try:
            # Create session metadata
            metadata = SessionMetadata(
                session_id=session_id,
                started_at=datetime.now(timezone.utc),
                host_info={"address": host_addr},
                client_info={"address": client_addr},
                participants=[user_id] if user_id else [],
                device_fingerprint=self._generate_device_fingerprint()
            )
            
            # Initialize recording directory
            session_dir = self.temp_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            # Start recording process (simplified - would integrate with actual RDP recording)
            await self._start_recording_process(session_id, session_dir, policy_config)
            
            # Initialize resource monitoring
            if policy_config:
                await self._setup_resource_monitoring(session_id, policy_config)
            
            # Store session metadata
            self.active_sessions[session_id] = metadata
            
            # Save to database
            await self.db["sessions"].insert_one(metadata.to_dict())
            
            # Notify callbacks
            await self._notify_callbacks("session_started", {
                "session_id": session_id,
                "metadata": metadata.to_dict()
            })
            
            logger.info(f"Started recording session {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start session recording: {e}")
            raise
            
    async def stop_session(self, session_id: str) -> SessionMetadata:
        """Stop recording a session and finalize metadata."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found or not active")
            
        try:
            metadata = self.active_sessions[session_id]
            metadata.ended_at = datetime.now(timezone.utc)
            
            # Stop recording process
            await self._stop_recording_process(session_id)
            
            # Calculate final session statistics
            session_dir = self.temp_dir / session_id
            if session_dir.exists():
                total_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                metadata.total_size_bytes = total_size
                
            # Stop resource monitoring
            if session_id in self.resource_monitors:
                del self.resource_monitors[session_id]
                
            # Update database
            await self.db["sessions"].replace_one(
                {"session_id": session_id},
                metadata.to_dict()
            )
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            # Notify callbacks
            await self._notify_callbacks("session_ended", {
                "session_id": session_id,
                "metadata": metadata.to_dict()
            })
            
            logger.info(f"Stopped recording session {session_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to stop session recording: {e}")
            raise
            
    async def record_resource_access(
        self,
        session_id: str,
        resource_type: str,
        action: str,
        details: Optional[Dict] = None
    ) -> None:
        """Record resource access event during session."""
        if session_id not in self.active_sessions:
            return
            
        try:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_type": resource_type,  # clipboard, file_transfer, audio, webcam, etc.
                "action": action,  # read, write, request, grant, deny
                "details": details or {}
            }
            
            # Store in session events collection
            await self.db["session_events"].insert_one({
                "session_id": session_id,
                "event_type": "resource_access",
                "event_data": event,
                "timestamp": datetime.now(timezone.utc)
            })
            
            # Update session metadata
            metadata = self.active_sessions[session_id]
            access_key = f"{resource_type}:{action}"
            if access_key not in metadata.resource_access:
                metadata.resource_access.append(access_key)
                
            logger.debug(f"Recorded resource access: {resource_type}:{action} for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to record resource access: {e}")
            
    async def record_keystroke(
        self,
        session_id: str,
        key_data: Dict[str, Any],
        window_info: Optional[Dict] = None
    ) -> None:
        """Record keystroke data (if enabled and permitted)."""
        if not self.keylog_enabled or session_id not in self.active_sessions:
            return
            
        try:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "key_data": key_data,  # Would be sanitized/encrypted
                "window_info": window_info,
                "type": "keystroke"
            }
            
            await self.db["session_events"].insert_one({
                "session_id": session_id,
                "event_type": "keystroke",
                "event_data": event,
                "timestamp": datetime.now(timezone.utc)
            })
            
        except Exception as e:
            logger.error(f"Failed to record keystroke: {e}")
            
    async def get_session_events(
        self,
        session_id: str,
        event_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get events for a session."""
        try:
            query = {"session_id": session_id}
            if event_types:
                query["event_type"] = {"$in": event_types}
                
            cursor = self.db["session_events"].find(query).sort("timestamp", -1).limit(limit)
            events = []
            async for doc in cursor:
                events.append({
                    "event_type": doc["event_type"],
                    "event_data": doc["event_data"],
                    "timestamp": doc["timestamp"].isoformat() if hasattr(doc["timestamp"], 'isoformat') else doc["timestamp"]
                })
            return events
            
        except Exception as e:
            logger.error(f"Failed to get session events: {e}")
            return []
            
    async def get_active_sessions(self) -> List[SessionMetadata]:
        """Get list of currently active sessions."""
        return list(self.active_sessions.values())
        
    async def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Get metadata for a specific session."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
            
        try:
            doc = await self.db["sessions"].find_one({"session_id": session_id})
            if doc:
                return SessionMetadata.from_dict(doc)
        except Exception as e:
            logger.error(f"Failed to get session metadata: {e}")
            
        return None
        
    def add_event_callback(self, callback: Callable) -> None:
        """Add callback for session events."""
        self.event_callbacks.append(callback)
        
    async def cleanup_temp_files(self, older_than_hours: int = 24) -> None:
        """Clean up old temporary session files."""
        try:
            cutoff = datetime.now(timezone.utc).timestamp() - (older_than_hours * 3600)
            
            for session_dir in self.temp_dir.iterdir():
                if session_dir.is_dir():
                    # Check if session is still active
                    session_id = session_dir.name
                    if session_id in self.active_sessions:
                        continue
                        
                    # Check directory age
                    if session_dir.stat().st_mtime < cutoff:
                        import shutil
                        shutil.rmtree(session_dir)
                        logger.debug(f"Cleaned up temp files for session {session_id}")
                        
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            
    async def _start_recording_process(
        self,
        session_id: str,
        session_dir: Path,
        policy_config: Optional[Dict]
    ) -> None:
        """Start the actual recording process (simplified placeholder)."""
        # In production, this would start FFmpeg or similar recording process
        # with appropriate video/audio capture settings
        
        # Create placeholder files
        video_file = session_dir / "video.mp4"
        audio_file = session_dir / "audio.wav" if self.audio_enabled else None
        metadata_file = session_dir / "metadata.json"
        
        # Store recording info
        self.recording_processes[session_id] = {
            "video_file": str(video_file),
            "audio_file": str(audio_file) if audio_file else None,
            "metadata_file": str(metadata_file),
            "started_at": datetime.now(timezone.utc)
        }
        
        # In real implementation, would start:
        # - Screen capture via RDP protocol hooks
        # - Audio capture if enabled
        # - Metadata logging
        
    async def _stop_recording_process(self, session_id: str) -> None:
        """Stop the recording process and finalize files."""
        if session_id not in self.recording_processes:
            return
            
        try:
            # Stop recording processes gracefully
            # In production: terminate FFmpeg, flush buffers, etc.
            
            del self.recording_processes[session_id]
            
        except Exception as e:
            logger.error(f"Failed to stop recording process: {e}")
            
    async def _setup_resource_monitoring(
        self,
        session_id: str,
        policy_config: Dict
    ) -> None:
        """Setup monitoring for resource access based on policy."""
        monitors = {
            "clipboard": policy_config.get("clipboard_enabled", False),
            "file_transfer": policy_config.get("file_transfer_enabled", False),
            "audio": policy_config.get("audio_enabled", False),
            "webcam": policy_config.get("webcam_enabled", False),
            "usb": policy_config.get("usb_enabled", False)
        }
        
        self.resource_monitors[session_id] = monitors
        
    def _generate_device_fingerprint(self) -> str:
        """Generate a device fingerprint for the recording host."""
        import hashlib
        import platform
        
        # Collect device info
        info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0]
        }
        
        # Create fingerprint hash
        fingerprint_data = json.dumps(info, sort_keys=True)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
        
    async def _notify_callbacks(self, event_type: str, data: Dict) -> None:
        """Notify event callbacks."""
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
                
    async def ensure_indexes(self) -> None:
        """Ensure database indexes for sessions collections."""
        try:
            await self.db["sessions"].create_index("session_id", unique=True)
            await self.db["sessions"].create_index("started_at")
            await self.db["sessions"].create_index("participants")
            
            await self.db["session_events"].create_index([
                ("session_id", 1), ("timestamp", -1)
            ])
            await self.db["session_events"].create_index("event_type")
            
        except Exception as e:
            logger.warning(f"Failed to create session indexes: {e}")
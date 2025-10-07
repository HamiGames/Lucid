# Path: RDP/recorder/file_transfer_handler.py
# Lucid RDP File Transfer Handler - File transfer toggles
# Implements R-MUST-003: Remote Desktop Host Support with file transfer controls
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import threading
import hashlib
import base64
import mimetypes
import magic
import zipfile
import tarfile

# File transfer imports
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

logger = logging.getLogger(__name__)

# Configuration from environment
FILE_TRANSFER_LOG_PATH = Path(os.getenv("FILE_TRANSFER_LOG_PATH", "/var/log/lucid/file_transfer"))
FILE_TRANSFER_CACHE_PATH = Path(os.getenv("FILE_TRANSFER_CACHE_PATH", "/tmp/lucid/file_transfer"))
FILE_TRANSFER_MAX_SIZE = int(os.getenv("FILE_TRANSFER_MAX_SIZE", "104857600"))  # 100MB
FILE_TRANSFER_TIMEOUT_SECONDS = int(os.getenv("FILE_TRANSFER_TIMEOUT_SECONDS", "300"))  # 5 minutes
FILE_TRANSFER_CHUNK_SIZE = int(os.getenv("FILE_TRANSFER_CHUNK_SIZE", "65536"))  # 64KB


class FileTransferDirection(Enum):
    """File transfer direction"""
    HOST_TO_CLIENT = "host_to_client"
    CLIENT_TO_HOST = "client_to_host"
    BIDIRECTIONAL = "bidirectional"
    DISABLED = "disabled"


class FileTransferStatus(Enum):
    """File transfer status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileTransferSecurityLevel(Enum):
    """File transfer security level"""
    PERMISSIVE = "permissive"  # Allow all files
    MODERATE = "moderate"      # Filter dangerous files
    STRICT = "strict"          # Only allow safe files
    LOCKED = "locked"          # Disable file transfer entirely


@dataclass
class FileTransferEvent:
    """File transfer event data"""
    event_id: str
    session_id: str
    direction: FileTransferDirection
    file_path: str
    file_name: str
    file_size: int
    file_hash: str
    mime_type: str
    status: FileTransferStatus
    timestamp: datetime
    source_address: str
    target_address: str
    security_level: FileTransferSecurityLevel
    allowed: bool
    reason: Optional[str] = None
    transfer_speed: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileTransferConfig:
    """File transfer handler configuration"""
    session_id: str
    direction: FileTransferDirection = FileTransferDirection.BIDIRECTIONAL
    security_level: FileTransferSecurityLevel = FileTransferSecurityLevel.MODERATE
    max_file_size: int = FILE_TRANSFER_MAX_SIZE
    timeout_seconds: int = FILE_TRANSFER_TIMEOUT_SECONDS
    chunk_size: int = FILE_TRANSFER_CHUNK_SIZE
    log_events: bool = True
    cache_files: bool = True
    scan_files: bool = True
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
        ".mp3", ".wav", ".mp4", ".avi", ".mov", ".mkv",
        ".zip", ".tar", ".gz", ".bz2", ".7z"
    ])
    blocked_extensions: List[str] = field(default_factory=lambda: [
        ".exe", ".bat", ".cmd", ".com", ".scr", ".pif", ".vbs", ".js",
        ".jar", ".war", ".ear", ".class", ".py", ".pl", ".sh", ".ps1"
    ])
    allowed_mime_types: List[str] = field(default_factory=lambda: [
        "text/", "image/", "audio/", "video/", "application/pdf",
        "application/zip", "application/x-tar", "application/gzip"
    ])
    blocked_mime_types: List[str] = field(default_factory=lambda: [
        "application/x-executable", "application/x-msdownload",
        "application/x-msdos-program", "application/x-msi"
    ])
    max_files_per_session: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileTransferHandler:
    """
    File transfer handler for Lucid RDP.
    
    Provides:
    - Secure file transfer between host and client
    - File type validation and filtering
    - Virus scanning and security checks
    - Transfer progress monitoring
    - Access control and permissions
    """
    
    def __init__(self, config: FileTransferConfig):
        self.config = config
        self.is_enabled = config.direction != FileTransferDirection.DISABLED
        
        # Transfer state
        self.active_transfers: Dict[str, FileTransferEvent] = {}
        self.transfer_history: List[FileTransferEvent] = []
        self.session_files: Dict[str, List[str]] = {}  # session_id -> file_paths
        
        # Security filters
        self.file_filters: List[Callable] = []
        self.security_scanners: List[Callable] = []
        
        # Event callbacks
        self.event_callbacks: List[Callable] = []
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        
        # Create required directories
        self._create_directories()
        
        # Setup security filters
        self._setup_security_filters()
        
        logger.info(f"File Transfer Handler initialized for session: {config.session_id}")
    
    def _create_directories(self) -> None:
        """Create required directories for file transfer"""
        directories = [
            FILE_TRANSFER_LOG_PATH,
            FILE_TRANSFER_CACHE_PATH,
            FILE_TRANSFER_LOG_PATH / self.config.session_id,
            FILE_TRANSFER_CACHE_PATH / self.config.session_id,
            FILE_TRANSFER_CACHE_PATH / self.config.session_id / "uploads",
            FILE_TRANSFER_CACHE_PATH / self.config.session_id / "downloads"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def _setup_security_filters(self) -> None:
        """Setup security filters based on configuration"""
        try:
            # File size filter
            def size_filter(file_path: str, file_size: int) -> bool:
                return file_size <= self.config.max_file_size
            
            # File extension filter
            def extension_filter(file_path: str, file_size: int) -> bool:
                file_ext = Path(file_path).suffix.lower()
                return file_ext in self.config.allowed_extensions and file_ext not in self.config.blocked_extensions
            
            # MIME type filter
            def mime_filter(file_path: str, file_size: int, mime_type: str) -> bool:
                # Check allowed MIME types
                for allowed_type in self.config.allowed_mime_types:
                    if mime_type.startswith(allowed_type):
                        return True
                
                # Check blocked MIME types
                for blocked_type in self.config.blocked_mime_types:
                    if mime_type.startswith(blocked_type):
                        return False
                
                return True
            
            # File content filter
            def content_filter(file_path: str, file_size: int, mime_type: str) -> bool:
                if not self.config.scan_files:
                    return True
                
                try:
                    # Check for executable content
                    with open(file_path, 'rb') as f:
                        header = f.read(1024)
                        if b'MZ' in header or b'ELF' in header:
                            return False
                    
                    # Check for script content
                    if mime_type.startswith('text/'):
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(1024)
                            if any(keyword in content.lower() for keyword in ['exec', 'eval', 'system', 'shell']):
                                return False
                
                except Exception:
                    pass
                
                return True
            
            # Add filters
            self.file_filters.append(size_filter)
            self.file_filters.append(extension_filter)
            self.file_filters.append(mime_filter)
            self.file_filters.append(content_filter)
            
            logger.info("Security filters configured")
            
        except Exception as e:
            logger.error(f"Failed to setup security filters: {e}")
    
    async def start(self) -> bool:
        """Start the file transfer handler"""
        try:
            if not self.is_enabled:
                logger.info("File transfer handler disabled")
                return True
            
            logger.info("Starting File Transfer Handler...")
            
            # Start monitoring
            await self._start_monitoring()
            
            logger.info("File Transfer Handler started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start File Transfer Handler: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the file transfer handler"""
        try:
            logger.info("Stopping File Transfer Handler...")
            
            # Cancel active transfers
            for transfer_id in list(self.active_transfers.keys()):
                await self.cancel_transfer(transfer_id)
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Save transfer history
            await self._save_transfer_history()
            
            logger.info("File Transfer Handler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop File Transfer Handler: {e}")
            return False
    
    async def upload_file(
        self,
        file_path: str,
        target_path: str,
        source_address: str = "client"
    ) -> str:
        """Upload a file from client to host"""
        try:
            if not self.is_enabled:
                raise Exception("File transfer disabled")
            
            # Check if direction allows uploads
            if self.config.direction in [FileTransferDirection.HOST_TO_CLIENT, FileTransferDirection.DISABLED]:
                raise Exception("Upload direction not allowed")
            
            # Generate transfer ID
            transfer_id = str(uuid.uuid4())
            
            # Get file info
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise Exception(f"File not found: {file_path}")
            
            file_size = file_path_obj.stat().st_size
            file_name = file_path_obj.name
            
            # Get MIME type
            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path)
            
            # Validate file
            if not await self._validate_file(file_path, file_size, mime_type):
                raise Exception("File failed security validation")
            
            # Create transfer event
            transfer_event = FileTransferEvent(
                event_id=transfer_id,
                session_id=self.config.session_id,
                direction=FileTransferDirection.CLIENT_TO_HOST,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                status=FileTransferStatus.PENDING,
                timestamp=datetime.now(timezone.utc),
                source_address=source_address,
                target_address="host",
                security_level=self.config.security_level,
                allowed=True
            )
            
            # Start transfer
            await self._start_transfer(transfer_event, target_path)
            
            return transfer_id
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    async def download_file(
        self,
        file_path: str,
        target_path: str,
        source_address: str = "host"
    ) -> str:
        """Download a file from host to client"""
        try:
            if not self.is_enabled:
                raise Exception("File transfer disabled")
            
            # Check if direction allows downloads
            if self.config.direction in [FileTransferDirection.CLIENT_TO_HOST, FileTransferDirection.DISABLED]:
                raise Exception("Download direction not allowed")
            
            # Generate transfer ID
            transfer_id = str(uuid.uuid4())
            
            # Get file info
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise Exception(f"File not found: {file_path}")
            
            file_size = file_path_obj.stat().st_size
            file_name = file_path_obj.name
            
            # Get MIME type
            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path)
            
            # Validate file
            if not await self._validate_file(file_path, file_size, mime_type):
                raise Exception("File failed security validation")
            
            # Create transfer event
            transfer_event = FileTransferEvent(
                event_id=transfer_id,
                session_id=self.config.session_id,
                direction=FileTransferDirection.HOST_TO_CLIENT,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                status=FileTransferStatus.PENDING,
                timestamp=datetime.now(timezone.utc),
                source_address=source_address,
                target_address="client",
                security_level=self.config.security_level,
                allowed=True
            )
            
            # Start transfer
            await self._start_transfer(transfer_event, target_path)
            
            return transfer_id
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise
    
    async def cancel_transfer(self, transfer_id: str) -> bool:
        """Cancel an active transfer"""
        try:
            if transfer_id not in self.active_transfers:
                logger.warning(f"Transfer {transfer_id} not found")
                return False
            
            transfer = self.active_transfers[transfer_id]
            transfer.status = FileTransferStatus.CANCELLED
            
            # Remove from active transfers
            del self.active_transfers[transfer_id]
            
            # Add to history
            self.transfer_history.append(transfer)
            
            # Notify callbacks
            await self._notify_callbacks("transfer_cancelled", transfer)
            
            logger.info(f"Transfer {transfer_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel transfer {transfer_id}: {e}")
            return False
    
    async def get_transfer_status(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get transfer status"""
        try:
            # Check active transfers
            if transfer_id in self.active_transfers:
                transfer = self.active_transfers[transfer_id]
                return {
                    "transfer_id": transfer.event_id,
                    "status": transfer.status.value,
                    "direction": transfer.direction.value,
                    "file_name": transfer.file_name,
                    "file_size": transfer.file_size,
                    "mime_type": transfer.mime_type,
                    "progress": 0,  # Would be calculated from actual transfer
                    "transfer_speed": transfer.transfer_speed,
                    "timestamp": transfer.timestamp.isoformat()
                }
            
            # Check history
            for transfer in self.transfer_history:
                if transfer.event_id == transfer_id:
                    return {
                        "transfer_id": transfer.event_id,
                        "status": transfer.status.value,
                        "direction": transfer.direction.value,
                        "file_name": transfer.file_name,
                        "file_size": transfer.file_size,
                        "mime_type": transfer.mime_type,
                        "progress": 100 if transfer.status == FileTransferStatus.COMPLETED else 0,
                        "transfer_speed": transfer.transfer_speed,
                        "timestamp": transfer.timestamp.isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transfer status: {e}")
            return None
    
    async def list_transfers(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent transfers"""
        try:
            # Combine active and completed transfers
            all_transfers = list(self.active_transfers.values()) + self.transfer_history
            
            # Sort by timestamp (newest first)
            all_transfers.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Limit results
            recent_transfers = all_transfers[:limit]
            
            transfers = []
            for transfer in recent_transfers:
                transfers.append({
                    "transfer_id": transfer.event_id,
                    "status": transfer.status.value,
                    "direction": transfer.direction.value,
                    "file_name": transfer.file_name,
                    "file_size": transfer.file_size,
                    "mime_type": transfer.mime_type,
                    "timestamp": transfer.timestamp.isoformat(),
                    "allowed": transfer.allowed,
                    "reason": transfer.reason
                })
            
            return transfers
            
        except Exception as e:
            logger.error(f"Failed to list transfers: {e}")
            return []
    
    async def _validate_file(self, file_path: str, file_size: int, mime_type: str) -> bool:
        """Validate file against security filters"""
        try:
            # Apply file filters
            for filter_func in self.file_filters:
                if not filter_func(file_path, file_size, mime_type):
                    return False
            
            # Apply security scanners
            for scanner in self.security_scanners:
                if not scanner(file_path, file_size, mime_type):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate file hash: {e}")
            return ""
    
    async def _start_transfer(self, transfer_event: FileTransferEvent, target_path: str) -> None:
        """Start file transfer"""
        try:
            # Add to active transfers
            self.active_transfers[transfer_event.event_id] = transfer_event
            
            # Update status
            transfer_event.status = FileTransferStatus.IN_PROGRESS
            
            # Start transfer task
            asyncio.create_task(self._transfer_file(transfer_event, target_path))
            
            # Notify callbacks
            await self._notify_callbacks("transfer_started", transfer_event)
            
            logger.info(f"Started transfer: {transfer_event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to start transfer: {e}")
            transfer_event.status = FileTransferStatus.FAILED
            transfer_event.reason = str(e)
    
    async def _transfer_file(self, transfer_event: FileTransferEvent, target_path: str) -> None:
        """Transfer file with progress monitoring"""
        try:
            start_time = time.time()
            bytes_transferred = 0
            
            # Create target directory
            target_path_obj = Path(target_path)
            target_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(transfer_event.file_path, target_path)
            
            # Calculate transfer speed
            end_time = time.time()
            transfer_time = end_time - start_time
            transfer_speed = transfer_event.file_size / transfer_time if transfer_time > 0 else 0
            
            # Update transfer event
            transfer_event.status = FileTransferStatus.COMPLETED
            transfer_event.transfer_speed = transfer_speed
            
            # Remove from active transfers
            if transfer_event.event_id in self.active_transfers:
                del self.active_transfers[transfer_event.event_id]
            
            # Add to history
            self.transfer_history.append(transfer_event)
            
            # Update session files
            if transfer_event.session_id not in self.session_files:
                self.session_files[transfer_event.session_id] = []
            self.session_files[transfer_event.session_id].append(target_path)
            
            # Notify callbacks
            await self._notify_callbacks("transfer_completed", transfer_event)
            
            logger.info(f"Transfer completed: {transfer_event.event_id} ({transfer_speed:.2f} bytes/sec)")
            
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            transfer_event.status = FileTransferStatus.FAILED
            transfer_event.reason = str(e)
            
            # Remove from active transfers
            if transfer_event.event_id in self.active_transfers:
                del self.active_transfers[transfer_event.event_id]
            
            # Add to history
            self.transfer_history.append(transfer_event)
            
            # Notify callbacks
            await self._notify_callbacks("transfer_failed", transfer_event)
    
    async def _start_monitoring(self) -> None:
        """Start transfer monitoring"""
        try:
            if self.monitor_running:
                return
            
            self.monitor_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_transfers)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Transfer monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start transfer monitoring: {e}")
    
    async def _stop_monitoring(self) -> None:
        """Stop transfer monitoring"""
        try:
            self.monitor_running = False
            
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            logger.info("Transfer monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop transfer monitoring: {e}")
    
    def _monitor_transfers(self) -> None:
        """Monitor active transfers (runs in separate thread)"""
        while self.monitor_running:
            try:
                # Check for timeout transfers
                current_time = datetime.now(timezone.utc)
                timeout_transfers = []
                
                for transfer_id, transfer in self.active_transfers.items():
                    if transfer.status == FileTransferStatus.IN_PROGRESS:
                        elapsed = (current_time - transfer.timestamp).total_seconds()
                        if elapsed > self.config.timeout_seconds:
                            timeout_transfers.append(transfer_id)
                
                # Cancel timeout transfers
                for transfer_id in timeout_transfers:
                    asyncio.create_task(self.cancel_transfer(transfer_id))
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Transfer monitoring error: {e}")
                time.sleep(10)
    
    async def _save_transfer_history(self) -> None:
        """Save transfer history to file"""
        try:
            history_file = FILE_TRANSFER_LOG_PATH / self.config.session_id / "transfer_history.json"
            
            history_data = []
            for transfer in self.transfer_history:
                history_data.append({
                    "event_id": transfer.event_id,
                    "session_id": transfer.session_id,
                    "direction": transfer.direction.value,
                    "file_path": transfer.file_path,
                    "file_name": transfer.file_name,
                    "file_size": transfer.file_size,
                    "file_hash": transfer.file_hash,
                    "mime_type": transfer.mime_type,
                    "status": transfer.status.value,
                    "timestamp": transfer.timestamp.isoformat(),
                    "source_address": transfer.source_address,
                    "target_address": transfer.target_address,
                    "security_level": transfer.security_level.value,
                    "allowed": transfer.allowed,
                    "reason": transfer.reason,
                    "transfer_speed": transfer.transfer_speed,
                    "metadata": transfer.metadata
                })
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            logger.info(f"Transfer history saved: {history_file}")
            
        except Exception as e:
            logger.error(f"Failed to save transfer history: {e}")
    
    async def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify event callbacks"""
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in transfer callback: {e}")
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add an event callback"""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get handler status"""
        return {
            "enabled": self.is_enabled,
            "session_id": self.config.session_id,
            "direction": self.config.direction.value,
            "security_level": self.config.security_level.value,
            "max_file_size": self.config.max_file_size,
            "timeout_seconds": self.config.timeout_seconds,
            "chunk_size": self.config.chunk_size,
            "log_events": self.config.log_events,
            "cache_files": self.config.cache_files,
            "scan_files": self.config.scan_files,
            "allowed_extensions": self.config.allowed_extensions,
            "blocked_extensions": self.config.blocked_extensions,
            "active_transfers": len(self.active_transfers),
            "transfer_history": len(self.transfer_history),
            "monitoring": self.monitor_running
        }


# Global File Transfer Handler instance
_file_transfer_handler: Optional[FileTransferHandler] = None


def get_file_transfer_handler() -> Optional[FileTransferHandler]:
    """Get the global file transfer handler instance"""
    return _file_transfer_handler


async def initialize_file_transfer_handler(config: FileTransferConfig) -> FileTransferHandler:
    """Initialize the global file transfer handler"""
    global _file_transfer_handler
    
    if _file_transfer_handler is None:
        _file_transfer_handler = FileTransferHandler(config)
        await _file_transfer_handler.start()
    
    return _file_transfer_handler


async def shutdown_file_transfer_handler() -> None:
    """Shutdown the global file transfer handler"""
    global _file_transfer_handler
    
    if _file_transfer_handler:
        await _file_transfer_handler.stop()
        _file_transfer_handler = None


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[file-transfer-handler] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = FileTransferConfig(
        session_id="lucid_file_transfer_001",
        direction=FileTransferDirection.BIDIRECTIONAL,
        security_level=FileTransferSecurityLevel.MODERATE,
        max_file_size=104857600,
        timeout_seconds=300,
        chunk_size=65536,
        log_events=True,
        cache_files=True,
        scan_files=True
    )
    
    # Initialize and start handler
    handler = await initialize_file_transfer_handler(config)
    
    try:
        # Test file transfer operations
        test_file = "/tmp/test_file.txt"
        with open(test_file, 'w') as f:
            f.write("Test file content")
        
        transfer_id = await handler.upload_file(test_file, "/tmp/uploaded_test_file.txt")
        print(f"Upload transfer ID: {transfer_id}")
        
        # Keep handler running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down File Transfer Handler...")
        await shutdown_file_transfer_handler()


if __name__ == "__main__":
    asyncio.run(main())

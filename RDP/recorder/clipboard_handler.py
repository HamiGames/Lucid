# Path: RDP/recorder/clipboard_handler.py
# Lucid RDP Clipboard Handler - Clipboard transfer toggles
# Implements R-MUST-003: Remote Desktop Host Support with clipboard controls
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import threading
import hashlib
import base64

# Clipboard handling imports
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import tkinter as tk
    from tkinter import Tk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# Platform-specific clipboard imports
if sys.platform == "linux":
    try:
        import subprocess
        HAS_XCLIP = True
    except ImportError:
        HAS_XCLIP = False
elif sys.platform == "darwin":
    try:
        import subprocess
        HAS_PBCLIP = True
    except ImportError:
        HAS_PBCLIP = False
elif sys.platform == "win32":
    try:
        import win32clipboard
        HAS_WIN32CLIP = True
    except ImportError:
        HAS_WIN32CLIP = False

logger = logging.getLogger(__name__)

# Configuration from environment
CLIPBOARD_LOG_PATH = Path(os.getenv("CLIPBOARD_LOG_PATH", "/var/log/lucid/clipboard"))
CLIPBOARD_CACHE_PATH = Path(os.getenv("CLIPBOARD_CACHE_PATH", "/tmp/lucid/clipboard"))
CLIPBOARD_MAX_SIZE = int(os.getenv("CLIPBOARD_MAX_SIZE", "1048576"))  # 1MB
CLIPBOARD_TIMEOUT_SECONDS = int(os.getenv("CLIPBOARD_TIMEOUT_SECONDS", "30"))


class ClipboardDirection(Enum):
    """Clipboard transfer direction"""
    HOST_TO_CLIENT = "host_to_client"
    CLIENT_TO_HOST = "client_to_host"
    BIDIRECTIONAL = "bidirectional"
    DISABLED = "disabled"


class ClipboardSecurityLevel(Enum):
    """Clipboard security level"""
    PERMISSIVE = "permissive"  # Allow all content
    MODERATE = "moderate"      # Filter sensitive content
    STRICT = "strict"          # Only allow safe content
    LOCKED = "locked"          # Disable clipboard entirely


@dataclass
class ClipboardEvent:
    """Clipboard event data"""
    event_id: str
    session_id: str
    direction: ClipboardDirection
    content_type: str  # text, image, file, etc.
    content_size: int
    content_hash: str
    timestamp: datetime
    source_address: str
    target_address: str
    security_level: ClipboardSecurityLevel
    allowed: bool
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClipboardConfig:
    """Clipboard handler configuration"""
    session_id: str
    direction: ClipboardDirection = ClipboardDirection.BIDIRECTIONAL
    security_level: ClipboardSecurityLevel = ClipboardSecurityLevel.MODERATE
    max_content_size: int = CLIPBOARD_MAX_SIZE
    timeout_seconds: int = CLIPBOARD_TIMEOUT_SECONDS
    log_events: bool = True
    cache_content: bool = True
    filter_sensitive: bool = True
    allowed_content_types: List[str] = field(default_factory=lambda: ["text/plain", "text/html"])
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r"password\s*[:=]\s*\w+",
        r"secret\s*[:=]\s*\w+",
        r"key\s*[:=]\s*\w+",
        r"token\s*[:=]\s*\w+"
    ])
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClipboardHandler:
    """
    Clipboard transfer handler for Lucid RDP.
    
    Provides:
    - Cross-platform clipboard access
    - Security filtering and validation
    - Content filtering and sanitization
    - Event logging and monitoring
    - Access control and permissions
    """
    
    def __init__(self, config: ClipboardConfig):
        self.config = config
        self.is_enabled = config.direction != ClipboardDirection.DISABLED
        
        # Clipboard state
        self.current_content: Optional[str] = None
        self.content_cache: Dict[str, Any] = {}
        self.event_log: List[ClipboardEvent] = []
        
        # Security filters
        self.content_filters: List[Callable] = []
        self.security_validators: List[Callable] = []
        
        # Event callbacks
        self.event_callbacks: List[Callable] = []
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        
        # Create required directories
        self._create_directories()
        
        # Setup security filters
        self._setup_security_filters()
        
        logger.info(f"Clipboard Handler initialized for session: {config.session_id}")
    
    def _create_directories(self) -> None:
        """Create required directories for clipboard handling"""
        directories = [
            CLIPBOARD_LOG_PATH,
            CLIPBOARD_CACHE_PATH,
            CLIPBOARD_LOG_PATH / self.config.session_id,
            CLIPBOARD_CACHE_PATH / self.config.session_id
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def _setup_security_filters(self) -> None:
        """Setup security filters based on configuration"""
        try:
            # Content size filter
            def size_filter(content: str) -> bool:
                return len(content.encode('utf-8')) <= self.config.max_content_size
            
            # Sensitive content filter
            def sensitive_filter(content: str) -> bool:
                if not self.config.filter_sensitive:
                    return True
                
                import re
                for pattern in self.config.blocked_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        return False
                return True
            
            # Content type filter
            def type_filter(content: str, content_type: str) -> bool:
                return content_type in self.config.allowed_content_types
            
            # Add filters
            self.content_filters.append(size_filter)
            self.content_filters.append(sensitive_filter)
            self.content_filters.append(type_filter)
            
            logger.info("Security filters configured")
            
        except Exception as e:
            logger.error(f"Failed to setup security filters: {e}")
    
    async def start(self) -> bool:
        """Start the clipboard handler"""
        try:
            if not self.is_enabled:
                logger.info("Clipboard handler disabled")
                return True
            
            logger.info("Starting Clipboard Handler...")
            
            # Start clipboard monitoring
            await self._start_monitoring()
            
            logger.info("Clipboard Handler started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Clipboard Handler: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the clipboard handler"""
        try:
            logger.info("Stopping Clipboard Handler...")
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Save event log
            await self._save_event_log()
            
            logger.info("Clipboard Handler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Clipboard Handler: {e}")
            return False
    
    async def get_clipboard_content(self) -> Optional[str]:
        """Get current clipboard content"""
        try:
            if not self.is_enabled:
                return None
            
            # Check if direction allows reading
            if self.config.direction in [ClipboardDirection.CLIENT_TO_HOST, ClipboardDirection.DISABLED]:
                return None
            
            # Get clipboard content
            content = await self._read_clipboard()
            
            if content:
                # Validate content
                if await self._validate_content(content, "text/plain"):
                    # Log event
                    await self._log_clipboard_event(
                        direction=ClipboardDirection.HOST_TO_CLIENT,
                        content=content,
                        source_address="host",
                        target_address="client"
                    )
                    
                    return content
                else:
                    logger.warning("Clipboard content failed validation")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get clipboard content: {e}")
            return None
    
    async def set_clipboard_content(self, content: str, source_address: str = "client") -> bool:
        """Set clipboard content"""
        try:
            if not self.is_enabled:
                return False
            
            # Check if direction allows writing
            if self.config.direction in [ClipboardDirection.HOST_TO_CLIENT, ClipboardDirection.DISABLED]:
                return False
            
            # Validate content
            if not await self._validate_content(content, "text/plain"):
                logger.warning("Clipboard content failed validation")
                return False
            
            # Set clipboard content
            success = await self._write_clipboard(content)
            
            if success:
                # Log event
                await self._log_clipboard_event(
                    direction=ClipboardDirection.CLIENT_TO_HOST,
                    content=content,
                    source_address=source_address,
                    target_address="host"
                )
                
                # Update current content
                self.current_content = content
                
                logger.info("Clipboard content set successfully")
                return True
            else:
                logger.error("Failed to set clipboard content")
                return False
            
        except Exception as e:
            logger.error(f"Failed to set clipboard content: {e}")
            return False
    
    async def clear_clipboard(self) -> bool:
        """Clear clipboard content"""
        try:
            if not self.is_enabled:
                return False
            
            # Clear clipboard
            success = await self._clear_clipboard()
            
            if success:
                # Log event
                await self._log_clipboard_event(
                    direction=ClipboardDirection.BIDIRECTIONAL,
                    content="",
                    source_address="system",
                    target_address="system"
                )
                
                # Update current content
                self.current_content = None
                
                logger.info("Clipboard cleared successfully")
                return True
            else:
                logger.error("Failed to clear clipboard")
                return False
            
        except Exception as e:
            logger.error(f"Failed to clear clipboard: {e}")
            return False
    
    async def get_clipboard_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get clipboard history"""
        try:
            # Get recent events
            recent_events = self.event_log[-limit:] if self.event_log else []
            
            history = []
            for event in recent_events:
                history.append({
                    "event_id": event.event_id,
                    "direction": event.direction.value,
                    "content_type": event.content_type,
                    "content_size": event.content_size,
                    "timestamp": event.timestamp.isoformat(),
                    "source_address": event.source_address,
                    "target_address": event.target_address,
                    "allowed": event.allowed,
                    "reason": event.reason
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get clipboard history: {e}")
            return []
    
    async def _read_clipboard(self) -> Optional[str]:
        """Read clipboard content using platform-specific methods"""
        try:
            if HAS_PYPERCLIP:
                return pyperclip.paste()
            elif HAS_TKINTER:
                root = Tk()
                root.withdraw()
                try:
                    return root.clipboard_get()
                finally:
                    root.destroy()
            elif sys.platform == "linux" and HAS_XCLIP:
                result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], 
                                      capture_output=True, text=True)
                return result.stdout if result.returncode == 0 else None
            elif sys.platform == "darwin" and HAS_PBCLIP:
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return result.stdout if result.returncode == 0 else None
            elif sys.platform == "win32" and HAS_WIN32CLIP:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    data = win32clipboard.GetClipboardData()
                    return str(data) if data else None
                finally:
                    win32clipboard.CloseClipboard()
            else:
                logger.warning("No clipboard access method available")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read clipboard: {e}")
            return None
    
    async def _write_clipboard(self, content: str) -> bool:
        """Write clipboard content using platform-specific methods"""
        try:
            if HAS_PYPERCLIP:
                pyperclip.copy(content)
                return True
            elif HAS_TKINTER:
                root = Tk()
                root.withdraw()
                try:
                    root.clipboard_clear()
                    root.clipboard_append(content)
                    root.update()
                    return True
                finally:
                    root.destroy()
            elif sys.platform == "linux" and HAS_XCLIP:
                result = subprocess.run(["xclip", "-selection", "clipboard"], 
                                      input=content, text=True)
                return result.returncode == 0
            elif sys.platform == "darwin" and HAS_PBCLIP:
                result = subprocess.run(["pbcopy"], input=content, text=True)
                return result.returncode == 0
            elif sys.platform == "win32" and HAS_WIN32CLIP:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(content)
                    return True
                finally:
                    win32clipboard.CloseClipboard()
            else:
                logger.warning("No clipboard access method available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to write clipboard: {e}")
            return False
    
    async def _clear_clipboard(self) -> bool:
        """Clear clipboard content"""
        try:
            if HAS_PYPERCLIP:
                pyperclip.copy("")
                return True
            elif HAS_TKINTER:
                root = Tk()
                root.withdraw()
                try:
                    root.clipboard_clear()
                    return True
                finally:
                    root.destroy()
            elif sys.platform == "linux" and HAS_XCLIP:
                result = subprocess.run(["xclip", "-selection", "clipboard", "-c"], 
                                      input="", text=True)
                return result.returncode == 0
            elif sys.platform == "darwin" and HAS_PBCLIP:
                result = subprocess.run(["pbcopy"], input="", text=True)
                return result.returncode == 0
            elif sys.platform == "win32" and HAS_WIN32CLIP:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    return True
                finally:
                    win32clipboard.CloseClipboard()
            else:
                logger.warning("No clipboard access method available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear clipboard: {e}")
            return False
    
    async def _validate_content(self, content: str, content_type: str) -> bool:
        """Validate clipboard content against security filters"""
        try:
            # Apply content filters
            for filter_func in self.content_filters:
                if not filter_func(content, content_type):
                    return False
            
            # Apply security validators
            for validator in self.security_validators:
                if not validator(content, content_type):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return False
    
    async def _log_clipboard_event(
        self,
        direction: ClipboardDirection,
        content: str,
        source_address: str,
        target_address: str
    ) -> None:
        """Log a clipboard event"""
        try:
            # Generate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Create event
            event = ClipboardEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                direction=direction,
                content_type="text/plain",
                content_size=len(content.encode('utf-8')),
                content_hash=content_hash,
                timestamp=datetime.now(timezone.utc),
                source_address=source_address,
                target_address=target_address,
                security_level=self.config.security_level,
                allowed=True,  # Will be updated by validation
                metadata={}
            )
            
            # Validate content
            if not await self._validate_content(content, "text/plain"):
                event.allowed = False
                event.reason = "Content failed security validation"
            
            # Add to event log
            self.event_log.append(event)
            
            # Cache content if enabled
            if self.config.cache_content:
                await self._cache_content(event)
            
            # Notify callbacks
            await self._notify_callbacks("clipboard_event", event)
            
            logger.debug(f"Logged clipboard event: {event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to log clipboard event: {e}")
    
    async def _cache_content(self, event: ClipboardEvent) -> None:
        """Cache clipboard content"""
        try:
            cache_file = CLIPBOARD_CACHE_PATH / self.config.session_id / f"{event.event_id}.json"
            
            cache_data = {
                "event_id": event.event_id,
                "content": event.content_hash,  # Store hash, not content
                "content_size": event.content_size,
                "timestamp": event.timestamp.isoformat(),
                "direction": event.direction.value,
                "allowed": event.allowed
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            logger.debug(f"Cached clipboard content: {event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache clipboard content: {e}")
    
    async def _start_monitoring(self) -> None:
        """Start clipboard monitoring"""
        try:
            if self.monitor_running:
                return
            
            self.monitor_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_clipboard)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Clipboard monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start clipboard monitoring: {e}")
    
    async def _stop_monitoring(self) -> None:
        """Stop clipboard monitoring"""
        try:
            self.monitor_running = False
            
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            logger.info("Clipboard monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop clipboard monitoring: {e}")
    
    def _monitor_clipboard(self) -> None:
        """Monitor clipboard changes (runs in separate thread)"""
        last_content = None
        
        while self.monitor_running:
            try:
                # Read clipboard content
                if HAS_PYPERCLIP:
                    current_content = pyperclip.paste()
                else:
                    current_content = None
                
                # Check if content changed
                if current_content != last_content:
                    if current_content:
                        # Content was added
                        asyncio.create_task(self._handle_clipboard_change(current_content))
                    else:
                        # Content was cleared
                        asyncio.create_task(self._handle_clipboard_clear())
                    
                    last_content = current_content
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"Clipboard monitoring error: {e}")
                time.sleep(1)
    
    async def _handle_clipboard_change(self, content: str) -> None:
        """Handle clipboard content change"""
        try:
            # Validate content
            if await self._validate_content(content, "text/plain"):
                # Log event
                await self._log_clipboard_event(
                    direction=ClipboardDirection.BIDIRECTIONAL,
                    content=content,
                    source_address="system",
                    target_address="system"
                )
                
                # Update current content
                self.current_content = content
                
                logger.debug("Clipboard content changed")
            else:
                logger.warning("Clipboard content change blocked by security filter")
            
        except Exception as e:
            logger.error(f"Failed to handle clipboard change: {e}")
    
    async def _handle_clipboard_clear(self) -> None:
        """Handle clipboard clear"""
        try:
            # Log event
            await self._log_clipboard_event(
                direction=ClipboardDirection.BIDIRECTIONAL,
                content="",
                source_address="system",
                target_address="system"
            )
            
            # Update current content
            self.current_content = None
            
            logger.debug("Clipboard cleared")
            
        except Exception as e:
            logger.error(f"Failed to handle clipboard clear: {e}")
    
    async def _save_event_log(self) -> None:
        """Save event log to file"""
        try:
            log_file = CLIPBOARD_LOG_PATH / self.config.session_id / "clipboard_events.json"
            
            events_data = []
            for event in self.event_log:
                events_data.append({
                    "event_id": event.event_id,
                    "session_id": event.session_id,
                    "direction": event.direction.value,
                    "content_type": event.content_type,
                    "content_size": event.content_size,
                    "content_hash": event.content_hash,
                    "timestamp": event.timestamp.isoformat(),
                    "source_address": event.source_address,
                    "target_address": event.target_address,
                    "security_level": event.security_level.value,
                    "allowed": event.allowed,
                    "reason": event.reason,
                    "metadata": event.metadata
                })
            
            with open(log_file, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.info(f"Event log saved: {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save event log: {e}")
    
    async def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify event callbacks"""
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in clipboard callback: {e}")
    
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
            "max_content_size": self.config.max_content_size,
            "timeout_seconds": self.config.timeout_seconds,
            "log_events": self.config.log_events,
            "cache_content": self.config.cache_content,
            "filter_sensitive": self.config.filter_sensitive,
            "allowed_content_types": self.config.allowed_content_types,
            "event_count": len(self.event_log),
            "monitoring": self.monitor_running,
            "current_content": self.current_content is not None
        }


# Global Clipboard Handler instance
_clipboard_handler: Optional[ClipboardHandler] = None


def get_clipboard_handler() -> Optional[ClipboardHandler]:
    """Get the global clipboard handler instance"""
    return _clipboard_handler


async def initialize_clipboard_handler(config: ClipboardConfig) -> ClipboardHandler:
    """Initialize the global clipboard handler"""
    global _clipboard_handler
    
    if _clipboard_handler is None:
        _clipboard_handler = ClipboardHandler(config)
        await _clipboard_handler.start()
    
    return _clipboard_handler


async def shutdown_clipboard_handler() -> None:
    """Shutdown the global clipboard handler"""
    global _clipboard_handler
    
    if _clipboard_handler:
        await _clipboard_handler.stop()
        _clipboard_handler = None


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[clipboard-handler] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = ClipboardConfig(
        session_id="lucid_clipboard_001",
        direction=ClipboardDirection.BIDIRECTIONAL,
        security_level=ClipboardSecurityLevel.MODERATE,
        max_content_size=1048576,
        timeout_seconds=30,
        log_events=True,
        cache_content=True,
        filter_sensitive=True
    )
    
    # Initialize and start handler
    handler = await initialize_clipboard_handler(config)
    
    try:
        # Test clipboard operations
        await handler.set_clipboard_content("Test clipboard content")
        content = await handler.get_clipboard_content()
        print(f"Clipboard content: {content}")
        
        # Keep handler running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Clipboard Handler...")
        await shutdown_clipboard_handler()


if __name__ == "__main__":
    asyncio.run(main())

# Path: sessions/recorder/window_focus_monitor.py
# Lucid RDP Window Focus Monitor - Window focus tracking
# Implements R-MUST-005: Session Audit Trail with window focus metadata
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import hashlib

# Window monitoring imports
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import Xlib
    from Xlib import X, display
    from Xlib.ext import record
    from Xlib.protocol import rq
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False
    X = None
    display = None
    record = None
    rq = None

# Windows-specific imports
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# macOS-specific imports
try:
    import Quartz
    from AppKit import NSWorkspace
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False
    Quartz = None
    NSWorkspace = None

logger = logging.getLogger(__name__)

# Configuration from environment
WINDOW_LOG_PATH = Path(os.getenv("LUCID_WINDOW_LOG_PATH", "/var/log/lucid/windows"))
WINDOW_CACHE_PATH = Path(os.getenv("LUCID_WINDOW_CACHE_PATH", "/tmp/lucid/windows"))
WINDOW_MONITOR_INTERVAL = float(os.getenv("LUCID_WINDOW_MONITOR_INTERVAL", "1.0"))
WINDOW_MAX_EVENTS = int(os.getenv("LUCID_WINDOW_MAX_EVENTS", "10000"))
WINDOW_BATCH_SIZE = int(os.getenv("LUCID_WINDOW_BATCH_SIZE", "100"))


class WindowEventType(Enum):
    """Types of window events"""
    WINDOW_FOCUS = "window_focus"
    WINDOW_BLUR = "window_blur"
    WINDOW_OPEN = "window_open"
    WINDOW_CLOSE = "window_close"
    WINDOW_MINIMIZE = "window_minimize"
    WINDOW_MAXIMIZE = "window_maximize"
    WINDOW_RESTORE = "window_restore"
    WINDOW_MOVE = "window_move"
    WINDOW_RESIZE = "window_resize"
    APPLICATION_LAUNCH = "application_launch"
    APPLICATION_QUIT = "application_quit"
    DESKTOP_SWITCH = "desktop_switch"


class WindowState(Enum):
    """Window states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    HIDDEN = "hidden"
    CLOSED = "closed"


@dataclass
class WindowInfo:
    """Window information structure"""
    window_id: Optional[int] = None
    window_title: Optional[str] = None
    window_class: Optional[str] = None
    application_name: Optional[str] = None
    process_id: Optional[int] = None
    process_name: Optional[str] = None
    window_state: WindowState = WindowState.ACTIVE
    position: tuple[int, int] = (0, 0)
    size: tuple[int, int] = (0, 0)
    is_visible: bool = True
    is_focused: bool = False
    desktop_number: Optional[int] = None
    workspace_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WindowEvent:
    """Window event data structure"""
    event_id: str
    session_id: str
    timestamp: datetime
    event_type: WindowEventType
    window_info: WindowInfo
    previous_window: Optional[WindowInfo] = None
    duration_ms: Optional[int] = None
    is_sensitive: bool = False
    is_filtered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "window_info": {
                "window_id": self.window_info.window_id,
                "window_title": self.window_info.window_title,
                "window_class": self.window_info.window_class,
                "application_name": self.window_info.application_name,
                "process_id": self.window_info.process_id,
                "process_name": self.window_info.process_name,
                "window_state": self.window_info.window_state.value,
                "position": self.window_info.position,
                "size": self.window_info.size,
                "is_visible": self.window_info.is_visible,
                "is_focused": self.window_info.is_focused,
                "desktop_number": self.window_info.desktop_number,
                "workspace_name": self.window_info.workspace_name,
                "metadata": self.window_info.metadata
            },
            "previous_window": {
                "window_id": self.previous_window.window_id,
                "window_title": self.previous_window.window_title,
                "application_name": self.previous_window.application_name,
                "process_id": self.previous_window.process_id
            } if self.previous_window else None,
            "duration_ms": self.duration_ms,
            "is_sensitive": self.is_sensitive,
            "is_filtered": self.is_filtered,
            "metadata": self.metadata,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WindowEvent:
        """Create from dictionary"""
        window_info_data = data["window_info"]
        window_info = WindowInfo(
            window_id=window_info_data.get("window_id"),
            window_title=window_info_data.get("window_title"),
            window_class=window_info_data.get("window_class"),
            application_name=window_info_data.get("application_name"),
            process_id=window_info_data.get("process_id"),
            process_name=window_info_data.get("process_name"),
            window_state=WindowState(window_info_data.get("window_state", "active")),
            position=tuple(window_info_data.get("position", (0, 0))),
            size=tuple(window_info_data.get("size", (0, 0))),
            is_visible=window_info_data.get("is_visible", True),
            is_focused=window_info_data.get("is_focused", False),
            desktop_number=window_info_data.get("desktop_number"),
            workspace_name=window_info_data.get("workspace_name"),
            metadata=window_info_data.get("metadata", {})
        )
        
        previous_window = None
        if data.get("previous_window"):
            prev_data = data["previous_window"]
            previous_window = WindowInfo(
                window_id=prev_data.get("window_id"),
                window_title=prev_data.get("window_title"),
                application_name=prev_data.get("application_name"),
                process_id=prev_data.get("process_id")
            )
        
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=WindowEventType(data["event_type"]),
            window_info=window_info,
            previous_window=previous_window,
            duration_ms=data.get("duration_ms"),
            is_sensitive=data.get("is_sensitive", False),
            is_filtered=data.get("is_filtered", False),
            metadata=data.get("metadata", {}),
            hash=data.get("hash")
        )


@dataclass
class WindowFocusMonitorConfig:
    """Window focus monitor configuration"""
    session_id: str
    enabled: bool = True
    monitor_interval: float = WINDOW_MONITOR_INTERVAL
    max_events: int = WINDOW_MAX_EVENTS
    batch_size: int = WINDOW_BATCH_SIZE
    include_window_info: bool = True
    include_process_info: bool = True
    include_position_info: bool = True
    include_desktop_info: bool = True
    track_sensitive_windows: bool = True
    sensitive_applications: List[str] = field(default_factory=lambda: [
        "password", "keychain", "vault", "secret", "banking", "crypto"
    ])
    blocked_applications: List[str] = field(default_factory=lambda: [
        "taskmgr", "regedit", "cmd", "powershell", "terminal"
    ])
    allowed_applications: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WindowFocusMonitor:
    """
    Window focus monitoring system for Lucid RDP.
    
    Provides:
    - Cross-platform window focus tracking
    - Window state monitoring
    - Application context tracking
    - Desktop/workspace monitoring
    - Security filtering and analysis
    """
    
    def __init__(self, config: WindowFocusMonitorConfig):
        self.config = config
        self.is_enabled = config.enabled
        
        # Event storage
        self.event_buffer: List[WindowEvent] = []
        self.event_callbacks: List[Callable] = []
        
        # Monitoring state
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        
        # Window tracking
        self.current_window: Optional[WindowInfo] = None
        self.previous_window: Optional[WindowInfo] = None
        self.window_focus_start: Optional[datetime] = None
        self.window_history: List[WindowInfo] = []
        
        # Statistics
        self.event_count = 0
        self.focus_changes = 0
        self.filtered_count = 0
        self.sensitive_count = 0
        
        # Create required directories
        self._create_directories()
        
        logger.info(f"Window Focus Monitor initialized for session: {config.session_id}")
    
    def _create_directories(self) -> None:
        """Create required directories for window monitoring"""
        directories = [
            WINDOW_LOG_PATH,
            WINDOW_CACHE_PATH,
            WINDOW_LOG_PATH / self.config.session_id,
            WINDOW_CACHE_PATH / self.config.session_id
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    async def start(self) -> bool:
        """Start the window focus monitor"""
        try:
            if not self.is_enabled:
                logger.info("Window focus monitor disabled")
                return True
            
            logger.info("Starting Window Focus Monitor...")
            
            # Start monitoring thread
            await self._start_monitoring()
            
            logger.info("Window Focus Monitor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Window Focus Monitor: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the window focus monitor"""
        try:
            logger.info("Stopping Window Focus Monitor...")
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Flush remaining events
            await self._flush_events()
            
            logger.info("Window Focus Monitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Window Focus Monitor: {e}")
            return False
    
    async def _start_monitoring(self) -> None:
        """Start window monitoring"""
        try:
            if self.monitor_running:
                return
            
            self.monitor_running = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_windows)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Window monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start window monitoring: {e}")
    
    async def _stop_monitoring(self) -> None:
        """Stop window monitoring"""
        try:
            self.monitor_running = False
            
            # Stop monitoring thread
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            logger.info("Window monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop window monitoring: {e}")
    
    def _monitor_windows(self) -> None:
        """Monitor windows (runs in separate thread)"""
        try:
            while self.monitor_running:
                try:
                    # Get current window
                    current_window = self._get_current_window()
                    
                    # Check for focus change
                    if self._has_window_changed(current_window):
                        self._handle_window_change(current_window)
                    
                    # Update current window
                    self.current_window = current_window
                    
                    time.sleep(self.config.monitor_interval)
                    
                except Exception as e:
                    logger.error(f"Window monitoring error: {e}")
                    time.sleep(1)
            
        except Exception as e:
            logger.error(f"Window monitoring thread error: {e}")
    
    def _get_current_window(self) -> Optional[WindowInfo]:
        """Get current active window information"""
        try:
            if sys.platform == "win32" and HAS_WIN32:
                return self._get_windows_window()
            elif sys.platform == "linux" and HAS_XLIB:
                return self._get_linux_window()
            elif sys.platform == "darwin" and HAS_QUARTZ:
                return self._get_macos_window()
            else:
                return self._get_generic_window()
                
        except Exception as e:
            logger.debug(f"Failed to get current window: {e}")
            return None
    
    def _get_windows_window(self) -> Optional[WindowInfo]:
        """Get window info on Windows"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            
            # Get window title
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get process info
            _, process_id = win32gui.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(process_id)
                process_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = "unknown"
            
            # Get window position and size
            rect = win32gui.GetWindowRect(hwnd)
            position = (rect[0], rect[1])
            size = (rect[2] - rect[0], rect[3] - rect[1])
            
            # Get window state
            window_state = WindowState.ACTIVE
            if win32gui.IsIconic(hwnd):
                window_state = WindowState.MINIMIZED
            
            return WindowInfo(
                window_id=hwnd,
                window_title=window_title,
                application_name=process_name,
                process_id=process_id,
                process_name=process_name,
                window_state=window_state,
                position=position,
                size=size,
                is_visible=True,
                is_focused=True,
                metadata={"platform": "windows"}
            )
            
        except Exception as e:
            logger.debug(f"Failed to get Windows window: {e}")
            return None
    
    def _get_linux_window(self) -> Optional[WindowInfo]:
        """Get window info on Linux"""
        try:
            # This would require X11 integration
            # For now, return basic info
            return WindowInfo(
                window_id=None,
                window_title="Linux Window",
                application_name="unknown",
                process_id=None,
                process_name="unknown",
                window_state=WindowState.ACTIVE,
                position=(0, 0),
                size=(0, 0),
                is_visible=True,
                is_focused=True,
                metadata={"platform": "linux"}
            )
            
        except Exception as e:
            logger.debug(f"Failed to get Linux window: {e}")
            return None
    
    def _get_macos_window(self) -> Optional[WindowInfo]:
        """Get window info on macOS"""
        try:
            # Get frontmost application
            frontmost_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if not frontmost_app:
                return None
            
            # Get application name
            application_name = frontmost_app.localizedName()
            
            # Get window info
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            
            # Find the frontmost window
            for window in window_list:
                if window.get('kCGWindowLayer', 0) == 0:  # Frontmost layer
                    window_title = window.get('kCGWindowName', '')
                    window_id = window.get('kCGWindowNumber', 0)
                    
                    # Get window bounds
                    bounds = window.get('kCGWindowBounds', {})
                    position = (bounds.get('X', 0), bounds.get('Y', 0))
                    size = (bounds.get('Width', 0), bounds.get('Height', 0))
                    
                    return WindowInfo(
                        window_id=window_id,
                        window_title=window_title,
                        application_name=application_name,
                        process_id=frontmost_app.processIdentifier(),
                        process_name=application_name,
                        window_state=WindowState.ACTIVE,
                        position=position,
                        size=size,
                        is_visible=True,
                        is_focused=True,
                        metadata={"platform": "macos"}
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get macOS window: {e}")
            return None
    
    def _get_generic_window(self) -> Optional[WindowInfo]:
        """Get generic window info when platform-specific methods fail"""
        try:
            return WindowInfo(
                window_id=None,
                window_title="Generic Window",
                application_name="unknown",
                process_id=None,
                process_name="unknown",
                window_state=WindowState.ACTIVE,
                position=(0, 0),
                size=(0, 0),
                is_visible=True,
                is_focused=True,
                metadata={"platform": "generic"}
            )
            
        except Exception:
            return None
    
    def _has_window_changed(self, current_window: Optional[WindowInfo]) -> bool:
        """Check if window has changed"""
        try:
            if not current_window:
                return False
            
            if not self.current_window:
                return True
            
            # Compare key properties
            return (
                current_window.window_id != self.current_window.window_id or
                current_window.window_title != self.current_window.window_title or
                current_window.application_name != self.current_window.application_name or
                current_window.process_id != self.current_window.process_id
            )
            
        except Exception:
            return False
    
    def _handle_window_change(self, current_window: Optional[WindowInfo]) -> None:
        """Handle window focus change"""
        try:
            if not current_window:
                return
            
            # Create window event
            event = self._create_window_event(
                event_type=WindowEventType.WINDOW_FOCUS,
                window_info=current_window,
                previous_window=self.current_window
            )
            
            if event:
                # Add to buffer
                self.event_buffer.append(event)
                self.event_count += 1
                self.focus_changes += 1
                
                # Update focus tracking
                if self.window_focus_start and self.current_window:
                    # Calculate duration
                    duration = (datetime.now(timezone.utc) - self.window_focus_start).total_seconds()
                    event.duration_ms = int(duration * 1000)
                
                # Update focus start time
                self.window_focus_start = datetime.now(timezone.utc)
                
                # Add to history
                self.window_history.append(current_window)
                if len(self.window_history) > 100:  # Keep last 100 windows
                    self.window_history = self.window_history[-100:]
                
                # Flush if buffer is full
                if len(self.event_buffer) >= self.config.batch_size:
                    asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Window change handling error: {e}")
    
    def _create_window_event(
        self,
        event_type: WindowEventType,
        window_info: WindowInfo,
        previous_window: Optional[WindowInfo]
    ) -> Optional[WindowEvent]:
        """Create a window event"""
        try:
            # Check if event should be filtered
            is_filtered = self._should_filter_event(window_info)
            
            # Check if window is sensitive
            is_sensitive = self._is_sensitive_window(window_info)
            
            # Create event
            event = WindowEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                window_info=window_info,
                previous_window=previous_window,
                is_sensitive=is_sensitive,
                is_filtered=is_filtered,
                metadata={}
            )
            
            # Calculate event hash
            event.hash = self._calculate_event_hash(event)
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to create window event: {e}")
            return None
    
    def _should_filter_event(self, window_info: WindowInfo) -> bool:
        """Check if event should be filtered"""
        try:
            # Check if application is blocked
            if window_info.application_name:
                for blocked_app in self.config.blocked_applications:
                    if blocked_app.lower() in window_info.application_name.lower():
                        return True
            
            # Check if application is in allowed list
            if self.config.allowed_applications:
                if window_info.application_name not in self.config.allowed_applications:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _is_sensitive_window(self, window_info: WindowInfo) -> bool:
        """Check if window is sensitive"""
        try:
            if not self.config.track_sensitive_windows:
                return False
            
            # Check application name
            if window_info.application_name:
                for sensitive_app in self.config.sensitive_applications:
                    if sensitive_app.lower() in window_info.application_name.lower():
                        return True
            
            # Check window title
            if window_info.window_title:
                for sensitive_app in self.config.sensitive_applications:
                    if sensitive_app.lower() in window_info.window_title.lower():
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _calculate_event_hash(self, event: WindowEvent) -> str:
        """Calculate hash for event integrity"""
        try:
            # Create hashable string from event data
            hash_data = f"{event.session_id}{event.timestamp.isoformat()}{event.event_type.value}"
            if event.window_info.window_id:
                hash_data += str(event.window_info.window_id)
            if event.window_info.window_title:
                hash_data += event.window_info.window_title
            if event.window_info.application_name:
                hash_data += event.window_info.application_name
            
            return hashlib.sha256(hash_data.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate event hash: {e}")
            return ""
    
    async def _flush_events(self) -> None:
        """Flush events to storage"""
        try:
            if not self.event_buffer:
                return
            
            # Filter events
            filtered_events = []
            for event in self.event_buffer:
                if not event.is_filtered:
                    filtered_events.append(event)
                else:
                    self.filtered_count += 1
                
                if event.is_sensitive:
                    self.sensitive_count += 1
            
            # Save to file
            await self._save_events_to_file(filtered_events)
            
            # Notify callbacks
            for event in filtered_events:
                await self._notify_callbacks("window_event", event)
            
            # Clear buffer
            self.event_buffer.clear()
            
            logger.debug(f"Flushed {len(filtered_events)} window events")
            
        except Exception as e:
            logger.error(f"Failed to flush window events: {e}")
    
    async def _save_events_to_file(self, events: List[WindowEvent]) -> None:
        """Save events to file"""
        try:
            if not events:
                return
            
            # Create events data
            events_data = [event.to_dict() for event in events]
            
            # Save to JSON file
            log_file = WINDOW_LOG_PATH / self.config.session_id / f"windows_{int(time.time())}.json"
            with open(log_file, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.debug(f"Saved {len(events)} window events to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save window events: {e}")
    
    async def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[WindowEvent]:
        """Get window events with filtering"""
        try:
            events = []
            
            # Load from files
            log_dir = WINDOW_LOG_PATH / self.config.session_id
            if log_dir.exists():
                for log_file in log_dir.glob("windows_*.json"):
                    try:
                        with open(log_file, 'r') as f:
                            file_events = json.load(f)
                        
                        for event_data in file_events:
                            event = WindowEvent.from_dict(event_data)
                            
                            # Apply time filters
                            if start_time and event.timestamp < start_time:
                                continue
                            if end_time and event.timestamp > end_time:
                                continue
                            
                            events.append(event)
                            
                    except Exception as e:
                        logger.error(f"Failed to load events from {log_file}: {e}")
            
            # Sort by timestamp and limit
            events.sort(key=lambda x: x.timestamp, reverse=True)
            return events[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get window events: {e}")
            return []
    
    async def get_current_window(self) -> Optional[WindowInfo]:
        """Get current active window"""
        return self.current_window
    
    async def get_window_history(self, limit: int = 50) -> List[WindowInfo]:
        """Get window history"""
        return self.window_history[-limit:] if self.window_history else []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        try:
            return {
                "session_id": self.config.session_id,
                "enabled": self.is_enabled,
                "event_count": self.event_count,
                "focus_changes": self.focus_changes,
                "filtered_count": self.filtered_count,
                "sensitive_count": self.sensitive_count,
                "buffer_size": len(self.event_buffer),
                "monitoring": self.monitor_running,
                "current_window": self.current_window.window_title if self.current_window else None,
                "window_history_count": len(self.window_history),
                "include_window_info": self.config.include_window_info,
                "include_process_info": self.config.include_process_info,
                "include_position_info": self.config.include_position_info,
                "include_desktop_info": self.config.include_desktop_info,
                "track_sensitive_windows": self.config.track_sensitive_windows
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    async def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify event callbacks"""
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in window callback: {e}")
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add an event callback"""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status"""
        return {
            "enabled": self.is_enabled,
            "session_id": self.config.session_id,
            "event_count": self.event_count,
            "focus_changes": self.focus_changes,
            "filtered_count": self.filtered_count,
            "sensitive_count": self.sensitive_count,
            "buffer_size": len(self.event_buffer),
            "monitoring": self.monitor_running,
            "current_window": self.current_window.window_title if self.current_window else None,
            "window_history_count": len(self.window_history),
            "psutil_available": HAS_PSUTIL,
            "xlib_available": HAS_XLIB,
            "win32_available": HAS_WIN32,
            "quartz_available": HAS_QUARTZ
        }


# Global Window Focus Monitor instance
_window_focus_monitor: Optional[WindowFocusMonitor] = None


def get_window_focus_monitor() -> Optional[WindowFocusMonitor]:
    """Get the global window focus monitor instance"""
    return _window_focus_monitor


async def initialize_window_focus_monitor(config: WindowFocusMonitorConfig) -> WindowFocusMonitor:
    """Initialize the global window focus monitor"""
    global _window_focus_monitor
    
    if _window_focus_monitor is None:
        _window_focus_monitor = WindowFocusMonitor(config)
        await _window_focus_monitor.start()
    
    return _window_focus_monitor


async def shutdown_window_focus_monitor() -> None:
    """Shutdown the global window focus monitor"""
    global _window_focus_monitor
    
    if _window_focus_monitor:
        await _window_focus_monitor.stop()
        _window_focus_monitor = None


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[window-focus-monitor] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = WindowFocusMonitorConfig(
        session_id="lucid_window_001",
        enabled=True,
        monitor_interval=1.0,
        max_events=10000,
        batch_size=100,
        include_window_info=True,
        include_process_info=True,
        include_position_info=True,
        include_desktop_info=True,
        track_sensitive_windows=True
    )
    
    # Initialize and start monitor
    monitor = await initialize_window_focus_monitor(config)
    
    try:
        # Keep monitor running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Window Focus Monitor...")
        await shutdown_window_focus_monitor()


if __name__ == "__main__":
    asyncio.run(main())

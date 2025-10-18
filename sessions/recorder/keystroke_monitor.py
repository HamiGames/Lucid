# Path: sessions/recorder/keystroke_monitor.py
# Lucid RDP Keystroke Monitor - Keystroke metadata capture
# Implements R-MUST-005: Session Audit Trail with keystroke metadata
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
import base64

# Keystroke monitoring imports
try:
    import pynput
    from pynput import keyboard
    from pynput.keyboard import Key, Listener
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False
    Key = None
    Listener = None

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
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)

# Configuration from environment
KEYSTROKE_LOG_PATH = Path(os.getenv("LUCID_KEYSTROKE_LOG_PATH", "/var/log/lucid/keystrokes"))
KEYSTROKE_CACHE_PATH = Path(os.getenv("LUCID_KEYSTROKE_CACHE_PATH", "/tmp/lucid/keystrokes"))
KEYSTROKE_MAX_EVENTS = int(os.getenv("LUCID_KEYSTROKE_MAX_EVENTS", "10000"))
KEYSTROKE_BATCH_SIZE = int(os.getenv("LUCID_KEYSTROKE_BATCH_SIZE", "100"))
KEYSTROKE_FLUSH_INTERVAL = int(os.getenv("LUCID_KEYSTROKE_FLUSH_INTERVAL", "30"))


class KeystrokeEventType(Enum):
    """Types of keystroke events"""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    KEY_COMBO = "key_combo"
    TEXT_INPUT = "text_input"
    SPECIAL_KEY = "special_key"
    MODIFIER_KEY = "modifier_key"


class KeystrokeSecurityLevel(Enum):
    """Keystroke monitoring security levels"""
    DISABLED = "disabled"      # No keystroke monitoring
    BASIC = "basic"           # Only special keys and modifiers
    MODERATE = "moderate"     # Key patterns without sensitive content
    STRICT = "strict"         # Full monitoring with content filtering
    COMPREHENSIVE = "comprehensive"  # Full monitoring including text content


@dataclass
class KeystrokeEvent:
    """Keystroke event data structure"""
    event_id: str
    session_id: str
    timestamp: datetime
    event_type: KeystrokeEventType
    key_code: Optional[int] = None
    key_name: Optional[str] = None
    key_char: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    window_title: Optional[str] = None
    window_class: Optional[str] = None
    application_name: Optional[str] = None
    process_id: Optional[int] = None
    thread_id: Optional[int] = None
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
            "key_code": self.key_code,
            "key_name": self.key_name,
            "key_char": self.key_char,
            "modifiers": self.modifiers,
            "window_title": self.window_title,
            "window_class": self.window_class,
            "application_name": self.application_name,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "duration_ms": self.duration_ms,
            "is_sensitive": self.is_sensitive,
            "is_filtered": self.is_filtered,
            "metadata": self.metadata,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KeystrokeEvent:
        """Create from dictionary"""
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=KeystrokeEventType(data["event_type"]),
            key_code=data.get("key_code"),
            key_name=data.get("key_name"),
            key_char=data.get("key_char"),
            modifiers=data.get("modifiers", []),
            window_title=data.get("window_title"),
            window_class=data.get("window_class"),
            application_name=data.get("application_name"),
            process_id=data.get("process_id"),
            thread_id=data.get("thread_id"),
            duration_ms=data.get("duration_ms"),
            is_sensitive=data.get("is_sensitive", False),
            is_filtered=data.get("is_filtered", False),
            metadata=data.get("metadata", {}),
            hash=data.get("hash")
        )


@dataclass
class KeystrokeMonitorConfig:
    """Keystroke monitor configuration"""
    session_id: str
    enabled: bool = True
    security_level: KeystrokeSecurityLevel = KeystrokeSecurityLevel.MODERATE
    max_events: int = KEYSTROKE_MAX_EVENTS
    batch_size: int = KEYSTROKE_BATCH_SIZE
    flush_interval: int = KEYSTROKE_FLUSH_INTERVAL
    include_text_content: bool = False
    include_special_keys: bool = True
    include_modifiers: bool = True
    include_window_info: bool = True
    include_process_info: bool = True
    filter_sensitive_content: bool = True
    sensitive_patterns: List[str] = field(default_factory=lambda: [
        r"password\s*[:=]\s*\w+",
        r"secret\s*[:=]\s*\w+",
        r"key\s*[:=]\s*\w+",
        r"token\s*[:=]\s*\w+",
        r"passphrase\s*[:=]\s*\w+",
        r"api[_-]?key\s*[:=]\s*\w+"
    ])
    blocked_applications: List[str] = field(default_factory=lambda: [
        "password", "keychain", "vault", "secret"
    ])
    allowed_applications: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class KeystrokeMonitor:
    """
    Keystroke monitoring system for Lucid RDP.
    
    Provides:
    - Cross-platform keystroke capture
    - Security filtering and content analysis
    - Window and application context tracking
    - Sensitive content detection
    - Real-time event processing
    """
    
    def __init__(self, config: KeystrokeMonitorConfig):
        self.config = config
        self.is_enabled = config.enabled and config.security_level != KeystrokeSecurityLevel.DISABLED
        
        # Event storage
        self.event_buffer: List[KeystrokeEvent] = []
        self.event_callbacks: List[Callable] = []
        
        # Monitoring state
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        self.keyboard_listener: Optional[Listener] = None
        
        # Key state tracking
        self.pressed_keys: Dict[str, float] = {}  # key_name -> press_time
        self.key_combinations: List[str] = []
        
        # Statistics
        self.event_count = 0
        self.filtered_count = 0
        self.sensitive_count = 0
        
        # Create required directories
        self._create_directories()
        
        logger.info(f"Keystroke Monitor initialized for session: {config.session_id}")
    
    def _create_directories(self) -> None:
        """Create required directories for keystroke monitoring"""
        directories = [
            KEYSTROKE_LOG_PATH,
            KEYSTROKE_CACHE_PATH,
            KEYSTROKE_LOG_PATH / self.config.session_id,
            KEYSTROKE_CACHE_PATH / self.config.session_id
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    async def start(self) -> bool:
        """Start the keystroke monitor"""
        try:
            if not self.is_enabled:
                logger.info("Keystroke monitor disabled")
                return True
            
            logger.info("Starting Keystroke Monitor...")
            
            # Start monitoring thread
            await self._start_monitoring()
            
            logger.info("Keystroke Monitor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Keystroke Monitor: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the keystroke monitor"""
        try:
            logger.info("Stopping Keystroke Monitor...")
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Flush remaining events
            await self._flush_events()
            
            logger.info("Keystroke Monitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Keystroke Monitor: {e}")
            return False
    
    async def _start_monitoring(self) -> None:
        """Start keystroke monitoring"""
        try:
            if self.monitor_running:
                return
            
            self.monitor_running = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_keystrokes)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Keystroke monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start keystroke monitoring: {e}")
    
    async def _stop_monitoring(self) -> None:
        """Stop keystroke monitoring"""
        try:
            self.monitor_running = False
            
            # Stop keyboard listener
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            
            # Stop monitoring thread
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            logger.info("Keystroke monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop keystroke monitoring: {e}")
    
    def _monitor_keystrokes(self) -> None:
        """Monitor keystrokes (runs in separate thread)"""
        try:
            if not HAS_PYNPUT:
                logger.warning("pynput not available, keystroke monitoring disabled")
                return
            
            # Create keyboard listener
            self.keyboard_listener = Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            
            # Start listening
            self.keyboard_listener.start()
            
            # Keep monitoring running
            while self.monitor_running:
                time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Keystroke monitoring error: {e}")
    
    def _on_key_press(self, key) -> None:
        """Handle key press event"""
        try:
            # Create keystroke event
            event = self._create_keystroke_event(
                event_type=KeystrokeEventType.KEY_PRESS,
                key=key,
                is_press=True
            )
            
            if event:
                # Add to buffer
                self.event_buffer.append(event)
                self.event_count += 1
                
                # Track key state
                key_name = self._get_key_name(key)
                self.pressed_keys[key_name] = time.time()
                
                # Check for key combinations
                self._check_key_combinations(key_name)
                
                # Flush if buffer is full
                if len(self.event_buffer) >= self.config.batch_size:
                    asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Key press handling error: {e}")
    
    def _on_key_release(self, key) -> None:
        """Handle key release event"""
        try:
            # Create keystroke event
            event = self._create_keystroke_event(
                event_type=KeystrokeEventType.KEY_RELEASE,
                key=key,
                is_press=False
            )
            
            if event:
                # Add to buffer
                self.event_buffer.append(event)
                self.event_count += 1
                
                # Update key state
                key_name = self._get_key_name(key)
                if key_name in self.pressed_keys:
                    press_time = self.pressed_keys[key_name]
                    duration = int((time.time() - press_time) * 1000)
                    event.duration_ms = duration
                    del self.pressed_keys[key_name]
                
                # Flush if buffer is full
                if len(self.event_buffer) >= self.config.batch_size:
                    asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Key release handling error: {e}")
    
    def _create_keystroke_event(
        self,
        event_type: KeystrokeEventType,
        key,
        is_press: bool
    ) -> Optional[KeystrokeEvent]:
        """Create a keystroke event from key data"""
        try:
            # Get key information
            key_name = self._get_key_name(key)
            key_code = self._get_key_code(key)
            key_char = self._get_key_char(key)
            
            # Get window information
            window_title, window_class, application_name = self._get_window_info()
            
            # Get process information
            process_id, thread_id = self._get_process_info()
            
            # Check if content is sensitive
            is_sensitive = self._is_sensitive_content(key_char, window_title, application_name)
            
            # Check if event should be filtered
            is_filtered = self._should_filter_event(key_name, key_char, application_name)
            
            # Create event
            event = KeystrokeEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                key_code=key_code,
                key_name=key_name,
                key_char=key_char,
                modifiers=self._get_current_modifiers(),
                window_title=window_title,
                window_class=window_class,
                application_name=application_name,
                process_id=process_id,
                thread_id=thread_id,
                is_sensitive=is_sensitive,
                is_filtered=is_filtered,
                metadata={}
            )
            
            # Calculate event hash
            event.hash = self._calculate_event_hash(event)
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to create keystroke event: {e}")
            return None
    
    def _get_key_name(self, key) -> str:
        """Get key name from key object"""
        try:
            if hasattr(key, 'name'):
                return key.name
            elif hasattr(key, 'char') and key.char:
                return key.char
            else:
                return str(key)
        except Exception:
            return "unknown"
    
    def _get_key_code(self, key) -> Optional[int]:
        """Get key code from key object"""
        try:
            if hasattr(key, 'vk'):
                return key.vk
            elif hasattr(key, 'value'):
                return key.value
            else:
                return None
        except Exception:
            return None
    
    def _get_key_char(self, key) -> Optional[str]:
        """Get key character from key object"""
        try:
            if hasattr(key, 'char') and key.char:
                return key.char
            else:
                return None
        except Exception:
            return None
    
    def _get_current_modifiers(self) -> List[str]:
        """Get currently pressed modifier keys"""
        try:
            modifiers = []
            
            # Check for common modifiers
            if hasattr(pynput.keyboard, 'Key'):
                if pynput.keyboard.Listener().is_pressed(pynput.keyboard.Key.ctrl):
                    modifiers.append("ctrl")
                if pynput.keyboard.Listener().is_pressed(pynput.keyboard.Key.alt):
                    modifiers.append("alt")
                if pynput.keyboard.Listener().is_pressed(pynput.keyboard.Key.shift):
                    modifiers.append("shift")
                if pynput.keyboard.Listener().is_pressed(pynput.keyboard.Key.cmd):
                    modifiers.append("cmd")
            
            return modifiers
            
        except Exception:
            return []
    
    def _get_window_info(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get current window information"""
        try:
            if sys.platform == "win32" and HAS_WIN32:
                return self._get_windows_window_info()
            elif sys.platform == "linux" and HAS_XLIB:
                return self._get_linux_window_info()
            elif sys.platform == "darwin":
                return self._get_macos_window_info()
            else:
                return None, None, None
                
        except Exception as e:
            logger.debug(f"Failed to get window info: {e}")
            return None, None, None
    
    def _get_windows_window_info(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get window info on Windows"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get process info
            _, process_id = win32gui.GetWindowThreadProcessId(hwnd)
            process = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, process_id)
            process_name = win32api.GetModuleFileNameEx(process, 0)
            
            return window_title, None, process_name
            
        except Exception:
            return None, None, None
    
    def _get_linux_window_info(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get window info on Linux"""
        try:
            # This would require X11 integration
            # For now, return basic info
            return None, None, None
            
        except Exception:
            return None, None, None
    
    def _get_macos_window_info(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get window info on macOS"""
        try:
            # This would require macOS-specific integration
            # For now, return basic info
            return None, None, None
            
        except Exception:
            return None, None, None
    
    def _get_process_info(self) -> tuple[Optional[int], Optional[int]]:
        """Get current process information"""
        try:
            import os
            return os.getpid(), threading.get_ident()
        except Exception:
            return None, None
    
    def _is_sensitive_content(
        self,
        key_char: Optional[str],
        window_title: Optional[str],
        application_name: Optional[str]
    ) -> bool:
        """Check if content is sensitive"""
        try:
            if not self.config.filter_sensitive_content:
                return False
            
            # Check key character
            if key_char:
                for pattern in self.config.sensitive_patterns:
                    import re
                    if re.search(pattern, key_char, re.IGNORECASE):
                        return True
            
            # Check window title
            if window_title:
                for pattern in self.config.sensitive_patterns:
                    import re
                    if re.search(pattern, window_title, re.IGNORECASE):
                        return True
            
            # Check application name
            if application_name:
                for blocked_app in self.config.blocked_applications:
                    if blocked_app.lower() in application_name.lower():
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _should_filter_event(
        self,
        key_name: str,
        key_char: Optional[str],
        application_name: Optional[str]
    ) -> bool:
        """Check if event should be filtered"""
        try:
            # Check security level
            if self.config.security_level == KeystrokeSecurityLevel.DISABLED:
                return True
            
            # Check if application is blocked
            if application_name:
                for blocked_app in self.config.blocked_applications:
                    if blocked_app.lower() in application_name.lower():
                        return True
            
            # Check if application is in allowed list
            if self.config.allowed_applications:
                if application_name not in self.config.allowed_applications:
                    return True
            
            # Check security level restrictions
            if self.config.security_level == KeystrokeSecurityLevel.BASIC:
                # Only allow special keys and modifiers
                if key_char and key_char.isalnum():
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _check_key_combinations(self, key_name: str) -> None:
        """Check for key combinations"""
        try:
            # Add to current combination
            self.key_combinations.append(key_name)
            
            # Keep only recent keys (last 10)
            if len(self.key_combinations) > 10:
                self.key_combinations = self.key_combinations[-10:]
            
            # Check for common combinations
            combo_str = "+".join(self.key_combinations[-3:])  # Last 3 keys
            
            # Log significant combinations
            if len(combo_str) > 5:  # Arbitrary threshold
                logger.debug(f"Key combination detected: {combo_str}")
            
        except Exception as e:
            logger.error(f"Key combination check error: {e}")
    
    def _calculate_event_hash(self, event: KeystrokeEvent) -> str:
        """Calculate hash for event integrity"""
        try:
            # Create hashable string from event data
            hash_data = f"{event.session_id}{event.timestamp.isoformat()}{event.event_type.value}{event.key_name}"
            if event.key_char:
                hash_data += event.key_char
            hash_data += str(event.key_code or 0)
            
            return hashlib.sha256(hash_data.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate event hash: {e}")
            return ""
    
    async def _flush_events(self) -> None:
        """Flush events to storage"""
        try:
            if not self.event_buffer:
                return
            
            # Filter events based on security level
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
                await self._notify_callbacks("keystroke_event", event)
            
            # Clear buffer
            self.event_buffer.clear()
            
            logger.debug(f"Flushed {len(filtered_events)} keystroke events")
            
        except Exception as e:
            logger.error(f"Failed to flush keystroke events: {e}")
    
    async def _save_events_to_file(self, events: List[KeystrokeEvent]) -> None:
        """Save events to file"""
        try:
            if not events:
                return
            
            # Create events data
            events_data = [event.to_dict() for event in events]
            
            # Save to JSON file
            log_file = KEYSTROKE_LOG_PATH / self.config.session_id / f"keystrokes_{int(time.time())}.json"
            with open(log_file, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.debug(f"Saved {len(events)} keystroke events to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save keystroke events: {e}")
    
    async def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[KeystrokeEvent]:
        """Get keystroke events with filtering"""
        try:
            events = []
            
            # Load from files
            log_dir = KEYSTROKE_LOG_PATH / self.config.session_id
            if log_dir.exists():
                for log_file in log_dir.glob("keystrokes_*.json"):
                    try:
                        with open(log_file, 'r') as f:
                            file_events = json.load(f)
                        
                        for event_data in file_events:
                            event = KeystrokeEvent.from_dict(event_data)
                            
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
            logger.error(f"Failed to get keystroke events: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        try:
            return {
                "session_id": self.config.session_id,
                "enabled": self.is_enabled,
                "security_level": self.config.security_level.value,
                "event_count": self.event_count,
                "filtered_count": self.filtered_count,
                "sensitive_count": self.sensitive_count,
                "buffer_size": len(self.event_buffer),
                "monitoring": self.monitor_running,
                "include_text_content": self.config.include_text_content,
                "include_special_keys": self.config.include_special_keys,
                "include_modifiers": self.config.include_modifiers,
                "include_window_info": self.config.include_window_info,
                "include_process_info": self.config.include_process_info,
                "filter_sensitive_content": self.config.filter_sensitive_content
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
                logger.error(f"Error in keystroke callback: {e}")
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add an event callback"""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status"""
        return {
            "enabled": self.is_enabled,
            "session_id": self.config.session_id,
            "security_level": self.config.security_level.value,
            "event_count": self.event_count,
            "filtered_count": self.filtered_count,
            "sensitive_count": self.sensitive_count,
            "buffer_size": len(self.event_buffer),
            "monitoring": self.monitor_running,
            "pynput_available": HAS_PYNPUT,
            "xlib_available": HAS_XLIB,
            "win32_available": HAS_WIN32
        }


# Global Keystroke Monitor instance
_keystroke_monitor: Optional[KeystrokeMonitor] = None


def get_keystroke_monitor() -> Optional[KeystrokeMonitor]:
    """Get the global keystroke monitor instance"""
    return _keystroke_monitor


async def initialize_keystroke_monitor(config: KeystrokeMonitorConfig) -> KeystrokeMonitor:
    """Initialize the global keystroke monitor"""
    global _keystroke_monitor
    
    if _keystroke_monitor is None:
        _keystroke_monitor = KeystrokeMonitor(config)
        await _keystroke_monitor.start()
    
    return _keystroke_monitor


async def shutdown_keystroke_monitor() -> None:
    """Shutdown the global keystroke monitor"""
    global _keystroke_monitor
    
    if _keystroke_monitor:
        await _keystroke_monitor.stop()
        _keystroke_monitor = None


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[keystroke-monitor] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = KeystrokeMonitorConfig(
        session_id="lucid_keystroke_001",
        enabled=True,
        security_level=KeystrokeSecurityLevel.MODERATE,
        max_events=10000,
        batch_size=100,
        flush_interval=30,
        include_text_content=False,
        include_special_keys=True,
        include_modifiers=True,
        include_window_info=True,
        include_process_info=True,
        filter_sensitive_content=True
    )
    
    # Initialize and start monitor
    monitor = await initialize_keystroke_monitor(config)
    
    try:
        # Keep monitor running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Keystroke Monitor...")
        await shutdown_keystroke_monitor()


if __name__ == "__main__":
    asyncio.run(main())

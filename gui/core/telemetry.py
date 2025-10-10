# Path: gui/core/telemetry.py
"""
Optional telemetry system for Lucid RDP GUI.
Provides anonymous usage statistics and crash reporting (disabled by default).
"""

import os
import json
import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone
import hashlib
import platform
import sys

logger = logging.getLogger(__name__)


class TelemetryLevel(Enum):
    """Telemetry data collection levels"""
    DISABLED = "disabled"      # No data collection
    BASIC = "basic"           # Basic usage statistics only
    STANDARD = "standard"     # Standard usage + performance metrics
    FULL = "full"            # Full telemetry including detailed diagnostics


class EventType(Enum):
    """Telemetry event types"""
    # Application events
    APP_START = "app_start"
    APP_SHUTDOWN = "app_shutdown"
    APP_CRASH = "app_crash"
    
    # User interaction events
    BUTTON_CLICK = "button_click"
    MENU_SELECT = "menu_select"
    DIALOG_OPEN = "dialog_open"
    DIALOG_CLOSE = "dialog_close"
    
    # Feature usage events
    FEATURE_USED = "feature_used"
    CONNECTION_ATTEMPT = "connection_attempt"
    CONNECTION_SUCCESS = "connection_success"
    CONNECTION_FAILED = "connection_failed"
    
    # Performance events
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_OCCURRED = "error_occurred"
    
    # Configuration events
    SETTING_CHANGED = "setting_changed"
    THEME_CHANGED = "theme_changed"


@dataclass
class TelemetryEvent:
    """Telemetry event data structure"""
    event_id: str
    event_type: str
    timestamp: float
    session_id: str
    user_id_hash: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class TelemetryConfig:
    """Telemetry configuration"""
    enabled: bool = False
    level: TelemetryLevel = TelemetryLevel.DISABLED
    endpoint_url: Optional[str] = None
    local_storage: bool = True
    crash_reporting: bool = False
    session_duration_tracking: bool = True
    feature_usage_tracking: bool = False
    performance_tracking: bool = False
    
    # Privacy settings
    anonymize_data: bool = True
    hash_user_data: bool = True
    include_system_info: bool = False
    include_location_data: bool = False
    
    # Storage settings
    max_local_events: int = 1000
    retention_days: int = 30
    batch_size: int = 50
    flush_interval: int = 300  # seconds


class TelemetryCollector:
    """Collects and manages telemetry data"""
    
    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig()
        self.session_id = self._generate_session_id()
        self.user_id_hash = self._generate_user_id_hash()
        self.events: List[TelemetryEvent] = []
        self.session_start_time = time.time()
        self._lock = threading.Lock()
        
        # Setup storage
        self.storage_dir = Path.home() / ".lucid" / "telemetry"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Event handlers
        self.event_handlers: List[Callable[[TelemetryEvent], None]] = []
        
        logger.debug(f"Telemetry collector initialized (enabled: {self.config.enabled})")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
    
    def _generate_user_id_hash(self) -> str:
        """Generate anonymous user ID hash"""
        if not self.config.hash_user_data:
            return "anonymous"
        
        # Create hash from system information
        system_info = f"{platform.system()}-{platform.machine()}-{platform.node()}"
        return hashlib.sha256(system_info.encode()).hexdigest()[:16]
    
    def add_event_handler(self, handler: Callable[[TelemetryEvent], None]) -> None:
        """Add custom event handler"""
        self.event_handlers.append(handler)
    
    def collect_event(self, 
                     event_type: EventType, 
                     data: Optional[Dict[str, Any]] = None,
                     level_required: TelemetryLevel = TelemetryLevel.BASIC) -> None:
        """
        Collect telemetry event.
        
        Args:
            event_type: Type of event to collect
            data: Additional event data
            level_required: Minimum telemetry level required for this event
        """
        if not self.config.enabled or self.config.level == TelemetryLevel.DISABLED:
            return
        
        if self.config.level.value < level_required.value:
            return
        
        if data is None:
            data = {}
        
        # Add common data
        common_data = {
            'platform': platform.system(),
            'python_version': sys.version.split()[0],
            'app_version': self._get_app_version(),
            'session_duration': time.time() - self.session_start_time
        }
        
        # Add system info if enabled
        if self.config.include_system_info:
            common_data.update({
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_implementation': platform.python_implementation()
            })
        
        # Merge data
        event_data = {**common_data, **data}
        
        # Create event
        event = TelemetryEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type.value,
            timestamp=time.time(),
            session_id=self.session_id,
            user_id_hash=self.user_id_hash,
            data=event_data
        )
        
        with self._lock:
            self.events.append(event)
            
            # Trim events if over limit
            if len(self.events) > self.config.max_local_events:
                self.events = self.events[-self.config.max_local_events:]
        
        # Notify handlers
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Telemetry event handler failed: {e}")
        
        logger.debug(f"Collected telemetry event: {event_type.value}")
    
    def collect_error(self, error: Exception, context: Optional[str] = None) -> None:
        """Collect error information"""
        if not self.config.crash_reporting:
            return
        
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        self.collect_event(EventType.ERROR_OCCURRED, error_data, TelemetryLevel.STANDARD)
    
    def collect_performance_metric(self, 
                                 metric_name: str, 
                                 value: float, 
                                 unit: str = "ms") -> None:
        """Collect performance metric"""
        if not self.config.performance_tracking:
            return
        
        metric_data = {
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        }
        
        self.collect_event(EventType.PERFORMANCE_METRIC, metric_data, TelemetryLevel.STANDARD)
    
    def collect_feature_usage(self, feature_name: str, action: str = "used") -> None:
        """Collect feature usage data"""
        if not self.config.feature_usage_tracking:
            return
        
        usage_data = {
            'feature_name': feature_name,
            'action': action
        }
        
        self.collect_event(EventType.FEATURE_USED, usage_data, TelemetryLevel.STANDARD)
    
    def save_events_to_file(self) -> None:
        """Save events to local file"""
        if not self.config.local_storage:
            return
        
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"telemetry_events_{timestamp}.json"
            filepath = self.storage_dir / filename
            
            with self._lock:
                events_data = [event.to_dict() for event in self.events]
            
            with open(filepath, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'user_id_hash': self.user_id_hash,
                    'timestamp': timestamp,
                    'events': events_data
                }, f, indent=2)
            
            logger.debug(f"Saved {len(events_data)} telemetry events to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save telemetry events: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary statistics"""
        with self._lock:
            event_counts = {}
            for event in self.events:
                event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
        
        return {
            'session_id': self.session_id,
            'user_id_hash': self.user_id_hash,
            'session_duration': time.time() - self.session_start_time,
            'total_events': len(self.events),
            'event_counts': event_counts,
            'config': asdict(self.config)
        }
    
    def clear_old_data(self) -> None:
        """Clear old telemetry data"""
        try:
            cutoff_time = time.time() - (self.config.retention_days * 24 * 3600)
            
            for file_path in self.storage_dir.glob("telemetry_events_*.json"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Removed old telemetry file: {file_path}")
                    
        except Exception as e:
            logger.error(f"Failed to clear old telemetry data: {e}")
    
    def _get_app_version(self) -> str:
        """Get application version"""
        # This would typically be imported from a version module
        return "1.0.0"
    
    def flush_events(self) -> None:
        """Flush events to storage or remote endpoint"""
        if self.config.local_storage:
            self.save_events_to_file()
        
        # Clear events after flushing
        with self._lock:
            self.events.clear()


class TelemetryManager:
    """Manages telemetry system lifecycle"""
    
    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig()
        self.collector: Optional[TelemetryCollector] = None
        self._flush_timer: Optional[threading.Timer] = None
        
        if self.config.enabled:
            self.start()
    
    def start(self) -> None:
        """Start telemetry collection"""
        if self.collector is not None:
            return
        
        self.collector = TelemetryCollector(self.config)
        
        # Start periodic flushing
        if self.config.flush_interval > 0:
            self._start_flush_timer()
        
        # Collect startup event
        self.collector.collect_event(EventType.APP_START)
        
        logger.info("Telemetry system started")
    
    def stop(self) -> None:
        """Stop telemetry collection"""
        if self.collector is None:
            return
        
        # Collect shutdown event
        self.collector.collect_event(EventType.APP_SHUTDOWN)
        
        # Flush remaining events
        self.collector.flush_events()
        
        # Stop flush timer
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None
        
        self.collector = None
        logger.info("Telemetry system stopped")
    
    def _start_flush_timer(self) -> None:
        """Start periodic flush timer"""
        def flush_and_reschedule():
            if self.collector:
                self.collector.flush_events()
                self._start_flush_timer()
        
        self._flush_timer = threading.Timer(self.config.flush_interval, flush_and_reschedule)
        self._flush_timer.start()
    
    def get_collector(self) -> Optional[TelemetryCollector]:
        """Get telemetry collector instance"""
        return self.collector
    
    def update_config(self, config: TelemetryConfig) -> None:
        """Update telemetry configuration"""
        was_enabled = self.config.enabled
        self.config = config
        
        if config.enabled and not was_enabled:
            self.start()
        elif not config.enabled and was_enabled:
            self.stop()
        elif self.collector:
            self.collector.config = config


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager(config: Optional[TelemetryConfig] = None) -> TelemetryManager:
    """Get global telemetry manager instance"""
    global _telemetry_manager
    
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager(config)
    
    return _telemetry_manager


def cleanup_telemetry_manager() -> None:
    """Cleanup global telemetry manager"""
    global _telemetry_manager
    
    if _telemetry_manager:
        _telemetry_manager.stop()
        _telemetry_manager = None


# Convenience functions for common telemetry operations
def track_event(event_type: EventType, data: Optional[Dict[str, Any]] = None) -> None:
    """Track a telemetry event"""
    manager = get_telemetry_manager()
    collector = manager.get_collector()
    
    if collector:
        collector.collect_event(event_type, data)


def track_error(error: Exception, context: Optional[str] = None) -> None:
    """Track an error"""
    manager = get_telemetry_manager()
    collector = manager.get_collector()
    
    if collector:
        collector.collect_error(error, context)


def track_performance(metric_name: str, value: float, unit: str = "ms") -> None:
    """Track a performance metric"""
    manager = get_telemetry_manager()
    collector = manager.get_collector()
    
    if collector:
        collector.collect_performance_metric(metric_name, value, unit)


def track_feature_usage(feature_name: str, action: str = "used") -> None:
    """Track feature usage"""
    manager = get_telemetry_manager()
    collector = manager.get_collector()
    
    if collector:
        collector.collect_feature_usage(feature_name, action)


# Context manager for automatic telemetry
class TelemetryContext:
    """Context manager for automatic telemetry tracking"""
    
    def __init__(self, event_type: EventType, data: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.data = data or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        track_event(self.event_type, {**self.data, 'action': 'start'})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        
        if exc_type:
            track_error(exc_val, f"Context: {self.event_type.value}")
            track_event(self.event_type, {**self.data, 'action': 'error', 'duration': duration})
        else:
            track_event(self.event_type, {**self.data, 'action': 'complete', 'duration': duration})


# Decorator for automatic telemetry
def track_function(event_type: EventType, include_args: bool = False):
    """Decorator to automatically track function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            data = {}
            if include_args:
                data['function'] = func.__name__
                data['args_count'] = len(args)
                data['kwargs_count'] = len(kwargs)
            
            with TelemetryContext(event_type, data):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

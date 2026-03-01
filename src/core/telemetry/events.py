"""
Event tracking and logging system for Lucid telemetry.

This module provides comprehensive event tracking functionality including:
- Structured logging with correlation IDs
- Event correlation and tracing
- Audit trails and compliance logging
- Performance event tracking
- Security event monitoring
- Custom event handlers
- Event aggregation and filtering
"""

import asyncio
import logging
import json
import time
import uuid
import hashlib
from typing import Optional, Dict, List, Tuple, Any, Union, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import aiofiles
import structlog
from contextvars import ContextVar
from collections import defaultdict, deque

# Configure logging
logger = logging.getLogger(__name__)

# Context variables for correlation
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)

class EventLevel(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class EventCategory(Enum):
    """Event categories for classification."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    BUSINESS = "business"
    SYSTEM = "system"
    USER = "user"
    API = "api"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"

class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    IGNORED = "ignored"

@dataclass
class EventMetadata:
    """Event metadata container."""
    source: str
    version: str
    environment: str
    service: str
    hostname: str
    ip_address: str
    user_agent: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EventContext:
    """Event context information."""
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    action: Optional[str] = None

@dataclass
class TelemetryEvent:
    """Telemetry event data structure."""
    id: str
    timestamp: datetime
    level: EventLevel
    category: EventCategory
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: EventMetadata = field(default_factory=lambda: EventMetadata("", "", "", "", ""))
    context: EventContext = field(default_factory=EventContext)
    status: EventStatus = EventStatus.PENDING
    processing_time: Optional[float] = None
    error: Optional[str] = None
    correlation_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'category': self.category.value,
            'message': self.message,
            'data': self.data,
            'metadata': {
                'source': self.metadata.source,
                'version': self.metadata.version,
                'environment': self.metadata.environment,
                'service': self.metadata.service,
                'hostname': self.metadata.hostname,
                'ip_address': self.metadata.ip_address,
                'user_agent': self.metadata.user_agent,
                'tags': self.metadata.tags,
                'custom_fields': self.metadata.custom_fields
            },
            'context': {
                'correlation_id': self.context.correlation_id,
                'request_id': self.context.request_id,
                'user_id': self.context.user_id,
                'session_id': self.context.session_id,
                'trace_id': self.context.trace_id,
                'span_id': self.context.span_id,
                'parent_span_id': self.context.parent_span_id,
                'operation': self.context.operation,
                'component': self.context.component,
                'action': self.context.action
            },
            'status': self.status.value,
            'processing_time': self.processing_time,
            'error': self.error,
            'correlation_events': self.correlation_events
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TelemetryEvent':
        """Create from dictionary."""
        event = cls(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            level=EventLevel(data['level']),
            category=EventCategory(data['category']),
            message=data['message'],
            data=data.get('data', {}),
            status=EventStatus(data.get('status', 'pending'))
        )
        
        # Set metadata
        meta_data = data.get('metadata', {})
        event.metadata = EventMetadata(
            source=meta_data.get('source', ''),
            version=meta_data.get('version', ''),
            environment=meta_data.get('environment', ''),
            service=meta_data.get('service', ''),
            hostname=meta_data.get('hostname', ''),
            ip_address=meta_data.get('ip_address', ''),
            user_agent=meta_data.get('user_agent'),
            tags=meta_data.get('tags', []),
            custom_fields=meta_data.get('custom_fields', {})
        )
        
        # Set context
        context_data = data.get('context', {})
        event.context = EventContext(
            correlation_id=context_data.get('correlation_id'),
            request_id=context_data.get('request_id'),
            user_id=context_data.get('user_id'),
            session_id=context_data.get('session_id'),
            trace_id=context_data.get('trace_id'),
            span_id=context_data.get('span_id'),
            parent_span_id=context_data.get('parent_span_id'),
            operation=context_data.get('operation'),
            component=context_data.get('component'),
            action=context_data.get('action')
        )
        
        event.processing_time = data.get('processing_time')
        event.error = data.get('error')
        event.correlation_events = data.get('correlation_events', [])
        
        return event

class EventFilter:
    """Event filter for processing and routing."""
    
    def __init__(self, 
                 categories: Optional[Set[EventCategory]] = None,
                 levels: Optional[Set[EventLevel]] = None,
                 services: Optional[Set[str]] = None,
                 components: Optional[Set[str]] = None,
                 tags: Optional[Set[str]] = None,
                 custom_filter: Optional[Callable[[TelemetryEvent], bool]] = None):
        self.categories = categories or set()
        self.levels = levels or set()
        self.services = services or set()
        self.components = components or set()
        self.tags = tags or set()
        self.custom_filter = custom_filter
    
    def matches(self, event: TelemetryEvent) -> bool:
        """Check if event matches filter criteria."""
        if self.categories and event.category not in self.categories:
            return False
        if self.levels and event.level not in self.levels:
            return False
        if self.services and event.metadata.service not in self.services:
            return False
        if self.components and event.context.component not in self.components:
            return False
        if self.tags and not any(tag in event.metadata.tags for tag in self.tags):
            return False
        if self.custom_filter and not self.custom_filter(event):
            return False
        return True

class EventHandler:
    """Base event handler interface."""
    
    def __init__(self, name: str, filter: Optional[EventFilter] = None):
        self.name = name
        self.filter = filter
        self.enabled = True
        self.processed_count = 0
        self.error_count = 0
    
    async def handle_event(self, event: TelemetryEvent) -> bool:
        """Handle a telemetry event."""
        if not self.enabled:
            return False
        
        if self.filter and not self.filter.matches(event):
            return False
        
        try:
            await self._process_event(event)
            self.processed_count += 1
            return True
        except Exception as e:
            self.error_count += 1
            logger.error(f"Event handler {self.name} failed: {e}")
            return False
    
    async def _process_event(self, event: TelemetryEvent):
        """Process the event (to be implemented by subclasses)."""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'success_rate': (self.processed_count / (self.processed_count + self.error_count) * 100) 
                          if (self.processed_count + self.error_count) > 0 else 0.0
        }

class LogEventHandler(EventHandler):
    """Event handler that logs events."""
    
    def __init__(self, name: str = "log_handler", 
                 logger_name: Optional[str] = None,
                 filter: Optional[EventFilter] = None):
        super().__init__(name, filter)
        self.logger = logging.getLogger(logger_name or __name__)
        self.structured_logger = structlog.get_logger()
    
    async def _process_event(self, event: TelemetryEvent):
        """Log the event."""
        log_data = {
            'event_id': event.id,
            'level': event.level.value,
            'category': event.category.value,
            'message': event.message,
            'correlation_id': event.context.correlation_id,
            'request_id': event.context.request_id,
            'user_id': event.context.user_id,
            'session_id': event.context.session_id,
            'component': event.context.component,
            'operation': event.context.operation,
            'service': event.metadata.service,
            'hostname': event.metadata.hostname,
            'tags': event.metadata.tags,
            'data': event.data
        }
        
        if event.level == EventLevel.DEBUG:
            self.structured_logger.debug(event.message, **log_data)
        elif event.level == EventLevel.INFO:
            self.structured_logger.info(event.message, **log_data)
        elif event.level == EventLevel.WARNING:
            self.structured_logger.warning(event.message, **log_data)
        elif event.level == EventLevel.ERROR:
            self.structured_logger.error(event.message, **log_data)
        elif event.level == EventLevel.CRITICAL:
            self.structured_logger.critical(event.message, **log_data)

class FileEventHandler(EventHandler):
    """Event handler that writes events to file."""
    
    def __init__(self, name: str = "file_handler",
                 file_path: str = "events.log",
                 filter: Optional[EventFilter] = None,
                 rotation_size: int = 100 * 1024 * 1024,  # 100MB
                 max_files: int = 5):
        super().__init__(name, filter)
        self.file_path = Path(file_path)
        self.rotation_size = rotation_size
        self.max_files = max_files
        self.current_size = 0
        self._file_handle = None
    
    async def _process_event(self, event: TelemetryEvent):
        """Write event to file."""
        await self._ensure_file_open()
        
        event_json = json.dumps(event.to_dict()) + '\n'
        await self._file_handle.write(event_json.encode())
        await self._file_handle.flush()
        
        self.current_size += len(event_json)
        
        if self.current_size >= self.rotation_size:
            await self._rotate_file()
    
    async def _ensure_file_open(self):
        """Ensure file is open for writing."""
        if self._file_handle is None:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = await aiofiles.open(self.file_path, 'ab')
            self.current_size = self.file_path.stat().st_size if self.file_path.exists() else 0
    
    async def _rotate_file(self):
        """Rotate log file."""
        if self._file_handle:
            await self._file_handle.close()
            self._file_handle = None
        
        # Rotate existing files
        for i in range(self.max_files - 1, 0, -1):
            old_file = self.file_path.with_suffix(f'.{i}')
            new_file = self.file_path.with_suffix(f'.{i + 1}')
            if old_file.exists():
                old_file.rename(new_file)
        
        # Move current file to .1
        if self.file_path.exists():
            self.file_path.rename(self.file_path.with_suffix('.1'))
        
        self.current_size = 0

class EventAggregator:
    """Event aggregator for batch processing and analytics."""
    
    def __init__(self, window_size: int = 100, window_time: int = 60):
        self.window_size = window_size
        self.window_time = window_time
        self.events: deque = deque(maxlen=window_size)
        self.window_start = time.time()
        self.aggregated_stats: Dict[str, Any] = defaultdict(int)
    
    def add_event(self, event: TelemetryEvent):
        """Add event to aggregation window."""
        self.events.append(event)
        self._update_stats(event)
    
    def _update_stats(self, event: TelemetryEvent):
        """Update aggregation statistics."""
        key = f"{event.category.value}:{event.level.value}"
        self.aggregated_stats[key] += 1
        self.aggregated_stats[f"total_{event.category.value}"] += 1
        self.aggregated_stats[f"total_{event.level.value}"] += 1
        self.aggregated_stats['total_events'] += 1
    
    def get_window_stats(self) -> Dict[str, Any]:
        """Get current window statistics."""
        current_time = time.time()
        window_duration = current_time - self.window_start
        
        stats = {
            'window_duration': window_duration,
            'event_count': len(self.events),
            'events_per_second': len(self.events) / window_duration if window_duration > 0 else 0,
            'stats': dict(self.aggregated_stats)
        }
        
        # Reset window if time exceeded
        if window_duration >= self.window_time:
            self.events.clear()
            self.aggregated_stats.clear()
            self.window_start = current_time
        
        return stats
    
    def should_flush(self) -> bool:
        """Check if aggregation window should be flushed."""
        return (len(self.events) >= self.window_size or 
                time.time() - self.window_start >= self.window_time)

class EventCorrelator:
    """Event correlator for finding related events."""
    
    def __init__(self, correlation_window: int = 300):  # 5 minutes
        self.correlation_window = correlation_window
        self.events_by_correlation: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self.events_by_user: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self.events_by_session: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self.events_by_request: Dict[str, List[TelemetryEvent]] = defaultdict(list)
    
    def add_event(self, event: TelemetryEvent):
        """Add event for correlation."""
        now = time.time()
        
        # Add to correlation groups
        if event.context.correlation_id:
            self.events_by_correlation[event.context.correlation_id].append(event)
        
        if event.context.user_id:
            self.events_by_user[event.context.user_id].append(event)
        
        if event.context.session_id:
            self.events_by_session[event.context.session_id].append(event)
        
        if event.context.request_id:
            self.events_by_request[event.context.request_id].append(event)
        
        # Clean up old events
        self._cleanup_old_events(now)
    
    def _cleanup_old_events(self, current_time: float):
        """Remove events older than correlation window."""
        cutoff_time = current_time - self.correlation_window
        
        for event_list in [self.events_by_correlation, self.events_by_user, 
                          self.events_by_session, self.events_by_request]:
            for key, events in list(event_list.items()):
                # Filter out old events
                filtered_events = [
                    event for event in events 
                    if event.timestamp.timestamp() > cutoff_time
                ]
                if filtered_events:
                    event_list[key] = filtered_events
                else:
                    del event_list[key]
    
    def get_correlated_events(self, event: TelemetryEvent) -> Dict[str, List[TelemetryEvent]]:
        """Get events correlated with the given event."""
        correlated = {}
        
        if event.context.correlation_id:
            correlated['correlation_id'] = self.events_by_correlation.get(
                event.context.correlation_id, []
            )
        
        if event.context.user_id:
            correlated['user_id'] = self.events_by_user.get(event.context.user_id, [])
        
        if event.context.session_id:
            correlated['session_id'] = self.events_by_session.get(
                event.context.session_id, []
            )
        
        if event.context.request_id:
            correlated['request_id'] = self.events_by_request.get(
                event.context.request_id, []
            )
        
        return correlated

class EventProcessor:
    """Main event processor for telemetry events."""
    
    def __init__(self, 
                 metadata: Optional[EventMetadata] = None,
                 enable_correlation: bool = True,
                 enable_aggregation: bool = True):
        self.metadata = metadata or self._create_default_metadata()
        self.handlers: List[EventHandler] = []
        self.correlator = EventCorrelator() if enable_correlation else None
        self.aggregator = EventAggregator() if enable_aggregation else None
        self.processing_stats = {
            'total_events': 0,
            'processed_events': 0,
            'failed_events': 0,
            'start_time': datetime.now(timezone.utc)
        }
    
    def _create_default_metadata(self) -> EventMetadata:
        """Create default metadata."""
        import socket
        import platform
        
        return EventMetadata(
            source="lucid-core",
            version="1.0.0",
            environment="development",
            service="telemetry",
            hostname=platform.node(),
            ip_address=socket.gethostbyname(socket.gethostname()),
            tags=["telemetry", "core"]
        )
    
    def add_handler(self, handler: EventHandler):
        """Add event handler."""
        self.handlers.append(handler)
        logger.info(f"Added event handler: {handler.name}")
    
    def remove_handler(self, handler_name: str) -> bool:
        """Remove event handler by name."""
        for i, handler in enumerate(self.handlers):
            if handler.name == handler_name:
                del self.handlers[i]
                logger.info(f"Removed event handler: {handler_name}")
                return True
        return False
    
    async def emit_event(self, 
                        level: EventLevel,
                        category: EventCategory,
                        message: str,
                        data: Optional[Dict[str, Any]] = None,
                        context: Optional[EventContext] = None) -> str:
        """Emit a telemetry event."""
        event_id = str(uuid.uuid4())
        
        # Create event context with correlation info
        event_context = context or EventContext()
        if not event_context.correlation_id:
            event_context.correlation_id = correlation_id.get()
        if not event_context.request_id:
            event_context.request_id = request_id.get()
        if not event_context.user_id:
            event_context.user_id = user_id.get()
        if not event_context.session_id:
            event_context.session_id = session_id.get()
        
        # Create event
        event = TelemetryEvent(
            id=event_id,
            timestamp=datetime.now(timezone.utc),
            level=level,
            category=category,
            message=message,
            data=data or {},
            metadata=self.metadata,
            context=event_context
        )
        
        # Process event
        await self._process_event(event)
        
        return event_id
    
    async def _process_event(self, event: TelemetryEvent):
        """Process a telemetry event."""
        start_time = time.time()
        self.processing_stats['total_events'] += 1
        
        try:
            # Add to correlator
            if self.correlator:
                self.correlator.add_event(event)
            
            # Add to aggregator
            if self.aggregator:
                self.aggregator.add_event(event)
            
            # Process with handlers
            processed = False
            for handler in self.handlers:
                try:
                    if await handler.handle_event(event):
                        processed = True
                except Exception as e:
                    logger.error(f"Handler {handler.name} failed: {e}")
            
            event.status = EventStatus.COMPLETED if processed else EventStatus.IGNORED
            self.processing_stats['processed_events'] += 1
            
        except Exception as e:
            event.status = EventStatus.FAILED
            event.error = str(e)
            self.processing_stats['failed_events'] += 1
            logger.error(f"Event processing failed: {e}")
        
        finally:
            event.processing_time = time.time() - start_time
    
    def get_correlated_events(self, event_id: str) -> Optional[Dict[str, List[TelemetryEvent]]]:
        """Get events correlated with the given event ID."""
        if not self.correlator:
            return None
        
        # Find the event by ID (simplified - in production, use proper storage)
        for events in [self.correlator.events_by_correlation, self.correlator.events_by_user,
                      self.correlator.events_by_session, self.correlator.events_by_request]:
            for event_list in events.values():
                for event in event_list:
                    if event.id == event_id:
                        return self.correlator.get_correlated_events(event)
        return None
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        uptime = datetime.now(timezone.utc) - self.processing_stats['start_time']
        events_per_second = (self.processing_stats['processed_events'] / 
                           uptime.total_seconds()) if uptime.total_seconds() > 0 else 0
        
        stats = {
            'uptime_seconds': uptime.total_seconds(),
            'total_events': self.processing_stats['total_events'],
            'processed_events': self.processing_stats['processed_events'],
            'failed_events': self.processing_stats['failed_events'],
            'events_per_second': events_per_second,
            'handler_stats': [handler.get_stats() for handler in self.handlers]
        }
        
        if self.aggregator:
            stats['aggregation_stats'] = self.aggregator.get_window_stats()
        
        return stats

# Global event processor instance
_event_processor: Optional[EventProcessor] = None

def get_event_processor() -> EventProcessor:
    """Get the global event processor instance."""
    global _event_processor
    if _event_processor is None:
        _event_processor = EventProcessor()
        # Add default handlers
        _event_processor.add_handler(LogEventHandler())
    return _event_processor

def initialize_event_processor(metadata: Optional[EventMetadata] = None,
                             enable_correlation: bool = True,
                             enable_aggregation: bool = True) -> EventProcessor:
    """Initialize the global event processor."""
    global _event_processor
    if _event_processor is None:
        _event_processor = EventProcessor(metadata, enable_correlation, enable_aggregation)
        # Add default handlers
        _event_processor.add_handler(LogEventHandler())
    return _event_processor

def set_correlation_id(corr_id: str):
    """Set correlation ID in context."""
    correlation_id.set(corr_id)

def set_request_id(req_id: str):
    """Set request ID in context."""
    request_id.set(req_id)

def set_user_id(uid: str):
    """Set user ID in context."""
    user_id.set(uid)

def set_session_id(sess_id: str):
    """Set session ID in context."""
    session_id.set(sess_id)

def create_event_context(correlation_id: Optional[str] = None,
                        request_id: Optional[str] = None,
                        user_id: Optional[str] = None,
                        session_id: Optional[str] = None,
                        trace_id: Optional[str] = None,
                        span_id: Optional[str] = None,
                        parent_span_id: Optional[str] = None,
                        operation: Optional[str] = None,
                        component: Optional[str] = None,
                        action: Optional[str] = None) -> EventContext:
    """Create event context."""
    return EventContext(
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=user_id,
        session_id=session_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        operation=operation,
        component=component,
        action=action
    )

def create_event_metadata(source: str,
                         version: str,
                         environment: str,
                         service: str,
                         hostname: str,
                         ip_address: str,
                         user_agent: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         custom_fields: Optional[Dict[str, Any]] = None) -> EventMetadata:
    """Create event metadata."""
    return EventMetadata(
        source=source,
        version=version,
        environment=environment,
        service=service,
        hostname=hostname,
        ip_address=ip_address,
        user_agent=user_agent,
        tags=tags or [],
        custom_fields=custom_fields or {}
    )

# Convenience functions for common event types
async def log_debug(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log debug event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.DEBUG, EventCategory.SYSTEM, message, data, **kwargs)

async def log_info(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log info event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.INFO, EventCategory.SYSTEM, message, data, **kwargs)

async def log_warning(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log warning event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.WARNING, EventCategory.SYSTEM, message, data, **kwargs)

async def log_error(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log error event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.ERROR, EventCategory.SYSTEM, message, data, **kwargs)

async def log_critical(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log critical event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.CRITICAL, EventCategory.SYSTEM, message, data, **kwargs)

async def log_security_event(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log security event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.INFO, EventCategory.SECURITY, message, data, **kwargs)

async def log_performance_event(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log performance event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.INFO, EventCategory.PERFORMANCE, message, data, **kwargs)

async def log_audit_event(message: str, data: Optional[Dict[str, Any]] = None, **kwargs):
    """Log audit event."""
    processor = get_event_processor()
    return await processor.emit_event(EventLevel.INFO, EventCategory.AUDIT, message, data, **kwargs)

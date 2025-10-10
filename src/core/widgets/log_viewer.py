"""
Log viewing and management widgets for Lucid GUI applications.

This module provides comprehensive log viewing functionality including:
- Real-time log streaming
- Log filtering and search
- Log level filtering
- Log formatting and display
- Log export capabilities
- Log rotation handling
- Performance monitoring
"""

import asyncio
import logging
import time
import re
import json
import threading
from typing import Any, Dict, List, Optional, Union, Callable, Set, Iterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import queue
import gzip
import bz2
from collections import deque

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Log format enumeration."""
    PLAIN = "plain"
    JSON = "json"
    STRUCTURED = "structured"
    CUSTOM = "custom"


class FilterType(Enum):
    """Filter type enumeration."""
    CONTAINS = "contains"
    REGEX = "regex"
    EXACT = "exact"
    LEVEL = "level"
    TIMESTAMP = "timestamp"
    SOURCE = "source"


@dataclass
class LogEntry:
    """Log entry data structure."""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str
    thread_id: Optional[str] = None
    process_id: Optional[int] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    raw_line: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'source': self.source,
            'thread_id': self.thread_id,
            'process_id': self.process_id,
            'extra_data': self.extra_data,
            'raw_line': self.raw_line
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        data['level'] = LogLevel(data['level'])
        return cls(**data)


@dataclass
class LogFilter:
    """Log filter configuration."""
    filter_type: FilterType
    value: str
    case_sensitive: bool = False
    invert: bool = False
    enabled: bool = True


@dataclass
class LogViewerConfig:
    """Log viewer configuration."""
    max_entries: int = 10000
    refresh_interval: float = 0.1
    auto_scroll: bool = True
    show_timestamps: bool = True
    show_levels: bool = True
    show_sources: bool = True
    colorize_output: bool = True
    word_wrap: bool = True
    font_family: str = "monospace"
    font_size: int = 12
    theme: str = "dark"


class LogParser:
    """Log parser for different formats."""
    
    def __init__(self, log_format: LogFormat = LogFormat.PLAIN):
        self.log_format = log_format
        self.patterns = {
            LogFormat.PLAIN: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] (.+)$',
            LogFormat.STRUCTURED: r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z) (\w+) (\w+) (.+)$',
            LogFormat.JSON: r'^{.*}$'
        }
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a log line into LogEntry."""
        line = line.strip()
        if not line:
            return None
        
        try:
            if self.log_format == LogFormat.JSON:
                return self._parse_json_line(line)
            else:
                return self._parse_structured_line(line)
        except Exception as e:
            logger.debug(f"Failed to parse log line: {e}")
            return LogEntry(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                message=line,
                source="unknown",
                raw_line=line
            )
    
    def _parse_structured_line(self, line: str) -> Optional[LogEntry]:
        """Parse structured log line."""
        pattern = self.patterns.get(self.log_format)
        if not pattern:
            return None
        
        match = re.match(pattern, line)
        if not match:
            return None
        
        if self.log_format == LogFormat.PLAIN:
            timestamp_str, level_str, message = match.groups()
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
            level = LogLevel(level_str)
            source = "unknown"
        else:  # STRUCTURED
            timestamp_str, level_str, source, message = match.groups()
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            level = LogLevel(level_str)
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=source,
            raw_line=line
        )
    
    def _parse_json_line(self, line: str) -> Optional[LogEntry]:
        """Parse JSON log line."""
        try:
            data = json.loads(line)
            timestamp = datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00'))
            level = LogLevel(data.get('level', 'INFO'))
            message = data.get('message', '')
            source = data.get('source', 'unknown')
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=source,
                extra_data=data,
                raw_line=line
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse JSON log line: {e}")
            return None


class LogFilter:
    """Log filter implementation."""
    
    def __init__(self):
        self.filters: List[LogFilter] = []
        self.enabled_levels: Set[LogLevel] = set(LogLevel)
    
    def add_filter(self, filter_config: LogFilter):
        """Add a filter."""
        self.filters.append(filter_config)
    
    def remove_filter(self, index: int):
        """Remove a filter by index."""
        if 0 <= index < len(self.filters):
            del self.filters[index]
    
    def clear_filters(self):
        """Clear all filters."""
        self.filters.clear()
    
    def set_level_filter(self, levels: Set[LogLevel]):
        """Set level filter."""
        self.enabled_levels = levels
    
    def matches(self, entry: LogEntry) -> bool:
        """Check if log entry matches filters."""
        # Check level filter
        if entry.level not in self.enabled_levels:
            return False
        
        # Check other filters
        for filter_config in self.filters:
            if not filter_config.enabled:
                continue
            
            matches = self._check_filter(entry, filter_config)
            if filter_config.invert:
                matches = not matches
            
            if not matches:
                return False
        
        return True
    
    def _check_filter(self, entry: LogEntry, filter_config: LogFilter) -> bool:
        """Check if entry matches a specific filter."""
        if filter_config.filter_type == FilterType.CONTAINS:
            text = entry.message
            if not filter_config.case_sensitive:
                text = text.lower()
                value = filter_config.value.lower()
            else:
                value = filter_config.value
            return value in text
        
        elif filter_config.filter_type == FilterType.REGEX:
            flags = 0 if filter_config.case_sensitive else re.IGNORECASE
            return bool(re.search(filter_config.value, entry.message, flags))
        
        elif filter_config.filter_type == FilterType.EXACT:
            text = entry.message
            if not filter_config.case_sensitive:
                text = text.lower()
                value = filter_config.value.lower()
            else:
                value = filter_config.value
            return text == value
        
        elif filter_config.filter_type == FilterType.LEVEL:
            return entry.level == LogLevel(filter_config.value)
        
        elif filter_config.filter_type == FilterType.SOURCE:
            return entry.source == filter_config.value
        
        elif filter_config.filter_type == FilterType.TIMESTAMP:
            # Parse timestamp range
            try:
                start_str, end_str = filter_config.value.split(' - ')
                start_time = datetime.fromisoformat(start_str)
                end_time = datetime.fromisoformat(end_str)
                return start_time <= entry.timestamp <= end_time
            except ValueError:
                return False
        
        return True


class LogStreamer:
    """Log streamer for real-time log monitoring."""
    
    def __init__(self, log_file: Union[str, Path], parser: LogParser):
        self.log_file = Path(log_file)
        self.parser = parser
        self.running = False
        self.position = 0
        self.callbacks: List[Callable[[LogEntry], None]] = []
        self._task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
    
    def add_callback(self, callback: Callable[[LogEntry], None]):
        """Add log entry callback."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[LogEntry], None]):
        """Remove log entry callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start(self):
        """Start log streaming."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._stream_loop())
        logger.info(f"Started log streaming from {self.log_file}")
    
    async def stop(self):
        """Stop log streaming."""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped log streaming from {self.log_file}")
    
    async def _stream_loop(self):
        """Main streaming loop."""
        while self.running:
            try:
                await self._read_new_lines()
                await asyncio.sleep(0.1)  # Small delay to prevent excessive CPU usage
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in log streaming loop: {e}")
                await asyncio.sleep(1)
    
    async def _read_new_lines(self):
        """Read new lines from log file."""
        if not self.log_file.exists():
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.position)
                new_lines = f.readlines()
                self.position = f.tell()
                
                for line in new_lines:
                    entry = self.parser.parse_line(line)
                    if entry:
                        await self._notify_callbacks(entry)
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
    
    async def _notify_callbacks(self, entry: LogEntry):
        """Notify all callbacks of new log entry."""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(entry)
                else:
                    callback(entry)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")


class LogViewer:
    """Main log viewer widget."""
    
    def __init__(self, config: LogViewerConfig = None):
        self.config = config or LogViewerConfig()
        self.entries: deque = deque(maxlen=self.config.max_entries)
        self.filter = LogFilter()
        self.parser = LogParser()
        self.streamers: List[LogStreamer] = []
        self.search_results: List[int] = []
        self.current_search_index = 0
        self._lock = threading.Lock()
        self._update_callbacks: List[Callable[[], None]] = []
    
    def add_update_callback(self, callback: Callable[[], None]):
        """Add update callback."""
        self._update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable[[], None]):
        """Remove update callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
    
    def add_log_file(self, log_file: Union[str, Path], log_format: LogFormat = LogFormat.PLAIN):
        """Add a log file to monitor."""
        parser = LogParser(log_format)
        streamer = LogStreamer(log_file, parser)
        streamer.add_callback(self._on_new_log_entry)
        self.streamers.append(streamer)
        return streamer
    
    def remove_log_file(self, streamer: LogStreamer):
        """Remove a log file from monitoring."""
        if streamer in self.streamers:
            self.streamers.remove(streamer)
            asyncio.create_task(streamer.stop())
    
    async def start_monitoring(self):
        """Start monitoring all log files."""
        for streamer in self.streamers:
            await streamer.start()
    
    async def stop_monitoring(self):
        """Stop monitoring all log files."""
        for streamer in self.streamers:
            await streamer.stop()
    
    def add_entry(self, entry: LogEntry):
        """Add a log entry."""
        with self._lock:
            self.entries.append(entry)
            self._notify_update_callbacks()
    
    def get_entries(self, limit: Optional[int] = None) -> List[LogEntry]:
        """Get log entries."""
        with self._lock:
            entries = list(self.entries)
            if limit:
                entries = entries[-limit:]
            return [entry for entry in entries if self.filter.matches(entry)]
    
    def get_filtered_entries(self, filters: List[LogFilter]) -> List[LogEntry]:
        """Get entries filtered by specific filters."""
        with self._lock:
            entries = list(self.entries)
            filtered_entries = []
            
            for entry in entries:
                matches = True
                for filter_config in filters:
                    if not filter_config.enabled:
                        continue
                    
                    filter_matches = self._check_filter(entry, filter_config)
                    if filter_config.invert:
                        filter_matches = not filter_matches
                    
                    if not filter_matches:
                        matches = False
                        break
                
                if matches:
                    filtered_entries.append(entry)
            
            return filtered_entries
    
    def search(self, query: str, case_sensitive: bool = False) -> List[int]:
        """Search for entries containing query."""
        with self._lock:
            self.search_results = []
            flags = 0 if case_sensitive else re.IGNORECASE
            
            for i, entry in enumerate(self.entries):
                if re.search(query, entry.message, flags):
                    self.search_results.append(i)
            
            self.current_search_index = 0
            return self.search_results
    
    def get_next_search_result(self) -> Optional[int]:
        """Get next search result index."""
        if not self.search_results:
            return None
        
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        return self.search_results[self.current_search_index]
    
    def get_previous_search_result(self) -> Optional[int]:
        """Get previous search result index."""
        if not self.search_results:
            return None
        
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        return self.search_results[self.current_search_index]
    
    def clear_entries(self):
        """Clear all log entries."""
        with self._lock:
            self.entries.clear()
            self.search_results.clear()
            self.current_search_index = 0
            self._notify_update_callbacks()
    
    def export_entries(self, file_path: Union[str, Path], format_type: str = "json") -> bool:
        """Export log entries to file."""
        try:
            entries = self.get_entries()
            file_path = Path(file_path)
            
            if format_type.lower() == "json":
                data = [entry.to_dict() for entry in entries]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            elif format_type.lower() == "csv":
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'level', 'source', 'message'])
                    for entry in entries:
                        writer.writerow([
                            entry.timestamp.isoformat(),
                            entry.level.value,
                            entry.source,
                            entry.message
                        ])
            
            elif format_type.lower() == "txt":
                with open(file_path, 'w', encoding='utf-8') as f:
                    for entry in entries:
                        f.write(f"{entry.timestamp.isoformat()} [{entry.level.value}] {entry.source}: {entry.message}\n")
            
            else:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to export log entries: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get log statistics."""
        with self._lock:
            entries = list(self.entries)
            if not entries:
                return {}
            
            level_counts = {}
            source_counts = {}
            total_entries = len(entries)
            
            for entry in entries:
                level_counts[entry.level.value] = level_counts.get(entry.level.value, 0) + 1
                source_counts[entry.source] = source_counts.get(entry.source, 0) + 1
            
            return {
                'total_entries': total_entries,
                'level_counts': level_counts,
                'source_counts': source_counts,
                'oldest_entry': entries[0].timestamp if entries else None,
                'newest_entry': entries[-1].timestamp if entries else None
            }
    
    def _on_new_log_entry(self, entry: LogEntry):
        """Handle new log entry from streamer."""
        self.add_entry(entry)
    
    def _check_filter(self, entry: LogEntry, filter_config: LogFilter) -> bool:
        """Check if entry matches a specific filter."""
        if filter_config.filter_type == FilterType.CONTAINS:
            text = entry.message
            if not filter_config.case_sensitive:
                text = text.lower()
                value = filter_config.value.lower()
            else:
                value = filter_config.value
            return value in text
        
        elif filter_config.filter_type == FilterType.REGEX:
            flags = 0 if filter_config.case_sensitive else re.IGNORECASE
            return bool(re.search(filter_config.value, entry.message, flags))
        
        elif filter_config.filter_type == FilterType.EXACT:
            text = entry.message
            if not filter_config.case_sensitive:
                text = text.lower()
                value = filter_config.value.lower()
            else:
                value = filter_config.value
            return text == value
        
        elif filter_config.filter_type == FilterType.LEVEL:
            return entry.level == LogLevel(filter_config.value)
        
        elif filter_config.filter_type == FilterType.SOURCE:
            return entry.source == filter_config.value
        
        return True
    
    def _notify_update_callbacks(self):
        """Notify all update callbacks."""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in update callback: {e}")


# Global log viewer instance
_log_viewer: Optional[LogViewer] = None


def get_log_viewer() -> LogViewer:
    """Get the global log viewer instance."""
    global _log_viewer
    if _log_viewer is None:
        _log_viewer = LogViewer()
    return _log_viewer


def initialize_log_viewer(config: LogViewerConfig = None) -> LogViewer:
    """Initialize the global log viewer."""
    global _log_viewer
    _log_viewer = LogViewer(config)
    return _log_viewer


# Convenience functions
def add_log_file(log_file: Union[str, Path], log_format: LogFormat = LogFormat.PLAIN) -> LogStreamer:
    """Add a log file to the global viewer."""
    return get_log_viewer().add_log_file(log_file, log_format)


def get_log_entries(limit: Optional[int] = None) -> List[LogEntry]:
    """Get log entries from the global viewer."""
    return get_log_viewer().get_entries(limit)


def search_logs(query: str, case_sensitive: bool = False) -> List[int]:
    """Search logs in the global viewer."""
    return get_log_viewer().search(query, case_sensitive)


def export_logs(file_path: Union[str, Path], format_type: str = "json") -> bool:
    """Export logs from the global viewer."""
    return get_log_viewer().export_entries(file_path, format_type)

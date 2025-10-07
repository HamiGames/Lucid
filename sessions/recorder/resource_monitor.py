# Path: sessions/recorder/resource_monitor.py
# Lucid RDP Resource Monitor - Resource access tracking
# Implements R-MUST-005: Session Audit Trail with resource access tracking
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import time
import threading
import psutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import hashlib
import subprocess
import socket
import netifaces

logger = logging.getLogger(__name__)

# Configuration from environment
RESOURCE_LOG_PATH = Path(os.getenv("RESOURCE_LOG_PATH", "/var/log/lucid/resources"))
RESOURCE_CACHE_PATH = Path(os.getenv("RESOURCE_CACHE_PATH", "/tmp/lucid/resources"))
RESOURCE_MONITOR_INTERVAL = float(os.getenv("RESOURCE_MONITOR_INTERVAL", "5.0"))
RESOURCE_MAX_EVENTS = int(os.getenv("RESOURCE_MAX_EVENTS", "10000"))
RESOURCE_BATCH_SIZE = int(os.getenv("RESOURCE_BATCH_SIZE", "100"))


class ResourceType(Enum):
    """Types of system resources"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    FILE = "file"
    PROCESS = "process"
    PORT = "port"
    SERVICE = "service"
    REGISTRY = "registry"
    CLIPBOARD = "clipboard"
    AUDIO = "audio"
    VIDEO = "video"
    USB = "usb"
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    CAMERA = "camera"
    MICROPHONE = "microphone"


class ResourceAction(Enum):
    """Types of resource actions"""
    ACCESS = "access"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    CREATE = "create"
    MODIFY = "modify"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    INSTALL = "install"
    UNINSTALL = "uninstall"
    CONFIGURE = "configure"
    MONITOR = "monitor"


class ResourceEventType(Enum):
    """Types of resource events"""
    RESOURCE_ACCESS = "resource_access"
    RESOURCE_DENIED = "resource_denied"
    RESOURCE_ERROR = "resource_error"
    RESOURCE_WARNING = "resource_warning"
    RESOURCE_THRESHOLD = "resource_threshold"
    RESOURCE_ANOMALY = "resource_anomaly"
    SECURITY_VIOLATION = "security_violation"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class ResourceInfo:
    """Resource information structure"""
    resource_id: str
    resource_type: ResourceType
    resource_name: str
    resource_path: Optional[str] = None
    resource_size: Optional[int] = None
    resource_permissions: Optional[str] = None
    resource_owner: Optional[str] = None
    resource_group: Optional[str] = None
    resource_created: Optional[datetime] = None
    resource_modified: Optional[datetime] = None
    resource_accessed: Optional[datetime] = None
    resource_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceEvent:
    """Resource event data structure"""
    event_id: str
    session_id: str
    timestamp: datetime
    event_type: ResourceEventType
    resource_info: ResourceInfo
    action: ResourceAction
    actor_identity: str
    actor_type: str
    result: str = "success"  # success, failure, denied, error
    duration_ms: Optional[int] = None
    bytes_transferred: Optional[int] = None
    is_sensitive: bool = False
    is_filtered: bool = False
    security_level: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "resource_info": {
                "resource_id": self.resource_info.resource_id,
                "resource_type": self.resource_info.resource_type.value,
                "resource_name": self.resource_info.resource_name,
                "resource_path": self.resource_info.resource_path,
                "resource_size": self.resource_info.resource_size,
                "resource_permissions": self.resource_info.resource_permissions,
                "resource_owner": self.resource_info.resource_owner,
                "resource_group": self.resource_info.resource_group,
                "resource_created": self.resource_info.resource_created.isoformat() if self.resource_info.resource_created else None,
                "resource_modified": self.resource_info.resource_modified.isoformat() if self.resource_info.resource_modified else None,
                "resource_accessed": self.resource_info.resource_accessed.isoformat() if self.resource_info.resource_accessed else None,
                "resource_metadata": self.resource_info.resource_metadata
            },
            "action": self.action.value,
            "actor_identity": self.actor_identity,
            "actor_type": self.actor_type,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "bytes_transferred": self.bytes_transferred,
            "is_sensitive": self.is_sensitive,
            "is_filtered": self.is_filtered,
            "security_level": self.security_level,
            "metadata": self.metadata,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResourceEvent:
        """Create from dictionary"""
        resource_info_data = data["resource_info"]
        resource_info = ResourceInfo(
            resource_id=resource_info_data["resource_id"],
            resource_type=ResourceType(resource_info_data["resource_type"]),
            resource_name=resource_info_data["resource_name"],
            resource_path=resource_info_data.get("resource_path"),
            resource_size=resource_info_data.get("resource_size"),
            resource_permissions=resource_info_data.get("resource_permissions"),
            resource_owner=resource_info_data.get("resource_owner"),
            resource_group=resource_info_data.get("resource_group"),
            resource_created=datetime.fromisoformat(resource_info_data["resource_created"]) if resource_info_data.get("resource_created") else None,
            resource_modified=datetime.fromisoformat(resource_info_data["resource_modified"]) if resource_info_data.get("resource_modified") else None,
            resource_accessed=datetime.fromisoformat(resource_info_data["resource_accessed"]) if resource_info_data.get("resource_accessed") else None,
            resource_metadata=resource_info_data.get("resource_metadata", {})
        )
        
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=ResourceEventType(data["event_type"]),
            resource_info=resource_info,
            action=ResourceAction(data["action"]),
            actor_identity=data["actor_identity"],
            actor_type=data["actor_type"],
            result=data.get("result", "success"),
            duration_ms=data.get("duration_ms"),
            bytes_transferred=data.get("bytes_transferred"),
            is_sensitive=data.get("is_sensitive", False),
            is_filtered=data.get("is_filtered", False),
            security_level=data.get("security_level", "normal"),
            metadata=data.get("metadata", {}),
            hash=data.get("hash")
        )


@dataclass
class ResourceMonitorConfig:
    """Resource monitor configuration"""
    session_id: str
    enabled: bool = True
    monitor_interval: float = RESOURCE_MONITOR_INTERVAL
    max_events: int = RESOURCE_MAX_EVENTS
    batch_size: int = RESOURCE_BATCH_SIZE
    monitor_cpu: bool = True
    monitor_memory: bool = True
    monitor_disk: bool = True
    monitor_network: bool = True
    monitor_files: bool = True
    monitor_processes: bool = True
    monitor_ports: bool = True
    monitor_services: bool = True
    monitor_clipboard: bool = True
    monitor_audio: bool = True
    monitor_video: bool = True
    monitor_usb: bool = True
    monitor_bluetooth: bool = True
    monitor_wifi: bool = True
    monitor_camera: bool = True
    monitor_microphone: bool = True
    track_sensitive_resources: bool = True
    sensitive_paths: List[str] = field(default_factory=lambda: [
        "/etc/passwd", "/etc/shadow", "/etc/sudoers",
        "C:\\Windows\\System32\\config\\SAM",
        "C:\\Windows\\System32\\config\\SECURITY"
    ])
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/proc/kcore", "/dev/mem", "/dev/kmem"
    ])
    allowed_ports: Optional[List[int]] = None
    blocked_ports: List[int] = field(default_factory=lambda: [22, 23, 135, 139, 445, 1433, 3389])
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceMonitor:
    """
    Resource monitoring system for Lucid RDP.
    
    Provides:
    - Comprehensive system resource monitoring
    - File and process access tracking
    - Network and port monitoring
    - Hardware device monitoring
    - Security violation detection
    """
    
    def __init__(self, config: ResourceMonitorConfig):
        self.config = config
        self.is_enabled = config.enabled
        
        # Event storage
        self.event_buffer: List[ResourceEvent] = []
        self.event_callbacks: List[Callable] = []
        
        # Monitoring state
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        
        # Resource tracking
        self.resource_cache: Dict[str, Any] = {}
        self.resource_thresholds: Dict[str, float] = {
            "cpu_percent": 80.0,
            "memory_percent": 80.0,
            "disk_percent": 90.0,
            "network_bandwidth": 1000000000  # 1GB/s
        }
        
        # Statistics
        self.event_count = 0
        self.filtered_count = 0
        self.sensitive_count = 0
        self.threshold_violations = 0
        
        # Create required directories
        self._create_directories()
        
        logger.info(f"Resource Monitor initialized for session: {config.session_id}")
    
    def _create_directories(self) -> None:
        """Create required directories for resource monitoring"""
        directories = [
            RESOURCE_LOG_PATH,
            RESOURCE_CACHE_PATH,
            RESOURCE_LOG_PATH / self.config.session_id,
            RESOURCE_CACHE_PATH / self.config.session_id
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    async def start(self) -> bool:
        """Start the resource monitor"""
        try:
            if not self.is_enabled:
                logger.info("Resource monitor disabled")
                return True
            
            logger.info("Starting Resource Monitor...")
            
            # Start monitoring thread
            await self._start_monitoring()
            
            logger.info("Resource Monitor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Resource Monitor: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the resource monitor"""
        try:
            logger.info("Stopping Resource Monitor...")
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Flush remaining events
            await self._flush_events()
            
            logger.info("Resource Monitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Resource Monitor: {e}")
            return False
    
    async def _start_monitoring(self) -> None:
        """Start resource monitoring"""
        try:
            if self.monitor_running:
                return
            
            self.monitor_running = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_resources)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Resource monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start resource monitoring: {e}")
    
    async def _stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        try:
            self.monitor_running = False
            
            # Stop monitoring thread
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            logger.info("Resource monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop resource monitoring: {e}")
    
    def _monitor_resources(self) -> None:
        """Monitor system resources (runs in separate thread)"""
        try:
            while self.monitor_running:
                try:
                    # Monitor different resource types
                    if self.config.monitor_cpu:
                        self._monitor_cpu()
                    
                    if self.config.monitor_memory:
                        self._monitor_memory()
                    
                    if self.config.monitor_disk:
                        self._monitor_disk()
                    
                    if self.config.monitor_network:
                        self._monitor_network()
                    
                    if self.config.monitor_processes:
                        self._monitor_processes()
                    
                    if self.config.monitor_ports:
                        self._monitor_ports()
                    
                    if self.config.monitor_files:
                        self._monitor_files()
                    
                    if self.config.monitor_services:
                        self._monitor_services()
                    
                    if self.config.monitor_clipboard:
                        self._monitor_clipboard()
                    
                    if self.config.monitor_audio:
                        self._monitor_audio()
                    
                    if self.config.monitor_video:
                        self._monitor_video()
                    
                    if self.config.monitor_usb:
                        self._monitor_usb()
                    
                    if self.config.monitor_bluetooth:
                        self._monitor_bluetooth()
                    
                    if self.config.monitor_wifi:
                        self._monitor_wifi()
                    
                    if self.config.monitor_camera:
                        self._monitor_camera()
                    
                    if self.config.monitor_microphone:
                        self._monitor_microphone()
                    
                    time.sleep(self.config.monitor_interval)
                    
                except Exception as e:
                    logger.error(f"Resource monitoring error: {e}")
                    time.sleep(1)
            
        except Exception as e:
            logger.error(f"Resource monitoring thread error: {e}")
    
    def _monitor_cpu(self) -> None:
        """Monitor CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Check threshold
            if cpu_percent > self.resource_thresholds["cpu_percent"]:
                self._create_threshold_event(
                    ResourceType.CPU,
                    f"CPU usage {cpu_percent}%",
                    cpu_percent,
                    self.resource_thresholds["cpu_percent"]
                )
            
            # Update cache
            self.resource_cache["cpu"] = {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": cpu_freq.current if cpu_freq else None
            }
            
        except Exception as e:
            logger.error(f"CPU monitoring error: {e}")
    
    def _monitor_memory(self) -> None:
        """Monitor memory usage"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Check threshold
            if memory.percent > self.resource_thresholds["memory_percent"]:
                self._create_threshold_event(
                    ResourceType.MEMORY,
                    f"Memory usage {memory.percent}%",
                    memory.percent,
                    self.resource_thresholds["memory_percent"]
                )
            
            # Update cache
            self.resource_cache["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_free": swap.free
            }
            
        except Exception as e:
            logger.error(f"Memory monitoring error: {e}")
    
    def _monitor_disk(self) -> None:
        """Monitor disk usage"""
        try:
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Check threshold
            if disk_usage.percent > self.resource_thresholds["disk_percent"]:
                self._create_threshold_event(
                    ResourceType.DISK,
                    f"Disk usage {disk_usage.percent}%",
                    disk_usage.percent,
                    self.resource_thresholds["disk_percent"]
                )
            
            # Update cache
            self.resource_cache["disk"] = {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": disk_usage.percent,
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0,
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0
            }
            
        except Exception as e:
            logger.error(f"Disk monitoring error: {e}")
    
    def _monitor_network(self) -> None:
        """Monitor network usage"""
        try:
            network_io = psutil.net_io_counters()
            network_connections = psutil.net_connections()
            
            # Check for suspicious connections
            for conn in network_connections:
                if conn.status == 'ESTABLISHED':
                    # Check for blocked ports
                    if conn.laddr.port in self.config.blocked_ports:
                        self._create_security_event(
                            ResourceType.NETWORK,
                            f"Connection to blocked port {conn.laddr.port}",
                            f"{conn.laddr.ip}:{conn.laddr.port}",
                            "blocked_port_access"
                        )
            
            # Update cache
            self.resource_cache["network"] = {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv,
                "connections": len(network_connections)
            }
            
        except Exception as e:
            logger.error(f"Network monitoring error: {e}")
    
    def _monitor_processes(self) -> None:
        """Monitor running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    proc_info = proc.info
                    processes.append(proc_info)
                    
                    # Check for suspicious processes
                    if proc_info['cpu_percent'] > 50:  # High CPU usage
                        self._create_anomaly_event(
                            ResourceType.PROCESS,
                            f"High CPU usage process: {proc_info['name']}",
                            proc_info['name'],
                            f"CPU: {proc_info['cpu_percent']}%"
                        )
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Update cache
            self.resource_cache["processes"] = {
                "count": len(processes),
                "processes": processes[:10]  # Keep top 10
            }
            
        except Exception as e:
            logger.error(f"Process monitoring error: {e}")
    
    def _monitor_ports(self) -> None:
        """Monitor network ports"""
        try:
            connections = psutil.net_connections()
            listening_ports = []
            
            for conn in connections:
                if conn.status == 'LISTEN':
                    listening_ports.append(conn.laddr.port)
                    
                    # Check for blocked ports
                    if conn.laddr.port in self.config.blocked_ports:
                        self._create_security_event(
                            ResourceType.PORT,
                            f"Blocked port {conn.laddr.port} is listening",
                            f"{conn.laddr.ip}:{conn.laddr.port}",
                            "blocked_port_listening"
                        )
            
            # Update cache
            self.resource_cache["ports"] = {
                "listening_ports": listening_ports,
                "total_connections": len(connections)
            }
            
        except Exception as e:
            logger.error(f"Port monitoring error: {e}")
    
    def _monitor_files(self) -> None:
        """Monitor file access"""
        try:
            # This would require file system monitoring
            # For now, check for sensitive files
            for sensitive_path in self.config.sensitive_paths:
                if os.path.exists(sensitive_path):
                    # Check if file was accessed recently
                    stat = os.stat(sensitive_path)
                    access_time = datetime.fromtimestamp(stat.st_atime)
                    
                    if (datetime.now(timezone.utc) - access_time).total_seconds() < 3600:  # Last hour
                        self._create_sensitive_event(
                            ResourceType.FILE,
                            f"Sensitive file accessed: {sensitive_path}",
                            sensitive_path,
                            "sensitive_file_access"
                        )
            
        except Exception as e:
            logger.error(f"File monitoring error: {e}")
    
    def _monitor_services(self) -> None:
        """Monitor system services"""
        try:
            # This would require service monitoring
            # For now, check for common services
            common_services = ['ssh', 'apache', 'nginx', 'mysql', 'postgresql']
            
            for service in common_services:
                try:
                    # Check if service is running
                    result = subprocess.run(['systemctl', 'is-active', service], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        self._create_resource_event(
                            ResourceType.SERVICE,
                            f"Service {service} is active",
                            service,
                            ResourceAction.MONITOR,
                            "system"
                        )
                except Exception:
                    continue
            
        except Exception as e:
            logger.error(f"Service monitoring error: {e}")
    
    def _monitor_clipboard(self) -> None:
        """Monitor clipboard access"""
        try:
            # This would require clipboard monitoring
            # For now, just log that clipboard monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"Clipboard monitoring error: {e}")
    
    def _monitor_audio(self) -> None:
        """Monitor audio devices"""
        try:
            # This would require audio device monitoring
            # For now, just log that audio monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"Audio monitoring error: {e}")
    
    def _monitor_video(self) -> None:
        """Monitor video devices"""
        try:
            # This would require video device monitoring
            # For now, just log that video monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"Video monitoring error: {e}")
    
    def _monitor_usb(self) -> None:
        """Monitor USB devices"""
        try:
            # This would require USB device monitoring
            # For now, just log that USB monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"USB monitoring error: {e}")
    
    def _monitor_bluetooth(self) -> None:
        """Monitor Bluetooth devices"""
        try:
            # This would require Bluetooth monitoring
            # For now, just log that Bluetooth monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"Bluetooth monitoring error: {e}")
    
    def _monitor_wifi(self) -> None:
        """Monitor WiFi connections"""
        try:
            # This would require WiFi monitoring
            # For now, just log that WiFi monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"WiFi monitoring error: {e}")
    
    def _monitor_camera(self) -> None:
        """Monitor camera access"""
        try:
            # This would require camera monitoring
            # For now, just log that camera monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"Camera monitoring error: {e}")
    
    def _monitor_microphone(self) -> None:
        """Monitor microphone access"""
        try:
            # This would require microphone monitoring
            # For now, just log that microphone monitoring is active
            pass
            
        except Exception as e:
            logger.error(f"Microphone monitoring error: {e}")
    
    def _create_threshold_event(
        self,
        resource_type: ResourceType,
        description: str,
        current_value: float,
        threshold: float
    ) -> None:
        """Create a threshold violation event"""
        try:
            resource_info = ResourceInfo(
                resource_id=f"{resource_type.value}_threshold",
                resource_type=resource_type,
                resource_name=description,
                resource_metadata={
                    "current_value": current_value,
                    "threshold": threshold,
                    "violation_percent": ((current_value - threshold) / threshold) * 100
                }
            )
            
            event = ResourceEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=ResourceEventType.RESOURCE_THRESHOLD,
                resource_info=resource_info,
                action=ResourceAction.MONITOR,
                actor_identity="system",
                actor_type="system",
                result="warning",
                is_sensitive=False,
                is_filtered=False,
                security_level="warning",
                metadata={"threshold_violation": True}
            )
            
            # Calculate hash
            event.hash = self._calculate_event_hash(event)
            
            # Add to buffer
            self.event_buffer.append(event)
            self.event_count += 1
            self.threshold_violations += 1
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.config.batch_size:
                asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Failed to create threshold event: {e}")
    
    def _create_security_event(
        self,
        resource_type: ResourceType,
        description: str,
        resource_path: str,
        violation_type: str
    ) -> None:
        """Create a security violation event"""
        try:
            resource_info = ResourceInfo(
                resource_id=f"{resource_type.value}_security",
                resource_type=resource_type,
                resource_name=description,
                resource_path=resource_path,
                resource_metadata={"violation_type": violation_type}
            )
            
            event = ResourceEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=ResourceEventType.SECURITY_VIOLATION,
                resource_info=resource_info,
                action=ResourceAction.ACCESS,
                actor_identity="unknown",
                actor_type="user",
                result="denied",
                is_sensitive=True,
                is_filtered=False,
                security_level="high",
                metadata={"security_violation": True, "violation_type": violation_type}
            )
            
            # Calculate hash
            event.hash = self._calculate_event_hash(event)
            
            # Add to buffer
            self.event_buffer.append(event)
            self.event_count += 1
            self.sensitive_count += 1
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.config.batch_size:
                asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Failed to create security event: {e}")
    
    def _create_sensitive_event(
        self,
        resource_type: ResourceType,
        description: str,
        resource_path: str,
        access_type: str
    ) -> None:
        """Create a sensitive resource access event"""
        try:
            resource_info = ResourceInfo(
                resource_id=f"{resource_type.value}_sensitive",
                resource_type=resource_type,
                resource_name=description,
                resource_path=resource_path,
                resource_metadata={"access_type": access_type}
            )
            
            event = ResourceEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=ResourceEventType.RESOURCE_ACCESS,
                resource_info=resource_info,
                action=ResourceAction.ACCESS,
                actor_identity="user",
                actor_type="user",
                result="success",
                is_sensitive=True,
                is_filtered=False,
                security_level="high",
                metadata={"sensitive_access": True, "access_type": access_type}
            )
            
            # Calculate hash
            event.hash = self._calculate_event_hash(event)
            
            # Add to buffer
            self.event_buffer.append(event)
            self.event_count += 1
            self.sensitive_count += 1
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.config.batch_size:
                asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Failed to create sensitive event: {e}")
    
    def _create_anomaly_event(
        self,
        resource_type: ResourceType,
        description: str,
        resource_name: str,
        details: str
    ) -> None:
        """Create an anomaly event"""
        try:
            resource_info = ResourceInfo(
                resource_id=f"{resource_type.value}_anomaly",
                resource_type=resource_type,
                resource_name=description,
                resource_metadata={"details": details}
            )
            
            event = ResourceEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=ResourceEventType.RESOURCE_ANOMALY,
                resource_info=resource_info,
                action=ResourceAction.MONITOR,
                actor_identity="system",
                actor_type="system",
                result="warning",
                is_sensitive=False,
                is_filtered=False,
                security_level="medium",
                metadata={"anomaly": True, "details": details}
            )
            
            # Calculate hash
            event.hash = self._calculate_event_hash(event)
            
            # Add to buffer
            self.event_buffer.append(event)
            self.event_count += 1
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.config.batch_size:
                asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Failed to create anomaly event: {e}")
    
    def _create_resource_event(
        self,
        resource_type: ResourceType,
        description: str,
        resource_name: str,
        action: ResourceAction,
        actor_identity: str
    ) -> None:
        """Create a general resource event"""
        try:
            resource_info = ResourceInfo(
                resource_id=f"{resource_type.value}_{resource_name}",
                resource_type=resource_type,
                resource_name=description,
                resource_metadata={"monitored": True}
            )
            
            event = ResourceEvent(
                event_id=str(uuid.uuid4()),
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=ResourceEventType.RESOURCE_ACCESS,
                resource_info=resource_info,
                action=action,
                actor_identity=actor_identity,
                actor_type="system",
                result="success",
                is_sensitive=False,
                is_filtered=False,
                security_level="normal",
                metadata={"monitored": True}
            )
            
            # Calculate hash
            event.hash = self._calculate_event_hash(event)
            
            # Add to buffer
            self.event_buffer.append(event)
            self.event_count += 1
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.config.batch_size:
                asyncio.create_task(self._flush_events())
            
        except Exception as e:
            logger.error(f"Failed to create resource event: {e}")
    
    def _calculate_event_hash(self, event: ResourceEvent) -> str:
        """Calculate hash for event integrity"""
        try:
            # Create hashable string from event data
            hash_data = f"{event.session_id}{event.timestamp.isoformat()}{event.event_type.value}{event.resource_info.resource_id}{event.action.value}{event.actor_identity}"
            
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
            
            # Save to file
            await self._save_events_to_file(filtered_events)
            
            # Notify callbacks
            for event in filtered_events:
                await self._notify_callbacks("resource_event", event)
            
            # Clear buffer
            self.event_buffer.clear()
            
            logger.debug(f"Flushed {len(filtered_events)} resource events")
            
        except Exception as e:
            logger.error(f"Failed to flush resource events: {e}")
    
    async def _save_events_to_file(self, events: List[ResourceEvent]) -> None:
        """Save events to file"""
        try:
            if not events:
                return
            
            # Create events data
            events_data = [event.to_dict() for event in events]
            
            # Save to JSON file
            log_file = RESOURCE_LOG_PATH / self.config.session_id / f"resources_{int(time.time())}.json"
            with open(log_file, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.debug(f"Saved {len(events)} resource events to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save resource events: {e}")
    
    async def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ResourceEvent]:
        """Get resource events with filtering"""
        try:
            events = []
            
            # Load from files
            log_dir = RESOURCE_LOG_PATH / self.config.session_id
            if log_dir.exists():
                for log_file in log_dir.glob("resources_*.json"):
                    try:
                        with open(log_file, 'r') as f:
                            file_events = json.load(f)
                        
                        for event_data in file_events:
                            event = ResourceEvent.from_dict(event_data)
                            
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
            logger.error(f"Failed to get resource events: {e}")
            return []
    
    async def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        try:
            return {
                "session_id": self.config.session_id,
                "enabled": self.is_enabled,
                "monitoring": self.monitor_running,
                "event_count": self.event_count,
                "filtered_count": self.filtered_count,
                "sensitive_count": self.sensitive_count,
                "threshold_violations": self.threshold_violations,
                "buffer_size": len(self.event_buffer),
                "resource_cache": self.resource_cache,
                "thresholds": self.resource_thresholds
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource status: {e}")
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
                logger.error(f"Error in resource callback: {e}")
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add an event callback"""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status"""
        return {
            "enabled": self.is_enabled,
            "session_id": self.config.session_id,
            "event_count": self.event_count,
            "filtered_count": self.filtered_count,
            "sensitive_count": self.sensitive_count,
            "threshold_violations": self.threshold_violations,
            "buffer_size": len(self.event_buffer),
            "monitoring": self.monitor_running,
            "monitor_cpu": self.config.monitor_cpu,
            "monitor_memory": self.config.monitor_memory,
            "monitor_disk": self.config.monitor_disk,
            "monitor_network": self.config.monitor_network,
            "monitor_processes": self.config.monitor_processes,
            "monitor_ports": self.config.monitor_ports,
            "monitor_files": self.config.monitor_files,
            "monitor_services": self.config.monitor_services,
            "monitor_clipboard": self.config.monitor_clipboard,
            "monitor_audio": self.config.monitor_audio,
            "monitor_video": self.config.monitor_video,
            "monitor_usb": self.config.monitor_usb,
            "monitor_bluetooth": self.config.monitor_bluetooth,
            "monitor_wifi": self.config.monitor_wifi,
            "monitor_camera": self.config.monitor_camera,
            "monitor_microphone": self.config.monitor_microphone
        }


# Global Resource Monitor instance
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> Optional[ResourceMonitor]:
    """Get the global resource monitor instance"""
    return _resource_monitor


async def initialize_resource_monitor(config: ResourceMonitorConfig) -> ResourceMonitor:
    """Initialize the global resource monitor"""
    global _resource_monitor
    
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor(config)
        await _resource_monitor.start()
    
    return _resource_monitor


async def shutdown_resource_monitor() -> None:
    """Shutdown the global resource monitor"""
    global _resource_monitor
    
    if _resource_monitor:
        await _resource_monitor.stop()
        _resource_monitor = None


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[resource-monitor] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = ResourceMonitorConfig(
        session_id="lucid_resource_001",
        enabled=True,
        monitor_interval=5.0,
        max_events=10000,
        batch_size=100,
        monitor_cpu=True,
        monitor_memory=True,
        monitor_disk=True,
        monitor_network=True,
        monitor_processes=True,
        monitor_ports=True,
        monitor_files=True,
        monitor_services=True,
        monitor_clipboard=True,
        monitor_audio=True,
        monitor_video=True,
        monitor_usb=True,
        monitor_bluetooth=True,
        monitor_wifi=True,
        monitor_camera=True,
        monitor_microphone=True,
        track_sensitive_resources=True
    )
    
    # Initialize and start monitor
    monitor = await initialize_resource_monitor(config)
    
    try:
        # Keep monitor running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Resource Monitor...")
        await shutdown_resource_monitor()


if __name__ == "__main__":
    asyncio.run(main())

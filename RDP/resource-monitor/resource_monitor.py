"""
RDP Resource Monitor - Resource Monitoring Service

This module provides resource monitoring functionality for RDP sessions,
including CPU, memory, disk, and network monitoring.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

logger = logging.getLogger(__name__)

class ResourceMetrics:
    """Resource metrics data structure"""
    
    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.timestamp = datetime.utcnow()
        self.cpu_percent = 0.0
        self.memory_usage = 0
        self.memory_percent = 0.0
        self.disk_usage = 0
        self.disk_percent = 0.0
        self.network_bytes_sent = 0
        self.network_bytes_recv = 0
        self.network_packets_sent = 0
        self.network_packets_recv = 0
        self.active_connections = 0
        self.process_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "session_id": str(self.session_id),
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_usage": self.memory_usage,
            "memory_percent": self.memory_percent,
            "disk_usage": self.disk_usage,
            "disk_percent": self.disk_percent,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "network_packets_sent": self.network_packets_sent,
            "network_packets_recv": self.network_packets_recv,
            "active_connections": self.active_connections,
            "process_count": self.process_count
        }

class ResourceMonitor:
    """Monitors system resources for RDP sessions"""
    
    def __init__(self):
        self.monitored_sessions: Dict[UUID, Dict[str, Any]] = {}
        self.metrics_history: Dict[UUID, List[ResourceMetrics]] = {}
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 80.0,
            "disk_percent": 90.0,
            "network_bandwidth": 1000  # MB/s
        }
        self.monitoring_interval = 30  # seconds
        self.monitoring_active = False
    
    async def start_monitoring(self, session_id: UUID, session_config: Dict[str, Any]):
        """Start monitoring a session"""
        try:
            self.monitored_sessions[session_id] = {
                "config": session_config,
                "start_time": datetime.utcnow(),
                "last_metrics": None
            }
            
            if session_id not in self.metrics_history:
                self.metrics_history[session_id] = []
            
            logger.info(f"Started monitoring session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring session {session_id}: {e}")
            raise
    
    async def stop_monitoring(self, session_id: UUID):
        """Stop monitoring a session"""
        try:
            if session_id in self.monitored_sessions:
                del self.monitored_sessions[session_id]
            
            # Keep metrics history for analysis
            logger.info(f"Stopped monitoring session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring session {session_id}: {e}")
    
    async def collect_metrics(self, session_id: UUID) -> ResourceMetrics:
        """Collect resource metrics for a session"""
        try:
            metrics = ResourceMetrics(session_id)
            
            # Get system-wide metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network statistics
            network_io = psutil.net_io_counters()
            
            # Get process information
            processes = psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])
            process_count = 0
            total_cpu = 0.0
            total_memory = 0.0
            
            for proc in processes:
                try:
                    process_count += 1
                    total_cpu += proc.info['cpu_percent'] or 0
                    total_memory += proc.info['memory_percent'] or 0
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Update metrics
            metrics.cpu_percent = cpu_percent
            metrics.memory_usage = memory.used
            metrics.memory_percent = memory.percent
            metrics.disk_usage = disk.used
            metrics.disk_percent = (disk.used / disk.total) * 100
            metrics.network_bytes_sent = network_io.bytes_sent
            metrics.network_bytes_recv = network_io.bytes_recv
            metrics.network_packets_sent = network_io.packets_sent
            metrics.network_packets_recv = network_io.packets_recv
            metrics.process_count = process_count
            
            # Calculate active connections
            try:
                connections = psutil.net_connections()
                metrics.active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
            except Exception:
                metrics.active_connections = 0
            
            # Store metrics
            if session_id in self.metrics_history:
                self.metrics_history[session_id].append(metrics)
                
                # Keep only last 100 metrics per session
                if len(self.metrics_history[session_id]) > 100:
                    self.metrics_history[session_id] = self.metrics_history[session_id][-100:]
            
            # Update last metrics
            if session_id in self.monitored_sessions:
                self.monitored_sessions[session_id]["last_metrics"] = metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for session {session_id}: {e}")
            raise
    
    async def get_session_metrics(self, session_id: UUID) -> Optional[ResourceMetrics]:
        """Get latest metrics for a session"""
        if session_id in self.monitored_sessions:
            return self.monitored_sessions[session_id].get("last_metrics")
        return None
    
    async def get_metrics_history(
        self, 
        session_id: UUID, 
        hours: int = 1
    ) -> List[ResourceMetrics]:
        """Get metrics history for a session"""
        if session_id not in self.metrics_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            metrics for metrics in self.metrics_history[session_id]
            if metrics.timestamp >= cutoff_time
        ]
    
    async def check_alerts(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Check for resource alerts"""
        try:
            metrics = await self.get_session_metrics(session_id)
            if not metrics:
                return []
            
            alerts = []
            
            # Check CPU usage
            if metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
                alerts.append({
                    "type": "cpu_high",
                    "level": "warning",
                    "value": metrics.cpu_percent,
                    "threshold": self.alert_thresholds["cpu_percent"],
                    "message": f"High CPU usage: {metrics.cpu_percent:.1f}%"
                })
            
            # Check memory usage
            if metrics.memory_percent > self.alert_thresholds["memory_percent"]:
                alerts.append({
                    "type": "memory_high",
                    "level": "warning",
                    "value": metrics.memory_percent,
                    "threshold": self.alert_thresholds["memory_percent"],
                    "message": f"High memory usage: {metrics.memory_percent:.1f}%"
                })
            
            # Check disk usage
            if metrics.disk_percent > self.alert_thresholds["disk_percent"]:
                alerts.append({
                    "type": "disk_high",
                    "level": "critical",
                    "value": metrics.disk_percent,
                    "threshold": self.alert_thresholds["disk_percent"],
                    "message": f"High disk usage: {metrics.disk_percent:.1f}%"
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to check alerts for session {session_id}: {e}")
            return []
    
    async def get_system_summary(self) -> Dict[str, Any]:
        """Get system-wide resource summary"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network_io = psutil.net_io_counters()
            
            # Count monitored sessions
            active_sessions = len(self.monitored_sessions)
            
            # Calculate average metrics across all sessions
            total_cpu = 0.0
            total_memory = 0.0
            total_disk = 0.0
            
            for session_id in self.monitored_sessions:
                metrics = await self.get_session_metrics(session_id)
                if metrics:
                    total_cpu += metrics.cpu_percent
                    total_memory += metrics.memory_percent
                    total_disk += metrics.disk_percent
            
            avg_cpu = total_cpu / active_sessions if active_sessions > 0 else 0
            avg_memory = total_memory / active_sessions if active_sessions > 0 else 0
            avg_disk = total_disk / active_sessions if active_sessions > 0 else 0
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "network_bytes_sent": network_io.bytes_sent,
                    "network_bytes_recv": network_io.bytes_recv
                },
                "sessions": {
                    "active_count": active_sessions,
                    "average_cpu": avg_cpu,
                    "average_memory": avg_memory,
                    "average_disk": avg_disk
                },
                "thresholds": self.alert_thresholds
            }
            
        except Exception as e:
            logger.error(f"Failed to get system summary: {e}")
            return {}
    
    async def start_continuous_monitoring(self):
        """Start continuous monitoring of all sessions"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                # Collect metrics for all monitored sessions
                for session_id in list(self.monitored_sessions.keys()):
                    try:
                        await self.collect_metrics(session_id)
                        
                        # Check for alerts
                        alerts = await self.check_alerts(session_id)
                        if alerts:
                            logger.warning(f"Alerts for session {session_id}: {alerts}")
                            
                    except Exception as e:
                        logger.error(f"Failed to monitor session {session_id}: {e}")
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Continuous monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def stop_continuous_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
    
    async def cleanup_old_metrics(self, hours: int = 24):
        """Clean up old metrics data"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for session_id in self.metrics_history:
                self.metrics_history[session_id] = [
                    metrics for metrics in self.metrics_history[session_id]
                    if metrics.timestamp >= cutoff_time
                ]
            
            logger.info("Cleaned up old metrics data")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")

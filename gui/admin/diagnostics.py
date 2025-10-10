# Path: gui/admin/diagnostics.py
"""
System diagnostics and health monitoring interface for Lucid RDP GUI.
Provides comprehensive system health checks, performance monitoring, and diagnostic tools.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import logging
import psutil
import platform
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import os
from pathlib import Path
import sys

from ..core.networking import TorHttpClient, SecurityConfig
from ..core.security import get_security_validator
from ..core.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class DiagnosticLevel(Enum):
    """Diagnostic level enumeration"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class DiagnosticResult:
    """Diagnostic result container"""
    test_name: str
    status: HealthStatus
    level: DiagnosticLevel
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiagnosticResult':
        """Create DiagnosticResult from dictionary"""
        data['status'] = HealthStatus(data['status'])
        data['level'] = DiagnosticLevel(data['level'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class SystemMetrics:
    """System metrics container"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_used: int
    disk_total: int
    network_sent: int
    network_recv: int
    process_count: int
    load_average: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class DiagnosticManager:
    """
    System diagnostics and health monitoring interface.
    
    Provides functionality for:
    - System health checks
    - Performance monitoring
    - Network diagnostics
    - Tor connectivity tests
    - Resource usage monitoring
    """
    
    def __init__(self, parent_frame: tk.Frame, node_api_url: str = "http://localhost:8080"):
        self.parent_frame = parent_frame
        self.node_api_url = node_api_url.rstrip('/')
        
        # Data storage
        self.diagnostic_results: List[DiagnosticResult] = []
        self.system_metrics: List[SystemMetrics] = []
        self.monitoring_active = False
        
        # Configuration
        self.config_manager = get_config_manager()
        self.security_validator = get_security_validator()
        
        # Setup GUI
        self.setup_gui()
        self.setup_networking()
        
        # Load historical data
        self.load_diagnostic_history()
        
        # Start monitoring
        self.start_monitoring()
    
    def setup_gui(self) -> None:
        """Setup the diagnostics GUI."""
        # Main container
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_overview_tab()
        self.create_system_tab()
        self.create_network_tab()
        self.create_tor_tab()
        self.create_logs_tab()
    
    def create_overview_tab(self) -> None:
        """Create system overview tab."""
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Overview")
        
        # Health status
        status_frame = ttk.LabelFrame(self.overview_frame, text="System Health")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Overall status
        overall_frame = ttk.Frame(status_frame)
        overall_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(overall_frame, text="Overall Status:").pack(side=tk.LEFT)
        self.overall_status_label = ttk.Label(overall_frame, text="Unknown", font=('Arial', 12, 'bold'))
        self.overall_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Quick actions
        actions_frame = ttk.Frame(status_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(actions_frame, text="Run All Diagnostics", command=self.run_all_diagnostics).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Refresh Status", command=self.refresh_overview).pack(side=tk.LEFT, padx=5)
        
        # System metrics
        metrics_frame = ttk.LabelFrame(self.overview_frame, text="System Metrics")
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # CPU usage
        cpu_frame = ttk.Frame(metrics_frame)
        cpu_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(cpu_frame, text="CPU Usage:").pack(side=tk.LEFT)
        self.cpu_usage_label = ttk.Label(cpu_frame, text="0%")
        self.cpu_usage_label.pack(side=tk.RIGHT)
        
        self.cpu_progress = ttk.Progressbar(cpu_frame, length=200, mode='determinate')
        self.cpu_progress.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Memory usage
        memory_frame = ttk.Frame(metrics_frame)
        memory_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(memory_frame, text="Memory Usage:").pack(side=tk.LEFT)
        self.memory_usage_label = ttk.Label(memory_frame, text="0%")
        self.memory_usage_label.pack(side=tk.RIGHT)
        
        self.memory_progress = ttk.Progressbar(memory_frame, length=200, mode='determinate')
        self.memory_progress.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Disk usage
        disk_frame = ttk.Frame(metrics_frame)
        disk_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(disk_frame, text="Disk Usage:").pack(side=tk.LEFT)
        self.disk_usage_label = ttk.Label(disk_frame, text="0%")
        self.disk_usage_label.pack(side=tk.RIGHT)
        
        self.disk_progress = ttk.Progressbar(disk_frame, length=200, mode='determinate')
        self.disk_progress.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Network activity
        network_frame = ttk.Frame(metrics_frame)
        network_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(network_frame, text="Network Activity:").pack(side=tk.LEFT)
        self.network_activity_label = ttk.Label(network_frame, text="0 KB/s")
        self.network_activity_label.pack(side=tk.RIGHT)
        
        # Process count
        process_frame = ttk.Frame(metrics_frame)
        process_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(process_frame, text="Process Count:").pack(side=tk.LEFT)
        self.process_count_label = ttk.Label(process_frame, text="0")
        self.process_count_label.pack(side=tk.RIGHT)
    
    def create_system_tab(self) -> None:
        """Create system diagnostics tab."""
        self.system_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.system_frame, text="System")
        
        # Toolbar
        toolbar = ttk.Frame(self.system_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="CPU Test", command=lambda: self.run_diagnostic("cpu_test")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Memory Test", command=lambda: self.run_diagnostic("memory_test")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Disk Test", command=lambda: self.run_diagnostic("disk_test")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Process Test", command=lambda: self.run_diagnostic("process_test")).pack(side=tk.LEFT, padx=5)
        
        # System info
        info_frame = ttk.LabelFrame(self.system_frame, text="System Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.system_info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=8)
        self.system_info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Diagnostic results
        results_frame = ttk.LabelFrame(self.system_frame, text="Diagnostic Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('test', 'status', 'message', 'timestamp')
        self.system_results_tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        
        self.system_results_tree.heading('test', text='Test')
        self.system_results_tree.heading('status', text='Status')
        self.system_results_tree.heading('message', text='Message')
        self.system_results_tree.heading('timestamp', text='Timestamp')
        
        system_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.system_results_tree.yview)
        self.system_results_tree.configure(yscrollcommand=system_scroll.set)
        
        self.system_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        system_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def create_network_tab(self) -> None:
        """Create network diagnostics tab."""
        self.network_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.network_frame, text="Network")
        
        # Toolbar
        toolbar = ttk.Frame(self.network_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="DNS Test", command=lambda: self.run_diagnostic("dns_test")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Connectivity Test", command=lambda: self.run_diagnostic("connectivity_test")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Port Scan", command=lambda: self.run_diagnostic("port_scan")).pack(side=tk.LEFT, padx=5)
        
        # Network info
        info_frame = ttk.LabelFrame(self.network_frame, text="Network Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.network_info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=6)
        self.network_info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Network diagnostics
        diag_frame = ttk.LabelFrame(self.network_frame, text="Network Diagnostics")
        diag_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('test', 'status', 'message', 'timestamp')
        self.network_results_tree = ttk.Treeview(diag_frame, columns=columns, show='headings')
        
        self.network_results_tree.heading('test', text='Test')
        self.network_results_tree.heading('status', text='Status')
        self.network_results_tree.heading('message', text='Message')
        self.network_results_tree.heading('timestamp', text='Timestamp')
        
        network_scroll = ttk.Scrollbar(diag_frame, orient=tk.VERTICAL, command=self.network_results_tree.yview)
        self.network_results_tree.configure(yscrollcommand=network_scroll.set)
        
        self.network_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        network_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def create_tor_tab(self) -> None:
        """Create Tor diagnostics tab."""
        self.tor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tor_frame, text="Tor")
        
        # Toolbar
        toolbar = ttk.Frame(self.tor_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Tor Status", command=lambda: self.run_diagnostic("tor_status")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="SOCKS Test", command=lambda: self.run_diagnostic("socks_test")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Circuit Test", command=lambda: self.run_diagnostic("circuit_test")).pack(side=tk.LEFT, padx=5)
        
        # Tor info
        info_frame = ttk.LabelFrame(self.tor_frame, text="Tor Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.tor_info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=6)
        self.tor_info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Tor diagnostics
        diag_frame = ttk.LabelFrame(self.tor_frame, text="Tor Diagnostics")
        diag_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('test', 'status', 'message', 'timestamp')
        self.tor_results_tree = ttk.Treeview(diag_frame, columns=columns, show='headings')
        
        self.tor_results_tree.heading('test', text='Test')
        self.tor_results_tree.heading('status', text='Status')
        self.tor_results_tree.heading('message', text='Message')
        self.tor_results_tree.heading('timestamp', text='Timestamp')
        
        tor_scroll = ttk.Scrollbar(diag_frame, orient=tk.VERTICAL, command=self.tor_results_tree.yview)
        self.tor_results_tree.configure(yscrollcommand=tor_scroll.set)
        
        self.tor_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        tor_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def create_logs_tab(self) -> None:
        """Create logs and history tab."""
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="Logs")
        
        # Toolbar
        toolbar = ttk.Frame(self.logs_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Export Logs", command=self.export_logs).pack(side=tk.LEFT, padx=5)
        
        # Log level filter
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.log_filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.log_filter_var,
                                  values=["all", "info", "warning", "error", "critical"],
                                  width=10, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(5, 0))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_log_filter)
        
        # Log display
        log_frame = ttk.LabelFrame(self.logs_frame, text="Diagnostic Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('timestamp', 'level', 'test', 'message')
        self.logs_tree = ttk.Treeview(log_frame, columns=columns, show='headings')
        
        self.logs_tree.heading('timestamp', text='Timestamp')
        self.logs_tree.heading('level', text='Level')
        self.logs_tree.heading('test', text='Test')
        self.logs_tree.heading('message', text='Message')
        
        logs_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.logs_tree.yview)
        self.logs_tree.configure(yscrollcommand=logs_scroll.set)
        
        self.logs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        logs_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to view details
        self.logs_tree.bind('<Double-1>', self.view_log_details)
    
    def setup_networking(self) -> None:
        """Setup networking components."""
        try:
            security_config = SecurityConfig(
                allowed_onions=[],
                certificate_pinning=True
            )
            self.http_client = TorHttpClient(security_config)
        except Exception as e:
            logger.error(f"Failed to setup networking: {e}")
            self.http_client = None
    
    def start_monitoring(self) -> None:
        """Start system monitoring."""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Initial system info
        self.update_system_info()
    
    def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        self.monitoring_active = False
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                self.collect_system_metrics()
                self.update_overview_display()
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(30)  # Wait longer on error
    
    def collect_system_metrics(self) -> None:
        """Collect current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            memory_total = memory.total
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used = disk.used
            disk_total = disk.total
            
            # Network stats
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent
            network_recv = network.bytes_recv
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (Unix only)
            load_average = []
            if hasattr(os, 'getloadavg'):
                load_average = list(os.getloadavg())
            
            # Create metrics
            metrics = SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used=memory_used,
                memory_total=memory_total,
                disk_percent=disk_percent,
                disk_used=disk_used,
                disk_total=disk_total,
                network_sent=network_sent,
                network_recv=network_recv,
                process_count=process_count,
                load_average=load_average
            )
            
            self.system_metrics.append(metrics)
            
            # Keep only last 100 metrics
            if len(self.system_metrics) > 100:
                self.system_metrics = self.system_metrics[-100:]
            
            logger.debug(f"Collected system metrics: CPU {cpu_percent}%, Memory {memory_percent}%")
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def update_overview_display(self) -> None:
        """Update overview display with current metrics."""
        if not self.system_metrics:
            return
        
        latest = self.system_metrics[-1]
        
        # Update CPU
        self.cpu_progress['value'] = latest.cpu_percent
        self.cpu_usage_label.configure(text=f"{latest.cpu_percent:.1f}%")
        
        # Update Memory
        self.memory_progress['value'] = latest.memory_percent
        memory_used_gb = latest.memory_used / (1024**3)
        memory_total_gb = latest.memory_total / (1024**3)
        self.memory_usage_label.configure(text=f"{latest.memory_percent:.1f}% ({memory_used_gb:.1f}/{memory_total_gb:.1f} GB)")
        
        # Update Disk
        self.disk_progress['value'] = latest.disk_percent
        disk_used_gb = latest.disk_used / (1024**3)
        disk_total_gb = latest.disk_total / (1024**3)
        self.disk_usage_label.configure(text=f"{latest.disk_percent:.1f}% ({disk_used_gb:.1f}/{disk_total_gb:.1f} GB)")
        
        # Update Network
        network_speed = 0
        if len(self.system_metrics) >= 2:
            prev = self.system_metrics[-2]
            time_diff = (latest.timestamp - prev.timestamp).total_seconds()
            if time_diff > 0:
                sent_diff = latest.network_sent - prev.network_sent
                recv_diff = latest.network_recv - prev.network_recv
                network_speed = (sent_diff + recv_diff) / time_diff / 1024  # KB/s
        
        self.network_activity_label.configure(text=f"{network_speed:.1f} KB/s")
        
        # Update Process Count
        self.process_count_label.configure(text=str(latest.process_count))
        
        # Update overall status
        self.update_overall_status()
    
    def update_overall_status(self) -> None:
        """Update overall system status."""
        if not self.system_metrics:
            status = HealthStatus.UNKNOWN
            status_text = "Unknown"
            status_color = "orange"
        else:
            latest = self.system_metrics[-1]
            
            # Determine status based on metrics
            if latest.cpu_percent > 90 or latest.memory_percent > 90 or latest.disk_percent > 95:
                status = HealthStatus.CRITICAL
                status_text = "Critical"
                status_color = "red"
            elif latest.cpu_percent > 80 or latest.memory_percent > 80 or latest.disk_percent > 85:
                status = HealthStatus.ERROR
                status_text = "Error"
                status_color = "red"
            elif latest.cpu_percent > 70 or latest.memory_percent > 70 or latest.disk_percent > 75:
                status = HealthStatus.WARNING
                status_text = "Warning"
                status_color = "orange"
            else:
                status = HealthStatus.HEALTHY
                status_text = "Healthy"
                status_color = "green"
        
        self.overall_status_label.configure(text=status_text, foreground=status_color)
    
    def update_system_info(self) -> None:
        """Update system information display."""
        try:
            info = f"""System: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Processor: {platform.processor()}
Python: {sys.version}
Hostname: {platform.node()}
Boot Time: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.system_info_text.delete(1.0, tk.END)
            self.system_info_text.insert(tk.END, info)
            
        except Exception as e:
            logger.error(f"Failed to update system info: {e}")
    
    def run_all_diagnostics(self) -> None:
        """Run all diagnostic tests."""
        tests = [
            "cpu_test",
            "memory_test", 
            "disk_test",
            "process_test",
            "dns_test",
            "connectivity_test",
            "tor_status",
            "socks_test"
        ]
        
        for test in tests:
            self.run_diagnostic(test)
    
    def run_diagnostic(self, test_name: str) -> None:
        """Run a specific diagnostic test."""
        start_time = time.time()
        
        try:
            if test_name == "cpu_test":
                result = self._cpu_test()
            elif test_name == "memory_test":
                result = self._memory_test()
            elif test_name == "disk_test":
                result = self._disk_test()
            elif test_name == "process_test":
                result = self._process_test()
            elif test_name == "dns_test":
                result = self._dns_test()
            elif test_name == "connectivity_test":
                result = self._connectivity_test()
            elif test_name == "port_scan":
                result = self._port_scan_test()
            elif test_name == "tor_status":
                result = self._tor_status_test()
            elif test_name == "socks_test":
                result = self._socks_test()
            elif test_name == "circuit_test":
                result = self._circuit_test()
            else:
                result = DiagnosticResult(
                    test_name=test_name,
                    status=HealthStatus.ERROR,
                    level=DiagnosticLevel.ERROR,
                    message="Unknown test",
                    details={},
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Add duration
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            
            # Store result
            self.diagnostic_results.append(result)
            
            # Update displays
            self.update_diagnostic_displays()
            
            logger.info(f"Diagnostic test '{test_name}' completed: {result.status.value}")
            
        except Exception as e:
            logger.error(f"Diagnostic test '{test_name}' failed: {e}")
            
            error_result = DiagnosticResult(
                test_name=test_name,
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - start_time) * 1000
            )
            
            self.diagnostic_results.append(error_result)
            self.update_diagnostic_displays()
    
    def _cpu_test(self) -> DiagnosticResult:
        """Test CPU performance."""
        try:
            # Run CPU stress test
            start_time = time.time()
            cpu_percent = psutil.cpu_percent(interval=1)
            end_time = time.time()
            
            # Check CPU usage
            if cpu_percent > 90:
                status = HealthStatus.CRITICAL
                level = DiagnosticLevel.CRITICAL
                message = f"CPU usage critically high: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = HealthStatus.ERROR
                level = DiagnosticLevel.ERROR
                message = f"CPU usage high: {cpu_percent:.1f}%"
            elif cpu_percent > 70:
                status = HealthStatus.WARNING
                level = DiagnosticLevel.WARNING
                message = f"CPU usage elevated: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            return DiagnosticResult(
                test_name="CPU Test",
                status=status,
                level=level,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="CPU Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"CPU test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _memory_test(self) -> DiagnosticResult:
        """Test memory usage and performance."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Check memory usage
            if memory.percent > 90:
                status = HealthStatus.CRITICAL
                level = DiagnosticLevel.CRITICAL
                message = f"Memory usage critically high: {memory.percent:.1f}%"
            elif memory.percent > 80:
                status = HealthStatus.ERROR
                level = DiagnosticLevel.ERROR
                message = f"Memory usage high: {memory.percent:.1f}%"
            elif memory.percent > 70:
                status = HealthStatus.WARNING
                level = DiagnosticLevel.WARNING
                message = f"Memory usage elevated: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"Memory usage normal: {memory.percent:.1f}%"
            
            return DiagnosticResult(
                test_name="Memory Test",
                status=status,
                level=level,
                message=message,
                details={
                    "memory_total": memory.total,
                    "memory_available": memory.available,
                    "memory_used": memory.used,
                    "memory_percent": memory.percent,
                    "swap_total": swap.total,
                    "swap_used": swap.used,
                    "swap_percent": swap.percent
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="Memory Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Memory test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _disk_test(self) -> DiagnosticResult:
        """Test disk usage and performance."""
        try:
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Check disk usage
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent > 95:
                status = HealthStatus.CRITICAL
                level = DiagnosticLevel.CRITICAL
                message = f"Disk usage critically high: {disk_percent:.1f}%"
            elif disk_percent > 90:
                status = HealthStatus.ERROR
                level = DiagnosticLevel.ERROR
                message = f"Disk usage high: {disk_percent:.1f}%"
            elif disk_percent > 80:
                status = HealthStatus.WARNING
                level = DiagnosticLevel.WARNING
                message = f"Disk usage elevated: {disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"Disk usage normal: {disk_percent:.1f}%"
            
            return DiagnosticResult(
                test_name="Disk Test",
                status=status,
                level=level,
                message=message,
                details={
                    "disk_total": disk.total,
                    "disk_used": disk.used,
                    "disk_free": disk.free,
                    "disk_percent": disk_percent,
                    "disk_read_count": disk_io.read_count if disk_io else 0,
                    "disk_write_count": disk_io.write_count if disk_io else 0
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="Disk Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Disk test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _process_test(self) -> DiagnosticResult:
        """Test process information and performance."""
        try:
            processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
            process_count = len(processes)
            
            # Find top processes by CPU and memory
            top_cpu = sorted(processes, key=lambda p: p.info.get('cpu_percent', 0), reverse=True)[:5]
            top_memory = sorted(processes, key=lambda p: p.info.get('memory_percent', 0), reverse=True)[:5]
            
            # Check process count
            if process_count > 1000:
                status = HealthStatus.WARNING
                level = DiagnosticLevel.WARNING
                message = f"High process count: {process_count}"
            else:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"Process count normal: {process_count}"
            
            return DiagnosticResult(
                test_name="Process Test",
                status=status,
                level=level,
                message=message,
                details={
                    "process_count": process_count,
                    "top_cpu_processes": [
                        {
                            "pid": p.info['pid'],
                            "name": p.info['name'],
                            "cpu_percent": p.info.get('cpu_percent', 0)
                        } for p in top_cpu
                    ],
                    "top_memory_processes": [
                        {
                            "pid": p.info['pid'],
                            "name": p.info['name'],
                            "memory_percent": p.info.get('memory_percent', 0)
                        } for p in top_memory
                    ]
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="Process Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Process test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _dns_test(self) -> DiagnosticResult:
        """Test DNS resolution."""
        try:
            test_hostnames = ["google.com", "cloudflare.com", "1.1.1.1"]
            results = []
            
            for hostname in test_hostnames:
                try:
                    start_time = time.time()
                    ip = socket.gethostbyname(hostname)
                    resolve_time = (time.time() - start_time) * 1000
                    results.append({
                        "hostname": hostname,
                        "ip": ip,
                        "resolve_time_ms": resolve_time,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "hostname": hostname,
                        "error": str(e),
                        "success": False
                    })
            
            # Check results
            success_count = sum(1 for r in results if r["success"])
            
            if success_count == 0:
                status = HealthStatus.CRITICAL
                level = DiagnosticLevel.CRITICAL
                message = "DNS resolution completely failed"
            elif success_count < len(test_hostnames):
                status = HealthStatus.WARNING
                level = DiagnosticLevel.WARNING
                message = f"DNS resolution partially failed: {success_count}/{len(test_hostnames)}"
            else:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"DNS resolution working: {success_count}/{len(test_hostnames)}"
            
            return DiagnosticResult(
                test_name="DNS Test",
                status=status,
                level=level,
                message=message,
                details={"results": results},
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="DNS Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"DNS test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _connectivity_test(self) -> DiagnosticResult:
        """Test network connectivity."""
        try:
            test_hosts = [
                ("8.8.8.8", 53),  # Google DNS
                ("1.1.1.1", 53),  # Cloudflare DNS
                ("208.67.222.222", 53)  # OpenDNS
            ]
            
            results = []
            
            for host, port in test_hosts:
                try:
                    start_time = time.time()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    connect_time = (time.time() - start_time) * 1000
                    sock.close()
                    
                    results.append({
                        "host": host,
                        "port": port,
                        "success": result == 0,
                        "connect_time_ms": connect_time
                    })
                except Exception as e:
                    results.append({
                        "host": host,
                        "port": port,
                        "error": str(e),
                        "success": False
                    })
            
            # Check results
            success_count = sum(1 for r in results if r["success"])
            
            if success_count == 0:
                status = HealthStatus.CRITICAL
                level = DiagnosticLevel.CRITICAL
                message = "Network connectivity completely failed"
            elif success_count < len(test_hosts):
                status = HealthStatus.WARNING
                level = DiagnosticLevel.WARNING
                message = f"Network connectivity degraded: {success_count}/{len(test_hosts)}"
            else:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"Network connectivity working: {success_count}/{len(test_hosts)}"
            
            return DiagnosticResult(
                test_name="Connectivity Test",
                status=status,
                level=level,
                message=message,
                details={"results": results},
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="Connectivity Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Connectivity test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _port_scan_test(self) -> None:
        """Port scan test (placeholder)."""
        # This would implement port scanning functionality
        pass
    
    def _tor_status_test(self) -> DiagnosticResult:
        """Test Tor status and connectivity."""
        try:
            # Check if Tor is running
            tor_running = False
            socks_port = None
            
            try:
                # Try to connect to Tor SOCKS port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', 9150))  # Default Tor SOCKS port
                if result == 0:
                    tor_running = True
                    socks_port = 9150
                sock.close()
            except:
                pass
            
            if not tor_running:
                # Try alternative port
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('127.0.0.1', 9050))  # Alternative Tor SOCKS port
                    if result == 0:
                        tor_running = True
                        socks_port = 9050
                    sock.close()
                except:
                    pass
            
            if tor_running:
                status = HealthStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"Tor is running on port {socks_port}"
            else:
                status = HealthStatus.ERROR
                level = DiagnosticLevel.ERROR
                message = "Tor is not running or not accessible"
            
            return DiagnosticResult(
                test_name="Tor Status",
                status=status,
                level=level,
                message=message,
                details={
                    "tor_running": tor_running,
                    "socks_port": socks_port
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="Tor Status",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Tor status test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _socks_test(self) -> DiagnosticResult:
        """Test SOCKS proxy functionality."""
        try:
            # This would test SOCKS proxy through Tor
            # For now, just check if we can make a request through Tor
            
            if self.http_client:
                try:
                    # Try to make a request through Tor
                    response = self.http_client.get("https://httpbin.org/ip", timeout=10)
                    if response.status_code == 200:
                        status = HealthStatus.HEALTHY
                        level = DiagnosticLevel.INFO
                        message = "SOCKS proxy working correctly"
                        details = {"response": response.json()}
                    else:
                        status = HealthStatus.WARNING
                        level = DiagnosticLevel.WARNING
                        message = f"SOCKS proxy returned status {response.status_code}"
                        details = {"status_code": response.status_code}
                except Exception as e:
                    status = HealthStatus.ERROR
                    level = DiagnosticLevel.ERROR
                    message = f"SOCKS proxy test failed: {e}"
                    details = {"error": str(e)}
            else:
                status = HealthStatus.ERROR
                level = DiagnosticLevel.ERROR
                message = "HTTP client not available"
                details = {"error": "No HTTP client"}
            
            return DiagnosticResult(
                test_name="SOCKS Test",
                status=status,
                level=level,
                message=message,
                details=details,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="SOCKS Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"SOCKS test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def _circuit_test(self) -> DiagnosticResult:
        """Test Tor circuit functionality."""
        try:
            # This would test Tor circuit building and management
            # For now, return a placeholder result
            
            return DiagnosticResult(
                test_name="Circuit Test",
                status=HealthStatus.HEALTHY,
                level=DiagnosticLevel.INFO,
                message="Circuit test completed (placeholder)",
                details={"note": "Circuit test not yet implemented"},
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="Circuit Test",
                status=HealthStatus.ERROR,
                level=DiagnosticLevel.ERROR,
                message=f"Circuit test failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc)
            )
    
    def update_diagnostic_displays(self) -> None:
        """Update all diagnostic result displays."""
        # Update system results
        self._update_results_tree(self.system_results_tree, "system")
        
        # Update network results
        self._update_results_tree(self.network_results_tree, "network")
        
        # Update Tor results
        self._update_results_tree(self.tor_results_tree, "tor")
        
        # Update logs
        self.update_logs_display()
    
    def _update_results_tree(self, tree: ttk.Treeview, category: str) -> None:
        """Update a specific results tree."""
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Filter results by category
        category_tests = {
            "system": ["cpu_test", "memory_test", "disk_test", "process_test"],
            "network": ["dns_test", "connectivity_test", "port_scan"],
            "tor": ["tor_status", "socks_test", "circuit_test"]
        }
        
        relevant_tests = category_tests.get(category, [])
        
        # Add results
        for result in self.diagnostic_results:
            if result.test_name.lower().replace(" ", "_") in relevant_tests:
                timestamp_str = result.timestamp.strftime("%H:%M:%S")
                
                # Status color
                status_colors = {
                    "healthy": "green",
                    "warning": "orange",
                    "error": "red",
                    "critical": "red",
                    "unknown": "gray"
                }
                
                item = tree.insert('', 'end', values=(
                    result.test_name,
                    result.status.value.title(),
                    result.message,
                    timestamp_str
                ))
    
    def update_logs_display(self) -> None:
        """Update logs display."""
        # Clear existing items
        for item in self.logs_tree.get_children():
            self.logs_tree.delete(item)
        
        # Add results
        for result in self.diagnostic_results:
            # Apply filter
            if self.log_filter_var.get() != "all" and result.level.value != self.log_filter_var.get():
                continue
            
            timestamp_str = result.timestamp.strftime("%H:%M:%S")
            
            item = self.logs_tree.insert('', 'end', values=(
                timestamp_str,
                result.level.value.upper(),
                result.test_name,
                result.message
            ))
    
    def apply_log_filter(self, event=None) -> None:
        """Apply filter to logs display."""
        self.update_logs_display()
    
    def view_log_details(self, event) -> None:
        """View detailed log information."""
        selection = self.logs_tree.selection()
        if not selection:
            return
        
        item = self.logs_tree.item(selection[0])
        values = item['values']
        
        # Find the corresponding result
        timestamp_str = values[0]
        test_name = values[2]
        
        result = None
        for r in self.diagnostic_results:
            if (r.timestamp.strftime("%H:%M:%S") == timestamp_str and 
                r.test_name == test_name):
                result = r
                break
        
        if not result:
            return
        
        # Create details dialog
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title(f"Diagnostic Details - {result.test_name}")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        
        # Details text
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=70, height=25)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format details
        details = f"""Test: {result.test_name}
Status: {result.status.value.title()}
Level: {result.level.value.upper()}
Message: {result.message}
Timestamp: {result.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
Duration: {result.duration_ms:.2f} ms

Details:
{json.dumps(result.details, indent=2)}
"""
        
        details_text.insert(tk.END, details)
        details_text.configure(state=tk.DISABLED)
        
        # Close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def refresh_overview(self) -> None:
        """Refresh overview display."""
        self.update_system_info()
        self.update_overview_display()
    
    def clear_logs(self) -> None:
        """Clear diagnostic logs."""
        self.diagnostic_results.clear()
        self.update_diagnostic_displays()
    
    def export_logs(self) -> None:
        """Export diagnostic logs."""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Diagnostic Logs"
        )
        
        if filename:
            try:
                export_data = {
                    "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "diagnostic_results": [result.to_dict() for result in self.diagnostic_results],
                    "system_metrics": [metrics.to_dict() for metrics in self.system_metrics[-50:]]  # Last 50 metrics
                }
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Diagnostic logs exported to {filename}")
                
            except Exception as e:
                logger.error(f"Log export failed: {e}")
                messagebox.showerror("Error", f"Failed to export logs: {e}")
    
    def load_diagnostic_history(self) -> None:
        """Load diagnostic history from storage."""
        try:
            history_data = self.config_manager.load_config("diagnostic_history", default_data={})
            
            # Load diagnostic results
            results_data = history_data.get("results", [])
            self.diagnostic_results.clear()
            
            for result_dict in results_data:
                result = DiagnosticResult.from_dict(result_dict)
                self.diagnostic_results.append(result)
            
            # Load system metrics (limited to last 100)
            metrics_data = history_data.get("metrics", [])
            self.system_metrics.clear()
            
            for metrics_dict in metrics_data[-100:]:
                metrics = SystemMetrics(**metrics_dict)
                metrics.timestamp = datetime.fromisoformat(metrics_dict['timestamp'])
                self.system_metrics.append(metrics)
            
            logger.info(f"Loaded diagnostic history: {len(self.diagnostic_results)} results, {len(self.system_metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Failed to load diagnostic history: {e}")
    
    def save_diagnostic_history(self) -> None:
        """Save diagnostic history to storage."""
        try:
            history_data = {
                "results": [result.to_dict() for result in self.diagnostic_results[-1000:]],  # Last 1000 results
                "metrics": [metrics.to_dict() for metrics in self.system_metrics[-100:]]  # Last 100 metrics
            }
            
            self.config_manager.save_config("diagnostic_history", history_data)
            
            logger.debug(f"Saved diagnostic history: {len(self.diagnostic_results)} results, {len(self.system_metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Failed to save diagnostic history: {e}")

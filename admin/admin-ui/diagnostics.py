# Path: admin/admin-ui/diagnostics.py
# Lucid Admin UI - System Diagnostics
# Provides comprehensive system health monitoring and diagnostics
# LUCID-STRICT Layer 1 Core Infrastructure

from __future__ import annotations

import asyncio
import logging
import os
import psutil
import time
import json
import subprocess
import platform
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import docker
import requests
import aiohttp

logger = logging.getLogger(__name__)

# Configuration from environment
DIAGNOSTICS_INTERVAL = int(os.getenv("DIAGNOSTICS_INTERVAL", "30"))  # seconds
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))  # seconds
MAX_LOG_LINES = int(os.getenv("MAX_LOG_LINES", "1000"))
DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")


class DiagnosticLevel(Enum):
    """Diagnostic severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemStatus(Enum):
    """Overall system status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class DiagnosticResult:
    """Individual diagnostic result"""
    name: str
    status: SystemStatus
    level: DiagnosticLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None


@dataclass
class SystemDiagnostics:
    """Complete system diagnostics report"""
    overall_status: SystemStatus
    timestamp: datetime
    diagnostics: List[DiagnosticResult] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class SystemDiagnostics:
    """System diagnostics and health monitoring service"""
    
    def __init__(self):
        self.docker_client = None
        self._initialize_docker_client()
        
    def _initialize_docker_client(self):
        """Initialize Docker client"""
        try:
            if os.path.exists(DOCKER_SOCKET_PATH):
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized successfully")
            else:
                logger.warning("Docker socket not found, Docker diagnostics will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
    
    async def run_full_diagnostics(self) -> SystemDiagnostics:
        """Run comprehensive system diagnostics"""
        logger.info("Starting full system diagnostics")
        start_time = time.time()
        
        diagnostics = []
        
        # System resource diagnostics
        diagnostics.extend(await self._check_system_resources())
        
        # Docker diagnostics
        diagnostics.extend(await self._check_docker_services())
        
        # Network diagnostics
        diagnostics.extend(await self._check_network_connectivity())
        
        # Storage diagnostics
        diagnostics.extend(await self._check_storage_health())
        
        # Service health checks
        diagnostics.extend(await self._check_service_health())
        
        # Security diagnostics
        diagnostics.extend(await self._check_security_status())
        
        # Performance metrics
        performance_metrics = await self._collect_performance_metrics()
        
        # System information
        system_info = self._collect_system_info()
        
        # Determine overall status
        overall_status = self._determine_overall_status(diagnostics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(diagnostics)
        
        duration = (time.time() - start_time) * 1000
        
        return SystemDiagnostics(
            overall_status=overall_status,
            timestamp=datetime.now(timezone.utc),
            diagnostics=diagnostics,
            system_info=system_info,
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )
    
    async def _check_system_resources(self) -> List[DiagnosticResult]:
        """Check system resource utilization"""
        diagnostics = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = SystemStatus.HEALTHY if cpu_percent < 80 else SystemStatus.DEGRADED
            if cpu_percent > 95:
                cpu_status = SystemStatus.CRITICAL
                
            diagnostics.append(DiagnosticResult(
                name="cpu_usage",
                status=cpu_status,
                level=DiagnosticLevel.WARNING if cpu_percent > 80 else DiagnosticLevel.INFO,
                message=f"CPU usage: {cpu_percent:.1f}%",
                details={"cpu_percent": cpu_percent, "cpu_count": psutil.cpu_count()}
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_status = SystemStatus.HEALTHY if memory.percent < 80 else SystemStatus.DEGRADED
            if memory.percent > 95:
                memory_status = SystemStatus.CRITICAL
                
            diagnostics.append(DiagnosticResult(
                name="memory_usage",
                status=memory_status,
                level=DiagnosticLevel.WARNING if memory.percent > 80 else DiagnosticLevel.INFO,
                message=f"Memory usage: {memory.percent:.1f}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)",
                details={
                    "memory_percent": memory.percent,
                    "memory_used_gb": memory.used / (1024**3),
                    "memory_total_gb": memory.total / (1024**3),
                    "memory_available_gb": memory.available / (1024**3)
                }
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_status = SystemStatus.HEALTHY if disk.percent < 80 else SystemStatus.DEGRADED
            if disk.percent > 95:
                disk_status = SystemStatus.CRITICAL
                
            diagnostics.append(DiagnosticResult(
                name="disk_usage",
                status=disk_status,
                level=DiagnosticLevel.WARNING if disk.percent > 80 else DiagnosticLevel.INFO,
                message=f"Disk usage: {disk.percent:.1f}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)",
                details={
                    "disk_percent": disk.percent,
                    "disk_used_gb": disk.used / (1024**3),
                    "disk_total_gb": disk.total / (1024**3),
                    "disk_free_gb": disk.free / (1024**3)
                }
            ))
            
            # Load average (Unix systems)
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()
                cpu_count = psutil.cpu_count()
                load_status = SystemStatus.HEALTHY if load_avg[0] < cpu_count else SystemStatus.DEGRADED
                
                diagnostics.append(DiagnosticResult(
                    name="load_average",
                    status=load_status,
                    level=DiagnosticLevel.WARNING if load_avg[0] > cpu_count else DiagnosticLevel.INFO,
                    message=f"Load average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}",
                    details={"load_1min": load_avg[0], "load_5min": load_avg[1], "load_15min": load_avg[2], "cpu_count": cpu_count}
                ))
                
        except Exception as e:
            diagnostics.append(DiagnosticResult(
                name="system_resources",
                status=SystemStatus.CRITICAL,
                level=DiagnosticLevel.ERROR,
                message=f"Failed to check system resources: {e}",
                details={"error": str(e)}
            ))
        
        return diagnostics
    
    async def _check_docker_services(self) -> List[DiagnosticResult]:
        """Check Docker services and containers"""
        diagnostics = []
        
        if not self.docker_client:
            diagnostics.append(DiagnosticResult(
                name="docker_services",
                status=SystemStatus.UNKNOWN,
                level=DiagnosticLevel.WARNING,
                message="Docker client not available",
                details={"reason": "Docker socket not accessible"}
            ))
            return diagnostics
        
        try:
            # Check Docker daemon
            docker_info = self.docker_client.info()
            diagnostics.append(DiagnosticResult(
                name="docker_daemon",
                status=SystemStatus.HEALTHY,
                level=DiagnosticLevel.INFO,
                message="Docker daemon is running",
                details={
                    "containers_running": docker_info.get('ContainersRunning', 0),
                    "containers_stopped": docker_info.get('ContainersStopped', 0),
                    "images": docker_info.get('Images', 0),
                    "docker_version": docker_info.get('ServerVersion', 'unknown')
                }
            ))
            
            # Check Lucid containers
            lucid_containers = self.docker_client.containers.list(filters={"label": "lucid.service"})
            running_containers = [c for c in lucid_containers if c.status == 'running']
            
            if len(running_containers) == len(lucid_containers) and len(lucid_containers) > 0:
                status = SystemStatus.HEALTHY
                level = DiagnosticLevel.INFO
                message = f"All {len(lucid_containers)} Lucid containers are running"
            elif len(running_containers) > 0:
                status = SystemStatus.DEGRADED
                level = DiagnosticLevel.WARNING
                message = f"{len(running_containers)}/{len(lucid_containers)} Lucid containers are running"
            else:
                status = SystemStatus.CRITICAL
                level = DiagnosticLevel.ERROR
                message = "No Lucid containers are running"
            
            diagnostics.append(DiagnosticResult(
                name="lucid_containers",
                status=status,
                level=level,
                message=message,
                details={
                    "total_containers": len(lucid_containers),
                    "running_containers": len(running_containers),
                    "container_names": [c.name for c in lucid_containers]
                }
            ))
            
        except Exception as e:
            diagnostics.append(DiagnosticResult(
                name="docker_services",
                status=SystemStatus.CRITICAL,
                level=DiagnosticLevel.ERROR,
                message=f"Failed to check Docker services: {e}",
                details={"error": str(e)}
            ))
        
        return diagnostics
    
    async def _check_network_connectivity(self) -> List[DiagnosticResult]:
        """Check network connectivity and services"""
        diagnostics = []
        
        # Test endpoints - configured via environment variables
        blockchain_url = os.getenv("BLOCKCHAIN_ENGINE_URL") or os.getenv("BLOCKCHAIN_URL") or ""
        auth_url = os.getenv("AUTH_SERVICE_URL") or ""
        admin_ui_url = os.getenv("ADMIN_UI_URL") or ""
        
        endpoints = []
        if blockchain_url:
            endpoints.append({"name": "blockchain-api", "url": blockchain_url, "service": "blockchain-api"})
        if auth_url:
            endpoints.append({"name": "authentication", "url": auth_url, "service": "authentication"})
        if admin_ui_url:
            endpoints.append({"name": "admin-ui", "url": admin_ui_url, "service": "admin-ui"})
        
        for endpoint in endpoints:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=HEALTH_CHECK_TIMEOUT)) as session:
                    async with session.get(endpoint["url"]) as response:
                        if response.status == 200:
                            status = SystemStatus.HEALTHY
                            level = DiagnosticLevel.INFO
                            message = f"{endpoint['service']} is responding"
                        else:
                            status = SystemStatus.DEGRADED
                            level = DiagnosticLevel.WARNING
                            message = f"{endpoint['service']} returned status {response.status}"
                        
                        diagnostics.append(DiagnosticResult(
                            name=f"service_{endpoint['service']}",
                            status=status,
                            level=level,
                            message=message,
                            details={"url": endpoint["url"], "status_code": response.status}
                        ))
                        
            except asyncio.TimeoutError:
                diagnostics.append(DiagnosticResult(
                    name=f"service_{endpoint['service']}",
                    status=SystemStatus.CRITICAL,
                    level=DiagnosticLevel.ERROR,
                    message=f"{endpoint['service']} is not responding (timeout)",
                    details={"url": endpoint["url"], "timeout": HEALTH_CHECK_TIMEOUT}
                ))
            except Exception as e:
                diagnostics.append(DiagnosticResult(
                    name=f"service_{endpoint['service']}",
                    status=SystemStatus.CRITICAL,
                    level=DiagnosticLevel.ERROR,
                    message=f"{endpoint['service']} connection failed: {e}",
                    details={"url": endpoint["url"], "error": str(e)}
                ))
        
        return diagnostics
    
    async def _check_storage_health(self) -> List[DiagnosticResult]:
        """Check storage health and permissions"""
        diagnostics = []
        
        # Check critical directories
        critical_dirs = [
            "/data",
            "/data/rdp_sessions",
            "/data/rdp_recordings",
            "/data/blockchain",
            "/data/wallet",
            "/secrets"
        ]
        
        for dir_path in critical_dirs:
            try:
                path = Path(dir_path)
                if path.exists():
                    if path.is_dir():
                        # Check if writable
                        test_file = path / ".write_test"
                        try:
                            test_file.touch()
                            test_file.unlink()
                            status = SystemStatus.HEALTHY
                            level = DiagnosticLevel.INFO
                            message = f"Directory {dir_path} is accessible and writable"
                        except PermissionError:
                            status = SystemStatus.CRITICAL
                            level = DiagnosticLevel.ERROR
                            message = f"Directory {dir_path} is not writable"
                        
                        # Check disk space
                        stat = path.stat()
                        diagnostics.append(DiagnosticResult(
                            name=f"directory_{dir_path.replace('/', '_')}",
                            status=status,
                            level=level,
                            message=message,
                            details={"path": dir_path, "exists": True, "writable": status == SystemStatus.HEALTHY}
                        ))
                    else:
                        diagnostics.append(DiagnosticResult(
                            name=f"directory_{dir_path.replace('/', '_')}",
                            status=SystemStatus.CRITICAL,
                            level=DiagnosticLevel.ERROR,
                            message=f"Path {dir_path} exists but is not a directory",
                            details={"path": dir_path, "exists": True, "is_directory": False}
                        ))
                else:
                    diagnostics.append(DiagnosticResult(
                        name=f"directory_{dir_path.replace('/', '_')}",
                        status=SystemStatus.DEGRADED,
                        level=DiagnosticLevel.WARNING,
                        message=f"Directory {dir_path} does not exist",
                        details={"path": dir_path, "exists": False}
                    ))
                    
            except Exception as e:
                diagnostics.append(DiagnosticResult(
                    name=f"directory_{dir_path.replace('/', '_')}",
                    status=SystemStatus.CRITICAL,
                    level=DiagnosticLevel.ERROR,
                    message=f"Failed to check directory {dir_path}: {e}",
                    details={"path": dir_path, "error": str(e)}
                ))
        
        return diagnostics
    
    async def _check_service_health(self) -> List[DiagnosticResult]:
        """Check individual service health"""
        diagnostics = []
        
        # Check if critical processes are running
        critical_processes = [
            {"name": "xrdp", "description": "XRDP server"},
            {"name": "mongod", "description": "MongoDB daemon"},
            {"name": "docker", "description": "Docker daemon"}
        ]
        
        for process_info in critical_processes:
            try:
                running_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_info["name"] in proc.info['name']:
                            running_processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if running_processes:
                    status = SystemStatus.HEALTHY
                    level = DiagnosticLevel.INFO
                    message = f"{process_info['description']} is running ({len(running_processes)} processes)"
                else:
                    status = SystemStatus.CRITICAL
                    level = DiagnosticLevel.ERROR
                    message = f"{process_info['description']} is not running"
                
                diagnostics.append(DiagnosticResult(
                    name=f"process_{process_info['name']}",
                    status=status,
                    level=level,
                    message=message,
                    details={"process_name": process_info["name"], "running_count": len(running_processes)}
                ))
                
            except Exception as e:
                diagnostics.append(DiagnosticResult(
                    name=f"process_{process_info['name']}",
                    status=SystemStatus.UNKNOWN,
                    level=DiagnosticLevel.WARNING,
                    message=f"Failed to check {process_info['description']}: {e}",
                    details={"process_name": process_info["name"], "error": str(e)}
                ))
        
        return diagnostics
    
    async def _check_security_status(self) -> List[DiagnosticResult]:
        """Check security-related configurations"""
        diagnostics = []
        
        # Check file permissions on sensitive files
        sensitive_files = [
            "/etc/xrdp/xrdp.ini",
            "/etc/xrdp/sesman.ini",
            "/secrets/",
            "/data/wallet/"
        ]
        
        for file_path in sensitive_files:
            try:
                path = Path(file_path)
                if path.exists():
                    stat = path.stat()
                    # Check if file is readable by others (security risk)
                    if stat.st_mode & 0o044:  # Readable by group or others
                        status = SystemStatus.DEGRADED
                        level = DiagnosticLevel.WARNING
                        message = f"File {file_path} has overly permissive permissions"
                    else:
                        status = SystemStatus.HEALTHY
                        level = DiagnosticLevel.INFO
                        message = f"File {file_path} has secure permissions"
                    
                    diagnostics.append(DiagnosticResult(
                        name=f"security_{file_path.replace('/', '_')}",
                        status=status,
                        level=level,
                        message=message,
                        details={"path": file_path, "permissions": oct(stat.st_mode)}
                    ))
                    
            except Exception as e:
                diagnostics.append(DiagnosticResult(
                    name=f"security_{file_path.replace('/', '_')}",
                    status=SystemStatus.UNKNOWN,
                    level=DiagnosticLevel.WARNING,
                    message=f"Failed to check security for {file_path}: {e}",
                    details={"path": file_path, "error": str(e)}
                ))
        
        return diagnostics
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics"""
        metrics = {}
        
        try:
            # System metrics
            metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
            metrics["memory_percent"] = psutil.virtual_memory().percent
            metrics["disk_percent"] = psutil.disk_usage('/').percent
            
            # Network metrics
            net_io = psutil.net_io_counters()
            metrics["network_bytes_sent"] = net_io.bytes_sent
            metrics["network_bytes_recv"] = net_io.bytes_recv
            
            # Process metrics
            metrics["process_count"] = len(psutil.pids())
            
            # Docker metrics (if available)
            if self.docker_client:
                try:
                    containers = self.docker_client.containers.list()
                    metrics["docker_containers"] = len(containers)
                    metrics["docker_running_containers"] = len([c for c in containers if c.status == 'running'])
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add Docker info if available
        if self.docker_client:
            try:
                docker_info = self.docker_client.info()
                info["docker_version"] = docker_info.get('ServerVersion', 'unknown')
                info["docker_containers"] = docker_info.get('Containers', 0)
                info["docker_images"] = docker_info.get('Images', 0)
            except:
                pass
        
        return info
    
    def _determine_overall_status(self, diagnostics: List[DiagnosticResult]) -> SystemStatus:
        """Determine overall system status based on individual diagnostics"""
        if not diagnostics:
            return SystemStatus.UNKNOWN
        
        critical_count = sum(1 for d in diagnostics if d.status == SystemStatus.CRITICAL)
        degraded_count = sum(1 for d in diagnostics if d.status == SystemStatus.DEGRADED)
        
        if critical_count > 0:
            return SystemStatus.CRITICAL
        elif degraded_count > 0:
            return SystemStatus.DEGRADED
        else:
            return SystemStatus.HEALTHY
    
    def _generate_recommendations(self, diagnostics: List[DiagnosticResult]) -> List[str]:
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        for diagnostic in diagnostics:
            if diagnostic.status == SystemStatus.CRITICAL:
                if "cpu" in diagnostic.name and diagnostic.details.get("cpu_percent", 0) > 95:
                    recommendations.append("Consider scaling up CPU resources or optimizing CPU-intensive processes")
                elif "memory" in diagnostic.name and diagnostic.details.get("memory_percent", 0) > 95:
                    recommendations.append("Consider increasing memory allocation or optimizing memory usage")
                elif "disk" in diagnostic.name and diagnostic.details.get("disk_percent", 0) > 95:
                    recommendations.append("Critical: Disk space is nearly full. Clean up old files or expand storage")
                elif "container" in diagnostic.name:
                    recommendations.append("Check Docker container logs and restart failed services")
                elif "service" in diagnostic.name:
                    recommendations.append(f"Service {diagnostic.name} is not responding. Check service status and logs")
            
            elif diagnostic.status == SystemStatus.DEGRADED:
                if "cpu" in diagnostic.name and diagnostic.details.get("cpu_percent", 0) > 80:
                    recommendations.append("Monitor CPU usage - consider optimization if trend continues")
                elif "memory" in diagnostic.name and diagnostic.details.get("memory_percent", 0) > 80:
                    recommendations.append("Monitor memory usage - consider optimization if trend continues")
                elif "disk" in diagnostic.name and diagnostic.details.get("disk_percent", 0) > 80:
                    recommendations.append("Disk space is getting low - consider cleanup or expansion")
        
        return recommendations
    
    async def get_logs(self, service: str, lines: int = 100) -> List[str]:
        """Get recent logs for a specific service"""
        try:
            if self.docker_client:
                containers = self.docker_client.containers.list(filters={"label": f"lucid.service={service}"})
                if containers:
                    container = containers[0]
                    logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
                    return logs.split('\n')[-lines:]
            
            # Fallback to system logs
            log_paths = [
                f"/var/log/{service}.log",
                f"/var/log/lucid/{service}.log",
                f"/data/logs/{service}.log"
            ]
            
            for log_path in log_paths:
                if Path(log_path).exists():
                    with open(log_path, 'r') as f:
                        all_lines = f.readlines()
                        return [line.strip() for line in all_lines[-lines:]]
            
            return [f"No logs found for service: {service}"]
            
        except Exception as e:
            logger.error(f"Failed to get logs for {service}: {e}")
            return [f"Error retrieving logs: {e}"]


# Global diagnostics instance
diagnostics_service = SystemDiagnostics()


async def get_system_diagnostics() -> SystemDiagnostics:
    """Get current system diagnostics"""
    return await diagnostics_service.run_full_diagnostics()


async def get_service_logs(service: str, lines: int = 100) -> List[str]:
    """Get logs for a specific service"""
    return await diagnostics_service.get_logs(service, lines)


if __name__ == "__main__":
    # Test the diagnostics service
    async def test_diagnostics():
        diagnostics = await get_system_diagnostics()
        print(f"System Status: {diagnostics.overall_status}")
        print(f"Diagnostics Count: {len(diagnostics.diagnostics)}")
        for diagnostic in diagnostics.diagnostics:
            print(f"  {diagnostic.name}: {diagnostic.status} - {diagnostic.message}")
        
        if diagnostics.recommendations:
            print("\nRecommendations:")
            for rec in diagnostics.recommendations:
                print(f"  - {rec}")
    
    asyncio.run(test_diagnostics())

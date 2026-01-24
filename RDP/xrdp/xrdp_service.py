# LUCID XRDP Service Manager - XRDP Service Management
# LUCID-STRICT Layer 2 Service Integration with Security Hardening
# Multi-platform support for Pi 5 ARM64
# Hardened container implementation with security best practices

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """XRDP service status states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    RESTARTING = "restarting"

@dataclass
class XRDPProcess:
    """XRDP process information"""
    process_id: str
    port: int
    status: ServiceStatus
    process: Optional[subprocess.Popen] = None
    config_path: Optional[Path] = None
    log_path: Optional[Path] = None
    session_path: Optional[Path] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    pid: Optional[int] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)

class XRDPServiceManager:
    """
    XRDP service manager for Lucid system.
    
    Manages XRDP service lifecycle, process monitoring, and resource management.
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self):
        """Initialize XRDP service manager"""
        self.active_processes: Dict[str, XRDPProcess] = {}
        self.monitor_tasks: Dict[str, asyncio.Task] = {}
        
        # Service configuration - use writable volume mount locations
        # /app/config and /app/logs are volume mounts (writable in container)
        self.base_config_path = Path("/app/config/servers")
        self.base_log_path = Path("/app/logs/servers")
        self.base_session_path = Path("/app/config/sessions")
        
        # Validate base paths for security (prevent directory traversal)
        self._validate_base_paths()
        
        # XRDP binary paths - verify existence and permissions
        self.xrdp_binary = self._get_executable_path("xrdp", "/usr/sbin/xrdp")
        self.xrdp_sesman = self._get_executable_path("xrdp-sesman", "/usr/sbin/xrdp-sesman")
        
        # Service limits - enforce reasonable bounds for security
        try:
            max_procs = int(os.getenv("MAX_XRDP_PROCESSES", "10"))
            self.max_processes = max(1, min(max_procs, 100))  # Clamp between 1-100
        except (ValueError, TypeError):
            self.max_processes = 10
            
        try:
            timeout = int(os.getenv("PROCESS_TIMEOUT", "30"))
            self.process_timeout = max(5, min(timeout, 300))  # Clamp between 5-300 seconds
        except (ValueError, TypeError):
            self.process_timeout = 30
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [self.base_config_path, self.base_log_path, self.base_session_path]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
    def _validate_base_paths(self) -> None:
        """Validate base paths to prevent directory traversal attacks"""
        for path in [self.base_config_path, self.base_log_path, self.base_session_path]:
            # Ensure path is absolute and resolve symlinks
            resolved = path.resolve()
            # Only allow paths under /app or /var/lib
            if not (str(resolved).startswith("/app/") or str(resolved).startswith("/var/lib/")):
                raise ValueError(f"Security: Path {path} outside allowed directories")
            logger.info(f"Validated path: {resolved}")
    
    def _get_executable_path(self, executable_name: str, default_path: str) -> str:
        """
        Get path to executable with security validation.
        
        Args:
            executable_name: Name of the executable
            default_path: Default absolute path to check
            
        Returns:
            Validated path to executable
            
        Raises:
            RuntimeError if executable not found or not executable
        """
        # Check environment override (allow flexibility)
        env_path = os.getenv(f"{executable_name.upper()}_PATH")
        paths_to_check = [env_path] if env_path else []
        paths_to_check.append(default_path)
        
        for path in paths_to_check:
            if not path:
                continue
            
            # Security: Only allow absolute paths
            if not os.path.isabs(path):
                logger.warning(f"Security: Rejecting relative path for {executable_name}: {path}")
                continue
            
            # Security: Ensure path doesn't contain suspicious patterns
            if ".." in path or path.count("//") > 1:
                logger.warning(f"Security: Rejecting suspicious path for {executable_name}: {path}")
                continue
            
            # Check if executable exists and is actually executable
            if os.path.isfile(path) and os.access(path, os.X_OK):
                logger.info(f"Found executable {executable_name} at {path}")
                return path
        
        raise RuntimeError(
            f"Security: Executable '{executable_name}' not found in secure locations. "
            f"Checked: {paths_to_check}. Override with {executable_name.upper()}_PATH env var."
        )

    
    async def initialize(self) -> None:
        """Initialize XRDP service manager"""
        logger.info("Initializing XRDP Service Manager...")
        
        # Check XRDP binaries
        await self._check_xrdp_binaries()
        
        # Load existing processes
        await self._load_existing_processes()
        
        logger.info("XRDP Service Manager initialized")
    
    async def _check_xrdp_binaries(self) -> None:
        """Check if XRDP binaries are available"""
        try:
            # Check xrdp binary
            result = subprocess.run([self.xrdp_binary, "--version"], 
                                 capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception(f"XRDP binary not available: {self.xrdp_binary}")
            
            # Check xrdp-sesman binary
            result = subprocess.run([self.xrdp_sesman, "--version"], 
                                 capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception(f"XRDP sesman binary not available: {self.xrdp_sesman}")
            
            logger.info("XRDP binaries verified")
            
        except Exception as e:
            logger.error(f"XRDP binary check failed: {e}")
            raise
    
    async def _load_existing_processes(self) -> None:
        """Load existing XRDP processes"""
        # TODO: Implement process discovery from system
        logger.info("Loading existing XRDP processes...")
    
    async def start_xrdp_service(self, 
                                process_id: str,
                                port: int,
                                config_path: Path,
                                log_path: Path,
                                session_path: Path) -> XRDPProcess:
        """Start XRDP service for specific configuration"""
        try:
            # Check process limits
            if len(self.active_processes) >= self.max_processes:
                raise Exception("Maximum XRDP processes reached")
            
            # Create process object
            xrdp_process = XRDPProcess(
                process_id=process_id,
                port=port,
                status=ServiceStatus.STARTING,
                config_path=config_path,
                log_path=log_path,
                session_path=session_path,
                started_at=datetime.now(timezone.utc)
            )
            
            # Store process
            self.active_processes[process_id] = xrdp_process
            
            # Start XRDP process
            await self._start_xrdp_process(xrdp_process)
            
            # Start monitoring
            monitor_task = asyncio.create_task(self._monitor_process(xrdp_process))
            self.monitor_tasks[process_id] = monitor_task
            
            logger.info(f"XRDP service started: {process_id} on port {port}")
            
            return xrdp_process
            
        except Exception as e:
            logger.error(f"XRDP service start failed: {e}")
            # Cleanup on failure
            if process_id in self.active_processes:
                del self.active_processes[process_id]
            raise
    
    async def _start_xrdp_process(self, xrdp_process: XRDPProcess) -> None:
        """Start XRDP process"""
        try:
            # Validate paths for security (prevent directory traversal)
            config_file = xrdp_process.config_path / "xrdp.ini"
            if not str(config_file.resolve()).startswith(str(self.base_config_path.resolve())):
                raise ValueError("Security: Config path outside allowed directory")
            
            log_file = xrdp_process.log_path / "xrdp.log"
            if not str(log_file.resolve()).startswith(str(self.base_log_path.resolve())):
                raise ValueError("Security: Log path outside allowed directory")
            
            # Validate port is in safe range
            if xrdp_process.port < 3000 or xrdp_process.port > 65535:
                raise ValueError(f"Security: Port {xrdp_process.port} outside safe range (3000-65535)")
            
            # Build command with safety - NEVER use shell=True
            cmd = [
                self.xrdp_binary,
                "--port", str(xrdp_process.port),
                "--config", str(config_file),
                "--session-path", str(xrdp_process.session_path),
                "--log-file", str(log_file),
                "--pid-file", str(xrdp_process.log_path / "xrdp.pid")
            ]
            
            # Start process with safety measures (shell=False is critical)
            xrdp_process.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(xrdp_process.session_path),
                preexec_fn=os.setsid,  # Create new process group
                shell=False,  # CRITICAL: Never allow shell interpretation
                user=os.getuid(),  # Run as current user (container user 65532)
                env=self._get_safe_env()  # Use minimal, safe environment
            )
            
            # Wait for startup
            await asyncio.sleep(3)
            
            # Check if process is running
            if xrdp_process.process.poll() is None:
                xrdp_process.status = ServiceStatus.RUNNING
                xrdp_process.pid = xrdp_process.process.pid
                logger.info(f"XRDP process started: PID {xrdp_process.pid}")
            else:
                xrdp_process.status = ServiceStatus.FAILED
                stderr_output = xrdp_process.process.stderr.read().decode('utf-8', errors='ignore') if xrdp_process.process.stderr else ""
                logger.error(f"XRDP process failed to start. Error: {stderr_output}")
                raise Exception("XRDP process failed to start")
                
        except Exception as e:
            xrdp_process.status = ServiceStatus.FAILED
            logger.error(f"XRDP process start failed: {e}")
            raise
    
    def _get_safe_env(self) -> Dict[str, str]:
        """Get safe environment variables for subprocess execution"""
        # Only pass through essential variables, not the full environment
        safe_env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "XRDP_PORT": os.getenv("XRDP_PORT", "3389"),
        }
        return safe_env
    
    async def stop_xrdp_service(self, process_id: str) -> Dict[str, Any]:
        """Stop XRDP service"""
        if process_id not in self.active_processes:
            raise Exception("XRDP process not found")
        
        xrdp_process = self.active_processes[process_id]
        
        try:
            xrdp_process.status = ServiceStatus.STOPPING
            logger.info(f"Stopping XRDP service: {process_id}")
            
            # Cancel monitoring task
            if process_id in self.monitor_tasks:
                self.monitor_tasks[process_id].cancel()
                del self.monitor_tasks[process_id]
            
            # Stop process
            if xrdp_process.process:
                # Send SIGTERM
                xrdp_process.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    xrdp_process.process.wait(timeout=self.process_timeout)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    xrdp_process.process.kill()
                    xrdp_process.process.wait()
                
                xrdp_process.process = None
            
            xrdp_process.status = ServiceStatus.STOPPED
            xrdp_process.stopped_at = datetime.now(timezone.utc)
            
            logger.info(f"XRDP service stopped: {process_id}")
            
            return {
                "process_id": process_id,
                "status": xrdp_process.status.value,
                "stopped_at": xrdp_process.stopped_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"XRDP service stop failed: {e}")
            raise
    
    async def restart_xrdp_service(self, process_id: str) -> Dict[str, Any]:
        """Restart XRDP service"""
        try:
            # Stop service
            await self.stop_xrdp_service(process_id)
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Get process info
            xrdp_process = self.active_processes[process_id]
            
            # Start service again
            await self._start_xrdp_process(xrdp_process)
            
            # Start monitoring
            monitor_task = asyncio.create_task(self._monitor_process(xrdp_process))
            self.monitor_tasks[process_id] = monitor_task
            
            logger.info(f"XRDP service restarted: {process_id}")
            
            return {
                "process_id": process_id,
                "status": xrdp_process.status.value,
                "restarted_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"XRDP service restart failed: {e}")
            raise
    
    async def _monitor_process(self, xrdp_process: XRDPProcess) -> None:
        """Monitor XRDP process health"""
        try:
            while xrdp_process.status == ServiceStatus.RUNNING:
                # Check process status
                if xrdp_process.process and xrdp_process.process.poll() is not None:
                    xrdp_process.status = ServiceStatus.FAILED
                    logger.error(f"XRDP process died: {xrdp_process.process_id}")
                    break
                
                # Update resource usage
                await self._update_resource_usage(xrdp_process)
                
                # Sleep between checks
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info(f"Process monitoring cancelled: {xrdp_process.process_id}")
        except Exception as e:
            logger.error(f"Process monitoring error: {e}")
            xrdp_process.status = ServiceStatus.FAILED
    
    async def _update_resource_usage(self, xrdp_process: XRDPProcess) -> None:
        """Update process resource usage"""
        try:
            if xrdp_process.pid:
                # Get process info using ps - use list, never concatenate user input into command
                cmd = ["ps", "-p", str(xrdp_process.pid), "-o", "pid,ppid,pcpu,pmem,etime,comm"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, shell=False)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        data = lines[1].split()
                        if len(data) >= 6:
                            try:
                                xrdp_process.resource_usage = {
                                    "pid": int(data[0]),  # Validate as int
                                    "ppid": int(data[1]),
                                    "cpu_percent": float(data[2]) if data[2] != '-' else 0.0,
                                    "memory_percent": float(data[3]) if data[3] != '-' else 0.0,
                                    "elapsed_time": str(data[4]),  # String is safe
                                    "command": str(data[5]),  # String is safe
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Failed to parse ps output: {e}")
            
        except subprocess.TimeoutExpired:
            logger.warning(f"ps command timed out for PID {xrdp_process.pid}")
        except Exception as e:
            logger.error(f"Resource usage update failed: {e}")
    
    async def get_process_status(self, process_id: str) -> Optional[XRDPProcess]:
        """Get XRDP process status"""
        return self.active_processes.get(process_id)
    
    async def list_processes(self) -> List[XRDPProcess]:
        """List all active XRDP processes"""
        return list(self.active_processes.values())
    
    async def shutdown_all(self) -> None:
        """Shutdown all XRDP processes"""
        logger.info("Shutting down all XRDP processes...")
        
        # Stop all processes
        for process_id in list(self.active_processes.keys()):
            try:
                await self.stop_xrdp_service(process_id)
            except Exception as e:
                logger.error(f"Failed to stop process {process_id}: {e}")
        
        logger.info("All XRDP processes stopped")
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            running_count = sum(1 for p in self.active_processes.values() 
                               if p.status == ServiceStatus.RUNNING)
            failed_count = sum(1 for p in self.active_processes.values() 
                             if p.status == ServiceStatus.FAILED)
            
            return {
                "total_processes": len(self.active_processes),
                "running_processes": running_count,
                "failed_processes": failed_count,
                "max_processes": self.max_processes,
                "processes": [
                    {
                        "process_id": p.process_id,
                        "port": p.port,
                        "status": p.status.value,
                        "pid": p.pid,
                        "started_at": p.started_at.isoformat() if p.started_at else None,
                        "resource_usage": p.resource_usage
                    }
                    for p in self.active_processes.values()
                ]
            }
            
        except Exception as e:
            logger.error(f"Service statistics failed: {e}")
            return {}

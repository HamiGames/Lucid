# LUCID XRDP Service Manager - XRDP Service Management
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

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
        
        # Service configuration
        self.base_config_path = Path("/etc/xrdp/servers")
        self.base_log_path = Path("/var/log/xrdp/servers")
        self.base_session_path = Path("/data/sessions")
        
        # XRDP binary paths
        self.xrdp_binary = "/usr/sbin/xrdp"
        self.xrdp_sesman = "/usr/sbin/xrdp-sesman"
        
        # Service limits
        self.max_processes = int(os.getenv("MAX_XRDP_PROCESSES", "10"))
        self.process_timeout = int(os.getenv("PROCESS_TIMEOUT", "30"))
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [self.base_config_path, self.base_log_path, self.base_session_path]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
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
            # Build command
            cmd = [
                self.xrdp_binary,
                "--port", str(xrdp_process.port),
                "--config", str(xrdp_process.config_path / "xrdp.ini"),
                "--session-path", str(xrdp_process.session_path),
                "--log-file", str(xrdp_process.log_path / "xrdp.log"),
                "--pid-file", str(xrdp_process.log_path / "xrdp.pid")
            ]
            
            # Start process
            xrdp_process.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(xrdp_process.session_path),
                preexec_fn=os.setsid  # Create new process group
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
                logger.error(f"XRDP process failed to start: {process_id}")
                raise Exception("XRDP process failed to start")
                
        except Exception as e:
            xrdp_process.status = ServiceStatus.FAILED
            logger.error(f"XRDP process start failed: {e}")
            raise
    
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
                # Get process info using ps
                cmd = ["ps", "-p", str(xrdp_process.pid), "-o", "pid,ppid,pcpu,pmem,etime,comm"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        data = lines[1].split()
                        if len(data) >= 6:
                            xrdp_process.resource_usage = {
                                "pid": data[0],
                                "ppid": data[1],
                                "cpu_percent": float(data[2]) if data[2] != '-' else 0.0,
                                "memory_percent": float(data[3]) if data[3] != '-' else 0.0,
                                "elapsed_time": data[4],
                                "command": data[5],
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
            
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

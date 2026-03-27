"""
Tor service management for Lucid RDP.

This module provides comprehensive Tor daemon lifecycle management,
configuration, monitoring, and integration with the LUCID-STRICT security model.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import aiofiles
import psutil

from ..security.trust_nothing_engine import (
    TrustNothingEngine, SecurityContext, SecurityAssessment,
    TrustLevel, RiskLevel, ActionType, PolicyLevel
)


class TorStatus(Enum):
    """Tor daemon status states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


class TorServiceType(Enum):
    """Types of Tor services"""
    CLIENT = "client"
    RELAY = "relay"
    BRIDGE = "bridge"
    HIDDEN_SERVICE = "hidden_service"
    AUTHORITY = "authority"


class TorConnectionStatus(Enum):
    """Tor connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class TorConfiguration:
    """Tor daemon configuration"""
    config_id: str
    data_directory: str
    control_port: int = 9051
    socks_port: int = 9050
    dns_port: int = 9053
    service_type: TorServiceType = TorServiceType.CLIENT
    log_level: str = "notice"
    log_file: Optional[str] = None
    control_password: Optional[str] = None
    exit_policy: str = "reject *:*"
    circuit_build_timeout: int = 60
    new_circuit_period: int = 30
    max_circuit_dirtiness: int = 600
    enforce_distinct_subnets: bool = True
    strict_nodes: bool = False
    exclude_nodes: List[str] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)
    exit_nodes: List[str] = field(default_factory=list)
    bridge_lines: List[str] = field(default_factory=list)
    hidden_service_configs: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TorServiceInfo:
    """Information about Tor service"""
    service_id: str
    status: TorStatus
    pid: Optional[int] = None
    version: Optional[str] = None
    uptime: Optional[float] = None
    connection_status: TorConnectionStatus = TorConnectionStatus.DISCONNECTED
    circuit_count: int = 0
    bandwidth_used: int = 0
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    configuration: Optional[TorConfiguration] = None


@dataclass
class TorCircuitInfo:
    """Information about Tor circuit"""
    circuit_id: str
    status: str
    purpose: str
    age: int
    flags: List[str]
    path: List[str]
    build_flags: List[str]
    time_built: datetime
    bytes_received: int = 0
    bytes_sent: int = 0


@dataclass
class TorStreamInfo:
    """Information about Tor stream"""
    stream_id: str
    status: str
    circuit_id: str
    target_host: str
    target_port: int
    source_address: str
    source_port: int
    purpose: str
    time_created: datetime
    bytes_received: int = 0
    bytes_sent: int = 0


class TorManager:
    """
    Comprehensive Tor service management for Lucid RDP.
    
    Provides lifecycle management, configuration, monitoring, and integration
    with the LUCID-STRICT security model.
    """
    
    def __init__(self, trust_engine: Optional[TrustNothingEngine] = None):
        self.trust_engine = trust_engine or TrustNothingEngine()
        self.logger = logging.getLogger(__name__)
        
        # Service state
        self.service_info: Optional[TorServiceInfo] = None
        self.configuration: Optional[TorConfiguration] = None
        self.control_connection: Optional[asyncio.StreamReader] = None
        self.control_writer: Optional[asyncio.StreamWriter] = None
        
        # Monitoring
        self.monitoring_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 30  # seconds
        self.circuit_cache: Dict[str, TorCircuitInfo] = {}
        self.stream_cache: Dict[str, TorStreamInfo] = {}
        
        # Security integration
        self.security_context_cache: Dict[str, SecurityContext] = {}
        self.rate_limits: Dict[str, Tuple[datetime, int]] = {}
        
        # Configuration paths
        self.tor_binary = self._find_tor_binary()
        self.default_data_dir = Path.home() / ".lucid" / "tor"
        self.config_file_path: Optional[Path] = None
        
        self.logger.info("TorManager initialized")
    
    async def initialize(
        self,
        config: Optional[TorConfiguration] = None,
        auto_start: bool = False
    ) -> bool:
        """Initialize Tor manager with configuration"""
        try:
            self.configuration = config or self._create_default_configuration()
            
            # Create data directory
            os.makedirs(self.configuration.data_directory, exist_ok=True)
            
            # Generate configuration file
            self.config_file_path = await self._generate_config_file()
            
            # Initialize service info
            self.service_info = TorServiceInfo(
                service_id=f"tor_{int(time.time())}",
                status=TorStatus.STOPPED,
                configuration=self.configuration
            )
            
            if auto_start:
                await self.start_service()
            
            self.logger.info("TorManager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TorManager: {e}")
            return False
    
    async def start_service(self) -> bool:
        """Start Tor daemon"""
        try:
            if self.service_info and self.service_info.status == TorStatus.RUNNING:
                self.logger.warning("Tor service is already running")
                return True
            
            # Security assessment
            context = SecurityContext(
                request_id=f"tor_start_{int(time.time())}",
                service_name="tor_manager",
                component_name="tor_daemon",
                operation="start_service",
                resource_path="/tor/daemon"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.HIGH)
            if assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Update service status
            if self.service_info:
                self.service_info.status = TorStatus.STARTING
                self.service_info.error_message = None
            
            # Start Tor process
            cmd = [
                self.tor_binary,
                "-f", str(self.config_file_path),
                "--DataDirectory", self.configuration.data_directory
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for startup
            await asyncio.sleep(5)
            
            if process.returncode is None:
                # Process is running
                if self.service_info:
                    self.service_info.status = TorStatus.RUNNING
                    self.service_info.pid = process.pid
                    self.service_info.uptime = 0
                    self.service_info.last_heartbeat = datetime.now(timezone.utc)
                
                # Start monitoring
                self.monitoring_task = asyncio.create_task(self._monitor_service())
                
                # Connect to control port
                await self._connect_control_port()
                
                self.logger.info("Tor service started successfully")
                return True
            else:
                # Process failed to start
                if self.service_info:
                    self.service_info.status = TorStatus.ERROR
                    self.service_info.error_message = "Failed to start Tor daemon"
                
                self.logger.error("Failed to start Tor daemon")
                return False
                
        except Exception as e:
            if self.service_info:
                self.service_info.status = TorStatus.ERROR
                self.service_info.error_message = str(e)
            
            self.logger.error(f"Failed to start Tor service: {e}")
            return False
    
    async def stop_service(self, force: bool = False) -> bool:
        """Stop Tor daemon"""
        try:
            if not self.service_info or self.service_info.status != TorStatus.RUNNING:
                self.logger.warning("Tor service is not running")
                return True
            
            # Security assessment
            context = SecurityContext(
                request_id=f"tor_stop_{int(time.time())}",
                service_name="tor_manager",
                component_name="tor_daemon",
                operation="stop_service",
                resource_path="/tor/daemon"
            )
            
            assessment = await self.trust_engine.assess_security(context, TrustLevel.HIGH)
            if not force and assessment.recommended_action != ActionType.ALLOW:
                self.logger.error(f"Security assessment failed: {assessment.recommended_action}")
                return False
            
            # Update service status
            self.service_info.status = TorStatus.STOPPING
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            # Disconnect control port
            await self._disconnect_control_port()
            
            # Stop Tor process
            if self.service_info.pid:
                try:
                    process = psutil.Process(self.service_info.pid)
                    if force:
                        process.kill()
                    else:
                        process.terminate()
                    
                    # Wait for process to stop
                    process.wait(timeout=10)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
            
            # Update service status
            self.service_info.status = TorStatus.STOPPED
            self.service_info.pid = None
            self.service_info.uptime = None
            
            self.logger.info("Tor service stopped successfully")
            return True
            
        except Exception as e:
            if self.service_info:
                self.service_info.status = TorStatus.ERROR
                self.service_info.error_message = str(e)
            
            self.logger.error(f"Failed to stop Tor service: {e}")
            return False
    
    async def restart_service(self) -> bool:
        """Restart Tor daemon"""
        try:
            self.logger.info("Restarting Tor service...")
            
            if not await self.stop_service():
                return False
            
            await asyncio.sleep(2)
            
            if not await self.start_service():
                return False
            
            self.logger.info("Tor service restarted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart Tor service: {e}")
            return False
    
    async def get_service_status(self) -> Optional[TorServiceInfo]:
        """Get current Tor service status"""
        if not self.service_info:
            return None
        
        # Update uptime if running
        if (self.service_info.status == TorStatus.RUNNING and 
            self.service_info.pid):
            try:
                process = psutil.Process(self.service_info.pid)
                if process.is_running():
                    self.service_info.uptime = time.time() - process.create_time()
                else:
                    self.service_info.status = TorStatus.STOPPED
                    self.service_info.pid = None
            except psutil.NoSuchProcess:
                self.service_info.status = TorStatus.STOPPED
                self.service_info.pid = None
        
        return self.service_info
    
    async def get_circuit_info(self) -> List[TorCircuitInfo]:
        """Get information about Tor circuits"""
        try:
            if not self.control_connection or not self.control_writer:
                return []
            
            # Send GETINFO circuit-status command
            command = "GETINFO circuit-status\n"
            self.control_writer.write(command.encode())
            await self.control_writer.drain()
            
            # Read response
            response = await self.control_connection.readline()
            circuits = []
            
            if response.startswith(b"250-circuit-status="):
                circuit_data = response[21:].decode().strip()
                for line in circuit_data.split('\n'):
                    if line.strip():
                        circuit_info = self._parse_circuit_line(line)
                        if circuit_info:
                            circuits.append(circuit_info)
                            self.circuit_cache[circuit_info.circuit_id] = circuit_info
            
            return circuits
            
        except Exception as e:
            self.logger.error(f"Failed to get circuit info: {e}")
            return []
    
    async def get_stream_info(self) -> List[TorStreamInfo]:
        """Get information about Tor streams"""
        try:
            if not self.control_connection or not self.control_writer:
                return []
            
            # Send GETINFO stream-status command
            command = "GETINFO stream-status\n"
            self.control_writer.write(command.encode())
            await self.control_writer.drain()
            
            # Read response
            response = await self.control_connection.readline()
            streams = []
            
            if response.startswith(b"250-stream-status="):
                stream_data = response[20:].decode().strip()
                for line in stream_data.split('\n'):
                    if line.strip():
                        stream_info = self._parse_stream_line(line)
                        if stream_info:
                            streams.append(stream_info)
                            self.stream_cache[stream_info.stream_id] = stream_info
            
            return streams
            
        except Exception as e:
            self.logger.error(f"Failed to get stream info: {e}")
            return []
    
    async def new_circuit(self) -> bool:
        """Create a new Tor circuit"""
        try:
            if not self.control_connection or not self.control_writer:
                return False
            
            # Send NEWCIRCUIT command
            command = "NEWCIRCUIT\n"
            self.control_writer.write(command.encode())
            await self.control_writer.drain()
            
            # Read response
            response = await self.control_connection.readline()
            return response.startswith(b"250")
            
        except Exception as e:
            self.logger.error(f"Failed to create new circuit: {e}")
            return False
    
    async def close_circuit(self, circuit_id: str) -> bool:
        """Close a specific Tor circuit"""
        try:
            if not self.control_connection or not self.control_writer:
                return False
            
            # Send CLOSECIRCUIT command
            command = f"CLOSECIRCUIT {circuit_id}\n"
            self.control_writer.write(command.encode())
            await self.control_writer.drain()
            
            # Read response
            response = await self.control_connection.readline()
            return response.startswith(b"250")
            
        except Exception as e:
            self.logger.error(f"Failed to close circuit {circuit_id}: {e}")
            return False
    
    async def reload_configuration(self) -> bool:
        """Reload Tor configuration"""
        try:
            if not self.control_connection or not self.control_writer:
                return False
            
            # Send SIGNAL RELOAD command
            command = "SIGNAL RELOAD\n"
            self.control_writer.write(command.encode())
            await self.control_writer.drain()
            
            # Read response
            response = await self.control_connection.readline()
            return response.startswith(b"250")
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            return False
    
    async def get_bandwidth_usage(self) -> Dict[str, int]:
        """Get bandwidth usage statistics"""
        try:
            if not self.control_connection or not self.control_writer:
                return {"bytes_read": 0, "bytes_written": 0}
            
            # Send GETINFO traffic/read and traffic/written commands
            commands = [
                "GETINFO traffic/read\n",
                "GETINFO traffic/written\n"
            ]
            
            bandwidth = {"bytes_read": 0, "bytes_written": 0}
            
            for command in commands:
                self.control_writer.write(command.encode())
                await self.control_writer.drain()
                
                response = await self.control_connection.readline()
                
                if command.startswith("GETINFO traffic/read"):
                    if response.startswith(b"250-traffic/read="):
                        bandwidth["bytes_read"] = int(response[19:].decode().strip())
                elif command.startswith("GETINFO traffic/written"):
                    if response.startswith(b"250-traffic/written="):
                        bandwidth["bytes_written"] = int(response[21:].decode().strip())
            
            return bandwidth
            
        except Exception as e:
            self.logger.error(f"Failed to get bandwidth usage: {e}")
            return {"bytes_read": 0, "bytes_written": 0}
    
    async def _monitor_service(self) -> None:
        """Monitor Tor service health and performance"""
        while True:
            try:
                if not self.service_info:
                    break
                
                # Update heartbeat
                self.service_info.last_heartbeat = datetime.now(timezone.utc)
                
                # Check process status
                if self.service_info.pid:
                    try:
                        process = psutil.Process(self.service_info.pid)
                        if not process.is_running():
                            self.service_info.status = TorStatus.STOPPED
                            self.service_info.pid = None
                            break
                        
                        # Update uptime
                        self.service_info.uptime = time.time() - process.create_time()
                        
                        # Update bandwidth usage
                        bandwidth = await self.get_bandwidth_usage()
                        self.service_info.bandwidth_used = bandwidth.get("bytes_read", 0) + bandwidth.get("bytes_written", 0)
                        
                    except psutil.NoSuchProcess:
                        self.service_info.status = TorStatus.STOPPED
                        self.service_info.pid = None
                        break
                
                # Update circuit count
                circuits = await self.get_circuit_info()
                self.service_info.circuit_count = len(circuits)
                
                # Check connection status
                if self.control_connection and self.control_writer:
                    self.service_info.connection_status = TorConnectionStatus.CONNECTED
                else:
                    self.service_info.connection_status = TorConnectionStatus.DISCONNECTED
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in service monitoring: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _connect_control_port(self) -> bool:
        """Connect to Tor control port"""
        try:
            if not self.configuration:
                return False
            
            # Connect to control port
            self.control_connection, self.control_writer = await asyncio.open_connection(
                '127.0.0.1', self.configuration.control_port
            )
            
            # Authenticate if password is set
            if self.configuration.control_password:
                auth_command = f'AUTHENTICATE "{self.configuration.control_password}"\n'
                self.control_writer.write(auth_command.encode())
                await self.control_writer.drain()
                
                response = await self.control_connection.readline()
                if not response.startswith(b"250"):
                    self.logger.error("Failed to authenticate with Tor control port")
                    await self._disconnect_control_port()
                    return False
            
            self.logger.info("Connected to Tor control port")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to control port: {e}")
            return False
    
    async def _disconnect_control_port(self) -> None:
        """Disconnect from Tor control port"""
        try:
            if self.control_writer:
                self.control_writer.close()
                await self.control_writer.wait_closed()
            
            self.control_connection = None
            self.control_writer = None
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from control port: {e}")
    
    async def _generate_config_file(self) -> Path:
        """Generate Tor configuration file"""
        try:
            config_content = self._build_config_content()
            
            # Create temporary config file
            config_file = Path(tempfile.mktemp(suffix='.torrc'))
            
            async with aiofiles.open(config_file, 'w') as f:
                await f.write(config_content)
            
            return config_file
            
        except Exception as e:
            self.logger.error(f"Failed to generate config file: {e}")
            raise
    
    def _build_config_content(self) -> str:
        """Build Tor configuration content"""
        if not self.configuration:
            raise ValueError("No configuration available")
        
        config_lines = [
            f"DataDirectory {self.configuration.data_directory}",
            f"ControlPort {self.configuration.control_port}",
            f"SocksPort {self.configuration.socks_port}",
            f"DNSPort {self.configuration.dns_port}",
            f"Log {self.configuration.log_level}",
        ]
        
        if self.configuration.log_file:
            config_lines.append(f"Log {self.configuration.log_level} file {self.configuration.log_file}")
        
        if self.configuration.control_password:
            config_lines.append(f'HashedControlPassword {self._hash_password(self.configuration.control_password)}')
        
        config_lines.extend([
            f"ExitPolicy {self.configuration.exit_policy}",
            f"CircuitBuildTimeout {self.configuration.circuit_build_timeout}",
            f"NewCircuitPeriod {self.configuration.new_circuit_period}",
            f"MaxCircuitDirtiness {self.configuration.max_circuit_dirtiness}",
        ])
        
        if self.configuration.enforce_distinct_subnets:
            config_lines.append("EnforceDistinctSubnets 1")
        else:
            config_lines.append("EnforceDistinctSubnets 0")
        
        if self.configuration.strict_nodes:
            config_lines.append("StrictNodes 1")
        else:
            config_lines.append("StrictNodes 0")
        
        # Add node restrictions
        if self.configuration.exclude_nodes:
            config_lines.append(f"ExcludeNodes {','.join(self.configuration.exclude_nodes)}")
        
        if self.configuration.entry_nodes:
            config_lines.append(f"EntryNodes {','.join(self.configuration.entry_nodes)}")
        
        if self.configuration.exit_nodes:
            config_lines.append(f"ExitNodes {','.join(self.configuration.exit_nodes)}")
        
        # Add bridge configuration
        for bridge in self.configuration.bridge_lines:
            config_lines.append(f"Bridge {bridge}")
        
        # Add hidden service configurations
        for hs_config in self.configuration.hidden_service_configs:
            config_lines.extend([
                f"HiddenServiceDir {hs_config['directory']}",
                f"HiddenServicePort {hs_config['port']} {hs_config['target']}"
            ])
        
        return '\n'.join(config_lines)
    
    def _create_default_configuration(self) -> TorConfiguration:
        """Create default Tor configuration"""
        return TorConfiguration(
            config_id=f"tor_config_{int(time.time())}",
            data_directory=str(self.default_data_dir),
            control_port=9051,
            socks_port=9050,
            dns_port=9053,
            service_type=TorServiceType.CLIENT,
            log_level="notice",
            exit_policy="reject *:*",
            circuit_build_timeout=60,
            new_circuit_period=30,
            max_circuit_dirtiness=600,
            enforce_distinct_subnets=True,
            strict_nodes=False
        )
    
    def _find_tor_binary(self) -> str:
        """Find Tor binary path"""
        possible_paths = [
            "/usr/bin/tor",
            "/usr/local/bin/tor",
            "/opt/homebrew/bin/tor",
            "tor"  # In PATH
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) or path == "tor":
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return path
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
        
        raise RuntimeError("Tor binary not found. Please install Tor.")
    
    def _hash_password(self, password: str) -> str:
        """Hash password for Tor control authentication"""
        import hashlib
        salt = os.urandom(8)
        hash_obj = hashlib.sha1()
        hash_obj.update(salt + password.encode())
        return f"16:{salt.hex()}{hash_obj.hexdigest()}"
    
    def _parse_circuit_line(self, line: str) -> Optional[TorCircuitInfo]:
        """Parse circuit status line"""
        try:
            parts = line.split()
            if len(parts) < 6:
                return None
            
            circuit_id = parts[0]
            status = parts[1]
            purpose = parts[2]
            age = int(parts[3])
            flags = parts[4].split(',') if parts[4] != 'BUILD_FLAGS' else []
            path = parts[5].split(',') if len(parts) > 5 else []
            build_flags = parts[6].split(',') if len(parts) > 6 and parts[6] != 'BUILD_FLAGS' else []
            
            return TorCircuitInfo(
                circuit_id=circuit_id,
                status=status,
                purpose=purpose,
                age=age,
                flags=flags,
                path=path,
                build_flags=build_flags,
                time_built=datetime.now(timezone.utc) - timedelta(seconds=age)
            )
            
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Failed to parse circuit line: {line} - {e}")
            return None
    
    def _parse_stream_line(self, line: str) -> Optional[TorStreamInfo]:
        """Parse stream status line"""
        try:
            parts = line.split()
            if len(parts) < 8:
                return None
            
            stream_id = parts[0]
            status = parts[1]
            circuit_id = parts[2]
            target = parts[3]
            target_host, target_port = target.split(':')
            source = parts[4]
            source_address, source_port = source.split(':')
            purpose = parts[5]
            
            return TorStreamInfo(
                stream_id=stream_id,
                status=status,
                circuit_id=circuit_id,
                target_host=target_host,
                target_port=int(target_port),
                source_address=source_address,
                source_port=int(source_port),
                purpose=purpose,
                time_created=datetime.now(timezone.utc)
            )
            
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Failed to parse stream line: {line} - {e}")
            return None


# Global instance management
_tor_manager_instance: Optional[TorManager] = None


def get_tor_manager() -> Optional[TorManager]:
    """Get the global TorManager instance"""
    return _tor_manager_instance


def create_tor_manager(trust_engine: Optional[TrustNothingEngine] = None) -> TorManager:
    """Create a new TorManager instance"""
    global _tor_manager_instance
    _tor_manager_instance = TorManager(trust_engine)
    return _tor_manager_instance


async def main():
    """Example usage of TorManager"""
    # Create Tor manager
    tor_manager = create_tor_manager()
    
    # Initialize with default configuration
    await tor_manager.initialize(auto_start=True)
    
    # Get service status
    status = await tor_manager.get_service_status()
    print(f"Tor status: {status.status if status else 'Unknown'}")
    
    # Get circuit information
    circuits = await tor_manager.get_circuit_info()
    print(f"Active circuits: {len(circuits)}")
    
    # Get bandwidth usage
    bandwidth = await tor_manager.get_bandwidth_usage()
    print(f"Bandwidth: {bandwidth}")
    
    # Stop service
    await tor_manager.stop_service()


if __name__ == "__main__":
    asyncio.run(main())

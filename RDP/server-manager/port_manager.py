# LUCID RDP Port Manager - Port Allocation Management
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PortStatus(Enum):
    """Port status states"""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RESERVED = "reserved"
    BLOCKED = "blocked"

@dataclass
class PortInfo:
    """Port information"""
    port: int
    status: PortStatus
    allocated_to: Optional[str] = None
    allocated_at: Optional[str] = None
    expires_at: Optional[str] = None

class PortManager:
    """
    Port allocation manager for RDP servers.
    
    Manages port allocation in the range 13389-14389 (1000 ports).
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self, start_port: int = 13389, end_port: int = 14389):
        """Initialize port manager"""
        self.start_port = start_port
        self.end_port = end_port
        self.port_range = end_port - start_port + 1
        
        # Port tracking
        self.ports: Dict[int, PortInfo] = {}
        self.allocated_ports: Set[int] = set()
        self.available_ports: Set[int] = set()
        
        # Initialize port range
        self._initialize_ports()
        
        logger.info(f"Port Manager initialized: {start_port}-{end_port} ({self.port_range} ports)")
    
    def _initialize_ports(self) -> None:
        """Initialize port range"""
        for port in range(self.start_port, self.end_port + 1):
            # Check if port is available
            if self._is_port_available(port):
                self.ports[port] = PortInfo(port=port, status=PortStatus.AVAILABLE)
                self.available_ports.add(port)
            else:
                self.ports[port] = PortInfo(port=port, status=PortStatus.BLOCKED)
                logger.warning(f"Port {port} is not available")
    
    def _is_port_available(self, port: int) -> bool:
        """Check if port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return False
    
    async def initialize(self) -> None:
        """Initialize port manager"""
        logger.info("Initializing Port Manager...")
        
        # Refresh port availability
        await self._refresh_port_availability()
        
        logger.info(f"Port Manager initialized: {len(self.available_ports)} available ports")
    
    async def _refresh_port_availability(self) -> None:
        """Refresh port availability status"""
        for port in range(self.start_port, self.end_port + 1):
            if port not in self.allocated_ports:
                if self._is_port_available(port):
                    self.ports[port].status = PortStatus.AVAILABLE
                    self.available_ports.add(port)
                else:
                    self.ports[port].status = PortStatus.BLOCKED
                    self.available_ports.discard(port)
    
    async def allocate_port(self, preferred_port: Optional[int] = None) -> Optional[int]:
        """Allocate an available port"""
        try:
            # Try preferred port first
            if preferred_port and self._can_allocate_port(preferred_port):
                return await self._allocate_specific_port(preferred_port)
            
            # Find first available port
            for port in sorted(self.available_ports):
                if self._can_allocate_port(port):
                    return await self._allocate_specific_port(port)
            
            logger.warning("No available ports for allocation")
            return None
            
        except Exception as e:
            logger.error(f"Port allocation failed: {e}")
            return None
    
    def _can_allocate_port(self, port: int) -> bool:
        """Check if port can be allocated"""
        return (port in self.available_ports and 
                port not in self.allocated_ports and
                self.ports[port].status == PortStatus.AVAILABLE)
    
    async def _allocate_specific_port(self, port: int) -> int:
        """Allocate specific port"""
        from datetime import datetime, timezone
        
        # Update port status
        self.ports[port].status = PortStatus.ALLOCATED
        self.ports[port].allocated_at = datetime.now(timezone.utc).isoformat()
        
        # Update tracking sets
        self.available_ports.discard(port)
        self.allocated_ports.add(port)
        
        logger.info(f"Allocated port: {port}")
        return port
    
    async def release_port(self, port: int) -> bool:
        """Release allocated port"""
        try:
            if port not in self.allocated_ports:
                logger.warning(f"Port {port} is not allocated")
                return False
            
            # Update port status
            self.ports[port].status = PortStatus.AVAILABLE
            self.ports[port].allocated_to = None
            self.ports[port].allocated_at = None
            self.ports[port].expires_at = None
            
            # Update tracking sets
            self.allocated_ports.discard(port)
            self.available_ports.add(port)
            
            logger.info(f"Released port: {port}")
            return True
            
        except Exception as e:
            logger.error(f"Port release failed: {e}")
            return False
    
    async def reserve_port(self, port: int, reserved_by: str, expires_in: int = 3600) -> bool:
        """Reserve a port for future use"""
        try:
            if not self._can_allocate_port(port):
                return False
            
            from datetime import datetime, timezone, timedelta
            
            # Update port status
            self.ports[port].status = PortStatus.RESERVED
            self.ports[port].allocated_to = reserved_by
            self.ports[port].allocated_at = datetime.now(timezone.utc).isoformat()
            self.ports[port].expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
            
            # Update tracking sets
            self.available_ports.discard(port)
            self.allocated_ports.add(port)
            
            logger.info(f"Reserved port: {port} for {reserved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Port reservation failed: {e}")
            return False
    
    async def get_port_status(self, port: int) -> Optional[PortInfo]:
        """Get port status"""
        return self.ports.get(port)
    
    async def get_available_ports(self) -> List[int]:
        """Get list of available ports"""
        return sorted(self.available_ports)
    
    async def get_allocated_ports(self) -> List[int]:
        """Get list of allocated ports"""
        return sorted(self.allocated_ports)
    
    def get_available_ports_count(self) -> int:
        """Get count of available ports"""
        return len(self.available_ports)
    
    def get_allocated_ports_count(self) -> int:
        """Get count of allocated ports"""
        return len(self.allocated_ports)
    
    async def get_port_statistics(self) -> Dict[str, Any]:
        """Get port allocation statistics"""
        total_ports = self.port_range
        available_count = len(self.available_ports)
        allocated_count = len(self.allocated_ports)
        blocked_count = total_ports - available_count - allocated_count
        
        return {
            "total_ports": total_ports,
            "available_ports": available_count,
            "allocated_ports": allocated_count,
            "blocked_ports": blocked_count,
            "utilization_percent": (allocated_count / total_ports) * 100,
            "port_range": f"{self.start_port}-{self.end_port}"
        }
    
    async def cleanup_expired_reservations(self) -> int:
        """Cleanup expired port reservations"""
        from datetime import datetime, timezone
        
        cleaned_count = 0
        current_time = datetime.now(timezone.utc)
        
        for port, port_info in self.ports.items():
            if (port_info.status == PortStatus.RESERVED and 
                port_info.expires_at and 
                datetime.fromisoformat(port_info.expires_at) < current_time):
                
                # Release expired reservation
                await self.release_port(port)
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired port reservations")
        
        return cleaned_count
    
    async def force_release_port(self, port: int) -> bool:
        """Force release port (admin operation)"""
        try:
            if port in self.allocated_ports:
                await self.release_port(port)
                logger.warning(f"Force released port: {port}")
                return True
            else:
                logger.warning(f"Port {port} is not allocated")
                return False
                
        except Exception as e:
            logger.error(f"Force port release failed: {e}")
            return False
    
    async def get_port_usage_report(self) -> Dict[str, Any]:
        """Get detailed port usage report"""
        report = {
            "statistics": await self.get_port_statistics(),
            "allocated_ports": [],
            "available_ports": [],
            "blocked_ports": [],
            "reserved_ports": []
        }
        
        for port, port_info in self.ports.items():
            port_data = {
                "port": port,
                "status": port_info.status.value,
                "allocated_to": port_info.allocated_to,
                "allocated_at": port_info.allocated_at,
                "expires_at": port_info.expires_at
            }
            
            if port_info.status == PortStatus.ALLOCATED:
                report["allocated_ports"].append(port_data)
            elif port_info.status == PortStatus.AVAILABLE:
                report["available_ports"].append(port_data)
            elif port_info.status == PortStatus.BLOCKED:
                report["blocked_ports"].append(port_data)
            elif port_info.status == PortStatus.RESERVED:
                report["reserved_ports"].append(port_data)
        
        return report

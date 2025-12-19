#!/usr/bin/env python3
"""
Tunnel Tools Status Module
Manages tunnel status information and health checks.
All configuration from environment variables - no hardcoded values.
"""

import os
import json
import socket
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Load configuration from environment
STATUS_JSON_PATH = Path(os.getenv("STATUS_JSON_PATH", "/run/lucid/onion/tunnel_status.json"))
STATUS_ENV_PATH = Path(os.getenv("STATUS_ENV_PATH", "/run/lucid/onion/tunnel_status.env"))
CONTROL_HOST = os.getenv("CONTROL_HOST", "tor-proxy")
CONTROL_PORT = int(os.getenv("CONTROL_PORT", "9051"))
COOKIE_FILE = Path(os.getenv("COOKIE_FILE", "/var/lib/tor/control_auth_cookie"))
WRITE_ENV = Path(os.getenv("WRITE_ENV", "/run/lucid/onion/.onion.env"))
TOR_PROXY = os.getenv("TOR_PROXY", "tor-proxy:9050")
TOR_PROXY_HOST = os.getenv("TOR_PROXY_HOST", TOR_PROXY.split(":")[0] if ":" in TOR_PROXY else TOR_PROXY)
TOR_PROXY_PORT = int(os.getenv("TOR_PROXY_PORT", TOR_PROXY.split(":")[1] if ":" in TOR_PROXY else "9050"))


class TunnelStatus:
    """Manages tunnel status information."""
    
    def __init__(self, status_path: Path = STATUS_JSON_PATH):
        self.status_path = status_path
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self._status: Dict[str, Any] = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Load existing status from file."""
        if self.status_path.exists():
            try:
                with open(self.status_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Initialize default status structure
        return {
            "version": "1.0.0",
            "service": "tunnel-tools",
            "status": "unknown",
            "health": "unknown",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "onion": {
                "address": None,
                "created_at": None,
                "ports": []
            },
            "tor_connection": {
                "control_host": CONTROL_HOST,
                "control_port": CONTROL_PORT,
                "connected": False,
                "authenticated": False,
                "last_check": None
            },
            "verification": {
                "last_verified": None,
                "status": None,
                "reachable": False
            },
            "uptime": {
                "started_at": datetime.utcnow().isoformat() + "Z",
                "seconds": 0
            }
        }
    
    def _save_status(self) -> None:
        """Save status to file."""
        try:
            self._status["timestamp"] = datetime.utcnow().isoformat() + "Z"
            
            with open(self.status_path, 'w') as f:
                json.dump(self._status, f, indent=2)
            
            # Also write to .env file for shell script compatibility
            self._write_env_file()
        except (IOError, OSError):
            # Don't fail if we can't write status
            pass
    
    def _write_env_file(self) -> None:
        """Write status to .env file for shell script compatibility."""
        try:
            STATUS_ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(STATUS_ENV_PATH, 'w') as f:
                f.write(f"TUNNEL_STATUS={self._status['status']}\n")
                f.write(f"TUNNEL_HEALTH={self._status['health']}\n")
                if self._status['onion']['address']:
                    f.write(f"ONION_ADDRESS={self._status['onion']['address']}\n")
                f.write(f"TOR_CONNECTED={str(self._status['tor_connection']['connected']).lower()}\n")
                f.write(f"TOR_AUTHENTICATED={str(self._status['tor_connection']['authenticated']).lower()}\n")
        except (IOError, OSError):
            pass
    
    def check_tor_connection(self) -> bool:
        """Check if Tor control port is reachable."""
        try:
            with socket.create_connection((CONTROL_HOST, CONTROL_PORT), timeout=5) as sock:
                self._status["tor_connection"]["connected"] = True
                self._status["tor_connection"]["last_check"] = datetime.utcnow().isoformat() + "Z"
                self._save_status()
                return True
        except (socket.timeout, socket.gaierror, OSError):
            self._status["tor_connection"]["connected"] = False
            self._status["tor_connection"]["last_check"] = datetime.utcnow().isoformat() + "Z"
            self._save_status()
            return False
    
    def set_tor_authenticated(self, authenticated: bool) -> None:
        """Set Tor authentication status."""
        self._status["tor_connection"]["authenticated"] = authenticated
        self._save_status()
    
    def set_onion_address(self, address: str, ports: Optional[list] = None) -> None:
        """Set current onion address."""
        self._status["onion"]["address"] = address
        self._status["onion"]["created_at"] = datetime.utcnow().isoformat() + "Z"
        if ports:
            self._status["onion"]["ports"] = ports
        self._save_status()
    
    def set_status(self, status: str) -> None:
        """Set overall service status."""
        self._status["status"] = status
        self._save_status()
    
    def set_health(self, health: str) -> None:
        """Set health status (healthy, unhealthy, degraded)."""
        self._status["health"] = health
        self._save_status()
    
    def set_verification(self, reachable: bool) -> None:
        """Set verification status."""
        self._status["verification"]["reachable"] = reachable
        self._status["verification"]["last_verified"] = datetime.utcnow().isoformat() + "Z"
        self._status["verification"]["status"] = "success" if reachable else "failed"
        self._save_status()
    
    def update_uptime(self) -> None:
        """Update uptime calculation."""
        if "started_at" in self._status["uptime"]:
            started = datetime.fromisoformat(self._status["uptime"]["started_at"].replace("Z", "+00:00"))
            uptime_seconds = int((datetime.utcnow() - started.replace(tzinfo=None)).total_seconds())
            self._status["uptime"]["seconds"] = uptime_seconds
            self._save_status()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status dictionary."""
        self.update_uptime()
        return self._status.copy()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a health summary for monitoring."""
        self.update_uptime()
        return {
            "status": self._status["status"],
            "health": self._status["health"],
            "tor_connected": self._status["tor_connection"]["connected"],
            "tor_authenticated": self._status["tor_connection"]["authenticated"],
            "onion_active": self._status["onion"]["address"] is not None,
            "verification_reachable": self._status["verification"]["reachable"],
            "uptime_seconds": self._status["uptime"]["seconds"],
            "timestamp": self._status["timestamp"]
        }


# Global status instance
_status_instance: Optional[TunnelStatus] = None


def get_status() -> TunnelStatus:
    """Get or create the global status instance."""
    global _status_instance
    if _status_instance is None:
        _status_instance = TunnelStatus()
    return _status_instance


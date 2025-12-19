#!/usr/bin/env python3
"""
Tunnel Tools Metrics Collection Module
Collects and maintains operational metrics for tunnel-tools container.
All configuration from environment variables - no hardcoded values.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Load configuration from environment
METRICS_JSON_PATH = Path(os.getenv("METRICS_JSON_PATH", "/var/lib/tunnel/metrics.json"))
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
METRICS_UPDATE_INTERVAL = int(os.getenv("METRICS_UPDATE_INTERVAL", "60"))
METRICS_RETENTION_DAYS = int(os.getenv("METRICS_RETENTION_DAYS", "7"))


class TunnelMetrics:
    """Manages tunnel operational metrics."""
    
    def __init__(self, metrics_path: Path = METRICS_JSON_PATH):
        self.metrics_path = metrics_path
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self._metrics: Dict[str, Any] = self._load_metrics()
    
    def _load_metrics(self) -> Dict[str, Any]:
        """Load existing metrics from file."""
        if self.metrics_path.exists():
            try:
                with open(self.metrics_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Initialize default metrics structure
        return {
            "version": "1.0.0",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "counters": {
                "onion_creations": 0,
                "onion_rotations": 0,
                "verification_successes": 0,
                "verification_failures": 0,
                "errors": 0,
                "recoveries": 0
            },
            "current_state": {
                "onion_address": None,
                "onion_created_at": None,
                "status": "unknown",
                "last_verification": None,
                "verification_status": None
            },
            "history": []
        }
    
    def _save_metrics(self) -> None:
        """Save metrics to file."""
        if not METRICS_ENABLED:
            return
        
        try:
            self._metrics["last_updated"] = datetime.utcnow().isoformat() + "Z"
            # Clean old history entries
            self._clean_history()
            
            with open(self.metrics_path, 'w') as f:
                json.dump(self._metrics, f, indent=2)
        except (IOError, OSError) as e:
            # Don't fail if we can't write metrics
            pass
    
    def _clean_history(self) -> None:
        """Remove history entries older than retention period."""
        if "history" not in self._metrics:
            return
        
        cutoff = datetime.utcnow() - timedelta(days=METRICS_RETENTION_DAYS)
        cutoff_iso = cutoff.isoformat() + "Z"
        
        self._metrics["history"] = [
            entry for entry in self._metrics["history"]
            if entry.get("timestamp", "") > cutoff_iso
        ]
    
    def increment_counter(self, counter_name: str, amount: int = 1) -> None:
        """Increment a counter metric."""
        if counter_name not in self._metrics["counters"]:
            self._metrics["counters"][counter_name] = 0
        self._metrics["counters"][counter_name] += amount
        self._save_metrics()
    
    def set_current_state(self, key: str, value: Any) -> None:
        """Update current state metric."""
        self._metrics["current_state"][key] = value
        self._save_metrics()
    
    def add_history_entry(self, event_type: str, details: Dict[str, Any]) -> None:
        """Add an entry to the history log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "details": details
        }
        self._metrics["history"].append(entry)
        # Keep only last 1000 entries
        if len(self._metrics["history"]) > 1000:
            self._metrics["history"] = self._metrics["history"][-1000:]
        self._save_metrics()
    
    def record_onion_creation(self, onion_address: str) -> None:
        """Record onion service creation."""
        self.increment_counter("onion_creations")
        self.set_current_state("onion_address", onion_address)
        self.set_current_state("onion_created_at", datetime.utcnow().isoformat() + "Z")
        self.set_current_state("status", "active")
        self.add_history_entry("onion_created", {"address": onion_address})
    
    def record_onion_rotation(self, old_address: Optional[str], new_address: str) -> None:
        """Record onion service rotation."""
        self.increment_counter("onion_rotations")
        self.set_current_state("onion_address", new_address)
        self.set_current_state("onion_created_at", datetime.utcnow().isoformat() + "Z")
        self.add_history_entry("onion_rotated", {
            "old_address": old_address,
            "new_address": new_address
        })
    
    def record_verification(self, success: bool, onion_address: Optional[str] = None) -> None:
        """Record tunnel verification result."""
        if success:
            self.increment_counter("verification_successes")
            self.set_current_state("verification_status", "success")
        else:
            self.increment_counter("verification_failures")
            self.set_current_state("verification_status", "failed")
        
        self.set_current_state("last_verification", datetime.utcnow().isoformat() + "Z")
        if onion_address:
            self.set_current_state("onion_address", onion_address)
        
        self.add_history_entry("verification", {
            "success": success,
            "onion_address": onion_address
        })
    
    def record_error(self, error_type: str, error_message: str) -> None:
        """Record an error."""
        self.increment_counter("errors")
        self.set_current_state("status", "error")
        self.add_history_entry("error", {
            "error_type": error_type,
            "error_message": error_message
        })
    
    def record_recovery(self) -> None:
        """Record successful recovery from error."""
        self.increment_counter("recoveries")
        self.set_current_state("status", "recovered")
        self.add_history_entry("recovery", {})
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics dictionary."""
        return self._metrics.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics."""
        return {
            "status": self._metrics["current_state"]["status"],
            "onion_address": self._metrics["current_state"]["onion_address"],
            "onion_created_at": self._metrics["current_state"]["onion_created_at"],
            "verification_status": self._metrics["current_state"]["verification_status"],
            "counters": self._metrics["counters"].copy(),
            "last_updated": self._metrics["last_updated"]
        }


# Global metrics instance
_metrics_instance: Optional[TunnelMetrics] = None


def get_metrics() -> TunnelMetrics:
    """Get or create the global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = TunnelMetrics()
    return _metrics_instance


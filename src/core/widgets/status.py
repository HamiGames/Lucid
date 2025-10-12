"""
Status widgets for Lucid application.

This module provides comprehensive status display widgets for various
components and services in the Lucid ecosystem.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass
import threading
import time
from datetime import datetime


class StatusLevel(Enum):
    """Status level enumeration."""
    UNKNOWN = "unknown"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ONLINE = "online"
    WARNING = "warning"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ComponentType(Enum):
    """Component type enumeration."""
    SERVICE = "service"
    DATABASE = "database"
    BLOCKCHAIN = "blockchain"
    TOR = "tor"
    NODE = "node"
    RDP = "rdp"
    API = "api"
    GUI = "gui"
    STORAGE = "storage"


@dataclass
class StatusInfo:
    """Status information data structure."""
    component_id: str
    component_type: ComponentType
    name: str
    status: StatusLevel
    message: str
    last_updated: datetime
    details: Optional[Dict[str, Any]] = None
    health_score: float = 0.0
    response_time: Optional[float] = None
    uptime: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "last_updated": self.last_updated.isoformat(),
            "details": self.details or {},
            "health_score": self.health_score,
            "response_time": self.response_time,
            "uptime": self.uptime
        }


class StatusWidget:
    """Base status widget class."""
    
    def __init__(self, parent: tk.Widget, component_id: str, name: str, 
                 component_type: ComponentType = ComponentType.SERVICE):
        self.parent = parent
        self.component_id = component_id
        self.name = name
        self.component_type = component_type
        self.status_info: Optional[StatusInfo] = None
        self.callbacks: List[Callable] = []
        
        # Status level colors
        self.status_colors = {
            StatusLevel.UNKNOWN: "#808080",
            StatusLevel.OFFLINE: "#FF0000",
            StatusLevel.CONNECTING: "#FFA500",
            StatusLevel.ONLINE: "#00FF00",
            StatusLevel.WARNING: "#FFFF00",
            StatusLevel.ERROR: "#FF4500",
            StatusLevel.MAINTENANCE: "#8A2BE2"
        }
        
        # Status level icons (Unicode symbols)
        self.status_icons = {
            StatusLevel.UNKNOWN: "?",
            StatusLevel.OFFLINE: "●",
            StatusLevel.CONNECTING: "◐",
            StatusLevel.ONLINE: "●",
            StatusLevel.WARNING: "⚠",
            StatusLevel.ERROR: "✗",
            StatusLevel.MAINTENANCE: "⚙"
        }
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the widget components."""
        self.frame = ttk.Frame(self.parent)
        
        # Status indicator
        self.status_label = ttk.Label(
            self.frame,
            text=self.status_icons[StatusLevel.UNKNOWN],
            font=("Arial", 12, "bold"),
            foreground=self.status_colors[StatusLevel.UNKNOWN]
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Component name
        self.name_label = ttk.Label(
            self.frame,
            text=self.name,
            font=("Arial", 10, "bold")
        )
        self.name_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status text
        self.status_text = ttk.Label(
            self.frame,
            text="Unknown",
            font=("Arial", 9)
        )
        self.status_text.pack(side=tk.LEFT, padx=(0, 10))
        
        # Details button
        self.details_button = ttk.Button(
            self.frame,
            text="Details",
            command=self._show_details,
            width=8
        )
        self.details_button.pack(side=tk.RIGHT)
    
    def update_status(self, status_info: StatusInfo):
        """Update the status display."""
        self.status_info = status_info
        
        # Update status indicator
        color = self.status_colors.get(status_info.status, "#808080")
        icon = self.status_icons.get(status_info.status, "?")
        
        self.status_label.configure(
            text=icon,
            foreground=color
        )
        
        # Update status text
        self.status_text.configure(text=status_info.message)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(status_info)
            except Exception:
                pass  # Ignore callback errors
    
    def add_callback(self, callback: Callable):
        """Add status update callback."""
        self.callbacks.append(callback)
    
    def _show_details(self):
        """Show detailed status information."""
        if not self.status_info:
            return
        
        # Create details window
        details_window = tk.Toplevel(self.parent)
        details_window.title(f"Status Details - {self.name}")
        details_window.geometry("400x300")
        details_window.resizable(False, False)
        
        # Details text
        details_text = tk.Text(details_window, wrap=tk.WORD, padx=10, pady=10)
        details_text.pack(fill=tk.BOTH, expand=True)
        
        # Format details
        details = self.status_info.to_dict()
        details_str = "\n".join([f"{k}: {v}" for k, v in details.items()])
        details_text.insert(tk.END, details_str)
        details_text.configure(state=tk.DISABLED)
        
        # Close button
        close_button = ttk.Button(details_window, text="Close", 
                                command=details_window.destroy)
        close_button.pack(pady=10)


class StatusGrid:
    """Grid layout for multiple status widgets."""
    
    def __init__(self, parent: tk.Widget, title: str = "System Status"):
        self.parent = parent
        self.title = title
        self.widgets: Dict[str, StatusWidget] = {}
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the grid widget components."""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        
        # Title
        title_label = ttk.Label(
            self.main_frame,
            text=self.title,
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Status widgets container
        self.container_frame = ttk.Frame(self.main_frame)
        self.container_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.container_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            self.container_frame,
            yscrollcommand=self.scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar.configure(command=self.canvas.yview)
        
        # Scrollable frame
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )
        
        # Bind events
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(
                self.canvas_window,
                width=e.width
            )
        )
    
    def add_component(self, component_id: str, name: str, 
                     component_type: ComponentType = ComponentType.SERVICE) -> StatusWidget:
        """Add a status widget for a component."""
        widget = StatusWidget(
            self.scrollable_frame,
            component_id,
            name,
            component_type
        )
        widget.frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.widgets[component_id] = widget
        return widget
    
    def update_component_status(self, component_id: str, status_info: StatusInfo):
        """Update status for a specific component."""
        if component_id in self.widgets:
            self.widgets[component_id].update_status(status_info)
    
    def remove_component(self, component_id: str):
        """Remove a component from the grid."""
        if component_id in self.widgets:
            self.widgets[component_id].frame.destroy()
            del self.widgets[component_id]
    
    def get_component_widget(self, component_id: str) -> Optional[StatusWidget]:
        """Get a component widget by ID."""
        return self.widgets.get(component_id)


class StatusMonitor:
    """Background status monitoring service."""
    
    def __init__(self, status_grid: StatusGrid, update_interval: int = 30):
        self.status_grid = status_grid
        self.update_interval = update_interval
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.status_checkers: Dict[str, Callable] = {}
    
    def add_status_checker(self, component_id: str, checker: Callable):
        """Add a status checker function for a component."""
        self.status_checkers[component_id] = checker
    
    def start_monitoring(self):
        """Start background status monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background status monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            for component_id, checker in self.status_checkers.items():
                try:
                    status_info = checker()
                    if status_info:
                        self.status_grid.update_component_status(component_id, status_info)
                except Exception:
                    # Create error status
                    error_status = StatusInfo(
                        component_id=component_id,
                        component_type=ComponentType.SERVICE,
                        name=self.status_grid.get_component_widget(component_id).name if component_id in self.status_grid.widgets else "Unknown",
                        status=StatusLevel.ERROR,
                        message="Status check failed",
                        last_updated=datetime.now(),
                        health_score=0.0
                    )
                    self.status_grid.update_component_status(component_id, error_status)
            
            time.sleep(self.update_interval)


class HealthIndicator:
    """Health score indicator widget."""
    
    def __init__(self, parent: tk.Widget, size: int = 20):
        self.parent = parent
        self.size = size
        self.health_score = 0.0
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the health indicator widget."""
        self.canvas = tk.Canvas(
            self.parent,
            width=self.size,
            height=self.size,
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Draw initial indicator
        self._draw_indicator()
    
    def _draw_indicator(self):
        """Draw the health indicator."""
        self.canvas.delete("all")
        
        # Calculate color based on health score
        if self.health_score >= 0.8:
            color = "#00FF00"  # Green
        elif self.health_score >= 0.6:
            color = "#FFFF00"  # Yellow
        elif self.health_score >= 0.4:
            color = "#FFA500"  # Orange
        else:
            color = "#FF0000"  # Red
        
        # Draw circle
        margin = 2
        self.canvas.create_oval(
            margin, margin,
            self.size - margin, self.size - margin,
            fill=color,
            outline="black",
            width=1
        )
    
    def update_health(self, health_score: float):
        """Update the health score and redraw."""
        self.health_score = max(0.0, min(1.0, health_score))
        self._draw_indicator()


def create_default_status_checker(component_id: str, component_type: ComponentType) -> Callable:
    """Create a default status checker for a component."""
    def checker() -> StatusInfo:
        """Default status checker."""
        # this would check the actual component status
        return StatusInfo(
            component_id=component_id,
            component_type=component_type,
            name=component_id.replace("_", " ").title(),
            status=StatusLevel.ONLINE,
            message="Component is running",
            last_updated=datetime.now(),
            health_score=0.9,
            response_time=50.0,
            uptime="2h 30m"
        )
    
    return checker


def create_lucid_status_grid(parent: tk.Widget) -> StatusGrid:
    """Create a pre-configured status grid for Lucid components."""
    status_grid = StatusGrid(parent, "Lucid System Status")
    
    # Add common Lucid components
    components = [
        ("lucid_api", "API Service", ComponentType.API),
        ("lucid_gui", "GUI Interface", ComponentType.GUI),
        ("lucid_database", "MongoDB", ComponentType.DATABASE),
        ("lucid_blockchain", "Blockchain Node", ComponentType.BLOCKCHAIN),
        ("lucid_tor", "Tor Proxy", ComponentType.TOR),
        ("lucid_rdp", "RDP Server", ComponentType.RDP),
        ("lucid_node", "Consensus Node", ComponentType.NODE),
        ("lucid_storage", "Storage Service", ComponentType.STORAGE)
    ]
    
    for component_id, name, component_type in components:
        status_grid.add_component(component_id, name, component_type)
    
    return status_grid

"""
Progress widgets for Lucid application.

This module provides comprehensive progress tracking and display widgets
for various operations in the Lucid ecosystem.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
from dataclasses import dataclass
import threading
import time
from datetime import datetime, timedelta
import math


class ProgressType(Enum):
    """Progress type enumeration."""
    DETERMINATE = "determinate"
    INDETERMINATE = "indeterminate"
    PULSE = "pulse"
    STEP = "step"


class ProgressStyle(Enum):
    """Progress display style enumeration."""
    BAR = "bar"
    CIRCULAR = "circular"
    TEXT = "text"
    MINIMAL = "minimal"


class OperationType(Enum):
    """Operation type enumeration."""
    DOWNLOAD = "download"
    UPLOAD = "upload"
    BUILD = "build"
    SYNC = "sync"
    BACKUP = "backup"
    RESTORE = "restore"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    COMPRESS = "compress"
    EXTRACT = "extract"
    PROCESS = "process"
    SCAN = "scan"
    VALIDATE = "validate"
    GENERIC = "generic"


@dataclass
class ProgressInfo:
    """Progress information data structure."""
    operation_id: str
    operation_type: OperationType
    title: str
    description: str
    progress_type: ProgressType
    current_value: float
    max_value: float
    step_count: Optional[int] = None
    current_step: Optional[int] = None
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    speed: Optional[float] = None  # items per second
    eta: Optional[timedelta] = None
    status_message: str = ""
    is_cancellable: bool = True
    is_paused: bool = False
    error_message: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        """Calculate percentage completion."""
        if self.max_value == 0:
            return 0.0
        return min(100.0, (self.current_value / self.max_value) * 100.0)
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.current_value >= self.max_value
    
    @property
    def is_running(self) -> bool:
        """Check if operation is running."""
        return not self.is_complete and not self.is_paused and self.error_message is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "title": self.title,
            "description": self.description,
            "progress_type": self.progress_type.value,
            "current_value": self.current_value,
            "max_value": self.max_value,
            "step_count": self.step_count,
            "current_step": self.current_step,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "speed": self.speed,
            "eta": str(self.eta) if self.eta else None,
            "status_message": self.status_message,
            "is_cancellable": self.is_cancellable,
            "is_paused": self.is_paused,
            "error_message": self.error_message,
            "percentage": self.percentage,
            "is_complete": self.is_complete,
            "is_running": self.is_running
        }


class BaseProgressWidget:
    """Base progress widget class."""
    
    def __init__(self, parent: tk.Widget, operation_id: str, title: str,
                 operation_type: OperationType = OperationType.GENERIC):
        self.parent = parent
        self.operation_id = operation_id
        self.title = title
        self.operation_type = operation_type
        self.progress_info: Optional[ProgressInfo] = None
        self.callbacks: Dict[str, List[Callable]] = {
            "update": [],
            "complete": [],
            "cancel": [],
            "pause": [],
            "resume": [],
            "error": []
        }
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the widget components. Override in subclasses."""
        self.frame = ttk.Frame(self.parent)
    
    def update_progress(self, progress_info: ProgressInfo):
        """Update the progress display. Override in subclasses."""
        self.progress_info = progress_info
        self._emit_callback("update", progress_info)
    
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for progress events."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _emit_callback(self, event: str, *args, **kwargs):
        """Emit a callback event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass  # Ignore callback errors


class ProgressBarWidget(BaseProgressWidget):
    """Standard progress bar widget."""
    
    def __init__(self, parent: tk.Widget, operation_id: str, title: str,
                 operation_type: OperationType = OperationType.GENERIC,
                 show_percentage: bool = True, show_eta: bool = True):
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        super().__init__(parent, operation_id, title, operation_type)
    
    def _create_widgets(self):
        """Create the progress bar widget components."""
        super()._create_widgets()
        
        # Title
        self.title_label = ttk.Label(
            self.frame,
            text=self.title,
            font=("Arial", 10, "bold")
        )
        self.title_label.pack(anchor=tk.W, pady=(0, 2))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            mode="determinate",
            length=300
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 2))
        
        # Status frame
        self.status_frame = ttk.Frame(self.frame)
        self.status_frame.pack(fill=tk.X)
        
        # Status message
        self.status_label = ttk.Label(
            self.status_frame,
            text="",
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Percentage label
        if self.show_percentage:
            self.percentage_label = ttk.Label(
                self.status_frame,
                text="0%",
                font=("Arial", 9, "bold")
            )
            self.percentage_label.pack(side=tk.RIGHT)
        
        # Control buttons frame
        self.controls_frame = ttk.Frame(self.frame)
        self.controls_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Cancel button
        self.cancel_button = ttk.Button(
            self.controls_frame,
            text="Cancel",
            command=self._cancel_operation,
            width=10
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
        # Pause/Resume button
        self.pause_button = ttk.Button(
            self.controls_frame,
            text="Pause",
            command=self._toggle_pause,
            width=10
        )
        self.pause_button.pack(side=tk.RIGHT, padx=(0, 5))
    
    def update_progress(self, progress_info: ProgressInfo):
        """Update the progress bar display."""
        super().update_progress(progress_info)
        
        if not progress_info:
            return
        
        # Update progress bar
        self.progress_var.set(progress_info.percentage)
        
        # Update status message
        self.status_label.configure(text=progress_info.status_message)
        
        # Update percentage
        if self.show_percentage:
            self.percentage_label.configure(text=f"{progress_info.percentage:.1f}%")
        
        # Update button states
        self.cancel_button.configure(state="normal" if progress_info.is_cancellable else "disabled")
        self.pause_button.configure(
            text="Resume" if progress_info.is_paused else "Pause",
            state="normal" if progress_info.is_running else "disabled"
        )
        
        # Change progress bar mode for indeterminate operations
        if progress_info.progress_type == ProgressType.INDETERMINATE:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
        else:
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.stop()
    
    def _cancel_operation(self):
        """Cancel the operation."""
        if self.progress_info and self.progress_info.is_cancellable:
            self._emit_callback("cancel", self.progress_info)
    
    def _toggle_pause(self):
        """Toggle pause/resume."""
        if self.progress_info and self.progress_info.is_running:
            event = "resume" if self.progress_info.is_paused else "pause"
            self._emit_callback(event, self.progress_info)


class CircularProgressWidget(BaseProgressWidget):
    """Circular progress widget."""
    
    def __init__(self, parent: tk.Widget, operation_id: str, title: str,
                 operation_type: OperationType = OperationType.GENERIC,
                 size: int = 100):
        self.size = size
        super().__init__(parent, operation_id, title, operation_type)
    
    def _create_widgets(self):
        """Create the circular progress widget components."""
        super()._create_widgets()
        
        # Title
        self.title_label = ttk.Label(
            self.frame,
            text=self.title,
            font=("Arial", 10, "bold")
        )
        self.title_label.pack(pady=(0, 5))
        
        # Canvas for circular progress
        self.canvas = tk.Canvas(
            self.frame,
            width=self.size,
            height=self.size,
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Percentage label in center
        self.percentage_label = ttk.Label(
            self.canvas,
            text="0%",
            font=("Arial", 12, "bold")
        )
        self.canvas.create_window(
            self.size // 2, self.size // 2,
            window=self.percentage_label
        )
        
        # Status message
        self.status_label = ttk.Label(
            self.frame,
            text="",
            font=("Arial", 9)
        )
        self.status_label.pack(pady=(5, 0))
    
    def update_progress(self, progress_info: ProgressInfo):
        """Update the circular progress display."""
        super().update_progress(progress_info)
        
        if not progress_info:
            return
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw background circle
        margin = 5
        self.canvas.create_oval(
            margin, margin,
            self.size - margin, self.size - margin,
            outline="#E0E0E0",
            width=3
        )
        
        # Draw progress arc
        if progress_info.percentage > 0:
            extent = (progress_info.percentage / 100.0) * 360
            self.canvas.create_arc(
                margin, margin,
                self.size - margin, self.size - margin,
                start=90, extent=-extent,
                outline="#0078D4",
                width=3,
                style=tk.ARC
            )
        
        # Update percentage label
        self.percentage_label.configure(text=f"{progress_info.percentage:.0f}%")
        
        # Update status message
        self.status_label.configure(text=progress_info.status_message)


class StepProgressWidget(BaseProgressWidget):
    """Step-based progress widget."""
    
    def __init__(self, parent: tk.Widget, operation_id: str, title: str,
                 operation_type: OperationType = OperationType.GENERIC):
        self.steps: List[str] = []
        super().__init__(parent, operation_id, title, operation_type)
    
    def set_steps(self, steps: List[str]):
        """Set the step descriptions."""
        self.steps = steps
        self._update_step_display()
    
    def _create_widgets(self):
        """Create the step progress widget components."""
        super()._create_widgets()
        
        # Title
        self.title_label = ttk.Label(
            self.frame,
            text=self.title,
            font=("Arial", 10, "bold")
        )
        self.title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Steps container
        self.steps_frame = ttk.Frame(self.frame)
        self.steps_frame.pack(fill=tk.X)
        
        # Status message
        self.status_label = ttk.Label(
            self.frame,
            text="",
            font=("Arial", 9)
        )
        self.status_label.pack(pady=(10, 0))
    
    def _update_step_display(self):
        """Update the step display."""
        # Clear existing step widgets
        for widget in self.steps_frame.winfo_children():
            widget.destroy()
        
        # Create step widgets
        for i, step in enumerate(self.steps):
            step_frame = ttk.Frame(self.steps_frame)
            step_frame.pack(fill=tk.X, pady=2)
            
            # Step number
            step_number = ttk.Label(
                step_frame,
                text=str(i + 1),
                font=("Arial", 10, "bold"),
                width=3
            )
            step_number.pack(side=tk.LEFT)
            
            # Step description
            step_label = ttk.Label(
                step_frame,
                text=step,
                font=("Arial", 9)
            )
            step_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # Step status indicator
            status_indicator = ttk.Label(
                step_frame,
                text="○",
                font=("Arial", 12),
                foreground="#808080"
            )
            status_indicator.pack(side=tk.RIGHT)
            
            # Store references for updates
            setattr(step_frame, "step_number", step_number)
            setattr(step_frame, "step_label", step_label)
            setattr(step_frame, "status_indicator", status_indicator)
    
    def update_progress(self, progress_info: ProgressInfo):
        """Update the step progress display."""
        super().update_progress(progress_info)
        
        if not progress_info:
            return
        
        # Update step indicators
        for i, step_frame in enumerate(self.steps_frame.winfo_children()):
            status_indicator = step_frame.status_indicator
            
            if i < progress_info.current_step:
                # Completed step
                status_indicator.configure(text="●", foreground="#00FF00")
            elif i == progress_info.current_step:
                # Current step
                status_indicator.configure(text="◐", foreground="#FFA500")
            else:
                # Future step
                status_indicator.configure(text="○", foreground="#808080")
        
        # Update status message
        self.status_label.configure(text=progress_info.status_message)


class ProgressManager:
    """Manager for multiple progress operations."""
    
    def __init__(self, parent: tk.Widget, max_concurrent: int = 5):
        self.parent = parent
        self.max_concurrent = max_concurrent
        self.active_operations: Dict[str, BaseProgressWidget] = {}
        self.completed_operations: List[ProgressInfo] = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the progress manager widgets."""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        
        # Title
        title_label = ttk.Label(
            self.main_frame,
            text="Progress Operations",
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Active operations frame
        self.active_frame = ttk.LabelFrame(
            self.main_frame,
            text="Active Operations"
        )
        self.active_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Completed operations frame
        self.completed_frame = ttk.LabelFrame(
            self.main_frame,
            text="Completed Operations"
        )
        self.completed_frame.pack(fill=tk.X)
        
        # Clear completed button
        self.clear_button = ttk.Button(
            self.completed_frame,
            text="Clear Completed",
            command=self._clear_completed
        )
        self.clear_button.pack(pady=5)
    
    def start_operation(self, operation_id: str, title: str,
                       operation_type: OperationType = OperationType.GENERIC,
                       progress_type: ProgressType = ProgressType.DETERMINATE,
                       style: ProgressStyle = ProgressStyle.BAR,
                       **kwargs) -> BaseProgressWidget:
        """Start a new progress operation."""
        if len(self.active_operations) >= self.max_concurrent:
            raise ValueError(f"Maximum concurrent operations ({self.max_concurrent}) exceeded")
        
        # Create appropriate widget based on style
        if style == ProgressStyle.BAR:
            widget = ProgressBarWidget(
                self.active_frame, operation_id, title, operation_type, **kwargs
            )
        elif style == ProgressStyle.CIRCULAR:
            widget = CircularProgressWidget(
                self.active_frame, operation_id, title, operation_type, **kwargs
            )
        elif style == ProgressStyle.TEXT:
            # Text-only progress (minimal implementation)
            widget = ProgressBarWidget(
                self.active_frame, operation_id, title, operation_type,
                show_percentage=True, show_eta=False, **kwargs
            )
        else:  # MINIMAL
            widget = ProgressBarWidget(
                self.active_frame, operation_id, title, operation_type,
                show_percentage=False, show_eta=False, **kwargs
            )
        
        widget.frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Add completion callback
        widget.add_callback("complete", self._on_operation_complete)
        
        self.active_operations[operation_id] = widget
        return widget
    
    def update_operation(self, operation_id: str, progress_info: ProgressInfo):
        """Update a progress operation."""
        if operation_id in self.active_operations:
            self.active_operations[operation_id].update_progress(progress_info)
            
            # Check if operation is complete
            if progress_info.is_complete:
                self._on_operation_complete(progress_info)
    
    def cancel_operation(self, operation_id: str):
        """Cancel a progress operation."""
        if operation_id in self.active_operations:
            widget = self.active_operations[operation_id]
            widget._emit_callback("cancel", widget.progress_info)
            self._remove_operation(operation_id)
    
    def _on_operation_complete(self, progress_info: ProgressInfo):
        """Handle operation completion."""
        if progress_info.operation_id in self.active_operations:
            self.completed_operations.append(progress_info)
            self._remove_operation(progress_info.operation_id)
    
    def _remove_operation(self, operation_id: str):
        """Remove an operation from active operations."""
        if operation_id in self.active_operations:
            widget = self.active_operations[operation_id]
            widget.frame.destroy()
            del self.active_operations[operation_id]
    
    def _clear_completed(self):
        """Clear completed operations list."""
        self.completed_operations.clear()


def format_eta(eta: timedelta) -> str:
    """Format ETA timedelta as human-readable string."""
    if eta is None:
        return "Unknown"
    
    total_seconds = int(eta.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_speed(speed: float, unit: str = "items") -> str:
    """Format speed as human-readable string."""
    if speed is None:
        return "Unknown"
    
    if speed < 1000:
        return f"{speed:.1f} {unit}/s"
    elif speed < 1000000:
        return f"{speed/1000:.1f}K {unit}/s"
    else:
        return f"{speed/1000000:.1f}M {unit}/s"


def create_progress_info(operation_id: str, title: str,
                        operation_type: OperationType = OperationType.GENERIC,
                        progress_type: ProgressType = ProgressType.DETERMINATE,
                        max_value: float = 100.0, current_value: float = 0.0,
                        **kwargs) -> ProgressInfo:
    """Create a ProgressInfo instance with common defaults."""
    return ProgressInfo(
        operation_id=operation_id,
        operation_type=operation_type,
        title=title,
        description=kwargs.get("description", ""),
        progress_type=progress_type,
        current_value=current_value,
        max_value=max_value,
        step_count=kwargs.get("step_count"),
        current_step=kwargs.get("current_step"),
        start_time=kwargs.get("start_time", datetime.now()),
        estimated_completion=kwargs.get("estimated_completion"),
        speed=kwargs.get("speed"),
        eta=kwargs.get("eta"),
        status_message=kwargs.get("status_message", ""),
        is_cancellable=kwargs.get("is_cancellable", True),
        is_paused=kwargs.get("is_paused", False),
        error_message=kwargs.get("error_message")
    )

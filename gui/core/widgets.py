# Path: gui/core/widgets.py
"""
Reusable Tkinter widgets and theming for Lucid RDP GUI.
Provides custom widgets, themes, and styling utilities for consistent GUI appearance.
"""

import tkinter as tk
from tkinter import ttk, font
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ThemeMode(Enum):
    """Theme mode enumeration"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


@dataclass
class ColorScheme:
    """Color scheme configuration"""
    # Background colors
    bg_primary: str = "#ffffff"
    bg_secondary: str = "#f5f5f5"
    bg_tertiary: str = "#e0e0e0"
    
    # Text colors
    text_primary: str = "#000000"
    text_secondary: str = "#666666"
    text_disabled: str = "#999999"
    
    # Accent colors
    accent_primary: str = "#007acc"
    accent_secondary: str = "#005a9e"
    accent_hover: str = "#0066cc"
    
    # Status colors
    success: str = "#28a745"
    warning: str = "#ffc107"
    error: str = "#dc3545"
    info: str = "#17a2b8"
    
    # Border colors
    border_light: str = "#cccccc"
    border_dark: str = "#333333"
    
    def to_dict(self) -> Dict[str, str]:
        """Convert color scheme to dictionary"""
        return {
            'bg_primary': self.bg_primary,
            'bg_secondary': self.bg_secondary,
            'bg_tertiary': self.bg_tertiary,
            'text_primary': self.text_primary,
            'text_secondary': self.text_secondary,
            'text_disabled': self.text_disabled,
            'accent_primary': self.accent_primary,
            'accent_secondary': self.accent_secondary,
            'accent_hover': self.accent_hover,
            'success': self.success,
            'warning': self.warning,
            'error': self.error,
            'info': self.info,
            'border_light': self.border_light,
            'border_dark': self.border_dark,
        }


class ThemeManager:
    """Manages GUI themes and styling"""
    
    def __init__(self):
        self.current_theme = ThemeMode.LIGHT
        self.color_schemes: Dict[ThemeMode, ColorScheme] = {
            ThemeMode.LIGHT: ColorScheme(),
            ThemeMode.DARK: ColorScheme(
                bg_primary="#1e1e1e",
                bg_secondary="#2d2d2d",
                bg_tertiary="#3c3c3c",
                text_primary="#ffffff",
                text_secondary="#cccccc",
                text_disabled="#888888",
                accent_primary="#007acc",
                accent_secondary="#005a9e",
                accent_hover="#0066cc",
                border_light="#555555",
                border_dark="#777777"
            )
        }
        self.custom_styles: Dict[str, Dict[str, Any]] = {}
        self._setup_default_styles()
    
    def _setup_default_styles(self) -> None:
        """Setup default ttk styles"""
        style = ttk.Style()
        
        # Configure base styles
        style.configure("Lucid.TFrame", background=self.get_color('bg_primary'))
        style.configure("Lucid.TLabel", background=self.get_color('bg_primary'), foreground=self.get_color('text_primary'))
        style.configure("Lucid.TButton", background=self.get_color('accent_primary'), foreground="white")
        style.configure("Lucid.TEntry", fieldbackground=self.get_color('bg_primary'), foreground=self.get_color('text_primary'))
        style.configure("Lucid.TCombobox", fieldbackground=self.get_color('bg_primary'), foreground=self.get_color('text_primary'))
        
        # Status styles
        style.configure("Success.TLabel", foreground=self.get_color('success'))
        style.configure("Warning.TLabel", foreground=self.get_color('warning'))
        style.configure("Error.TLabel", foreground=self.get_color('error'))
        style.configure("Info.TLabel", foreground=self.get_color('info'))
        
        # Custom button styles
        style.configure("Lucid.TButton", padding=(10, 5))
        style.map("Lucid.TButton",
                 background=[('active', self.get_color('accent_hover')),
                           ('pressed', self.get_color('accent_secondary'))])
    
    def set_theme(self, theme: ThemeMode) -> None:
        """Set the current theme"""
        self.current_theme = theme
        self._setup_default_styles()
        logger.info(f"Theme changed to: {theme.value}")
    
    def get_color(self, color_name: str) -> str:
        """Get color value by name"""
        scheme = self.color_schemes[self.current_theme]
        return getattr(scheme, color_name, "#000000")
    
    def get_color_scheme(self) -> ColorScheme:
        """Get current color scheme"""
        return self.color_schemes[self.current_theme]
    
    def create_custom_style(self, style_name: str, **kwargs) -> None:
        """Create custom ttk style"""
        self.custom_styles[style_name] = kwargs
        style = ttk.Style()
        style.configure(style_name, **kwargs)
    
    def apply_theme_to_widget(self, widget: tk.Widget, style_name: str = None) -> None:
        """Apply theme to a specific widget"""
        if isinstance(widget, ttk.Widget):
            if style_name:
                widget.configure(style=style_name)
            else:
                # Apply default styling based on widget type
                widget_class = widget.winfo_class()
                if 'Label' in widget_class:
                    widget.configure(style="Lucid.TLabel")
                elif 'Button' in widget_class:
                    widget.configure(style="Lucid.TButton")
                elif 'Frame' in widget_class:
                    widget.configure(style="Lucid.TFrame")
                elif 'Entry' in widget_class:
                    widget.configure(style="Lucid.TEntry")
        else:
            # Apply colors to regular tkinter widgets
            scheme = self.get_color_scheme()
            if isinstance(widget, (tk.Label, tk.Button)):
                widget.configure(bg=scheme.bg_primary, fg=scheme.text_primary)
            elif isinstance(widget, tk.Frame):
                widget.configure(bg=scheme.bg_primary)


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get global theme manager instance"""
    global _theme_manager
    
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    
    return _theme_manager


class StatusLabel(tk.Label):
    """Custom status label with built-in status styling"""
    
    def __init__(self, parent, text: str = "", status: str = "info", **kwargs):
        self.status = status
        self.theme_manager = get_theme_manager()
        
        # Configure based on status
        status_config = self._get_status_config(status)
        kwargs.update(status_config)
        
        super().__init__(parent, text=text, **kwargs)
    
    def _get_status_config(self, status: str) -> Dict[str, Any]:
        """Get configuration for status type"""
        scheme = self.theme_manager.get_color_scheme()
        
        status_colors = {
            'success': scheme.success,
            'warning': scheme.warning,
            'error': scheme.error,
            'info': scheme.info,
            'primary': scheme.text_primary,
            'secondary': scheme.text_secondary
        }
        
        return {
            'fg': status_colors.get(status, scheme.text_primary),
            'bg': scheme.bg_primary,
            'font': ('Arial', 9)
        }
    
    def set_status(self, status: str, text: str = None) -> None:
        """Update status and optionally text"""
        if text is not None:
            self.configure(text=text)
        
        self.status = status
        config = self._get_status_config(status)
        self.configure(**config)


class ProgressBar(tk.Frame):
    """Custom progress bar widget"""
    
    def __init__(self, parent, width: int = 200, height: int = 20, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.width = width
        self.height = height
        self.progress = 0.0
        self.theme_manager = get_theme_manager()
        
        # Create progress canvas
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=self.theme_manager.get_color('bg_secondary'),
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Draw initial progress bar
        self._draw_progress()
    
    def _draw_progress(self) -> None:
        """Draw the progress bar"""
        self.canvas.delete("progress")
        
        scheme = self.theme_manager.get_color_scheme()
        
        # Background
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=scheme.bg_secondary,
            outline=scheme.border_light,
            tags="progress"
        )
        
        # Progress fill
        if self.progress > 0:
            progress_width = int(self.width * self.progress)
            self.canvas.create_rectangle(
                0, 0, progress_width, self.height,
                fill=scheme.accent_primary,
                outline="",
                tags="progress"
            )
        
        # Progress text
        if self.progress > 0.1:  # Only show text if there's enough space
            percentage = int(self.progress * 100)
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=f"{percentage}%",
                fill=scheme.text_primary,
                font=('Arial', 8, 'bold'),
                tags="progress"
            )
    
    def set_progress(self, value: float) -> None:
        """Set progress value (0.0 to 1.0)"""
        self.progress = max(0.0, min(1.0, value))
        self._draw_progress()
    
    def get_progress(self) -> float:
        """Get current progress value"""
        return self.progress


class CollapsibleFrame(tk.Frame):
    """Collapsible frame widget"""
    
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title = title
        self.is_collapsed = False
        self.content_frame = None
        self.theme_manager = get_theme_manager()
        
        self._create_header()
    
    def _create_header(self) -> None:
        """Create collapsible header"""
        scheme = self.theme_manager.get_color_scheme()
        
        self.header_frame = tk.Frame(self, bg=scheme.bg_secondary)
        self.header_frame.pack(fill=tk.X, padx=2, pady=2)
        
        # Toggle button
        self.toggle_btn = tk.Button(
            self.header_frame,
            text="▼ " + self.title,
            command=self.toggle,
            bg=scheme.bg_secondary,
            fg=scheme.text_primary,
            relief=tk.FLAT,
            font=('Arial', 9, 'bold')
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5, pady=2)
    
    def set_content(self, content_frame: tk.Frame) -> None:
        """Set the content frame"""
        self.content_frame = content_frame
        if not self.is_collapsed:
            content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def toggle(self) -> None:
        """Toggle collapsed state"""
        self.is_collapsed = not self.is_collapsed
        
        if self.content_frame:
            if self.is_collapsed:
                self.content_frame.pack_forget()
                self.toggle_btn.configure(text="▶ " + self.title)
            else:
                self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                self.toggle_btn.configure(text="▼ " + self.title)


class LogViewer(tk.Frame):
    """Custom log viewer widget"""
    
    def __init__(self, parent, max_lines: int = 1000, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.max_lines = max_lines
        self.lines: List[str] = []
        self.theme_manager = get_theme_manager()
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Create log viewer widgets"""
        scheme = self.theme_manager.get_color_scheme()
        
        # Create text widget with scrollbar
        text_frame = tk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            bg=scheme.bg_primary,
            fg=scheme.text_primary,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control buttons
        button_frame = tk.Frame(self, bg=scheme.bg_primary)
        button_frame.pack(fill=tk.X, padx=5, pady=2)
        
        clear_btn = tk.Button(
            button_frame,
            text="Clear",
            command=self.clear,
            bg=scheme.accent_primary,
            fg="white",
            relief=tk.FLAT,
            font=('Arial', 8)
        )
        clear_btn.pack(side=tk.LEFT, padx=2)
        
        auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = tk.Checkbutton(
            button_frame,
            text="Auto-scroll",
            variable=auto_scroll_var,
            command=lambda: setattr(self, 'auto_scroll', auto_scroll_var.get()),
            bg=scheme.bg_primary,
            fg=scheme.text_primary,
            font=('Arial', 8)
        )
        auto_scroll_cb.pack(side=tk.LEFT, padx=10)
        
        self.auto_scroll = True
    
    def add_log(self, message: str, level: str = "INFO") -> None:
        """Add log message"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        
        self.lines.append(log_line)
        
        # Trim to max lines
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]
        
        # Update display
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the text widget display"""
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        
        for line in self.lines:
            self.text_widget.insert(tk.END, line + "\n")
        
        self.text_widget.configure(state=tk.DISABLED)
        
        # Auto-scroll to bottom
        if self.auto_scroll:
            self.text_widget.see(tk.END)
    
    def clear(self) -> None:
        """Clear all logs"""
        self.lines.clear()
        self._update_display()


class Tooltip:
    """Tooltip widget for GUI elements"""
    
    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None
        
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
    
    def on_enter(self, event=None) -> None:
        """Handle mouse enter event"""
        self.schedule_tooltip()
    
    def on_leave(self, event=None) -> None:
        """Handle mouse leave event"""
        self.cancel_tooltip()
        self.hide_tooltip()
    
    def on_motion(self, event=None) -> None:
        """Handle mouse motion event"""
        self.cancel_tooltip()
        self.schedule_tooltip()
    
    def schedule_tooltip(self) -> None:
        """Schedule tooltip display"""
        self.after_id = self.widget.after(self.delay, self.show_tooltip)
    
    def cancel_tooltip(self) -> None:
        """Cancel scheduled tooltip"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
    
    def show_tooltip(self) -> None:
        """Show tooltip window"""
        if self.tooltip_window or not self.text:
            return
        
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=('Arial', 9)
        )
        label.pack(ipadx=1)
    
    def hide_tooltip(self) -> None:
        """Hide tooltip window"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_tooltip(widget: tk.Widget, text: str, delay: int = 500) -> Tooltip:
    """Create a tooltip for a widget"""
    return Tooltip(widget, text, delay)


def apply_theme_to_window(window: tk.Tk, theme: ThemeMode = ThemeMode.LIGHT) -> None:
    """Apply theme to entire window"""
    theme_manager = get_theme_manager()
    theme_manager.set_theme(theme)
    
    scheme = theme_manager.get_color_scheme()
    window.configure(bg=scheme.bg_primary)
    
    # Apply theme to all widgets recursively
    def apply_to_children(widget):
        theme_manager.apply_theme_to_widget(widget)
        for child in widget.winfo_children():
            apply_to_children(child)
    
    apply_to_children(window)


# Convenience functions for common widgets
def create_status_label(parent, text: str = "", status: str = "info") -> StatusLabel:
    """Create a status label"""
    return StatusLabel(parent, text, status)


def create_progress_bar(parent, width: int = 200, height: int = 20) -> ProgressBar:
    """Create a progress bar"""
    return ProgressBar(parent, width, height)


def create_collapsible_frame(parent, title: str) -> CollapsibleFrame:
    """Create a collapsible frame"""
    return CollapsibleFrame(parent, title)


def create_log_viewer(parent, max_lines: int = 1000) -> LogViewer:
    """Create a log viewer"""
    return LogViewer(parent, max_lines)

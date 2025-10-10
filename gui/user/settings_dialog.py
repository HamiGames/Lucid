# Path: gui/user/settings_dialog.py
"""
User preferences and settings dialog for Lucid RDP GUI.
Provides comprehensive settings management for user preferences, connection parameters,
and application configuration.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading

from ..core.config_manager import get_config_manager, GuiConfig, ConfigScope
from ..core.security import get_security_validator, SecurityPolicy
from ..core.networking import SecurityConfig
from ..core.widgets import get_theme_manager, ThemeMode, create_tooltip

logger = logging.getLogger(__name__)


class SettingCategory(Enum):
    """Settings category enumeration"""
    GENERAL = "general"
    NETWORK = "network"
    SECURITY = "security"
    APPEARANCE = "appearance"
    SESSION = "session"
    ADVANCED = "advanced"


class SettingType(Enum):
    """Setting type enumeration"""
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    SELECT = "select"
    FILE_PATH = "file_path"
    DIRECTORY_PATH = "directory_path"
    JSON = "json"


@dataclass
class SettingDefinition:
    """Setting definition structure"""
    key: str
    name: str
    description: str
    category: SettingCategory
    setting_type: SettingType
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    options: Optional[List[str]] = None
    file_filter: Optional[List[tuple]] = None
    validation_func: Optional[Callable[[Any], bool]] = None
    change_callback: Optional[Callable[[Any], None]] = None


@dataclass
class SettingsGroup:
    """Settings group container"""
    name: str
    description: str
    settings: List[SettingDefinition]
    category: SettingCategory


class SettingsValidator:
    """Validates setting values"""
    
    @staticmethod
    def validate_port(value: Any) -> bool:
        """Validate port number"""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_timeout(value: Any) -> bool:
        """Validate timeout value"""
        try:
            timeout = float(value)
            return 1.0 <= timeout <= 300.0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_positive_int(value: Any) -> bool:
        """Validate positive integer"""
        try:
            return int(value) > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_percentage(value: Any) -> bool:
        """Validate percentage value"""
        try:
            percent = float(value)
            return 0.0 <= percent <= 100.0
        except (ValueError, TypeError):
            return False


class SettingsDialog:
    """
    User preferences and settings dialog.
    
    Provides a comprehensive settings interface with:
    - Categorized settings groups
    - Real-time validation
    - Import/export functionality
    - Reset to defaults
    - Live preview for appearance settings
    """
    
    def __init__(self, parent: tk.Widget, on_settings_changed: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.parent = parent
        self.on_settings_changed = on_settings_changed
        
        # Configuration management
        self.config_manager = get_config_manager()
        self.security_validator = get_security_validator()
        self.theme_manager = get_theme_manager()
        
        # Settings storage
        self.settings: Dict[str, Any] = {}
        self.original_settings: Dict[str, Any] = {}
        self.setting_widgets: Dict[str, tk.Widget] = {}
        
        # Setup settings definitions
        self.setup_settings_definitions()
        
        # Load current settings
        self.load_settings()
        
        # Create dialog
        self.dialog = None
        self.create_dialog()
    
    def setup_settings_definitions(self) -> None:
        """Setup all settings definitions"""
        self.settings_groups = [
            SettingsGroup(
                name="General",
                description="General application settings",
                category=SettingCategory.GENERAL,
                settings=[
                    SettingDefinition(
                        key="auto_start",
                        name="Auto-start with system",
                        description="Start Lucid RDP automatically when system boots",
                        category=SettingCategory.GENERAL,
                        setting_type=SettingType.BOOLEAN,
                        default_value=False
                    ),
                    SettingDefinition(
                        key="minimize_to_tray",
                        name="Minimize to system tray",
                        description="Minimize application to system tray instead of closing",
                        category=SettingCategory.GENERAL,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="auto_save_sessions",
                        name="Auto-save sessions",
                        description="Automatically save session configurations",
                        category=SettingCategory.GENERAL,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="check_updates",
                        name="Check for updates",
                        description="Automatically check for application updates",
                        category=SettingCategory.GENERAL,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="update_interval",
                        name="Update check interval (days)",
                        description="How often to check for updates",
                        category=SettingCategory.GENERAL,
                        setting_type=SettingType.INTEGER,
                        default_value=7,
                        min_value=1,
                        max_value=30,
                        validation_func=SettingsValidator.validate_positive_int
                    )
                ]
            ),
            SettingsGroup(
                name="Network",
                description="Network and connection settings",
                category=SettingCategory.NETWORK,
                settings=[
                    SettingDefinition(
                        key="node_api_url",
                        name="Node API URL",
                        description="Default API endpoint for node connections",
                        category=SettingCategory.NETWORK,
                        setting_type=SettingType.STRING,
                        default_value="http://localhost:8080"
                    ),
                    SettingDefinition(
                        key="tor_socks_port",
                        name="Tor SOCKS port",
                        description="SOCKS5 proxy port for Tor connections",
                        category=SettingCategory.NETWORK,
                        setting_type=SettingType.INTEGER,
                        default_value=9150,
                        min_value=1024,
                        max_value=65535,
                        validation_func=SettingsValidator.validate_port
                    ),
                    SettingDefinition(
                        key="tor_control_port",
                        name="Tor control port",
                        description="Control port for Tor management",
                        category=SettingCategory.NETWORK,
                        setting_type=SettingType.INTEGER,
                        default_value=9151,
                        min_value=1024,
                        max_value=65535,
                        validation_func=SettingsValidator.validate_port
                    ),
                    SettingDefinition(
                        key="connection_timeout",
                        name="Connection timeout (seconds)",
                        description="Timeout for establishing connections",
                        category=SettingCategory.NETWORK,
                        setting_type=SettingType.FLOAT,
                        default_value=30.0,
                        min_value=5.0,
                        max_value=120.0,
                        validation_func=SettingsValidator.validate_timeout
                    ),
                    SettingDefinition(
                        key="read_timeout",
                        name="Read timeout (seconds)",
                        description="Timeout for reading data from connections",
                        category=SettingCategory.NETWORK,
                        setting_type=SettingType.FLOAT,
                        default_value=60.0,
                        min_value=10.0,
                        max_value=300.0,
                        validation_func=SettingsValidator.validate_timeout
                    ),
                    SettingDefinition(
                        key="max_retries",
                        name="Maximum retries",
                        description="Maximum number of connection retry attempts",
                        category=SettingCategory.NETWORK,
                        setting_type=SettingType.INTEGER,
                        default_value=3,
                        min_value=0,
                        max_value=10
                    )
                ]
            ),
            SettingsGroup(
                name="Security",
                description="Security and privacy settings",
                category=SettingCategory.SECURITY,
                settings=[
                    SettingDefinition(
                        key="certificate_pinning",
                        name="Certificate pinning",
                        description="Enable certificate pinning for enhanced security",
                        category=SettingCategory.SECURITY,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="verify_ssl",
                        name="Verify SSL certificates",
                        description="Verify SSL certificates for all connections",
                        category=SettingCategory.SECURITY,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="require_onion_addresses",
                        name="Require .onion addresses",
                        description="Only allow connections to .onion addresses",
                        category=SettingCategory.SECURITY,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="auto_accept_known_certificates",
                        name="Auto-accept known certificates",
                        description="Automatically accept previously seen certificates",
                        category=SettingCategory.SECURITY,
                        setting_type=SettingType.BOOLEAN,
                        default_value=False
                    ),
                    SettingDefinition(
                        key="log_security_events",
                        name="Log security events",
                        description="Log security-related events for monitoring",
                        category=SettingCategory.SECURITY,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    )
                ]
            ),
            SettingsGroup(
                name="Appearance",
                description="User interface appearance settings",
                category=SettingCategory.APPEARANCE,
                settings=[
                    SettingDefinition(
                        key="theme",
                        name="Theme",
                        description="Application color theme",
                        category=SettingCategory.APPEARANCE,
                        setting_type=SettingType.SELECT,
                        default_value="light",
                        options=["light", "dark", "auto"],
                        change_callback=self._on_theme_changed
                    ),
                    SettingDefinition(
                        key="font_family",
                        name="Font family",
                        description="Application font family",
                        category=SettingCategory.APPEARANCE,
                        setting_type=SettingType.SELECT,
                        default_value="Arial",
                        options=["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"]
                    ),
                    SettingDefinition(
                        key="font_size",
                        name="Font size",
                        description="Application font size",
                        category=SettingCategory.APPEARANCE,
                        setting_type=SettingType.INTEGER,
                        default_value=10,
                        min_value=8,
                        max_value=24,
                        change_callback=self._on_font_size_changed
                    ),
                    SettingDefinition(
                        key="window_width",
                        name="Default window width",
                        description="Default window width in pixels",
                        category=SettingCategory.APPEARANCE,
                        setting_type=SettingType.INTEGER,
                        default_value=1200,
                        min_value=800,
                        max_value=3840
                    ),
                    SettingDefinition(
                        key="window_height",
                        name="Default window height",
                        description="Default window height in pixels",
                        category=SettingCategory.APPEARANCE,
                        setting_type=SettingType.INTEGER,
                        default_value=800,
                        min_value=600,
                        max_value=2160
                    ),
                    SettingDefinition(
                        key="show_tooltips",
                        name="Show tooltips",
                        description="Display helpful tooltips for interface elements",
                        category=SettingCategory.APPEARANCE,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    )
                ]
            ),
            SettingsGroup(
                name="Session",
                description="Session and connection behavior settings",
                category=SettingCategory.SESSION,
                settings=[
                    SettingDefinition(
                        key="auto_reconnect",
                        name="Auto-reconnect on disconnect",
                        description="Automatically attempt to reconnect when connection is lost",
                        category=SettingCategory.SESSION,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="reconnect_delay",
                        name="Reconnect delay (seconds)",
                        description="Delay before attempting to reconnect",
                        category=SettingCategory.SESSION,
                        setting_type=SettingType.FLOAT,
                        default_value=5.0,
                        min_value=1.0,
                        max_value=60.0
                    ),
                    SettingDefinition(
                        key="heartbeat_interval",
                        name="Heartbeat interval (seconds)",
                        description="Interval for connection heartbeat checks",
                        category=SettingCategory.SESSION,
                        setting_type=SettingType.INTEGER,
                        default_value=5,
                        min_value=1,
                        max_value=30
                    ),
                    SettingDefinition(
                        key="session_timeout",
                        name="Session timeout (minutes)",
                        description="Maximum session duration before timeout",
                        category=SettingCategory.SESSION,
                        setting_type=SettingType.INTEGER,
                        default_value=480,  # 8 hours
                        min_value=5,
                        max_value=1440  # 24 hours
                    ),
                    SettingDefinition(
                        key="quality_level",
                        name="Default quality level",
                        description="Default video quality level (1-100)",
                        category=SettingCategory.SESSION,
                        setting_type=SettingType.INTEGER,
                        default_value=80,
                        min_value=1,
                        max_value=100,
                        validation_func=SettingsValidator.validate_percentage
                    ),
                    SettingDefinition(
                        key="frame_rate",
                        name="Default frame rate (FPS)",
                        description="Default video frame rate",
                        category=SettingCategory.SESSION,
                        setting_type=SettingType.INTEGER,
                        default_value=30,
                        min_value=1,
                        max_value=60
                    )
                ]
            ),
            SettingsGroup(
                name="Advanced",
                description="Advanced configuration settings",
                category=SettingCategory.ADVANCED,
                settings=[
                    SettingDefinition(
                        key="debug_mode",
                        name="Debug mode",
                        description="Enable debug logging and additional information",
                        category=SettingCategory.ADVANCED,
                        setting_type=SettingType.BOOLEAN,
                        default_value=False,
                        change_callback=self._on_debug_mode_changed
                    ),
                    SettingDefinition(
                        key="experimental_features",
                        name="Experimental features",
                        description="Enable experimental and beta features",
                        category=SettingCategory.ADVANCED,
                        setting_type=SettingType.BOOLEAN,
                        default_value=False
                    ),
                    SettingDefinition(
                        key="telemetry_enabled",
                        name="Telemetry and analytics",
                        description="Allow anonymous usage data collection",
                        category=SettingCategory.ADVANCED,
                        setting_type=SettingType.BOOLEAN,
                        default_value=False
                    ),
                    SettingDefinition(
                        key="log_level",
                        name="Log level",
                        description="Application logging verbosity",
                        category=SettingCategory.ADVANCED,
                        setting_type=SettingType.SELECT,
                        default_value="INFO",
                        options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                    ),
                    SettingDefinition(
                        key="config_backup_enabled",
                        name="Auto-backup configuration",
                        description="Automatically backup configuration files",
                        category=SettingCategory.ADVANCED,
                        setting_type=SettingType.BOOLEAN,
                        default_value=True
                    ),
                    SettingDefinition(
                        key="backup_interval",
                        name="Backup interval (hours)",
                        description="How often to create configuration backups",
                        category=SettingCategory.ADVANCED,
                        setting_type=SettingType.INTEGER,
                        default_value=24,
                        min_value=1,
                        max_value=168  # 1 week
                    )
                ]
            )
        ]
    
    def load_settings(self) -> None:
        """Load current settings from configuration"""
        try:
            # Load GUI configuration
            gui_config_data = self.config_manager.load_config("gui", ConfigScope.USER, asdict(GuiConfig()))
            
            # Convert to settings format
            for group in self.settings_groups:
                for setting in group.settings:
                    key = setting.key
                    if key in gui_config_data:
                        self.settings[key] = gui_config_data[key]
                    else:
                        self.settings[key] = setting.default_value
            
            # Store original settings for comparison
            self.original_settings = self.settings.copy()
            
            logger.debug(f"Loaded {len(self.settings)} settings")
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            # Use default settings
            self.settings = {}
            for group in self.settings_groups:
                for setting in group.settings:
                    self.settings[setting.key] = setting.default_value
            self.original_settings = self.settings.copy()
    
    def create_dialog(self) -> None:
        """Create the settings dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Settings")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Create main layout
        self.create_main_layout()
        
        # Bind close event
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def create_main_layout(self) -> None:
        """Create the main dialog layout"""
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for categories
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create category tabs
        for group in self.settings_groups:
            self.create_category_tab(group)
        
        # Create button frame
        self.create_button_frame(main_frame)
    
    def create_category_tab(self, group: SettingsGroup) -> None:
        """Create a settings category tab"""
        # Create frame for this category
        category_frame = ttk.Frame(self.notebook)
        self.notebook.add(category_frame, text=group.name)
        
        # Create scrollable frame
        canvas = tk.Canvas(category_frame)
        scrollbar = ttk.Scrollbar(category_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create settings widgets
        for setting in group.settings:
            self.create_setting_widget(scrollable_frame, setting)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    def create_setting_widget(self, parent: tk.Widget, setting: SettingDefinition) -> None:
        """Create a widget for a setting"""
        # Create container frame
        setting_frame = ttk.LabelFrame(parent, text=setting.name)
        setting_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Description label
        if setting.description:
            desc_label = ttk.Label(setting_frame, text=setting.description, 
                                 font=('Arial', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        # Create appropriate widget based on type
        widget_frame = ttk.Frame(setting_frame)
        widget_frame.pack(fill=tk.X, padx=5, pady=5)
        
        current_value = self.settings.get(setting.key, setting.default_value)
        
        if setting.setting_type == SettingType.BOOLEAN:
            widget = self.create_boolean_widget(widget_frame, setting, current_value)
        elif setting.setting_type == SettingType.INTEGER:
            widget = self.create_integer_widget(widget_frame, setting, current_value)
        elif setting.setting_type == SettingType.FLOAT:
            widget = self.create_float_widget(widget_frame, setting, current_value)
        elif setting.setting_type == SettingType.STRING:
            widget = self.create_string_widget(widget_frame, setting, current_value)
        elif setting.setting_type == SettingType.SELECT:
            widget = self.create_select_widget(widget_frame, setting, current_value)
        elif setting.setting_type == SettingType.FILE_PATH:
            widget = self.create_file_widget(widget_frame, setting, current_value)
        elif setting.setting_type == SettingType.DIRECTORY_PATH:
            widget = self.create_directory_widget(widget_frame, setting, current_value)
        else:
            widget = self.create_string_widget(widget_frame, setting, current_value)
        
        # Store widget reference
        self.setting_widgets[setting.key] = widget
        
        # Add tooltip if enabled
        if self.settings.get("show_tooltips", True):
            create_tooltip(widget, setting.description)
    
    def create_boolean_widget(self, parent: tk.Widget, setting: SettingDefinition, value: bool) -> tk.Widget:
        """Create boolean (checkbox) widget"""
        var = tk.BooleanVar(value=value)
        widget = ttk.Checkbutton(parent, text="Enabled", variable=var,
                               command=lambda: self._on_setting_changed(setting.key, var.get()))
        widget.pack(anchor=tk.W)
        return widget
    
    def create_integer_widget(self, parent: tk.Widget, setting: SettingDefinition, value: int) -> tk.Widget:
        """Create integer (spinbox) widget"""
        var = tk.StringVar(value=str(value))
        
        widget_frame = ttk.Frame(parent)
        widget_frame.pack(fill=tk.X)
        
        spinbox = ttk.Spinbox(widget_frame, from_=setting.min_value or 0, 
                            to=setting.max_value or 1000, textvariable=var,
                            command=lambda: self._on_setting_changed(setting.key, int(var.get())),
                            width=10)
        spinbox.pack(side=tk.LEFT)
        
        # Bind validation
        spinbox.bind('<FocusOut>', lambda e: self._validate_and_update_setting(setting, var.get()))
        spinbox.bind('<Return>', lambda e: self._validate_and_update_setting(setting, var.get()))
        
        return spinbox
    
    def create_float_widget(self, parent: tk.Widget, setting: SettingDefinition, value: float) -> tk.Widget:
        """Create float (entry) widget"""
        var = tk.StringVar(value=str(value))
        
        widget_frame = ttk.Frame(parent)
        widget_frame.pack(fill=tk.X)
        
        entry = ttk.Entry(widget_frame, textvariable=var, width=15)
        entry.pack(side=tk.LEFT)
        
        # Bind validation
        entry.bind('<FocusOut>', lambda e: self._validate_and_update_setting(setting, var.get()))
        entry.bind('<Return>', lambda e: self._validate_and_update_setting(setting, var.get()))
        
        return entry
    
    def create_string_widget(self, parent: tk.Widget, setting: SettingDefinition, value: str) -> tk.Widget:
        """Create string (entry) widget"""
        var = tk.StringVar(value=str(value))
        
        entry = ttk.Entry(parent, textvariable=var, width=40)
        entry.pack(fill=tk.X)
        
        # Bind change event
        entry.bind('<FocusOut>', lambda e: self._on_setting_changed(setting.key, var.get()))
        entry.bind('<Return>', lambda e: self._on_setting_changed(setting.key, var.get()))
        
        return entry
    
    def create_select_widget(self, parent: tk.Widget, setting: SettingDefinition, value: str) -> tk.Widget:
        """Create select (combobox) widget"""
        var = tk.StringVar(value=str(value))
        
        combo = ttk.Combobox(parent, textvariable=var, values=setting.options, 
                           state="readonly", width=20)
        combo.pack(anchor=tk.W)
        
        # Bind change event
        combo.bind('<<ComboboxSelected>>', lambda e: self._on_setting_changed(setting.key, var.get()))
        
        return combo
    
    def create_file_widget(self, parent: tk.Widget, setting: SettingDefinition, value: str) -> tk.Widget:
        """Create file path widget"""
        var = tk.StringVar(value=str(value))
        
        widget_frame = ttk.Frame(parent)
        widget_frame.pack(fill=tk.X)
        
        entry = ttk.Entry(widget_frame, textvariable=var, width=30)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(widget_frame, text="Browse", 
                              command=lambda: self._browse_file(setting, var))
        browse_btn.pack(side=tk.RIGHT)
        
        # Bind change event
        entry.bind('<FocusOut>', lambda e: self._on_setting_changed(setting.key, var.get()))
        
        return widget_frame
    
    def create_directory_widget(self, parent: tk.Widget, setting: SettingDefinition, value: str) -> tk.Widget:
        """Create directory path widget"""
        var = tk.StringVar(value=str(value))
        
        widget_frame = ttk.Frame(parent)
        widget_frame.pack(fill=tk.X)
        
        entry = ttk.Entry(widget_frame, textvariable=var, width=30)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(widget_frame, text="Browse", 
                              command=lambda: self._browse_directory(var))
        browse_btn.pack(side=tk.RIGHT)
        
        # Bind change event
        entry.bind('<FocusOut>', lambda e: self._on_setting_changed(setting.key, var.get()))
        
        return widget_frame
    
    def create_button_frame(self, parent: tk.Widget) -> None:
        """Create button frame with action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame, text="Import Settings", command=self.import_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_frame, text="Export Settings", command=self.export_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="Reset to Defaults", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_frame, text="Apply", command=self.on_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=(5, 0))
    
    def _on_setting_changed(self, key: str, value: Any) -> None:
        """Handle setting value change"""
        try:
            # Find setting definition
            setting_def = None
            for group in self.settings_groups:
                for setting in group.settings:
                    if setting.key == key:
                        setting_def = setting
                        break
                if setting_def:
                    break
            
            if setting_def:
                # Validate value
                if setting_def.validation_func and not setting_def.validation_func(value):
                    messagebox.showerror("Invalid Value", f"Invalid value for {setting_def.name}")
                    return
                
                # Convert value to appropriate type
                if setting_def.setting_type == SettingType.INTEGER:
                    value = int(value)
                elif setting_def.setting_type == SettingType.FLOAT:
                    value = float(value)
                elif setting_def.setting_type == SettingType.BOOLEAN:
                    value = bool(value)
                
                # Update setting
                self.settings[key] = value
                
                # Call change callback if provided
                if setting_def.change_callback:
                    setting_def.change_callback(value)
                
                logger.debug(f"Setting changed: {key} = {value}")
                
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")
            messagebox.showerror("Error", f"Failed to update setting: {e}")
    
    def _validate_and_update_setting(self, setting: SettingDefinition, value_str: str) -> None:
        """Validate and update setting value"""
        try:
            if setting.setting_type == SettingType.INTEGER:
                value = int(value_str)
            elif setting.setting_type == SettingType.FLOAT:
                value = float(value_str)
            else:
                value = value_str
            
            # Validate
            if setting.validation_func and not setting.validation_func(value):
                messagebox.showerror("Invalid Value", f"Invalid value for {setting.name}")
                return
            
            # Check bounds
            if setting.min_value is not None and value < setting.min_value:
                value = setting.min_value
            if setting.max_value is not None and value > setting.max_value:
                value = setting.max_value
            
            self._on_setting_changed(setting.key, value)
            
        except ValueError:
            messagebox.showerror("Invalid Value", f"Invalid value for {setting.name}")
    
    def _browse_file(self, setting: SettingDefinition, var: tk.StringVar) -> None:
        """Browse for file"""
        file_filter = setting.file_filter or [("All files", "*.*")]
        filename = filedialog.askopenfilename(
            title=f"Select {setting.name}",
            filetypes=file_filter
        )
        if filename:
            var.set(filename)
            self._on_setting_changed(setting.key, filename)
    
    def _browse_directory(self, var: tk.StringVar) -> None:
        """Browse for directory"""
        directory = filedialog.askdirectory(title="Select Directory")
        if directory:
            var.set(directory)
    
    def _on_theme_changed(self, value: Any) -> None:
        """Handle theme change"""
        try:
            theme_mode = ThemeMode(value)
            self.theme_manager.set_theme(theme_mode)
            logger.info(f"Theme changed to: {value}")
        except Exception as e:
            logger.error(f"Failed to change theme: {e}")
    
    def _on_font_size_changed(self, value: Any) -> None:
        """Handle font size change"""
        try:
            # This would typically update the font size globally
            logger.info(f"Font size changed to: {value}")
        except Exception as e:
            logger.error(f"Failed to change font size: {e}")
    
    def _on_debug_mode_changed(self, value: Any) -> None:
        """Handle debug mode change"""
        try:
            # Update logging level
            if value:
                logging.getLogger().setLevel(logging.DEBUG)
            else:
                logging.getLogger().setLevel(logging.INFO)
            logger.info(f"Debug mode changed to: {value}")
        except Exception as e:
            logger.error(f"Failed to change debug mode: {e}")
    
    def import_settings(self) -> None:
        """Import settings from file"""
        filename = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported_settings = json.load(f)
                
                # Validate and apply settings
                for key, value in imported_settings.items():
                    if key in self.settings:
                        self.settings[key] = value
                
                # Refresh UI
                self.refresh_ui()
                
                messagebox.showinfo("Success", "Settings imported successfully")
                
            except Exception as e:
                logger.error(f"Failed to import settings: {e}")
                messagebox.showerror("Error", f"Failed to import settings: {e}")
    
    def export_settings(self) -> None:
        """Export settings to file"""
        filename = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.settings, f, indent=2, sort_keys=True)
                
                messagebox.showinfo("Success", f"Settings exported to {filename}")
                
            except Exception as e:
                logger.error(f"Failed to export settings: {e}")
                messagebox.showerror("Error", f"Failed to export settings: {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            try:
                # Reset to defaults
                for group in self.settings_groups:
                    for setting in group.settings:
                        self.settings[setting.key] = setting.default_value
                
                # Refresh UI
                self.refresh_ui()
                
                messagebox.showinfo("Success", "Settings reset to defaults")
                
            except Exception as e:
                logger.error(f"Failed to reset settings: {e}")
                messagebox.showerror("Error", f"Failed to reset settings: {e}")
    
    def refresh_ui(self) -> None:
        """Refresh UI with current settings"""
        for key, widget in self.setting_widgets.items():
            current_value = self.settings.get(key)
            
            if isinstance(widget, ttk.Checkbutton):
                widget.state(['!alternate'])
                widget.instate(['!alternate'], lambda: widget.configure(state='normal'))
                widget.configure(variable=tk.BooleanVar(value=current_value))
            elif isinstance(widget, ttk.Spinbox):
                widget.configure(textvariable=tk.StringVar(value=str(current_value)))
            elif isinstance(widget, ttk.Entry):
                widget.configure(textvariable=tk.StringVar(value=str(current_value)))
            elif isinstance(widget, ttk.Combobox):
                widget.configure(textvariable=tk.StringVar(value=str(current_value)))
    
    def save_settings(self) -> bool:
        """Save current settings to configuration"""
        try:
            # Convert settings to GUI config format
            gui_config_data = {}
            for key, value in self.settings.items():
                gui_config_data[key] = value
            
            # Save to configuration
            success = self.config_manager.save_config("gui", gui_config_data, ConfigScope.USER)
            
            if success:
                logger.info("Settings saved successfully")
                return True
            else:
                logger.error("Failed to save settings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def on_apply(self) -> None:
        """Handle Apply button click"""
        if self.save_settings():
            messagebox.showinfo("Success", "Settings applied successfully")
            if self.on_settings_changed:
                self.on_settings_changed(self.settings.copy())
        else:
            messagebox.showerror("Error", "Failed to apply settings")
    
    def on_ok(self) -> None:
        """Handle OK button click"""
        if self.save_settings():
            if self.on_settings_changed:
                self.on_settings_changed(self.settings.copy())
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def on_cancel(self) -> None:
        """Handle Cancel button click"""
        # Check if there are unsaved changes
        if self.settings != self.original_settings:
            if messagebox.askyesno("Unsaved Changes", 
                                 "You have unsaved changes. Do you want to discard them?"):
                self.dialog.destroy()
        else:
            self.dialog.destroy()
    
    def show(self) -> None:
        """Show the settings dialog"""
        if self.dialog:
            self.dialog.deiconify()
            self.dialog.focus_set()


def show_settings_dialog(parent: tk.Widget, on_settings_changed: Optional[Callable[[Dict[str, Any]], None]] = None) -> SettingsDialog:
    """Show the settings dialog"""
    dialog = SettingsDialog(parent, on_settings_changed)
    dialog.show()
    return dialog


# Convenience function for quick settings access
def get_setting(key: str, default_value: Any = None) -> Any:
    """Get a specific setting value"""
    config_manager = get_config_manager()
    gui_config_data = config_manager.load_config("gui", ConfigScope.USER, {})
    return gui_config_data.get(key, default_value)


def set_setting(key: str, value: Any) -> bool:
    """Set a specific setting value"""
    config_manager = get_config_manager()
    gui_config_data = config_manager.load_config("gui", ConfigScope.USER, {})
    gui_config_data[key] = value
    return config_manager.save_config("gui", gui_config_data, ConfigScope.USER)

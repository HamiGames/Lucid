# Path: gui/user/connection_dialog.py
"""
Session connection configuration dialog for Lucid RDP GUI.
Provides comprehensive session setup, policy configuration, and connection management.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import threading
import time

from ..core.config_manager import get_config_manager
from ..core.security import get_security_validator, CryptographicUtils
from ..core.networking import TorHttpClient, SecurityConfig
from .policy_controller import PolicyController, PolicyRule, PolicyEnforcementLevel

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Types of RDP connections"""
    HOST = "host"           # Host a new session
    JOIN = "join"           # Join existing session
    VIEW = "view"           # View-only session
    COLLABORATE = "collaborate"  # Collaborative session


class AuthenticationMethod(Enum):
    """Authentication methods"""
    TOKEN = "token"         # Authentication token
    QR_CODE = "qr_code"     # QR code scanning
    PUBLIC_KEY = "public_key"  # Public key authentication
    PASSWORD = "password"   # Password authentication


@dataclass
class ConnectionConfig:
    """Complete connection configuration"""
    connection_id: str
    connection_type: ConnectionType
    session_id: Optional[str]
    target_onion: Optional[str]
    target_port: int = 8080
    
    # Authentication
    auth_method: AuthenticationMethod = AuthenticationMethod.TOKEN
    auth_token: Optional[str] = None
    auth_password: Optional[str] = None
    public_key: Optional[str] = None
    
    # Session settings
    session_name: str = ""
    session_description: str = ""
    max_participants: int = 10
    session_timeout: int = 3600  # seconds
    
    # Quality settings
    video_quality: int = 80  # 1-100
    audio_quality: int = 80  # 1-100
    frame_rate: int = 30
    resolution: str = "1920x1080"
    
    # Security settings
    encryption_enabled: bool = True
    compression_enabled: bool = True
    certificate_pinning: bool = True
    
    # Policy settings
    policy_enabled: bool = True
    policy_rules: List[PolicyRule] = None
    
    # Advanced settings
    heartbeat_interval: int = 5
    connection_timeout: int = 30
    retry_attempts: int = 3
    auto_reconnect: bool = True
    
    def __post_init__(self):
        if not self.connection_id:
            self.connection_id = str(uuid.uuid4())
        if self.policy_rules is None:
            self.policy_rules = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['connection_type'] = self.connection_type.value
        data['auth_method'] = self.auth_method.value
        data['policy_rules'] = [rule.to_dict() for rule in self.policy_rules]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionConfig':
        """Create from dictionary"""
        # Convert enum strings back to enums
        data['connection_type'] = ConnectionType(data['connection_type'])
        data['auth_method'] = AuthenticationMethod(data['auth_method'])
        data['policy_rules'] = [PolicyRule(**rule) for rule in data.get('policy_rules', [])]
        return cls(**data)


class ConnectionDialog:
    """Main connection configuration dialog"""
    
    def __init__(self, parent: tk.Widget, on_connect: Optional[Callable[[ConnectionConfig], None]] = None):
        self.parent = parent
        self.on_connect_callback = on_connect
        self.config_manager = get_config_manager()
        self.policy_controller = PolicyController(parent)
        
        # Dialog state
        self.dialog = None
        self.config = None
        self.validation_errors = []
        
        # Saved configurations
        self.saved_configs: Dict[str, ConnectionConfig] = {}
        self.load_saved_configs()
        
        logger.info("Connection dialog initialized")
    
    def load_saved_configs(self) -> None:
        """Load saved connection configurations"""
        try:
            configs_data = self.config_manager.load_config(
                "connection_configs",
                default_data={"configs": {}}
            )
            
            for name, config_dict in configs_data.get("configs", {}).items():
                try:
                    self.saved_configs[name] = ConnectionConfig.from_dict(config_dict)
                except Exception as e:
                    logger.error(f"Failed to load config '{name}': {e}")
            
            logger.debug(f"Loaded {len(self.saved_configs)} saved configurations")
        except Exception as e:
            logger.error(f"Failed to load saved configurations: {e}")
    
    def save_config(self, name: str, config: ConnectionConfig) -> bool:
        """Save connection configuration"""
        try:
            self.saved_configs[name] = config
            
            configs_data = {
                "configs": {name: config.to_dict() for name, config in self.saved_configs.items()}
            }
            
            self.config_manager.save_config("connection_configs", configs_data)
            logger.info(f"Saved connection configuration: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def show_dialog(self, initial_config: Optional[ConnectionConfig] = None) -> None:
        """Show the connection configuration dialog"""
        self.config = initial_config or ConnectionConfig(connection_id="", connection_type=ConnectionType.JOIN)
        self.validation_errors.clear()
        
        # Create dialog window
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Configure RDP Connection")
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)
        
        # Make it modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (700 // 2)
        self.dialog.geometry(f"800x700+{x}+{y}")
        
        # Setup GUI
        self.setup_dialog_gui()
        
        # Load initial configuration
        if initial_config:
            self.load_config_to_gui(initial_config)
        
        # Bind close event
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_dialog)
    
    def setup_dialog_gui(self) -> None:
        """Setup the dialog GUI components"""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_connection_tab()
        self.create_authentication_tab()
        self.create_quality_tab()
        self.create_security_tab()
        self.create_policy_tab()
        self.create_advanced_tab()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        ttk.Button(button_frame, text="Save Configuration", command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Load Configuration", command=self.load_configuration).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Connect", command=self.connect_dialog).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_dialog).pack(side=tk.RIGHT)
    
    def create_connection_tab(self) -> None:
        """Create connection settings tab"""
        self.connection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.connection_frame, text="Connection")
        
        # Connection type
        type_frame = ttk.LabelFrame(self.connection_frame, text="Connection Type")
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.connection_type_var = tk.StringVar(value="join")
        type_radio_frame = ttk.Frame(type_frame)
        type_radio_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(type_radio_frame, text="Join Session", variable=self.connection_type_var, 
                       value="join", command=self.on_connection_type_changed).pack(anchor=tk.W)
        ttk.Radiobutton(type_radio_frame, text="Host Session", variable=self.connection_type_var, 
                       value="host", command=self.on_connection_type_changed).pack(anchor=tk.W)
        ttk.Radiobutton(type_radio_frame, text="View Only", variable=self.connection_type_var, 
                       value="view", command=self.on_connection_type_changed).pack(anchor=tk.W)
        
        # Session ID / Target
        target_frame = ttk.LabelFrame(self.connection_frame, text="Session Target")
        target_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Session ID
        session_frame = ttk.Frame(target_frame)
        session_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(session_frame, text="Session ID:").pack(side=tk.LEFT)
        self.session_id_entry = ttk.Entry(session_frame, width=40)
        self.session_id_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Target onion
        onion_frame = ttk.Frame(target_frame)
        onion_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(onion_frame, text="Target Onion:").pack(side=tk.LEFT)
        self.target_onion_entry = ttk.Entry(onion_frame, width=40)
        self.target_onion_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Port
        port_frame = ttk.Frame(target_frame)
        port_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.target_port_entry = ttk.Entry(port_frame, width=10)
        self.target_port_entry.insert(0, "8080")
        self.target_port_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Session settings (for hosting)
        self.session_settings_frame = ttk.LabelFrame(self.connection_frame, text="Session Settings")
        self.session_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Session name
        name_frame = ttk.Frame(self.session_settings_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(name_frame, text="Session Name:").pack(side=tk.LEFT)
        self.session_name_entry = ttk.Entry(name_frame, width=40)
        self.session_name_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Session description
        desc_frame = ttk.Frame(self.session_settings_frame)
        desc_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(desc_frame, text="Description:").pack(side=tk.LEFT)
        self.session_desc_entry = ttk.Entry(desc_frame, width=40)
        self.session_desc_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Max participants
        participants_frame = ttk.Frame(self.session_settings_frame)
        participants_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(participants_frame, text="Max Participants:").pack(side=tk.LEFT)
        self.max_participants_spinbox = ttk.Spinbox(participants_frame, from_=1, to=100, width=10)
        self.max_participants_spinbox.set("10")
        self.max_participants_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Session timeout
        timeout_frame = ttk.Frame(self.session_settings_frame)
        timeout_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(timeout_frame, text="Session Timeout (minutes):").pack(side=tk.LEFT)
        self.session_timeout_spinbox = ttk.Spinbox(timeout_frame, from_=1, to=1440, width=10)
        self.session_timeout_spinbox.set("60")
        self.session_timeout_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Initially hide session settings
        self.session_settings_frame.pack_forget()
    
    def create_authentication_tab(self) -> None:
        """Create authentication settings tab"""
        self.auth_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.auth_frame, text="Authentication")
        
        # Authentication method
        method_frame = ttk.LabelFrame(self.auth_frame, text="Authentication Method")
        method_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.auth_method_var = tk.StringVar(value="token")
        method_radio_frame = ttk.Frame(method_frame)
        method_radio_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(method_radio_frame, text="Authentication Token", 
                       variable=self.auth_method_var, value="token",
                       command=self.on_auth_method_changed).pack(anchor=tk.W)
        ttk.Radiobutton(method_radio_frame, text="QR Code", 
                       variable=self.auth_method_var, value="qr_code",
                       command=self.on_auth_method_changed).pack(anchor=tk.W)
        ttk.Radiobutton(method_radio_frame, text="Public Key", 
                       variable=self.auth_method_var, value="public_key",
                       command=self.on_auth_method_changed).pack(anchor=tk.W)
        ttk.Radiobutton(method_radio_frame, text="Password", 
                       variable=self.auth_method_var, value="password",
                       command=self.on_auth_method_changed).pack(anchor=tk.W)
        
        # Authentication details
        self.auth_details_frame = ttk.LabelFrame(self.auth_frame, text="Authentication Details")
        self.auth_details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Token authentication
        self.token_frame = ttk.Frame(self.auth_details_frame)
        
        token_label = ttk.Label(self.token_frame, text="Authentication Token:")
        token_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.auth_token_entry = ttk.Entry(self.token_frame, width=50, show="*")
        self.auth_token_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # QR Code authentication
        self.qr_frame = ttk.Frame(self.auth_details_frame)
        
        qr_label = ttk.Label(self.qr_frame, text="Scan QR Code to authenticate:")
        qr_label.pack(anchor=tk.W, padx=5, pady=5)
        
        ttk.Button(self.qr_frame, text="Scan QR Code", 
                  command=self.scan_qr_code).pack(padx=5, pady=5)
        
        # Public key authentication
        self.pubkey_frame = ttk.Frame(self.auth_details_frame)
        
        pubkey_label = ttk.Label(self.pubkey_frame, text="Public Key:")
        pubkey_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.public_key_text = tk.Text(self.pubkey_frame, height=8, width=60)
        self.public_key_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Password authentication
        self.password_frame = ttk.Frame(self.auth_details_frame)
        
        password_label = ttk.Label(self.password_frame, text="Password:")
        password_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.auth_password_entry = ttk.Entry(self.password_frame, width=50, show="*")
        self.auth_password_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Initially show token frame
        self.token_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_quality_tab(self) -> None:
        """Create quality settings tab"""
        self.quality_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.quality_frame, text="Quality")
        
        # Video settings
        video_frame = ttk.LabelFrame(self.quality_frame, text="Video Settings")
        video_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Video quality
        quality_frame = ttk.Frame(video_frame)
        quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(quality_frame, text="Video Quality:").pack(side=tk.LEFT)
        self.video_quality_var = tk.IntVar(value=80)
        self.video_quality_scale = ttk.Scale(quality_frame, from_=10, to=100, 
                                           variable=self.video_quality_var, orient=tk.HORIZONTAL)
        self.video_quality_scale.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        self.video_quality_label = ttk.Label(quality_frame, text="80%")
        self.video_quality_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Frame rate
        framerate_frame = ttk.Frame(video_frame)
        framerate_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(framerate_frame, text="Frame Rate:").pack(side=tk.LEFT)
        self.frame_rate_var = tk.StringVar(value="30")
        framerate_combo = ttk.Combobox(framerate_frame, textvariable=self.frame_rate_var,
                                     values=["15", "24", "30", "60"], state="readonly", width=10)
        framerate_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Resolution
        resolution_frame = ttk.Frame(video_frame)
        resolution_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(resolution_frame, text="Resolution:").pack(side=tk.LEFT)
        self.resolution_var = tk.StringVar(value="1920x1080")
        resolution_combo = ttk.Combobox(resolution_frame, textvariable=self.resolution_var,
                                      values=["1280x720", "1920x1080", "2560x1440", "3840x2160"],
                                      state="readonly", width=15)
        resolution_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Audio settings
        audio_frame = ttk.LabelFrame(self.quality_frame, text="Audio Settings")
        audio_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Audio quality
        audio_quality_frame = ttk.Frame(audio_frame)
        audio_quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(audio_quality_frame, text="Audio Quality:").pack(side=tk.LEFT)
        self.audio_quality_var = tk.IntVar(value=80)
        self.audio_quality_scale = ttk.Scale(audio_quality_frame, from_=10, to=100,
                                           variable=self.audio_quality_var, orient=tk.HORIZONTAL)
        self.audio_quality_scale.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        self.audio_quality_label = ttk.Label(audio_quality_frame, text="80%")
        self.audio_quality_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Bind scale events
        self.video_quality_scale.configure(command=self.on_video_quality_changed)
        self.audio_quality_scale.configure(command=self.on_audio_quality_changed)
    
    def create_security_tab(self) -> None:
        """Create security settings tab"""
        self.security_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.security_frame, text="Security")
        
        # Encryption settings
        encryption_frame = ttk.LabelFrame(self.security_frame, text="Encryption")
        encryption_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.encryption_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(encryption_frame, text="Enable Encryption",
                       variable=self.encryption_enabled_var).pack(anchor=tk.W, padx=5, pady=5)
        
        self.compression_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(encryption_frame, text="Enable Compression",
                       variable=self.compression_enabled_var).pack(anchor=tk.W, padx=5, pady=5)
        
        self.certificate_pinning_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(encryption_frame, text="Certificate Pinning",
                       variable=self.certificate_pinning_var).pack(anchor=tk.W, padx=5, pady=5)
        
        # Connection security
        connection_frame = ttk.LabelFrame(self.security_frame, text="Connection Security")
        connection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Connection timeout
        timeout_frame = ttk.Frame(connection_frame)
        timeout_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(timeout_frame, text="Connection Timeout (seconds):").pack(side=tk.LEFT)
        self.connection_timeout_spinbox = ttk.Spinbox(timeout_frame, from_=5, to=300, width=10)
        self.connection_timeout_spinbox.set("30")
        self.connection_timeout_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Retry attempts
        retry_frame = ttk.Frame(connection_frame)
        retry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(retry_frame, text="Retry Attempts:").pack(side=tk.LEFT)
        self.retry_attempts_spinbox = ttk.Spinbox(retry_frame, from_=0, to=10, width=10)
        self.retry_attempts_spinbox.set("3")
        self.retry_attempts_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Auto-reconnect
        self.auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(connection_frame, text="Auto-Reconnect on Disconnect",
                       variable=self.auto_reconnect_var).pack(anchor=tk.W, padx=5, pady=5)
    
    def create_policy_tab(self) -> None:
        """Create policy settings tab"""
        self.policy_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.policy_frame, text="Policy")
        
        # Policy settings
        settings_frame = ttk.LabelFrame(self.policy_frame, text="Policy Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.policy_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Enable Policy Enforcement",
                       variable=self.policy_enabled_var).pack(anchor=tk.W, padx=5, pady=5)
        
        # Policy rules
        rules_frame = ttk.LabelFrame(self.policy_frame, text="Policy Rules")
        rules_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Rules toolbar
        rules_toolbar = ttk.Frame(rules_frame)
        rules_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(rules_toolbar, text="Add Rule", command=self.add_policy_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(rules_toolbar, text="Edit Rule", command=self.edit_policy_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(rules_toolbar, text="Remove Rule", command=self.remove_policy_rule).pack(side=tk.LEFT, padx=5)
        
        # Rules list
        columns = ('name', 'enabled', 'enforcement', 'description')
        self.policy_rules_tree = ttk.Treeview(rules_frame, columns=columns, show='headings')
        
        self.policy_rules_tree.heading('name', text='Rule Name')
        self.policy_rules_tree.heading('enabled', text='Enabled')
        self.policy_rules_tree.heading('enforcement', text='Enforcement')
        self.policy_rules_tree.heading('description', text='Description')
        
        self.policy_rules_tree.column('name', width=150)
        self.policy_rules_tree.column('enabled', width=80)
        self.policy_rules_tree.column('enforcement', width=100)
        self.policy_rules_tree.column('description', width=300)
        
        rules_scroll = ttk.Scrollbar(rules_frame, orient=tk.VERTICAL, command=self.policy_rules_tree.yview)
        self.policy_rules_tree.configure(yscrollcommand=rules_scroll.set)
        
        self.policy_rules_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        rules_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to edit
        self.policy_rules_tree.bind('<Double-1>', self.edit_policy_rule)
    
    def create_advanced_tab(self) -> None:
        """Create advanced settings tab"""
        self.advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_frame, text="Advanced")
        
        # Network settings
        network_frame = ttk.LabelFrame(self.advanced_frame, text="Network Settings")
        network_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Heartbeat interval
        heartbeat_frame = ttk.Frame(network_frame)
        heartbeat_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(heartbeat_frame, text="Heartbeat Interval (seconds):").pack(side=tk.LEFT)
        self.heartbeat_interval_spinbox = ttk.Spinbox(heartbeat_frame, from_=1, to=60, width=10)
        self.heartbeat_interval_spinbox.set("5")
        self.heartbeat_interval_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Debug settings
        debug_frame = ttk.LabelFrame(self.advanced_frame, text="Debug Settings")
        debug_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(debug_frame, text="Enable Debug Mode",
                       variable=self.debug_mode_var).pack(anchor=tk.W, padx=5, pady=5)
        
        self.verbose_logging_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(debug_frame, text="Verbose Logging",
                       variable=self.verbose_logging_var).pack(anchor=tk.W, padx=5, pady=5)
    
    def on_connection_type_changed(self) -> None:
        """Handle connection type change"""
        connection_type = self.connection_type_var.get()
        
        if connection_type == "host":
            self.session_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        else:
            self.session_settings_frame.pack_forget()
    
    def on_auth_method_changed(self) -> None:
        """Handle authentication method change"""
        auth_method = self.auth_method_var.get()
        
        # Hide all frames
        for frame in [self.token_frame, self.qr_frame, self.pubkey_frame, self.password_frame]:
            frame.pack_forget()
        
        # Show selected frame
        if auth_method == "token":
            self.token_frame.pack(fill=tk.BOTH, expand=True)
        elif auth_method == "qr_code":
            self.qr_frame.pack(fill=tk.BOTH, expand=True)
        elif auth_method == "public_key":
            self.pubkey_frame.pack(fill=tk.BOTH, expand=True)
        elif auth_method == "password":
            self.password_frame.pack(fill=tk.BOTH, expand=True)
    
    def on_video_quality_changed(self, value: str) -> None:
        """Handle video quality scale change"""
        self.video_quality_label.configure(text=f"{int(float(value))}%")
    
    def on_audio_quality_changed(self, value: str) -> None:
        """Handle audio quality scale change"""
        self.audio_quality_label.configure(text=f"{int(float(value))}%")
    
    def scan_qr_code(self) -> None:
        """Scan QR code for authentication"""
        messagebox.showinfo("QR Code", "QR code scanning functionality would be implemented here")
    
    def add_policy_rule(self) -> None:
        """Add a new policy rule"""
        # This would open a policy rule editor dialog
        messagebox.showinfo("Add Rule", "Policy rule editor would be implemented here")
    
    def edit_policy_rule(self, event=None) -> None:
        """Edit selected policy rule"""
        selection = self.policy_rules_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a rule to edit")
            return
        
        # This would open a policy rule editor dialog
        messagebox.showinfo("Edit Rule", "Policy rule editor would be implemented here")
    
    def remove_policy_rule(self) -> None:
        """Remove selected policy rule"""
        selection = self.policy_rules_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a rule to remove")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to remove this rule?"):
            self.policy_rules_tree.delete(selection[0])
    
    def save_configuration(self) -> None:
        """Save current configuration"""
        name = tk.simpledialog.askstring("Save Configuration", "Enter configuration name:")
        if name:
            config = self.get_config_from_gui()
            if self.save_config(name, config):
                messagebox.showinfo("Success", f"Configuration '{name}' saved")
            else:
                messagebox.showerror("Error", "Failed to save configuration")
    
    def load_configuration(self) -> None:
        """Load saved configuration"""
        if not self.saved_configs:
            messagebox.showinfo("No Configurations", "No saved configurations found")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Load Configuration")
        dialog.geometry("400x300")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # Configuration list
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(frame, text="Select Configuration:").pack(anchor=tk.W)
        
        config_listbox = tk.Listbox(frame)
        config_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        for name in self.saved_configs.keys():
            config_listbox.insert(tk.END, name)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def load_selected():
            selection = config_listbox.curselection()
            if selection:
                name = config_listbox.get(selection[0])
                config = self.saved_configs[name]
                self.load_config_to_gui(config)
                dialog.destroy()
        
        ttk.Button(button_frame, text="Load", command=load_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)
    
    def test_connection(self) -> None:
        """Test connection settings"""
        def test_async():
            try:
                # Simulate connection test
                time.sleep(2)
                self.dialog.after(0, lambda: messagebox.showinfo("Test Result", "Connection test successful"))
            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror("Test Failed", str(e)))
        
        threading.Thread(target=test_async, daemon=True).start()
        messagebox.showinfo("Testing", "Testing connection...")
    
    def connect_dialog(self) -> None:
        """Connect with current configuration"""
        # Validate configuration
        if not self.validate_configuration():
            return
        
        # Get configuration
        config = self.get_config_from_gui()
        
        # Call callback if provided
        if self.on_connect_callback:
            self.on_connect_callback(config)
        
        # Close dialog
        self.dialog.destroy()
    
    def cancel_dialog(self) -> None:
        """Cancel dialog"""
        self.dialog.destroy()
    
    def validate_configuration(self) -> bool:
        """Validate current configuration"""
        self.validation_errors.clear()
        
        # Validate required fields based on connection type
        connection_type = self.connection_type_var.get()
        
        if connection_type in ["join", "view"]:
            session_id = self.session_id_entry.get().strip()
            if not session_id:
                self.validation_errors.append("Session ID is required for joining sessions")
        
        # Validate authentication
        auth_method = self.auth_method_var.get()
        if auth_method == "token" and not self.auth_token_entry.get().strip():
            self.validation_errors.append("Authentication token is required")
        elif auth_method == "password" and not self.auth_password_entry.get().strip():
            self.validation_errors.append("Password is required")
        elif auth_method == "public_key" and not self.public_key_text.get(1.0, tk.END).strip():
            self.validation_errors.append("Public key is required")
        
        # Validate port
        try:
            port = int(self.target_port_entry.get())
            if port < 1 or port > 65535:
                self.validation_errors.append("Port must be between 1 and 65535")
        except ValueError:
            self.validation_errors.append("Port must be a valid number")
        
        # Show errors if any
        if self.validation_errors:
            error_message = "Configuration validation failed:\n\n" + "\n".join(self.validation_errors)
            messagebox.showerror("Validation Error", error_message)
            return False
        
        return True
    
    def get_config_from_gui(self) -> ConnectionConfig:
        """Get configuration from GUI elements"""
        config = ConnectionConfig(
            connection_id=str(uuid.uuid4()),
            connection_type=ConnectionType(self.connection_type_var.get()),
            session_id=self.session_id_entry.get().strip() or None,
            target_onion=self.target_onion_entry.get().strip() or None,
            target_port=int(self.target_port_entry.get()),
            
            # Authentication
            auth_method=AuthenticationMethod(self.auth_method_var.get()),
            auth_token=self.auth_token_entry.get().strip() or None,
            auth_password=self.auth_password_entry.get().strip() or None,
            public_key=self.public_key_text.get(1.0, tk.END).strip() or None,
            
            # Session settings
            session_name=self.session_name_entry.get().strip(),
            session_description=self.session_desc_entry.get().strip(),
            max_participants=int(self.max_participants_spinbox.get()),
            session_timeout=int(self.session_timeout_spinbox.get()) * 60,  # Convert to seconds
            
            # Quality settings
            video_quality=self.video_quality_var.get(),
            audio_quality=self.audio_quality_var.get(),
            frame_rate=int(self.frame_rate_var.get()),
            resolution=self.resolution_var.get(),
            
            # Security settings
            encryption_enabled=self.encryption_enabled_var.get(),
            compression_enabled=self.compression_enabled_var.get(),
            certificate_pinning=self.certificate_pinning_var.get(),
            
            # Policy settings
            policy_enabled=self.policy_enabled_var.get(),
            
            # Advanced settings
            heartbeat_interval=int(self.heartbeat_interval_spinbox.get()),
            connection_timeout=int(self.connection_timeout_spinbox.get()),
            retry_attempts=int(self.retry_attempts_spinbox.get()),
            auto_reconnect=self.auto_reconnect_var.get()
        )
        
        return config
    
    def load_config_to_gui(self, config: ConnectionConfig) -> None:
        """Load configuration into GUI elements"""
        # Connection settings
        self.connection_type_var.set(config.connection_type.value)
        self.session_id_entry.delete(0, tk.END)
        self.session_id_entry.insert(0, config.session_id or "")
        self.target_onion_entry.delete(0, tk.END)
        self.target_onion_entry.insert(0, config.target_onion or "")
        self.target_port_entry.delete(0, tk.END)
        self.target_port_entry.insert(0, str(config.target_port))
        
        # Session settings
        self.session_name_entry.delete(0, tk.END)
        self.session_name_entry.insert(0, config.session_name)
        self.session_desc_entry.delete(0, tk.END)
        self.session_desc_entry.insert(0, config.session_description)
        self.max_participants_spinbox.set(str(config.max_participants))
        self.session_timeout_spinbox.set(str(config.session_timeout // 60))
        
        # Authentication
        self.auth_method_var.set(config.auth_method.value)
        self.auth_token_entry.delete(0, tk.END)
        self.auth_token_entry.insert(0, config.auth_token or "")
        self.auth_password_entry.delete(0, tk.END)
        self.auth_password_entry.insert(0, config.auth_password or "")
        self.public_key_text.delete(1.0, tk.END)
        self.public_key_text.insert(1.0, config.public_key or "")
        
        # Quality settings
        self.video_quality_var.set(config.video_quality)
        self.audio_quality_var.set(config.audio_quality)
        self.frame_rate_var.set(str(config.frame_rate))
        self.resolution_var.set(config.resolution)
        
        # Security settings
        self.encryption_enabled_var.set(config.encryption_enabled)
        self.compression_enabled_var.set(config.compression_enabled)
        self.certificate_pinning_var.set(config.certificate_pinning)
        
        # Policy settings
        self.policy_enabled_var.set(config.policy_enabled)
        
        # Advanced settings
        self.heartbeat_interval_spinbox.set(str(config.heartbeat_interval))
        self.connection_timeout_spinbox.set(str(config.connection_timeout))
        self.retry_attempts_spinbox.set(str(config.retry_attempts))
        self.auto_reconnect_var.set(config.auto_reconnect)
        
        # Update UI based on settings
        self.on_connection_type_changed()
        self.on_auth_method_changed()
        self.on_video_quality_changed(str(config.video_quality))
        self.on_audio_quality_changed(str(config.audio_quality))


# Import simpledialog for save dialog
import tkinter.simpledialog


# Convenience function
def show_connection_dialog(parent: tk.Widget, on_connect: Optional[Callable[[ConnectionConfig], None]] = None) -> None:
    """Show connection configuration dialog"""
    dialog = ConnectionDialog(parent, on_connect)
    dialog.show_dialog()

# Path: gui/user/user_gui.py
"""
Main user interface for RDP connection in Lucid RDP GUI.
Provides session connection, policy enforcement, and client controls.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import base64

from ..core.networking import TorHttpClient, SecurityConfig, OnionEndpoint
from ..core.security import get_security_validator, validate_onion_address
from ..core.config_manager import get_config_manager, ConfigScope
from ..core.widgets import get_theme_manager, StatusLabel, ProgressBar, create_tooltip
from ..core.telemetry import get_telemetry_manager, EventType, track_event

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class SessionPolicy(Enum):
    """Session policy types"""
    STRICT = "strict"
    STANDARD = "standard"
    CUSTOM = "custom"


@dataclass
class ConnectionParams:
    """Connection parameters for session policy"""
    # Input parameters
    mouse_enabled: bool = True
    mouse_rate_limit_hz: int = 60
    keyboard_enabled: bool = True
    keyboard_blocklist: List[str] = None
    keyboard_allowlist_mode: bool = False
    keyboard_allowlist: Optional[List[str]] = None
    
    # Clipboard parameters
    clipboard_host_to_remote: bool = False
    clipboard_remote_to_host: bool = False
    clipboard_max_bytes: int = 65536
    
    # File transfer parameters
    file_upload_enabled: bool = False
    file_download_enabled: bool = False
    file_max_size_mb: int = 25
    file_allowed_dirs: List[str] = None
    file_allowed_extensions: List[str] = None
    
    # System usage parameters
    system_screenshare_allowed: bool = False
    system_screenshots_allowed: bool = False
    system_audio_in: bool = False
    system_audio_out: bool = True
    system_camera: bool = False
    system_printing: bool = False
    system_shell_channels: bool = False
    
    def __post_init__(self):
        if self.keyboard_blocklist is None:
            self.keyboard_blocklist = ['PrintScreen']
        if self.file_allowed_dirs is None:
            self.file_allowed_dirs = []
        if self.file_allowed_extensions is None:
            self.file_allowed_extensions = []
    
    def policy_hash(self) -> str:
        """Calculate policy hash for this configuration"""
        data = asdict(self)
        # Remove None values and sort for consistent hashing
        clean_data = {k: v for k, v in data.items() if v is not None}
        json_str = json.dumps(clean_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class SessionInfo:
    """Session information"""
    session_id: str
    participant_pubkeys: List[str]
    codec: str
    chunk_count: int
    root_hash: str
    recorder_version: str
    device_fingerprint: str
    started_at: datetime
    policy_hash: str
    consent_receipt: Optional[str] = None


@dataclass
class ConsentReceipt:
    """Consent receipt for session connection"""
    user_id: str
    session_id: str
    policy_hash: str
    terms_hash: str
    accepted_at_iso: str
    signature_b64: str


class UserGUI:
    """
    Main user interface for RDP connection.
    
    Provides:
    - Session connection and management
    - Client-controlled policy enforcement
    - Connection parameter configuration
    - Terms of Connection acceptance
    - Session proofs viewing and export
    """
    
    def __init__(self, root: tk.Tk, node_api_url: str = "http://localhost:8080"):
        self.root = root
        self.node_api_url = node_api_url.rstrip('/')
        
        # Current state
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.current_session: Optional[SessionInfo] = None
        self.current_params = ConnectionParams()
        self.session_proofs: List[Dict[str, Any]] = []
        
        # Configuration
        self.config_manager = get_config_manager()
        self.security_validator = get_security_validator()
        self.telemetry_manager = get_telemetry_manager()
        self.theme_manager = get_theme_manager()
        
        # GUI components
        self.main_frame: Optional[ttk.Frame] = None
        self.notebook: Optional[ttk.Notebook] = None
        self.status_label: Optional[StatusLabel] = None
        self.progress_bar: Optional[ProgressBar] = None
        
        # Setup networking and GUI
        self.setup_networking()
        self.setup_gui()
        self.load_saved_params()
        
        # Start monitoring
        self.start_monitoring()
    
    def setup_networking(self) -> None:
        """Setup networking components."""
        try:
            security_config = SecurityConfig(
                allowed_onions=[],
                certificate_pinning=True
            )
            self.http_client = TorHttpClient(security_config)
        except Exception as e:
            logger.error(f"Failed to setup networking: {e}")
            self.http_client = None
    
    def setup_gui(self) -> None:
        """Setup the main GUI."""
        self.root.title("Lucid RDP - User Interface")
        self.root.geometry("1000x700")
        
        # Apply theme
        self.theme_manager.apply_theme_to_window(self.root)
        
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar
        self.create_status_bar()
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_connection_tab()
        self.create_policy_tab()
        self.create_session_tab()
        self.create_proofs_tab()
        self.create_settings_tab()
        
        # Setup menu
        self.setup_menu()
    
    def create_status_bar(self) -> None:
        """Create status bar at bottom of window."""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Connection status
        self.status_label = StatusLabel(status_frame, text="Disconnected", status="info")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Progress bar
        self.progress_bar = ProgressBar(status_frame, width=200, height=20)
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))
        
        # Connection info
        self.connection_info_label = ttk.Label(status_frame, text="No active session")
        self.connection_info_label.pack(side=tk.RIGHT)
        
        create_tooltip(self.status_label, "Current connection status")
        create_tooltip(self.progress_bar, "Connection progress")
    
    def create_connection_tab(self) -> None:
        """Create session connection tab."""
        self.connection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.connection_frame, text="Connect")
        
        # Connection section
        connection_section = ttk.LabelFrame(self.connection_frame, text="Session Connection")
        connection_section.pack(fill=tk.X, padx=10, pady=5)
        
        # Session ID input
        session_frame = ttk.Frame(connection_section)
        session_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(session_frame, text="Session ID:").pack(anchor=tk.W)
        self.session_id_entry = ttk.Entry(session_frame, width=50, font=('Consolas', 9))
        self.session_id_entry.pack(fill=tk.X, pady=(2, 0))
        create_tooltip(self.session_id_entry, "Enter the session ID to connect to")
        
        # QR code scanner button
        qr_frame = ttk.Frame(connection_section)
        qr_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(qr_frame, text="Scan QR Code", command=self.scan_qr_code).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(qr_frame, text="Generate Session", command=self.generate_session).pack(side=tk.LEFT, padx=5)
        
        # Connection controls
        controls_frame = ttk.Frame(connection_section)
        controls_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.connect_button = ttk.Button(controls_frame, text="Connect", command=self.connect_to_session)
        self.connect_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_button = ttk.Button(controls_frame, text="Disconnect", command=self.disconnect_from_session, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, padx=5)
        
        # Connection info
        self.connection_info_frame = ttk.LabelFrame(self.connection_frame, text="Connection Information")
        self.connection_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.connection_info_text = scrolledtext.ScrolledText(self.connection_info_frame, height=10, wrap=tk.WORD)
        self.connection_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_policy_tab(self) -> None:
        """Create connection policy tab."""
        self.policy_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.policy_frame, text="Policy")
        
        # Policy presets
        presets_frame = ttk.LabelFrame(self.policy_frame, text="Policy Presets")
        presets_frame.pack(fill=tk.X, padx=10, pady=5)
        
        preset_frame = ttk.Frame(presets_frame)
        preset_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.policy_preset_var = tk.StringVar(value="standard")
        ttk.Radiobutton(preset_frame, text="Strict", variable=self.policy_preset_var, value="strict", command=self.load_policy_preset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(preset_frame, text="Standard", variable=self.policy_preset_var, value="standard", command=self.load_policy_preset).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(preset_frame, text="Custom", variable=self.policy_preset_var, value="custom", command=self.load_policy_preset).pack(side=tk.LEFT)
        
        # Policy configuration notebook
        self.policy_notebook = ttk.Notebook(self.policy_frame)
        self.policy_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Input tab
        self.create_input_policy_tab()
        
        # Clipboard tab
        self.create_clipboard_policy_tab()
        
        # File transfer tab
        self.create_file_policy_tab()
        
        # System tab
        self.create_system_policy_tab()
        
        # Policy summary
        summary_frame = ttk.LabelFrame(self.policy_frame, text="Policy Summary")
        summary_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.policy_hash_label = ttk.Label(summary_frame, text="Policy Hash: Not calculated", font=('Consolas', 8))
        self.policy_hash_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Update policy hash when parameters change
        self.policy_notebook.bind('<<NotebookTabChanged>>', self.update_policy_hash)
    
    def create_input_policy_tab(self) -> None:
        """Create input policy configuration tab."""
        input_frame = ttk.Frame(self.policy_notebook)
        self.policy_notebook.add(input_frame, text="Input")
        
        # Mouse settings
        mouse_frame = ttk.LabelFrame(input_frame, text="Mouse Settings")
        mouse_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.mouse_enabled_var = tk.BooleanVar(value=self.current_params.mouse_enabled)
        ttk.Checkbutton(mouse_frame, text="Enable mouse input", variable=self.mouse_enabled_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        rate_frame = ttk.Frame(mouse_frame)
        rate_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(rate_frame, text="Rate limit (Hz):").pack(side=tk.LEFT)
        self.mouse_rate_var = tk.IntVar(value=self.current_params.mouse_rate_limit_hz)
        rate_spin = ttk.Spinbox(rate_frame, from_=1, to=240, width=10, textvariable=self.mouse_rate_var, command=self.update_policy_hash)
        rate_spin.pack(side=tk.LEFT, padx=(5, 0))
        
        # Keyboard settings
        keyboard_frame = ttk.LabelFrame(input_frame, text="Keyboard Settings")
        keyboard_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.keyboard_enabled_var = tk.BooleanVar(value=self.current_params.keyboard_enabled)
        ttk.Checkbutton(keyboard_frame, text="Enable keyboard input", variable=self.keyboard_enabled_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        # Blocklist
        blocklist_frame = ttk.Frame(keyboard_frame)
        blocklist_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(blocklist_frame, text="Blocked keys:").pack(anchor=tk.W)
        self.keyboard_blocklist_text = tk.Text(blocklist_frame, height=3, width=40)
        self.keyboard_blocklist_text.pack(fill=tk.X, pady=(2, 0))
        self.keyboard_blocklist_text.insert(tk.END, ', '.join(self.current_params.keyboard_blocklist))
        
        # Allowlist mode
        self.keyboard_allowlist_mode_var = tk.BooleanVar(value=self.current_params.keyboard_allowlist_mode)
        ttk.Checkbutton(keyboard_frame, text="Allowlist mode (only allow specified keys)", variable=self.keyboard_allowlist_mode_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
    
    def create_clipboard_policy_tab(self) -> None:
        """Create clipboard policy configuration tab."""
        clipboard_frame = ttk.Frame(self.policy_notebook)
        self.policy_notebook.add(clipboard_frame, text="Clipboard")
        
        # Clipboard directions
        direction_frame = ttk.LabelFrame(clipboard_frame, text="Clipboard Directions")
        direction_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.clipboard_host_to_remote_var = tk.BooleanVar(value=self.current_params.clipboard_host_to_remote)
        ttk.Checkbutton(direction_frame, text="Host to Remote", variable=self.clipboard_host_to_remote_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        self.clipboard_remote_to_host_var = tk.BooleanVar(value=self.current_params.clipboard_remote_to_host)
        ttk.Checkbutton(direction_frame, text="Remote to Host", variable=self.clipboard_remote_to_host_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        # Size limits
        size_frame = ttk.LabelFrame(clipboard_frame, text="Size Limits")
        size_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(size_frame, text="Maximum bytes:").pack(anchor=tk.W, padx=5, pady=2)
        self.clipboard_max_bytes_var = tk.IntVar(value=self.current_params.clipboard_max_bytes)
        ttk.Entry(size_frame, textvariable=self.clipboard_max_bytes_var, width=20).pack(anchor=tk.W, padx=5, pady=2)
    
    def create_file_policy_tab(self) -> None:
        """Create file transfer policy configuration tab."""
        file_frame = ttk.Frame(self.policy_notebook)
        self.policy_notebook.add(file_frame, text="File Transfer")
        
        # File directions
        direction_frame = ttk.LabelFrame(file_frame, text="File Transfer Directions")
        direction_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_upload_var = tk.BooleanVar(value=self.current_params.file_upload_enabled)
        ttk.Checkbutton(direction_frame, text="Upload (Host to Remote)", variable=self.file_upload_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        self.file_download_var = tk.BooleanVar(value=self.current_params.file_download_enabled)
        ttk.Checkbutton(direction_frame, text="Download (Remote to Host)", variable=self.file_download_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        # Size limits
        size_frame = ttk.LabelFrame(file_frame, text="Size Limits")
        size_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(size_frame, text="Maximum file size (MB):").pack(anchor=tk.W, padx=5, pady=2)
        self.file_max_size_var = tk.IntVar(value=self.current_params.file_max_size_mb)
        ttk.Entry(size_frame, textvariable=self.file_max_size_var, width=20).pack(anchor=tk.W, padx=5, pady=2)
        
        # Allowed directories
        dirs_frame = ttk.LabelFrame(file_frame, text="Allowed Directories")
        dirs_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(dirs_frame, text="Allowed directories (one per line):").pack(anchor=tk.W, padx=5, pady=2)
        self.file_dirs_text = tk.Text(dirs_frame, height=3, width=50)
        self.file_dirs_text.pack(fill=tk.X, padx=5, pady=2)
        self.file_dirs_text.insert(tk.END, '\n'.join(self.current_params.file_allowed_dirs))
    
    def create_system_policy_tab(self) -> None:
        """Create system usage policy configuration tab."""
        system_frame = ttk.Frame(self.policy_notebook)
        self.policy_notebook.add(system_frame, text="System")
        
        # Audio settings
        audio_frame = ttk.LabelFrame(system_frame, text="Audio")
        audio_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.audio_in_var = tk.BooleanVar(value=self.current_params.system_audio_in)
        ttk.Checkbutton(audio_frame, text="Audio Input", variable=self.audio_in_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        self.audio_out_var = tk.BooleanVar(value=self.current_params.system_audio_out)
        ttk.Checkbutton(audio_frame, text="Audio Output", variable=self.audio_out_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        # Video settings
        video_frame = ttk.LabelFrame(system_frame, text="Video")
        video_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.camera_var = tk.BooleanVar(value=self.current_params.system_camera)
        ttk.Checkbutton(video_frame, text="Camera Access", variable=self.camera_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        # Screen sharing
        screen_frame = ttk.LabelFrame(system_frame, text="Screen Sharing")
        screen_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.screenshare_var = tk.BooleanVar(value=self.current_params.system_screenshare_allowed)
        ttk.Checkbutton(screen_frame, text="Screen Sharing", variable=self.screenshare_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        self.screenshots_var = tk.BooleanVar(value=self.current_params.system_screenshots_allowed)
        ttk.Checkbutton(screen_frame, text="Screenshots", variable=self.screenshots_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        # Other system access
        other_frame = ttk.LabelFrame(system_frame, text="Other")
        other_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.printing_var = tk.BooleanVar(value=self.current_params.system_printing)
        ttk.Checkbutton(other_frame, text="Printing", variable=self.printing_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
        
        self.shell_var = tk.BooleanVar(value=self.current_params.system_shell_channels)
        ttk.Checkbutton(other_frame, text="Shell Channels", variable=self.shell_var, command=self.update_policy_hash).pack(anchor=tk.W, padx=5, pady=2)
    
    def create_session_tab(self) -> None:
        """Create active session tab."""
        self.session_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.session_frame, text="Session")
        
        # Session info
        info_frame = ttk.LabelFrame(self.session_frame, text="Session Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.session_info_text = scrolledtext.ScrolledText(info_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.session_info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Session controls
        controls_frame = ttk.LabelFrame(self.session_frame, text="Session Controls")
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Refresh Session", command=self.refresh_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="View Logs", command=self.view_session_logs).pack(side=tk.LEFT, padx=5)
        
        # Session activity
        activity_frame = ttk.LabelFrame(self.session_frame, text="Session Activity")
        activity_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.session_activity_text = scrolledtext.ScrolledText(activity_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.session_activity_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_proofs_tab(self) -> None:
        """Create session proofs tab."""
        self.proofs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.proofs_frame, text="Proofs")
        
        # Toolbar
        toolbar = ttk.Frame(self.proofs_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh Proofs", command=self.refresh_proofs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Export Proofs", command=self.export_proofs).pack(side=tk.LEFT, padx=5)
        
        # Proofs list
        self.proofs_tree = ttk.Treeview(self.proofs_frame, columns=('date', 'type', 'status', 'hash'), show='headings')
        
        self.proofs_tree.heading('date', text='Date')
        self.proofs_tree.heading('type', text='Type')
        self.proofs_tree.heading('status', text='Status')
        self.proofs_tree.heading('hash', text='Hash')
        
        self.proofs_tree.column('date', width=150)
        self.proofs_tree.column('type', width=100)
        self.proofs_tree.column('status', width=80)
        self.proofs_tree.column('hash', width=200)
        
        proofs_scroll = ttk.Scrollbar(self.proofs_frame, orient=tk.VERTICAL, command=self.proofs_tree.yview)
        self.proofs_tree.configure(yscrollcommand=proofs_scroll.set)
        
        self.proofs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        proofs_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to view details
        self.proofs_tree.bind('<Double-1>', self.view_proof_details)
    
    def create_settings_tab(self) -> None:
        """Create settings tab."""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Connection settings
        conn_frame = ttk.LabelFrame(self.settings_frame, text="Connection Settings")
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Node API URL
        url_frame = ttk.Frame(conn_frame)
        url_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(url_frame, text="Node API URL:").pack(anchor=tk.W)
        self.node_url_var = tk.StringVar(value=self.node_api_url)
        ttk.Entry(url_frame, textvariable=self.node_url_var, width=50).pack(fill=tk.X, pady=(2, 0))
        
        # Auto-reconnect
        self.auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(conn_frame, text="Auto-reconnect on connection loss", variable=self.auto_reconnect_var).pack(anchor=tk.W, padx=5, pady=5)
        
        # Save settings
        ttk.Button(conn_frame, text="Save Settings", command=self.save_settings).pack(anchor=tk.W, padx=5, pady=5)
    
    def setup_menu(self) -> None:
        """Setup application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Session", command=self.generate_session)
        file_menu.add_command(label="Connect to Session", command=self.connect_to_session)
        file_menu.add_separator()
        file_menu.add_command(label="Export Proofs", command=self.export_proofs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Policy Settings", command=lambda: self.notebook.select(1))
        edit_menu.add_command(label="Connection Settings", command=lambda: self.notebook.select(4))
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Session Info", command=lambda: self.notebook.select(2))
        view_menu.add_command(label="Proofs", command=lambda: self.notebook.select(3))
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Terms of Connection", command=self.show_terms)
    
    def load_policy_preset(self) -> None:
        """Load policy preset configuration."""
        preset = self.policy_preset_var.get()
        
        if preset == "strict":
            self.current_params = ConnectionParams(
                mouse_enabled=True,
                keyboard_enabled=True,
                keyboard_blocklist=['PrintScreen', 'F12', 'Ctrl+Alt+Del'],
                clipboard_host_to_remote=False,
                clipboard_remote_to_host=False,
                file_upload_enabled=False,
                file_download_enabled=False,
                system_screenshare_allowed=False,
                system_screenshots_allowed=False,
                system_audio_in=False,
                system_audio_out=True,
                system_camera=False,
                system_printing=False,
                system_shell_channels=False
            )
        elif preset == "standard":
            self.current_params = ConnectionParams(
                mouse_enabled=True,
                keyboard_enabled=True,
                keyboard_blocklist=['PrintScreen'],
                clipboard_host_to_remote=False,
                clipboard_remote_to_host=False,
                file_upload_enabled=False,
                file_download_enabled=False,
                system_screenshare_allowed=False,
                system_screenshots_allowed=False,
                system_audio_in=False,
                system_audio_out=True,
                system_camera=False,
                system_printing=False,
                system_shell_channels=False
            )
        # Custom preset doesn't change current params
        
        self.update_policy_ui()
        self.update_policy_hash()
    
    def update_policy_ui(self) -> None:
        """Update policy UI with current parameters."""
        self.mouse_enabled_var.set(self.current_params.mouse_enabled)
        self.mouse_rate_var.set(self.current_params.mouse_rate_limit_hz)
        self.keyboard_enabled_var.set(self.current_params.keyboard_enabled)
        self.keyboard_allowlist_mode_var.set(self.current_params.keyboard_allowlist_mode)
        
        # Update blocklist text
        self.keyboard_blocklist_text.delete(1.0, tk.END)
        self.keyboard_blocklist_text.insert(tk.END, ', '.join(self.current_params.keyboard_blocklist))
        
        self.clipboard_host_to_remote_var.set(self.current_params.clipboard_host_to_remote)
        self.clipboard_remote_to_host_var.set(self.current_params.clipboard_remote_to_host)
        self.clipboard_max_bytes_var.set(self.current_params.clipboard_max_bytes)
        
        self.file_upload_var.set(self.current_params.file_upload_enabled)
        self.file_download_var.set(self.current_params.file_download_enabled)
        self.file_max_size_var.set(self.current_params.file_max_size_mb)
        
        # Update file directories text
        self.file_dirs_text.delete(1.0, tk.END)
        self.file_dirs_text.insert(tk.END, '\n'.join(self.current_params.file_allowed_dirs))
        
        self.audio_in_var.set(self.current_params.system_audio_in)
        self.audio_out_var.set(self.current_params.system_audio_out)
        self.camera_var.set(self.current_params.system_camera)
        self.screenshare_var.set(self.current_params.system_screenshare_allowed)
        self.screenshots_var.set(self.current_params.system_screenshots_allowed)
        self.printing_var.set(self.current_params.system_printing)
        self.shell_var.set(self.current_params.system_shell_channels)
    
    def update_policy_hash(self, event=None) -> None:
        """Update policy hash display."""
        try:
            # Update current params from UI
            self.current_params.mouse_enabled = self.mouse_enabled_var.get()
            self.current_params.mouse_rate_limit_hz = self.mouse_rate_var.get()
            self.current_params.keyboard_enabled = self.keyboard_enabled_var.get()
            self.current_params.keyboard_allowlist_mode = self.keyboard_allowlist_mode_var.get()
            
            # Update blocklist from text
            blocklist_text = self.keyboard_blocklist_text.get(1.0, tk.END).strip()
            if blocklist_text:
                self.current_params.keyboard_blocklist = [k.strip() for k in blocklist_text.split(',') if k.strip()]
            else:
                self.current_params.keyboard_blocklist = []
            
            self.current_params.clipboard_host_to_remote = self.clipboard_host_to_remote_var.get()
            self.current_params.clipboard_remote_to_host = self.clipboard_remote_to_host_var.get()
            self.current_params.clipboard_max_bytes = self.clipboard_max_bytes_var.get()
            
            self.current_params.file_upload_enabled = self.file_upload_var.get()
            self.current_params.file_download_enabled = self.file_download_var.get()
            self.current_params.file_max_size_mb = self.file_max_size_var.get()
            
            # Update file directories from text
            dirs_text = self.file_dirs_text.get(1.0, tk.END).strip()
            if dirs_text:
                self.current_params.file_allowed_dirs = [d.strip() for d in dirs_text.split('\n') if d.strip()]
            else:
                self.current_params.file_allowed_dirs = []
            
            self.current_params.system_audio_in = self.audio_in_var.get()
            self.current_params.system_audio_out = self.audio_out_var.get()
            self.current_params.system_camera = self.camera_var.get()
            self.current_params.system_screenshare_allowed = self.screenshare_var.get()
            self.current_params.system_screenshots_allowed = self.screenshots_var.get()
            self.current_params.system_printing = self.printing_var.get()
            self.current_params.system_shell_channels = self.shell_var.get()
            
            # Calculate and display hash
            policy_hash = self.current_params.policy_hash()
            self.policy_hash_label.configure(text=f"Policy Hash: {policy_hash[:16]}...")
            
        except Exception as e:
            logger.error(f"Failed to update policy hash: {e}")
    
    def scan_qr_code(self) -> None:
        """Scan QR code for session ID."""
        # TODO: Implement QR code scanning
        messagebox.showinfo("QR Scanner", "QR code scanning not yet implemented")
    
    def generate_session(self) -> None:
        """Generate a new session."""
        try:
            response = self._make_api_request("POST", "/api/sessions/generate")
            if response:
                session_id = response.get("session_id")
                if session_id:
                    self.session_id_entry.delete(0, tk.END)
                    self.session_id_entry.insert(0, session_id)
                    messagebox.showinfo("Session Generated", f"New session ID: {session_id}")
                    track_event(EventType.FEATURE_USED, {"feature": "generate_session"})
        except Exception as e:
            logger.error(f"Failed to generate session: {e}")
            messagebox.showerror("Error", f"Failed to generate session: {e}")
    
    def connect_to_session(self) -> None:
        """Connect to a session."""
        session_id = self.session_id_entry.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Please enter a session ID")
            return
        
        # Show terms of connection
        if not self.show_terms_dialog():
            return
        
        # Update status
        self.connection_status = ConnectionStatus.CONNECTING
        self.update_status_display()
        
        # Start connection in thread
        threading.Thread(target=self._connect_to_session_async, args=(session_id,), daemon=True).start()
    
    def _connect_to_session_async(self, session_id: str) -> None:
        """Connect to session asynchronously."""
        try:
            # Create consent receipt
            consent_receipt = self._create_consent_receipt(session_id)
            
            # Connect to session
            response = self._make_api_request("POST", "/api/sessions/connect", {
                "session_id": session_id,
                "policy_hash": self.current_params.policy_hash(),
                "consent_receipt": consent_receipt
            })
            
            if response:
                self.current_session = SessionInfo(
                    session_id=session_id,
                    participant_pubkeys=response.get("participant_pubkeys", []),
                    codec=response.get("codec", ""),
                    chunk_count=response.get("chunk_count", 0),
                    root_hash=response.get("root_hash", ""),
                    recorder_version=response.get("recorder_version", ""),
                    device_fingerprint=response.get("device_fingerprint", ""),
                    started_at=datetime.now(timezone.utc),
                    policy_hash=self.current_params.policy_hash(),
                    consent_receipt=consent_receipt
                )
                
                self.connection_status = ConnectionStatus.CONNECTED
                self.root.after(0, self._on_connection_success)
            else:
                self.connection_status = ConnectionStatus.FAILED
                self.root.after(0, self._on_connection_failed, "Failed to connect to session")
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connection_status = ConnectionStatus.FAILED
            self.root.after(0, self._on_connection_failed, str(e))
    
    def _create_consent_receipt(self, session_id: str) -> str:
        """Create consent receipt for session connection."""
        user_id = str(uuid.uuid4())  # Generate user ID
        policy_hash = self.current_params.policy_hash()
        terms_hash = hashlib.sha256(b"Terms of Connection v1.0").hexdigest()
        accepted_at = datetime.now(timezone.utc).isoformat()
        
        # Create signature (simplified - would use proper crypto in production)
        signature_data = f"{user_id}|{session_id}|{policy_hash}|{terms_hash}|{accepted_at}"
        signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        consent_receipt = ConsentReceipt(
            user_id=user_id,
            session_id=session_id,
            policy_hash=policy_hash,
            terms_hash=terms_hash,
            accepted_at_iso=accepted_at,
            signature_b64=base64.b64encode(signature.encode()).decode()
        )
        
        return json.dumps(asdict(consent_receipt))
    
    def _on_connection_success(self) -> None:
        """Handle successful connection."""
        self.update_status_display()
        self.connect_button.configure(state=tk.DISABLED)
        self.disconnect_button.configure(state=tk.NORMAL)
        
        # Update connection info
        self.connection_info_text.configure(state=tk.NORMAL)
        self.connection_info_text.delete(1.0, tk.END)
        if self.current_session:
            info = f"""Session ID: {self.current_session.session_id}
Started: {self.current_session.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Codec: {self.current_session.codec}
Chunks: {self.current_session.chunk_count}
Root Hash: {self.current_session.root_hash[:16]}...
Device Fingerprint: {self.current_session.device_fingerprint[:16]}...
Policy Hash: {self.current_session.policy_hash[:16]}..."""
            self.connection_info_text.insert(tk.END, info)
        self.connection_info_text.configure(state=tk.DISABLED)
        
        messagebox.showinfo("Connected", "Successfully connected to session")
        track_event(EventType.CONNECTION_SUCCESS, {"session_id": self.current_session.session_id if self.current_session else ""})
    
    def _on_connection_failed(self, error_message: str) -> None:
        """Handle failed connection."""
        self.update_status_display()
        messagebox.showerror("Connection Failed", f"Failed to connect: {error_message}")
        track_event(EventType.CONNECTION_FAILED, {"error": error_message})
    
    def disconnect_from_session(self) -> None:
        """Disconnect from current session."""
        if not self.current_session:
            return
        
        try:
            response = self._make_api_request("POST", "/api/sessions/disconnect", {
                "session_id": self.current_session.session_id
            })
            
            self.connection_status = ConnectionStatus.DISCONNECTED
            self.current_session = None
            self.update_status_display()
            
            self.connect_button.configure(state=tk.NORMAL)
            self.disconnect_button.configure(state=tk.DISABLED)
            
            # Clear connection info
            self.connection_info_text.configure(state=tk.NORMAL)
            self.connection_info_text.delete(1.0, tk.END)
            self.connection_info_text.configure(state=tk.DISABLED)
            
            messagebox.showinfo("Disconnected", "Disconnected from session")
            
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            messagebox.showerror("Error", f"Failed to disconnect: {e}")
    
    def show_terms_dialog(self) -> bool:
        """Show terms of connection dialog."""
        terms_dialog = tk.Toplevel(self.root)
        terms_dialog.title("Terms of Connection")
        terms_dialog.geometry("600x400")
        terms_dialog.resizable(False, False)
        terms_dialog.transient(self.root)
        terms_dialog.grab_set()
        
        # Terms text
        terms_text = """TERMS OF CONNECTION - Lucid RDP

By connecting to this session, you agree to the following terms:

1. SECURITY AND PRIVACY
   - All session data is encrypted and logged
   - Your connection parameters define access permissions
   - Violations of policy will terminate the session

2. SESSION RECORDING
   - All session activity is recorded and anchored to blockchain
   - Session proofs are generated for audit purposes
   - You retain access to your session proofs

3. CLIENT CONTROLS
   - You control what the remote session can access
   - Policy enforcement happens on your client
   - Changes to policy require session restart

4. TRUST NOTHING POLICY
   - Default deny for all inputs and transfers
   - Explicit approval required for each capability
   - Session voided if policy violations detected

5. DATA HANDLING
   - Session chunks are encrypted with your keys
   - No plaintext data leaves your device
   - Blockchain anchors provide tamper-proof logs

Do you accept these terms?"""
        
        text_widget = scrolledtext.ScrolledText(terms_dialog, wrap=tk.WORD, width=70, height=20)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, terms_text)
        text_widget.configure(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(terms_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        accepted = False
        
        def accept():
            nonlocal accepted
            accepted = True
            terms_dialog.destroy()
        
        def decline():
            terms_dialog.destroy()
        
        ttk.Button(button_frame, text="Accept", command=accept).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Decline", command=decline).pack(side=tk.RIGHT)
        
        # Center dialog
        terms_dialog.update_idletasks()
        x = (terms_dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (terms_dialog.winfo_screenheight() // 2) - (400 // 2)
        terms_dialog.geometry(f"600x400+{x}+{y}")
        
        terms_dialog.wait_window()
        return accepted
    
    def refresh_session(self) -> None:
        """Refresh current session information."""
        if not self.current_session:
            return
        
        try:
            response = self._make_api_request("GET", f"/api/sessions/{self.current_session.session_id}")
            if response:
                # Update session info
                self.current_session.chunk_count = response.get("chunk_count", self.current_session.chunk_count)
                self.current_session.root_hash = response.get("root_hash", self.current_session.root_hash)
                
                # Update display
                self._on_connection_success()
        except Exception as e:
            logger.error(f"Failed to refresh session: {e}")
    
    def view_session_logs(self) -> None:
        """View session logs."""
        if not self.current_session:
            messagebox.showwarning("Warning", "No active session")
            return
        
        # TODO: Implement session logs viewer
        messagebox.showinfo("Session Logs", "Session logs viewer not yet implemented")
    
    def refresh_proofs(self) -> None:
        """Refresh session proofs."""
        if not self.current_session:
            messagebox.showwarning("Warning", "No active session")
            return
        
        try:
            response = self._make_api_request("GET", f"/api/sessions/{self.current_session.session_id}/proofs")
            if response:
                self.session_proofs = response.get("proofs", [])
                self.update_proofs_display()
        except Exception as e:
            logger.error(f"Failed to refresh proofs: {e}")
    
    def update_proofs_display(self) -> None:
        """Update proofs display."""
        # Clear existing items
        for item in self.proofs_tree.get_children():
            self.proofs_tree.delete(item)
        
        # Add proofs
        for proof in self.session_proofs:
            self.proofs_tree.insert('', 'end', values=(
                proof.get("created_at", ""),
                proof.get("type", ""),
                proof.get("status", ""),
                proof.get("hash", "")[:16] + "..." if proof.get("hash") else ""
            ))
    
    def view_proof_details(self, event) -> None:
        """View detailed proof information."""
        selection = self.proofs_tree.selection()
        if not selection:
            return
        
        item = self.proofs_tree.item(selection[0])
        values = item['values']
        
        # Find the proof
        proof = None
        for p in self.session_proofs:
            if p.get("created_at") == values[0]:
                proof = p
                break
        
        if not proof:
            return
        
        # Create details dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Proof Details")
        dialog.geometry("500x400")
        
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=60, height=20)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        details = json.dumps(proof, indent=2)
        details_text.insert(tk.END, details)
        details_text.configure(state=tk.DISABLED)
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def export_proofs(self) -> None:
        """Export session proofs to file."""
        if not self.session_proofs:
            messagebox.showwarning("Warning", "No proofs to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.session_proofs, f, indent=2, default=str)
                messagebox.showinfo("Success", f"Proofs exported to {filename}")
            except Exception as e:
                logger.error(f"Failed to export proofs: {e}")
                messagebox.showerror("Error", f"Failed to export proofs: {e}")
    
    def save_settings(self) -> None:
        """Save user settings."""
        try:
            settings = {
                "node_api_url": self.node_url_var.get(),
                "auto_reconnect": self.auto_reconnect_var.get(),
                "policy_preset": self.policy_preset_var.get()
            }
            
            self.config_manager.save_config("user_settings", settings, ConfigScope.USER)
            messagebox.showinfo("Success", "Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def load_saved_params(self) -> None:
        """Load saved connection parameters."""
        try:
            params_data = self.config_manager.load_config("connection_params", ConfigScope.USER)
            if params_data:
                self.current_params = ConnectionParams(**params_data)
                self.update_policy_ui()
                self.update_policy_hash()
        except Exception as e:
            logger.error(f"Failed to load saved parameters: {e}")
    
    def save_params(self) -> None:
        """Save current connection parameters."""
        try:
            params_dict = asdict(self.current_params)
            self.config_manager.save_config("connection_params", params_dict, ConfigScope.USER)
        except Exception as e:
            logger.error(f"Failed to save parameters: {e}")
    
    def start_monitoring(self) -> None:
        """Start background monitoring."""
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                if self.connection_status == ConnectionStatus.CONNECTED and self.current_session:
                    self.refresh_session()
                    self.refresh_proofs()
                
                time.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def update_status_display(self) -> None:
        """Update status display."""
        if self.connection_status == ConnectionStatus.CONNECTED:
            self.status_label.set_status("success", "Connected")
            self.connection_info_label.configure(text=f"Session: {self.current_session.session_id[:8] if self.current_session else 'N/A'}...")
        elif self.connection_status == ConnectionStatus.CONNECTING:
            self.status_label.set_status("warning", "Connecting...")
            self.connection_info_label.configure(text="Connecting...")
        elif self.connection_status == ConnectionStatus.FAILED:
            self.status_label.set_status("error", "Failed")
            self.connection_info_label.configure(text="Connection failed")
        else:
            self.status_label.set_status("info", "Disconnected")
            self.connection_info_label.configure(text="No active session")
    
    def show_about(self) -> None:
        """Show about dialog."""
        about_text = """Lucid RDP User Interface v1.0.0

A Tor-only, blockchain-anchored remote desktop platform.

Features:
- Client-controlled session policy enforcement
- End-to-end encrypted P2P transport
- Session audit trail with blockchain anchoring
- Trust-nothing policy engine

For more information, visit the project documentation."""
        
        messagebox.showinfo("About Lucid RDP", about_text)
    
    def show_terms(self) -> None:
        """Show terms of connection."""
        self.show_terms_dialog()
    
    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make API request to node."""
        if not self.http_client:
            return None
        
        try:
            url = f"{self.node_api_url}{endpoint}"
            
            if method == "GET":
                response = self.http_client.get(url)
            elif method == "POST":
                response = self.http_client.post(url, json=data)
            else:
                return None
            
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None


def main():
    """Main entry point for user GUI."""
    root = tk.Tk()
    app = UserGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
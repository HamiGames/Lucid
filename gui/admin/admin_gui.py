# Path: gui/admin/admin_gui.py
"""
Main admin interface for Lucid RDP.
Provides bootstrap wizard, manifests viewer, payouts management, key rotation, backups, diagnostics, and OTA updates.
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
import os
import subprocess
import shutil

from ..core.networking import TorHttpClient, SecurityConfig, OnionEndpoint
from ..core.security import get_security_validator, validate_onion_address
from ..core.config_manager import get_config_manager, ConfigScope
from ..core.widgets import get_theme_manager, StatusLabel, ProgressBar, create_tooltip, LogViewer
from ..core.telemetry import get_telemetry_manager, EventType, track_event
from .backup_restore import BackupManager
from .diagnostics import DiagnosticManager
from .key_management import KeyManager
from .payouts_manager import PayoutsManager

logger = logging.getLogger(__name__)


class AdminStatus(Enum):
    """Admin interface status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


class LedgerMode(Enum):
    """Ledger mode enumeration"""
    SANDBOX = "sandbox"      # TRON Shasta testnet
    PRODUCTION = "production"  # TRON Mainnet


class ApplianceStatus(Enum):
    """Appliance status enumeration"""
    OFFLINE = "offline"
    BOOTING = "booting"
    ONLINE = "online"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class ApplianceInfo:
    """Appliance information container"""
    appliance_id: str
    status: ApplianceStatus
    hostname: str
    onion_address: str
    last_seen: datetime
    version: str
    uptime_seconds: int
    total_sessions: int
    active_sessions: int
    total_payouts: float
    ledger_mode: LedgerMode
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['last_seen'] = self.last_seen.isoformat()
        data['ledger_mode'] = self.ledger_mode.value
        return data


@dataclass
class BootstrapConfig:
    """Bootstrap configuration for new appliance"""
    appliance_name: str
    admin_email: str
    admin_password: str
    ledger_mode: LedgerMode
    tor_onion_service: bool = True
    auto_backup_enabled: bool = True
    payout_threshold: float = 10.0
    key_rotation_days: int = 90
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['ledger_mode'] = self.ledger_mode.value
        return data


class AdminGUI:
    """Main admin interface for Lucid RDP appliance management"""
    
    def __init__(self, root: tk.Tk, node_api_url: str = "http://localhost:8080"):
        self.root = root
        self.node_api_url = node_api_url.rstrip('/')
        self.update_interval = 5000  # 5 seconds
        
        # Current state
        self.admin_status = AdminStatus.DISCONNECTED
        self.appliance_info: Optional[ApplianceInfo] = None
        self.current_ledger_mode = LedgerMode.SANDBOX
        
        # Component managers
        self.backup_manager: Optional[BackupManager] = None
        self.diagnostics_manager: Optional[DiagnosticManager] = None
        self.key_manager: Optional[KeyManager] = None
        self.payouts_manager: Optional[PayoutsManager] = None
        
        # GUI components
        self.notebook: Optional[ttk.Notebook] = None
        self.status_bar: Optional[StatusLabel] = None
        self.monitoring_active = False
        
        # Setup networking and core components
        self.setup_networking()
        self.setup_gui()
        self.setup_menu()
        
        # Start monitoring
        self.start_monitoring()
        
        logger.info("Admin GUI initialized")
    
    def setup_networking(self) -> None:
        """Setup networking components"""
        try:
            # Security configuration for admin interface
            self.security_config = SecurityConfig(
                allowed_onions=[
                    "lucid-admin.onion",  # Example admin onion
                    "lucid-node.onion"    # Example node onion
                ],
                certificate_pinning=True,
                connection_timeout=30,
                read_timeout=60
            )
            
            # Create Tor HTTP client
            self.http_client = TorHttpClient(self.security_config)
            
            logger.info("Networking setup completed")
        except Exception as e:
            logger.error(f"Failed to setup networking: {e}")
            messagebox.showerror("Network Error", f"Failed to setup networking: {e}")
    
    def setup_gui(self) -> None:
        """Setup the main GUI interface"""
        self.root.title("Lucid RDP - Admin Interface")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_bootstrap_tab()
        self.create_dashboard_tab()
        self.create_manifests_tab()
        self.create_payouts_tab()
        self.create_keys_tab()
        self.create_backups_tab()
        self.create_diagnostics_tab()
        self.create_ota_tab()
        
        # Status bar
        self.status_bar = StatusLabel(
            self.root,
            text="Disconnected",
            status="error"
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Apply theme
        theme_manager = get_theme_manager()
        theme_manager.apply_theme_to_window(self.root)
        
        logger.info("GUI setup completed")
    
    def setup_menu(self) -> None:
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect Appliance...", command=self.connect_appliance_dialog)
        file_menu.add_command(label="Disconnect", command=self.disconnect_appliance)
        file_menu.add_separator()
        file_menu.add_command(label="Export Configuration...", command=self.export_configuration)
        file_menu.add_command(label="Import Configuration...", command=self.import_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Appliance menu
        appliance_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Appliance", menu=appliance_menu)
        appliance_menu.add_command(label="Bootstrap New...", command=self.bootstrap_wizard)
        appliance_menu.add_command(label="Switch Ledger Mode...", command=self.switch_ledger_mode)
        appliance_menu.add_command(label="Restart Services", command=self.restart_services)
        appliance_menu.add_command(label="Shutdown", command=self.shutdown_appliance)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Session Explorer", command=self.open_session_explorer)
        tools_menu.add_command(label="Blockchain Explorer", command=self.open_blockchain_explorer)
        tools_menu.add_command(label="Tor Network Status", command=self.check_tor_status)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_bootstrap_tab(self) -> None:
        """Create bootstrap wizard tab"""
        self.bootstrap_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bootstrap_frame, text="Bootstrap")
        
        # Main bootstrap container
        main_frame = ttk.Frame(self.bootstrap_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Lucid RDP Appliance Bootstrap",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Bootstrap options frame
        options_frame = ttk.LabelFrame(main_frame, text="Bootstrap Options")
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # New appliance button
        new_appliance_btn = ttk.Button(
            options_frame,
            text="Bootstrap New Appliance",
            command=self.bootstrap_wizard,
            style="Accent.TButton"
        )
        new_appliance_btn.pack(pady=10, padx=10, fill=tk.X)
        
        # Connect existing button
        connect_existing_btn = ttk.Button(
            options_frame,
            text="Connect to Existing Appliance",
            command=self.connect_appliance_dialog
        )
        connect_existing_btn.pack(pady=10, padx=10, fill=tk.X)
        
        # Bootstrap status frame
        status_frame = ttk.LabelFrame(main_frame, text="Bootstrap Status")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status text
        self.bootstrap_status_text = scrolledtext.ScrolledText(
            status_frame,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.bootstrap_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Quick actions frame
        actions_frame = ttk.Frame(status_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(actions_frame, text="Clear Log", command=self.clear_bootstrap_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Export Log", command=self.export_bootstrap_log).pack(side=tk.LEFT)
    
    def create_dashboard_tab(self) -> None:
        """Create dashboard tab"""
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        
        # Main dashboard container
        main_frame = ttk.Frame(self.dashboard_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Status overview frame
        status_frame = ttk.LabelFrame(main_frame, text="Appliance Status")
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Status grid
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Appliance info labels
        self.appliance_status_label = StatusLabel(status_grid, text="Status: Unknown", status="unknown")
        self.appliance_status_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        self.ledger_mode_label = StatusLabel(status_grid, text="Ledger: Unknown", status="unknown")
        self.ledger_mode_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        self.uptime_label = ttk.Label(status_grid, text="Uptime: Unknown")
        self.uptime_label.grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        
        self.sessions_label = ttk.Label(status_grid, text="Sessions: 0")
        self.sessions_label.grid(row=0, column=3, sticky=tk.W)
        
        # Metrics frame
        metrics_frame = ttk.LabelFrame(main_frame, text="System Metrics")
        metrics_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create metrics grid
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # CPU usage
        ttk.Label(metrics_grid, text="CPU Usage:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.cpu_progress = ProgressBar(metrics_grid, width=200)
        self.cpu_progress.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Memory usage
        ttk.Label(metrics_grid, text="Memory Usage:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.memory_progress = ProgressBar(metrics_grid, width=200)
        self.memory_progress.grid(row=1, column=1, sticky=tk.W, padx=(0, 20))
        
        # Disk usage
        ttk.Label(metrics_grid, text="Disk Usage:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.disk_progress = ProgressBar(metrics_grid, width=200)
        self.disk_progress.grid(row=2, column=1, sticky=tk.W, padx=(0, 20))
        
        # Network usage
        ttk.Label(metrics_grid, text="Network:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.network_label = ttk.Label(metrics_grid, text="0 KB/s ↑ 0 KB/s ↓")
        self.network_label.grid(row=3, column=1, sticky=tk.W)
        
        # Recent activity frame
        activity_frame = ttk.LabelFrame(main_frame, text="Recent Activity")
        activity_frame.pack(fill=tk.BOTH, expand=True)
        
        # Activity log
        self.activity_log = LogViewer(activity_frame, max_lines=100)
        self.activity_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_manifests_tab(self) -> None:
        """Create session manifests tab"""
        self.manifests_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manifests_frame, text="Manifests")
        
        # Main manifests container
        main_frame = ttk.Frame(self.manifests_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Search and filter controls
        ttk.Label(controls_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.manifest_search_var = tk.StringVar()
        self.manifest_search_var.trace('w', self.filter_manifests)
        search_entry = ttk.Entry(controls_frame, textvariable=self.manifest_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Filter by date
        ttk.Label(controls_frame, text="Date Range:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_filter_var = tk.StringVar(value="All")
        date_combo = ttk.Combobox(controls_frame, textvariable=self.date_filter_var, 
                                 values=["All", "Today", "This Week", "This Month"])
        date_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh button
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_manifests).pack(side=tk.LEFT, padx=(0, 10))
        
        # Export button
        ttk.Button(controls_frame, text="Export Selected", command=self.export_selected_manifests).pack(side=tk.LEFT)
        
        # Manifests tree
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with scrollbars
        self.manifests_tree = ttk.Treeview(tree_frame, columns=(
            'session_id', 'started_at', 'duration', 'participants', 'chunks', 'status'
        ), show='headings', height=15)
        
        # Configure columns
        self.manifests_tree.heading('session_id', text='Session ID')
        self.manifests_tree.heading('started_at', text='Started At')
        self.manifests_tree.heading('duration', text='Duration')
        self.manifests_tree.heading('participants', text='Participants')
        self.manifests_tree.heading('chunks', text='Chunks')
        self.manifests_tree.heading('status', text='Status')
        
        self.manifests_tree.column('session_id', width=200)
        self.manifests_tree.column('started_at', width=150)
        self.manifests_tree.column('duration', width=100)
        self.manifests_tree.column('participants', width=100)
        self.manifests_tree.column('chunks', width=80)
        self.manifests_tree.column('status', width=100)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.manifests_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.manifests_tree.xview)
        self.manifests_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tree and scrollbars
        self.manifests_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind double-click to view details
        self.manifests_tree.bind('<Double-1>', self.view_manifest_details)
        
        # Manifest details frame
        details_frame = ttk.LabelFrame(main_frame, text="Manifest Details")
        details_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.manifest_details_text = scrolledtext.ScrolledText(
            details_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.manifest_details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_payouts_tab(self) -> None:
        """Create payouts management tab"""
        self.payouts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.payouts_frame, text="Payouts")
        
        # Initialize payouts manager
        self.payouts_manager = PayoutsManager(self.payouts_frame, self.node_api_url)
    
    def create_keys_tab(self) -> None:
        """Create key management tab"""
        self.keys_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.keys_frame, text="Keys")
        
        # Initialize key manager
        self.key_manager = KeyManager(self.keys_frame, self.node_api_url)
    
    def create_backups_tab(self) -> None:
        """Create backup and restore tab"""
        self.backups_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.backups_frame, text="Backups")
        
        # Initialize backup manager
        self.backup_manager = BackupManager(self.backups_frame, self.node_api_url)
    
    def create_diagnostics_tab(self) -> None:
        """Create diagnostics tab"""
        self.diagnostics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.diagnostics_frame, text="Diagnostics")
        
        # Initialize diagnostics manager
        self.diagnostics_manager = DiagnosticManager(self.diagnostics_frame, self.node_api_url)
    
    def create_ota_tab(self) -> None:
        """Create OTA updates tab"""
        self.ota_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ota_frame, text="OTA Updates")
        
        # Main OTA container
        main_frame = ttk.Frame(self.ota_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Over-The-Air Updates",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Current version frame
        version_frame = ttk.LabelFrame(main_frame, text="Current Version")
        version_frame.pack(fill=tk.X, pady=(0, 20))
        
        version_info_frame = ttk.Frame(version_frame)
        version_info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.current_version_label = ttk.Label(version_info_frame, text="Version: Unknown")
        self.current_version_label.pack(side=tk.LEFT)
        
        self.last_update_label = ttk.Label(version_info_frame, text="Last Update: Unknown")
        self.last_update_label.pack(side=tk.RIGHT)
        
        # Available updates frame
        updates_frame = ttk.LabelFrame(main_frame, text="Available Updates")
        updates_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Updates list
        updates_list_frame = ttk.Frame(updates_frame)
        updates_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.updates_tree = ttk.Treeview(updates_list_frame, columns=(
            'version', 'release_date', 'size', 'description', 'status'
        ), show='headings', height=8)
        
        self.updates_tree.heading('version', text='Version')
        self.updates_tree.heading('release_date', text='Release Date')
        self.updates_tree.heading('size', text='Size')
        self.updates_tree.heading('description', text='Description')
        self.updates_tree.heading('status', text='Status')
        
        self.updates_tree.column('version', width=100)
        self.updates_tree.column('release_date', width=120)
        self.updates_tree.column('size', width=80)
        self.updates_tree.column('description', width=300)
        self.updates_tree.column('status', width=100)
        
        updates_scrollbar = ttk.Scrollbar(updates_list_frame, orient=tk.VERTICAL, command=self.updates_tree.yview)
        self.updates_tree.configure(yscrollcommand=updates_scrollbar.set)
        
        self.updates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        updates_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update controls frame
        controls_frame = ttk.Frame(updates_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(controls_frame, text="Check for Updates", command=self.check_for_updates).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Install Selected", command=self.install_selected_update).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Rollback", command=self.rollback_update).pack(side=tk.LEFT)
        
        # Update progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Update Progress")
        progress_frame.pack(fill=tk.X)
        
        self.update_progress = ProgressBar(progress_frame, width=400)
        self.update_progress.pack(padx=10, pady=10)
        
        self.update_status_label = ttk.Label(progress_frame, text="Ready")
        self.update_status_label.pack(pady=(0, 10))
    
    def start_monitoring(self) -> None:
        """Start periodic monitoring"""
        self.monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self.update_appliance_status()
                self.update_dashboard_metrics()
                self.update_manifests_list()
                time.sleep(self.update_interval / 1000.0)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5.0)
    
    def update_appliance_status(self) -> None:
        """Update appliance status information"""
        try:
            # Make API request to get appliance status
            response = self.http_client.get(f"{self.node_api_url}/api/admin/status")
            if response.status_code == 200:
                data = response.json()
                self.appliance_info = ApplianceInfo(**data)
                self._update_status_display()
            else:
                self.admin_status = AdminStatus.ERROR
                self._update_status_display()
        except Exception as e:
            logger.error(f"Failed to update appliance status: {e}")
            self.admin_status = AdminStatus.DISCONNECTED
            self._update_status_display()
    
    def _update_status_display(self) -> None:
        """Update status display in GUI"""
        if self.appliance_info:
            status_text = f"Connected to {self.appliance_info.hostname}"
            status_type = "success" if self.appliance_info.status == ApplianceStatus.ONLINE else "warning"
            
            # Update status bar
            self.status_bar.set_status(status_type, status_text)
            
            # Update dashboard status
            if hasattr(self, 'appliance_status_label'):
                self.appliance_status_label.set_status(
                    status_type, 
                    f"Status: {self.appliance_info.status.value.title()}"
                )
            
            if hasattr(self, 'ledger_mode_label'):
                self.ledger_mode_label.set_status(
                    "info", 
                    f"Ledger: {self.appliance_info.ledger_mode.value.title()}"
                )
            
            if hasattr(self, 'uptime_label'):
                uptime_str = self._format_uptime(self.appliance_info.uptime_seconds)
                self.uptime_label.configure(text=f"Uptime: {uptime_str}")
            
            if hasattr(self, 'sessions_label'):
                self.sessions_label.configure(
                    text=f"Sessions: {self.appliance_info.active_sessions}/{self.appliance_info.total_sessions}"
                )
        else:
            self.status_bar.set_status("error", "Disconnected")
    
    def update_dashboard_metrics(self) -> None:
        """Update dashboard metrics"""
        try:
            response = self.http_client.get(f"{self.node_api_url}/api/admin/metrics")
            if response.status_code == 200:
                metrics = response.json()
                
                # Update progress bars
                if hasattr(self, 'cpu_progress'):
                    self.cpu_progress.set_progress(metrics.get('cpu_percent', 0))
                
                if hasattr(self, 'memory_progress'):
                    self.memory_progress.set_progress(metrics.get('memory_percent', 0))
                
                if hasattr(self, 'disk_progress'):
                    self.disk_progress.set_progress(metrics.get('disk_percent', 0))
                
                # Update network label
                if hasattr(self, 'network_label'):
                    network_sent = metrics.get('network_sent_kbps', 0)
                    network_recv = metrics.get('network_recv_kbps', 0)
                    self.network_label.configure(
                        text=f"{network_recv:.1f} KB/s ↑ {network_sent:.1f} KB/s ↓"
                    )
        except Exception as e:
            logger.error(f"Failed to update dashboard metrics: {e}")
    
    def update_manifests_list(self) -> None:
        """Update session manifests list"""
        try:
            response = self.http_client.get(f"{self.node_api_url}/api/admin/manifests")
            if response.status_code == 200:
                manifests = response.json()
                self._populate_manifests_tree(manifests)
        except Exception as e:
            logger.error(f"Failed to update manifests list: {e}")
    
    def _populate_manifests_tree(self, manifests: List[Dict[str, Any]]) -> None:
        """Populate manifests tree with data"""
        if not hasattr(self, 'manifests_tree'):
            return
        
        # Clear existing items
        for item in self.manifests_tree.get_children():
            self.manifests_tree.delete(item)
        
        # Add new items
        for manifest in manifests:
            duration = self._calculate_duration(manifest.get('started_at'), manifest.get('ended_at'))
            self.manifests_tree.insert('', 'end', values=(
                manifest.get('session_id', '')[:16] + '...',
                manifest.get('started_at', ''),
                duration,
                len(manifest.get('participants', [])),
                manifest.get('chunk_count', 0),
                manifest.get('status', 'unknown')
            ))
    
    def bootstrap_wizard(self) -> None:
        """Open bootstrap wizard dialog"""
        dialog = BootstrapDialog(self.root, self._on_bootstrap_complete)
        dialog.show()
    
    def _on_bootstrap_complete(self, config: BootstrapConfig) -> None:
        """Handle bootstrap completion"""
        self.log_bootstrap_message("Starting appliance bootstrap...")
        
        def bootstrap_async():
            try:
                # Send bootstrap request
                response = self.http_client.post(
                    f"{self.node_api_url}/api/admin/bootstrap",
                    json=config.to_dict()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.log_bootstrap_message(f"Bootstrap successful: {result.get('appliance_id')}")
                    self.log_bootstrap_message("Appliance is now online and ready for use.")
                else:
                    self.log_bootstrap_message(f"Bootstrap failed: {response.text}")
            except Exception as e:
                self.log_bootstrap_message(f"Bootstrap error: {e}")
        
        threading.Thread(target=bootstrap_async, daemon=True).start()
    
    def connect_appliance_dialog(self) -> None:
        """Open connect to appliance dialog"""
        dialog = ConnectDialog(self.root, self._on_connect_complete)
        dialog.show()
    
    def _on_connect_complete(self, connection_info: Dict[str, Any]) -> None:
        """Handle connection completion"""
        self.node_api_url = connection_info['api_url']
        self.admin_status = AdminStatus.CONNECTING
        self._update_status_display()
    
    def disconnect_appliance(self) -> None:
        """Disconnect from appliance"""
        self.admin_status = AdminStatus.DISCONNECTED
        self.appliance_info = None
        self._update_status_display()
        self.log_bootstrap_message("Disconnected from appliance")
    
    def switch_ledger_mode(self) -> None:
        """Switch ledger mode dialog"""
        dialog = LedgerModeDialog(self.root, self.current_ledger_mode, self._on_ledger_mode_changed)
        dialog.show()
    
    def _on_ledger_mode_changed(self, new_mode: LedgerMode) -> None:
        """Handle ledger mode change"""
        try:
            response = self.http_client.post(
                f"{self.node_api_url}/api/admin/ledger-mode",
                json={'mode': new_mode.value}
            )
            
            if response.status_code == 200:
                self.current_ledger_mode = new_mode
                self.log_bootstrap_message(f"Ledger mode switched to {new_mode.value}")
            else:
                messagebox.showerror("Error", f"Failed to switch ledger mode: {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to switch ledger mode: {e}")
    
    def restart_services(self) -> None:
        """Restart appliance services"""
        if messagebox.askyesno("Confirm", "Are you sure you want to restart all services?"):
            try:
                response = self.http_client.post(f"{self.node_api_url}/api/admin/restart")
                if response.status_code == 200:
                    self.log_bootstrap_message("Services restart initiated")
                else:
                    messagebox.showerror("Error", f"Failed to restart services: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restart services: {e}")
    
    def shutdown_appliance(self) -> None:
        """Shutdown appliance"""
        if messagebox.askyesno("Confirm", "Are you sure you want to shutdown the appliance?"):
            try:
                response = self.http_client.post(f"{self.node_api_url}/api/admin/shutdown")
                if response.status_code == 200:
                    self.log_bootstrap_message("Appliance shutdown initiated")
                    self.disconnect_appliance()
                else:
                    messagebox.showerror("Error", f"Failed to shutdown appliance: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to shutdown appliance: {e}")
    
    def check_for_updates(self) -> None:
        """Check for available updates"""
        self.update_status_label.configure(text="Checking for updates...")
        
        def check_async():
            try:
                response = self.http_client.get(f"{self.node_api_url}/api/admin/updates")
                if response.status_code == 200:
                    updates = response.json()
                    self._populate_updates_tree(updates)
                    self.update_status_label.configure(text=f"Found {len(updates)} updates")
                else:
                    self.update_status_label.configure(text="Failed to check for updates")
            except Exception as e:
                self.update_status_label.configure(text=f"Error: {e}")
        
        threading.Thread(target=check_async, daemon=True).start()
    
    def _populate_updates_tree(self, updates: List[Dict[str, Any]]) -> None:
        """Populate updates tree with available updates"""
        if not hasattr(self, 'updates_tree'):
            return
        
        # Clear existing items
        for item in self.updates_tree.get_children():
            self.updates_tree.delete(item)
        
        # Add new items
        for update in updates:
            self.updates_tree.insert('', 'end', values=(
                update.get('version', ''),
                update.get('release_date', ''),
                self._format_bytes(update.get('size', 0)),
                update.get('description', ''),
                update.get('status', 'available')
            ))
    
    def install_selected_update(self) -> None:
        """Install selected update"""
        selection = self.updates_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an update to install")
            return
        
        item = self.updates_tree.item(selection[0])
        version = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Install update {version}?"):
            self._install_update(version)
    
    def _install_update(self, version: str) -> None:
        """Install specific update version"""
        self.update_status_label.configure(text=f"Installing update {version}...")
        self.update_progress.set_progress(0)
        
        def install_async():
            try:
                response = self.http_client.post(
                    f"{self.node_api_url}/api/admin/updates/install",
                    json={'version': version}
                )
                
                if response.status_code == 200:
                    # Monitor installation progress
                    self._monitor_update_progress()
                else:
                    self.update_status_label.configure(text=f"Installation failed: {response.text}")
            except Exception as e:
                self.update_status_label.configure(text=f"Installation error: {e}")
        
        threading.Thread(target=install_async, daemon=True).start()
    
    def _monitor_update_progress(self) -> None:
        """Monitor update installation progress"""
        def monitor():
            while True:
                try:
                    response = self.http_client.get(f"{self.node_api_url}/api/admin/updates/progress")
                    if response.status_code == 200:
                        progress = response.json()
                        self.update_progress.set_progress(progress.get('percent', 0))
                        self.update_status_label.configure(text=progress.get('status', 'Installing...'))
                        
                        if progress.get('completed', False):
                            break
                    time.sleep(1)
                except Exception as e:
                    self.update_status_label.configure(text=f"Progress error: {e}")
                    break
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def rollback_update(self) -> None:
        """Rollback to previous version"""
        if messagebox.askyesno("Confirm", "Rollback to previous version?"):
            try:
                response = self.http_client.post(f"{self.node_api_url}/api/admin/updates/rollback")
                if response.status_code == 200:
                    self.update_status_label.configure(text="Rollback initiated")
                else:
                    messagebox.showerror("Error", f"Failed to rollback: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rollback: {e}")
    
    def refresh_manifests(self) -> None:
        """Refresh manifests list"""
        self.update_manifests_list()
    
    def filter_manifests(self, *args) -> None:
        """Filter manifests based on search criteria"""
        # Implementation would filter the tree based on search terms
        pass
    
    def export_selected_manifests(self) -> None:
        """Export selected manifests"""
        selection = self.manifests_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select manifests to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Manifests",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Get selected manifest data and export
                manifests_data = []
                for item_id in selection:
                    item = self.manifests_tree.item(item_id)
                    manifests_data.append(item['values'])
                
                with open(filename, 'w') as f:
                    json.dump(manifests_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Exported {len(manifests_data)} manifests to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export manifests: {e}")
    
    def view_manifest_details(self, event) -> None:
        """View detailed manifest information"""
        selection = self.manifests_tree.selection()
        if not selection:
            return
        
        item = self.manifests_tree.item(selection[0])
        session_id = item['values'][0]
        
        # Fetch detailed manifest data
        try:
            response = self.http_client.get(f"{self.node_api_url}/api/admin/manifests/{session_id}")
            if response.status_code == 200:
                manifest = response.json()
                self._display_manifest_details(manifest)
        except Exception as e:
            logger.error(f"Failed to fetch manifest details: {e}")
    
    def _display_manifest_details(self, manifest: Dict[str, Any]) -> None:
        """Display detailed manifest information"""
        if not hasattr(self, 'manifest_details_text'):
            return
        
        self.manifest_details_text.configure(state=tk.NORMAL)
        self.manifest_details_text.delete(1.0, tk.END)
        
        # Format manifest data
        details = json.dumps(manifest, indent=2)
        self.manifest_details_text.insert(1.0, details)
        self.manifest_details_text.configure(state=tk.DISABLED)
    
    def clear_bootstrap_log(self) -> None:
        """Clear bootstrap log"""
        if hasattr(self, 'bootstrap_status_text'):
            self.bootstrap_status_text.configure(state=tk.NORMAL)
            self.bootstrap_status_text.delete(1.0, tk.END)
            self.bootstrap_status_text.configure(state=tk.DISABLED)
    
    def export_bootstrap_log(self) -> None:
        """Export bootstrap log"""
        if not hasattr(self, 'bootstrap_status_text'):
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Bootstrap Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                content = self.bootstrap_status_text.get(1.0, tk.END)
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Bootstrap log exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export log: {e}")
    
    def log_bootstrap_message(self, message: str) -> None:
        """Log message to bootstrap status"""
        if hasattr(self, 'bootstrap_status_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            self.bootstrap_status_text.configure(state=tk.NORMAL)
            self.bootstrap_status_text.insert(tk.END, log_message)
            self.bootstrap_status_text.see(tk.END)
            self.bootstrap_status_text.configure(state=tk.DISABLED)
    
    def export_configuration(self) -> None:
        """Export current configuration"""
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                config_data = {
                    'appliance_info': self.appliance_info.to_dict() if self.appliance_info else None,
                    'ledger_mode': self.current_ledger_mode.value,
                    'admin_status': self.admin_status.value,
                    'node_api_url': self.node_api_url
                }
                
                with open(filename, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Configuration exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {e}")
    
    def import_configuration(self) -> None:
        """Import configuration"""
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    config_data = json.load(f)
                
                # Apply configuration
                if config_data.get('ledger_mode'):
                    self.current_ledger_mode = LedgerMode(config_data['ledger_mode'])
                
                if config_data.get('node_api_url'):
                    self.node_api_url = config_data['node_api_url']
                
                messagebox.showinfo("Success", "Configuration imported successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration: {e}")
    
    def open_session_explorer(self) -> None:
        """Open session explorer window"""
        messagebox.showinfo("Info", "Session explorer functionality would be implemented here")
    
    def open_blockchain_explorer(self) -> None:
        """Open blockchain explorer window"""
        messagebox.showinfo("Info", "Blockchain explorer functionality would be implemented here")
    
    def check_tor_status(self) -> None:
        """Check Tor network status"""
        messagebox.showinfo("Info", "Tor network status functionality would be implemented here")
    
    def show_documentation(self) -> None:
        """Show documentation"""
        messagebox.showinfo("Info", "Documentation functionality would be implemented here")
    
    def show_about(self) -> None:
        """Show about dialog"""
        about_text = """Lucid RDP Admin Interface v1.0.0

A Tor-only, blockchain-anchored remote desktop platform.

Features:
• Bootstrap wizard for new appliances
• Session manifest management
• Payout and wallet management
• Key rotation and backup
• System diagnostics
• OTA updates

For more information, visit the documentation."""
        
        messagebox.showinfo("About Lucid RDP Admin", about_text)
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in human readable format"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def _calculate_duration(self, started_at: str, ended_at: Optional[str]) -> str:
        """Calculate session duration"""
        try:
            start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            if ended_at:
                end = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
                duration = end - start
                return str(duration).split('.')[0]  # Remove microseconds
            else:
                return "Active"
        except Exception:
            return "Unknown"
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.monitoring_active = False
        
        # Cleanup component managers
        if self.backup_manager:
            self.backup_manager.cleanup()
        if self.diagnostics_manager:
            self.diagnostics_manager.stop_monitoring()
        if self.key_manager:
            self.key_manager.cleanup()
        if self.payouts_manager:
            self.payouts_manager.cleanup()
        
        # Close HTTP client
        if hasattr(self, 'http_client'):
            self.http_client.close()
        
        logger.info("Admin GUI cleanup completed")


class BootstrapDialog:
    """Bootstrap wizard dialog"""
    
    def __init__(self, parent: tk.Widget, on_complete: Callable[[BootstrapConfig], None]):
        self.parent = parent
        self.on_complete = on_complete
        self.dialog = None
        self.config = BootstrapConfig(
            appliance_name="",
            admin_email="",
            admin_password="",
            ledger_mode=LedgerMode.SANDBOX
        )
    
    def show(self) -> None:
        """Show bootstrap dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Bootstrap New Appliance")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self._create_dialog_content()
    
    def _create_dialog_content(self) -> None:
        """Create dialog content"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Bootstrap New Appliance",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Form fields
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)
        
        # Appliance name
        ttk.Label(fields_frame, text="Appliance Name:").pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(fields_frame, textvariable=self.name_var, width=40)
        name_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Admin email
        ttk.Label(fields_frame, text="Admin Email:").pack(anchor=tk.W, pady=(0, 5))
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(fields_frame, textvariable=self.email_var, width=40)
        email_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Admin password
        ttk.Label(fields_frame, text="Admin Password:").pack(anchor=tk.W, pady=(0, 5))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(fields_frame, textvariable=self.password_var, show="*", width=40)
        password_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Ledger mode
        ttk.Label(fields_frame, text="Ledger Mode:").pack(anchor=tk.W, pady=(0, 5))
        self.ledger_var = tk.StringVar(value=LedgerMode.SANDBOX.value)
        ledger_combo = ttk.Combobox(
            fields_frame,
            textvariable=self.ledger_var,
            values=[mode.value for mode in LedgerMode],
            state="readonly",
            width=37
        )
        ledger_combo.pack(fill=tk.X, pady=(0, 15))
        
        # Options frame
        options_frame = ttk.LabelFrame(fields_frame, text="Options")
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.tor_service_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Enable Tor Onion Service",
            variable=self.tor_service_var
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        self.auto_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Enable Auto Backup",
            variable=self.auto_backup_var
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            buttons_frame,
            text="Bootstrap",
            command=self._bootstrap,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT)
    
    def _bootstrap(self) -> None:
        """Handle bootstrap button click"""
        if not self.name_var.get().strip():
            messagebox.showerror("Error", "Appliance name is required")
            return
        
        if not self.email_var.get().strip():
            messagebox.showerror("Error", "Admin email is required")
            return
        
        if not self.password_var.get().strip():
            messagebox.showerror("Error", "Admin password is required")
            return
        
        # Create config
        config = BootstrapConfig(
            appliance_name=self.name_var.get().strip(),
            admin_email=self.email_var.get().strip(),
            admin_password=self.password_var.get().strip(),
            ledger_mode=LedgerMode(self.ledger_var.get()),
            tor_onion_service=self.tor_service_var.get(),
            auto_backup_enabled=self.auto_backup_var.get()
        )
        
        self.dialog.destroy()
        self.on_complete(config)
    
    def _cancel(self) -> None:
        """Handle cancel button click"""
        self.dialog.destroy()


class ConnectDialog:
    """Connect to existing appliance dialog"""
    
    def __init__(self, parent: tk.Widget, on_complete: Callable[[Dict[str, Any]], None]):
        self.parent = parent
        self.on_complete = on_complete
        self.dialog = None
    
    def show(self) -> None:
        """Show connect dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Connect to Appliance")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 100,
            self.parent.winfo_rooty() + 100
        ))
        
        self._create_dialog_content()
    
    def _create_dialog_content(self) -> None:
        """Create dialog content"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Connect to Existing Appliance",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Form fields
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)
        
        # API URL
        ttk.Label(fields_frame, text="Appliance API URL:").pack(anchor=tk.W, pady=(0, 5))
        self.api_url_var = tk.StringVar(value="http://localhost:8080")
        api_url_entry = ttk.Entry(fields_frame, textvariable=self.api_url_var, width=40)
        api_url_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Admin credentials
        ttk.Label(fields_frame, text="Admin Email:").pack(anchor=tk.W, pady=(0, 5))
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(fields_frame, textvariable=self.email_var, width=40)
        email_entry.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(fields_frame, text="Admin Password:").pack(anchor=tk.W, pady=(0, 5))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(fields_frame, textvariable=self.password_var, show="*", width=40)
        password_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            buttons_frame,
            text="Connect",
            command=self._connect,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT)
    
    def _connect(self) -> None:
        """Handle connect button click"""
        if not self.api_url_var.get().strip():
            messagebox.showerror("Error", "API URL is required")
            return
        
        # Get connection info
        connection_info = {
            'api_url': self.api_url_var.get().strip(),
            'admin_email': self.email_var.get().strip(),
            'admin_password': self.password_var.get().strip()
        }
        
        self.dialog.destroy()
        self.on_complete(connection_info)
    
    def _cancel(self) -> None:
        """Handle cancel button click"""
        self.dialog.destroy()


class LedgerModeDialog:
    """Ledger mode switching dialog"""
    
    def __init__(self, parent: tk.Widget, current_mode: LedgerMode, on_complete: Callable[[LedgerMode], None]):
        self.parent = parent
        self.current_mode = current_mode
        self.on_complete = on_complete
        self.dialog = None
    
    def show(self) -> None:
        """Show ledger mode dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Switch Ledger Mode")
        self.dialog.geometry("400x250")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 150,
            self.parent.winfo_rooty() + 100
        ))
        
        self._create_dialog_content()
    
    def _create_dialog_content(self) -> None:
        """Create dialog content"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Switch Ledger Mode",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Warning message
        warning_text = """
WARNING: Changing ledger mode will affect all blockchain operations.

• Sandbox Mode: Uses TRON Shasta testnet (for testing)
• Production Mode: Uses TRON Mainnet (real transactions)

This action cannot be undone without a system restore.
        """
        
        warning_label = ttk.Label(
            main_frame,
            text=warning_text.strip(),
            font=('Arial', 9),
            foreground='red'
        )
        warning_label.pack(pady=(0, 20))
        
        # Mode selection
        mode_frame = ttk.LabelFrame(main_frame, text="Select Ledger Mode")
        mode_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.mode_var = tk.StringVar(value=self.current_mode.value)
        
        sandbox_radio = ttk.Radiobutton(
            mode_frame,
            text="Sandbox (Testnet)",
            variable=self.mode_var,
            value=LedgerMode.SANDBOX.value
        )
        sandbox_radio.pack(anchor=tk.W, padx=10, pady=5)
        
        production_radio = ttk.Radiobutton(
            mode_frame,
            text="Production (Mainnet)",
            variable=self.mode_var,
            value=LedgerMode.PRODUCTION.value
        )
        production_radio.pack(anchor=tk.W, padx=10, pady=5)
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            buttons_frame,
            text="Switch Mode",
            command=self._switch_mode,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT)
    
    def _switch_mode(self) -> None:
        """Handle mode switch"""
        new_mode = LedgerMode(self.mode_var.get())
        
        if new_mode == self.current_mode:
            messagebox.showinfo("Info", "Selected mode is already active")
            return
        
        confirm_msg = f"Are you sure you want to switch to {new_mode.value} mode?"
        if new_mode == LedgerMode.PRODUCTION:
            confirm_msg += "\n\nThis will use the live TRON Mainnet!"
        
        if messagebox.askyesno("Confirm Mode Switch", confirm_msg):
            self.dialog.destroy()
            self.on_complete(new_mode)
    
    def _cancel(self) -> None:
        """Handle cancel button click"""
        self.dialog.destroy()


# Import the new bootstrap wizard
try:
    from .bootstrap_wizard import BootstrapWizard, BootstrapConfig, configure_bootstrap_for_docker
    BOOTSTRAP_WIZARD_AVAILABLE = True
except ImportError:
    BOOTSTRAP_WIZARD_AVAILABLE = False
    logger.warning("Bootstrap wizard not available")


class AdminGUI:
    """Main admin interface for Lucid RDP appliance management"""
    
    def __init__(self, root: tk.Tk, node_api_url: str = "http://localhost:8080"):
        self.root = root
        self.node_api_url = node_api_url.rstrip('/')
        self.update_interval = 5000  # 5 seconds
        
        # Current state
        self.admin_status = AdminStatus.DISCONNECTED
        self.appliance_info: Optional[ApplianceInfo] = None
        self.current_ledger_mode = LedgerMode.SANDBOX
        
        # Component managers
        self.backup_manager: Optional[BackupManager] = None
        self.diagnostics_manager: Optional[DiagnosticManager] = None
        self.key_manager: Optional[KeyManager] = None
        self.payouts_manager: Optional[PayoutsManager] = None
        
        # GUI components
        self.notebook: Optional[ttk.Notebook] = None
        self.status_bar: Optional[StatusLabel] = None
        self.monitoring_active = False
        
        # Docker environment configuration
        self.docker_config = self._load_docker_config()
        
        # Setup networking and core components
        self.setup_networking()
        self.setup_gui()
        self.setup_menu()
        
        # Start monitoring
        self.start_monitoring()
        
        logger.info("Admin GUI initialized")
    
    def _load_docker_config(self) -> Dict[str, Any]:
        """Load Docker environment configuration from distroless container environment"""
        # Default configuration for distroless container
        docker_config = {
            # Core service URLs from Docker environment
            'api_url': os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:8080'),
            'api_gateway_url': os.environ.get('API_GATEWAY_URL', 'http://localhost:8080'),
            'admin_port': int(os.environ.get('PORT', '3000')),
            
            # Database configuration
            'mongo_url': os.environ.get('MONGO_URL', 'mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false'),
            'mongo_db': os.environ.get('MONGO_DB', 'lucid'),
            
            # Blockchain configuration
            'tron_network': os.environ.get('TRON_NETWORK', 'shasta'),
            'tron_rpc': os.environ.get('TRON_HTTP_ENDPOINT', 'https://api.shasta.trongrid.io'),
            'tron_api_key': os.environ.get('TRONGRID_API_KEY', ''),
            'block_onion': os.environ.get('BLOCK_ONION', ''),
            'block_rpc_url': os.environ.get('BLOCK_RPC_URL', ''),
            
            # Tor configuration
            'tor_socks': os.environ.get('TOR_SOCKS', 'tor-proxy:9050'),
            'tor_control_port': os.environ.get('TOR_CONTROL_PORT', 'tor-proxy:9051'),
            'tor_control_password': os.environ.get('TOR_CONTROL_PASSWORD', ''),
            
            # Onion service addresses
            'onion_api_gateway': os.environ.get('ONION_API_GATEWAY', ''),
            'onion_api_server': os.environ.get('ONION_API_SERVER', ''),
            'onion_tunnel': os.environ.get('ONION_TUNNEL', ''),
            'onion_mongo': os.environ.get('ONION_MONGO', ''),
            
            # Security configuration
            'age_private_key': os.environ.get('AGE_PRIVATE_KEY', ''),
            'key_enc_secret': os.environ.get('KEY_ENC_SECRET', ''),
            
            # Environment settings
            'lucid_env': os.environ.get('LUCID_ENV', 'dev'),
            'lucid_plane': os.environ.get('LUCID_PLANE', 'ops'),
            'lucid_cluster_id': os.environ.get('LUCID_CLUSTER_ID', 'dev-core'),
            'debug_mode': os.environ.get('LUCID_ENV', 'dev') != 'production',
            'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
            
            # Dynamic onion support
            'onion_dir': os.environ.get('ONION_DIR', '/run/lucid/onion'),
            'dynamic_onion_support': os.environ.get('DYNAMIC_ONION_SUPPORT', 'enabled'),
            'wallet_onion_support': os.environ.get('WALLET_ONION_SUPPORT', 'enabled')
        }
        
        logger.info(f"Docker configuration loaded: {docker_config}")
        return docker_config
    
    def setup_networking(self) -> None:
        """Setup networking components with Docker configuration"""
        try:
            # Build allowed onions list from Docker environment
            allowed_onions = []
            
            # Add configured onion addresses from Docker environment
            onion_configs = [
                self.docker_config.get('onion_api_gateway'),
                self.docker_config.get('onion_api_server'),
                self.docker_config.get('onion_tunnel'),
                self.docker_config.get('onion_mongo'),
                self.docker_config.get('block_onion')
            ]
            
            for onion in onion_configs:
                if onion and onion.strip():
                    allowed_onions.append(onion.strip())
            
            # Add default onions if none configured
            if not allowed_onions:
                allowed_onions = [
                    "lucid-admin.onion",  # Default admin onion
                    "lucid-node.onion"    # Default node onion
                ]
            
            # Security configuration for admin interface
            self.security_config = SecurityConfig(
                allowed_onions=allowed_onions,
                certificate_pinning=True,
                connection_timeout=int(os.environ.get('NETWORK_TIMEOUT', '30')),
                read_timeout=int(os.environ.get('NETWORK_READ_TIMEOUT', '60')),
                max_retries=int(os.environ.get('NETWORK_RETRY_ATTEMPTS', '3')),
                verify_ssl=os.environ.get('VERIFY_SSL', 'true').lower() == 'true'
            )
            
            # Create Tor HTTP client
            self.http_client = TorHttpClient(self.security_config)
            
            # Update API URL from Docker config
            if self.docker_config.get('api_url'):
                self.node_api_url = self.docker_config['api_url']
            elif self.docker_config.get('api_gateway_url'):
                self.node_api_url = self.docker_config['api_gateway_url']
            
            logger.info(f"Networking setup completed with API URL: {self.node_api_url}")
            logger.info(f"Allowed onions: {allowed_onions}")
        except Exception as e:
            logger.error(f"Failed to setup networking: {e}")
            messagebox.showerror("Network Error", f"Failed to setup networking: {e}")
    
    def setup_gui(self) -> None:
        """Setup the main GUI interface"""
        self.root.title("Lucid RDP - Admin Interface")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_bootstrap_tab()
        self.create_dashboard_tab()
        self.create_manifests_tab()
        self.create_payouts_tab()
        self.create_keys_tab()
        self.create_backups_tab()
        self.create_diagnostics_tab()
        self.create_ota_tab()
        
        # Status bar
        self.status_bar = StatusLabel(
            self.root,
            text="Disconnected",
            status="error"
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Apply theme
        theme_manager = get_theme_manager()
        theme_manager.apply_theme_to_window(self.root)
        
        logger.info("GUI setup completed")
    
    def setup_menu(self) -> None:
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect Appliance...", command=self.connect_appliance_dialog)
        file_menu.add_command(label="Disconnect", command=self.disconnect_appliance)
        file_menu.add_separator()
        file_menu.add_command(label="Export Configuration...", command=self.export_configuration)
        file_menu.add_command(label="Import Configuration...", command=self.import_configuration)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Appliance menu
        appliance_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Appliance", menu=appliance_menu)
        appliance_menu.add_command(label="Bootstrap New...", command=self.bootstrap_wizard)
        appliance_menu.add_command(label="Switch Ledger Mode...", command=self.switch_ledger_mode)
        appliance_menu.add_command(label="Restart Services", command=self.restart_services)
        appliance_menu.add_command(label="Shutdown", command=self.shutdown_appliance)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Session Explorer", command=self.open_session_explorer)
        tools_menu.add_command(label="Blockchain Explorer", command=self.open_blockchain_explorer)
        tools_menu.add_command(label="Tor Network Status", command=self.check_tor_status)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_bootstrap_tab(self) -> None:
        """Create bootstrap wizard tab"""
        self.bootstrap_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bootstrap_frame, text="Bootstrap")
        
        # Main bootstrap container
        main_frame = ttk.Frame(self.bootstrap_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Lucid RDP Appliance Bootstrap",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Bootstrap options frame
        options_frame = ttk.LabelFrame(main_frame, text="Bootstrap Options")
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # New appliance button
        new_appliance_btn = ttk.Button(
            options_frame,
            text="Bootstrap New Appliance",
            command=self.bootstrap_wizard,
            style="Accent.TButton"
        )
        new_appliance_btn.pack(pady=10, padx=10, fill=tk.X)
        
        # Connect existing button
        connect_existing_btn = ttk.Button(
            options_frame,
            text="Connect to Existing Appliance",
            command=self.connect_appliance_dialog
        )
        connect_existing_btn.pack(pady=10, padx=10, fill=tk.X)
        
        # Bootstrap status frame
        status_frame = ttk.LabelFrame(main_frame, text="Bootstrap Status")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status text
        self.bootstrap_status_text = scrolledtext.ScrolledText(
            status_frame,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.bootstrap_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Quick actions frame
        actions_frame = ttk.Frame(status_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(actions_frame, text="Clear Log", command=self.clear_bootstrap_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Export Log", command=self.export_bootstrap_log).pack(side=tk.LEFT)
    
    def create_dashboard_tab(self) -> None:
        """Create dashboard tab"""
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        
        # Main dashboard container
        main_frame = ttk.Frame(self.dashboard_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Status overview frame
        status_frame = ttk.LabelFrame(main_frame, text="Appliance Status")
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Status grid
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Appliance info labels
        self.appliance_status_label = StatusLabel(status_grid, text="Status: Unknown", status="unknown")
        self.appliance_status_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        self.ledger_mode_label = StatusLabel(status_grid, text="Ledger: Unknown", status="unknown")
        self.ledger_mode_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        self.uptime_label = ttk.Label(status_grid, text="Uptime: Unknown")
        self.uptime_label.grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        
        self.sessions_label = ttk.Label(status_grid, text="Sessions: 0")
        self.sessions_label.grid(row=0, column=3, sticky=tk.W)
        
        # Metrics frame
        metrics_frame = ttk.LabelFrame(main_frame, text="System Metrics")
        metrics_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create metrics grid
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # CPU usage
        ttk.Label(metrics_grid, text="CPU Usage:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.cpu_progress = ProgressBar(metrics_grid, width=200)
        self.cpu_progress.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Memory usage
        ttk.Label(metrics_grid, text="Memory Usage:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.memory_progress = ProgressBar(metrics_grid, width=200)
        self.memory_progress.grid(row=1, column=1, sticky=tk.W, padx=(0, 20))
        
        # Disk usage
        ttk.Label(metrics_grid, text="Disk Usage:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.disk_progress = ProgressBar(metrics_grid, width=200)
        self.disk_progress.grid(row=2, column=1, sticky=tk.W, padx=(0, 20))
        
        # Network usage
        ttk.Label(metrics_grid, text="Network:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.network_label = ttk.Label(metrics_grid, text="0 KB/s ↑ 0 KB/s ↓")
        self.network_label.grid(row=3, column=1, sticky=tk.W)
        
        # Recent activity frame
        activity_frame = ttk.LabelFrame(main_frame, text="Recent Activity")
        activity_frame.pack(fill=tk.BOTH, expand=True)
        
        # Activity log
        self.activity_log = LogViewer(activity_frame, max_lines=100)
        self.activity_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_manifests_tab(self) -> None:
        """Create session manifests tab"""
        self.manifests_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manifests_frame, text="Manifests")
        
        # Main manifests container
        main_frame = ttk.Frame(self.manifests_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Search and filter controls
        ttk.Label(controls_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.manifest_search_var = tk.StringVar()
        self.manifest_search_var.trace('w', self.filter_manifests)
        search_entry = ttk.Entry(controls_frame, textvariable=self.manifest_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Filter by date
        ttk.Label(controls_frame, text="Date Range:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_filter_var = tk.StringVar(value="All")
        date_combo = ttk.Combobox(controls_frame, textvariable=self.date_filter_var, 
                                 values=["All", "Today", "This Week", "This Month"])
        date_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh button
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_manifests).pack(side=tk.LEFT, padx=(0, 10))
        
        # Export button
        ttk.Button(controls_frame, text="Export Selected", command=self.export_selected_manifests).pack(side=tk.LEFT)
        
        # Manifests tree
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with scrollbars
        self.manifests_tree = ttk.Treeview(tree_frame, columns=(
            'session_id', 'started_at', 'duration', 'participants', 'chunks', 'status'
        ), show='headings', height=15)
        
        # Configure columns
        self.manifests_tree.heading('session_id', text='Session ID')
        self.manifests_tree.heading('started_at', text='Started At')
        self.manifests_tree.heading('duration', text='Duration')
        self.manifests_tree.heading('participants', text='Participants')
        self.manifests_tree.heading('chunks', text='Chunks')
        self.manifests_tree.heading('status', text='Status')
        
        self.manifests_tree.column('session_id', width=200)
        self.manifests_tree.column('started_at', width=150)
        self.manifests_tree.column('duration', width=100)
        self.manifests_tree.column('participants', width=100)
        self.manifests_tree.column('chunks', width=80)
        self.manifests_tree.column('status', width=100)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.manifests_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.manifests_tree.xview)
        self.manifests_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tree and scrollbars
        self.manifests_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind double-click to view details
        self.manifests_tree.bind('<Double-1>', self.view_manifest_details)
        
        # Manifest details frame
        details_frame = ttk.LabelFrame(main_frame, text="Manifest Details")
        details_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.manifest_details_text = scrolledtext.ScrolledText(
            details_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.manifest_details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_payouts_tab(self) -> None:
        """Create payouts management tab"""
        self.payouts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.payouts_frame, text="Payouts")
        
        # Initialize payouts manager
        self.payouts_manager = PayoutsManager(self.payouts_frame, self.node_api_url)
    
    def create_keys_tab(self) -> None:
        """Create key management tab"""
        self.keys_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.keys_frame, text="Keys")
        
        # Initialize key manager
        self.key_manager = KeyManager(self.keys_frame, self.node_api_url)
    
    def create_backups_tab(self) -> None:
        """Create backup and restore tab"""
        self.backups_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.backups_frame, text="Backups")
        
        # Initialize backup manager
        self.backup_manager = BackupManager(self.backups_frame, self.node_api_url)
    
    def create_diagnostics_tab(self) -> None:
        """Create diagnostics tab"""
        self.diagnostics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.diagnostics_frame, text="Diagnostics")
        
        # Initialize diagnostics manager
        self.diagnostics_manager = DiagnosticManager(self.diagnostics_frame, self.node_api_url)
    
    def create_ota_tab(self) -> None:
        """Create OTA updates tab"""
        self.ota_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ota_frame, text="OTA Updates")
        
        # Main OTA container
        main_frame = ttk.Frame(self.ota_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Over-The-Air Updates",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Current version frame
        version_frame = ttk.LabelFrame(main_frame, text="Current Version")
        version_frame.pack(fill=tk.X, pady=(0, 20))
        
        version_info_frame = ttk.Frame(version_frame)
        version_info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.current_version_label = ttk.Label(version_info_frame, text="Version: Unknown")
        self.current_version_label.pack(side=tk.LEFT)
        
        self.last_update_label = ttk.Label(version_info_frame, text="Last Update: Unknown")
        self.last_update_label.pack(side=tk.RIGHT)
        
        # Available updates frame
        updates_frame = ttk.LabelFrame(main_frame, text="Available Updates")
        updates_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Updates list
        updates_list_frame = ttk.Frame(updates_frame)
        updates_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.updates_tree = ttk.Treeview(updates_list_frame, columns=(
            'version', 'release_date', 'size', 'description', 'status'
        ), show='headings', height=8)
        
        self.updates_tree.heading('version', text='Version')
        self.updates_tree.heading('release_date', text='Release Date')
        self.updates_tree.heading('size', text='Size')
        self.updates_tree.heading('description', text='Description')
        self.updates_tree.heading('status', text='Status')
        
        self.updates_tree.column('version', width=100)
        self.updates_tree.column('release_date', width=120)
        self.updates_tree.column('size', width=80)
        self.updates_tree.column('description', width=300)
        self.updates_tree.column('status', width=100)
        
        updates_scrollbar = ttk.Scrollbar(updates_list_frame, orient=tk.VERTICAL, command=self.updates_tree.yview)
        self.updates_tree.configure(yscrollcommand=updates_scrollbar.set)
        
        self.updates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        updates_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update controls frame
        controls_frame = ttk.Frame(updates_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(controls_frame, text="Check for Updates", command=self.check_for_updates).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Install Selected", command=self.install_selected_update).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Rollback", command=self.rollback_update).pack(side=tk.LEFT)
        
        # Update progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Update Progress")
        progress_frame.pack(fill=tk.X)
        
        self.update_progress = ProgressBar(progress_frame, width=400)
        self.update_progress.pack(padx=10, pady=10)
        
        self.update_status_label = ttk.Label(progress_frame, text="Ready")
        self.update_status_label.pack(pady=(0, 10))
    
    def start_monitoring(self) -> None:
        """Start periodic monitoring"""
        self.monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self.update_appliance_status()
                self.update_dashboard_metrics()
                self.update_manifests_list()
                time.sleep(self.update_interval / 1000.0)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5.0)
    
    def update_appliance_status(self) -> None:
        """Update appliance status information"""
        try:
            # Make API request to get appliance status
            response = self.http_client.get(f"{self.node_api_url}/api/admin/status")
            if response.status_code == 200:
                data = response.json()
                self.appliance_info = ApplianceInfo(**data)
                self._update_status_display()
            else:
                self.admin_status = AdminStatus.ERROR
                self._update_status_display()
        except Exception as e:
            logger.error(f"Failed to update appliance status: {e}")
            self.admin_status = AdminStatus.DISCONNECTED
            self._update_status_display()
    
    def _update_status_display(self) -> None:
        """Update status display in GUI"""
        if self.appliance_info:
            status_text = f"Connected to {self.appliance_info.hostname}"
            status_type = "success" if self.appliance_info.status == ApplianceStatus.ONLINE else "warning"
            
            # Update status bar
            self.status_bar.set_status(status_type, status_text)
            
            # Update dashboard status
            if hasattr(self, 'appliance_status_label'):
                self.appliance_status_label.set_status(
                    status_type, 
                    f"Status: {self.appliance_info.status.value.title()}"
                )
            
            if hasattr(self, 'ledger_mode_label'):
                self.ledger_mode_label.set_status(
                    "info", 
                    f"Ledger: {self.appliance_info.ledger_mode.value.title()}"
                )
            
            if hasattr(self, 'uptime_label'):
                uptime_str = self._format_uptime(self.appliance_info.uptime_seconds)
                self.uptime_label.configure(text=f"Uptime: {uptime_str}")
            
            if hasattr(self, 'sessions_label'):
                self.sessions_label.configure(
                    text=f"Sessions: {self.appliance_info.active_sessions}/{self.appliance_info.total_sessions}"
                )
        else:
            self.status_bar.set_status("error", "Disconnected")
    
    def update_dashboard_metrics(self) -> None:
        """Update dashboard metrics"""
        try:
            response = self.http_client.get(f"{self.node_api_url}/api/admin/metrics")
            if response.status_code == 200:
                metrics = response.json()
                
                # Update progress bars
                if hasattr(self, 'cpu_progress'):
                    self.cpu_progress.set_progress(metrics.get('cpu_percent', 0))
                
                if hasattr(self, 'memory_progress'):
                    self.memory_progress.set_progress(metrics.get('memory_percent', 0))
                
                if hasattr(self, 'disk_progress'):
                    self.disk_progress.set_progress(metrics.get('disk_percent', 0))
                
                # Update network label
                if hasattr(self, 'network_label'):
                    network_sent = metrics.get('network_sent_kbps', 0)
                    network_recv = metrics.get('network_recv_kbps', 0)
                    self.network_label.configure(
                        text=f"{network_recv:.1f} KB/s ↑ {network_sent:.1f} KB/s ↓"
                    )
        except Exception as e:
            logger.error(f"Failed to update dashboard metrics: {e}")
    
    def update_manifests_list(self) -> None:
        """Update session manifests list"""
        try:
            response = self.http_client.get(f"{self.node_api_url}/api/admin/manifests")
            if response.status_code == 200:
                manifests = response.json()
                self._populate_manifests_tree(manifests)
        except Exception as e:
            logger.error(f"Failed to update manifests list: {e}")
    
    def _populate_manifests_tree(self, manifests: List[Dict[str, Any]]) -> None:
        """Populate manifests tree with data"""
        if not hasattr(self, 'manifests_tree'):
            return
        
        # Clear existing items
        for item in self.manifests_tree.get_children():
            self.manifests_tree.delete(item)
        
        # Add new items
        for manifest in manifests:
            duration = self._calculate_duration(manifest.get('started_at'), manifest.get('ended_at'))
            self.manifests_tree.insert('', 'end', values=(
                manifest.get('session_id', '')[:16] + '...',
                manifest.get('started_at', ''),
                duration,
                len(manifest.get('participants', [])),
                manifest.get('chunk_count', 0),
                manifest.get('status', 'unknown')
            ))
    
    def bootstrap_wizard(self) -> None:
        """Open bootstrap wizard dialog"""
        if BOOTSTRAP_WIZARD_AVAILABLE:
            # Use the new enhanced bootstrap wizard
            wizard = BootstrapWizard(self.root, self._on_bootstrap_complete)
            wizard.show_wizard()
        else:
            # Fallback to simple dialog
            dialog = BootstrapDialog(self.root, self._on_bootstrap_complete)
            dialog.show()
    
    def _on_bootstrap_complete(self, config: BootstrapConfig) -> None:
        """Handle bootstrap completion"""
        self.log_bootstrap_message("Starting appliance bootstrap...")
        
        # Configure for Docker environment if available
        if BOOTSTRAP_WIZARD_AVAILABLE:
            configure_bootstrap_for_docker(config)
        
        def bootstrap_async():
            try:
                # Send bootstrap request
                response = self.http_client.post(
                    f"{self.node_api_url}/api/admin/bootstrap",
                    json=config.to_dict()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.log_bootstrap_message(f"Bootstrap successful: {result.get('appliance_id')}")
                    self.log_bootstrap_message("Appliance is now online and ready for use.")
                else:
                    self.log_bootstrap_message(f"Bootstrap failed: {response.text}")
            except Exception as e:
                self.log_bootstrap_message(f"Bootstrap error: {e}")
        
        threading.Thread(target=bootstrap_async, daemon=True).start()
    
    def connect_appliance_dialog(self) -> None:
        """Open connect to appliance dialog"""
        dialog = ConnectDialog(self.root, self._on_connect_complete)
        dialog.show()
    
    def _on_connect_complete(self, connection_info: Dict[str, Any]) -> None:
        """Handle connection completion"""
        self.node_api_url = connection_info['api_url']
        self.admin_status = AdminStatus.CONNECTING
        self._update_status_display()
    
    def disconnect_appliance(self) -> None:
        """Disconnect from appliance"""
        self.admin_status = AdminStatus.DISCONNECTED
        self.appliance_info = None
        self._update_status_display()
        self.log_bootstrap_message("Disconnected from appliance")
    
    def switch_ledger_mode(self) -> None:
        """Switch ledger mode dialog"""
        dialog = LedgerModeDialog(self.root, self.current_ledger_mode, self._on_ledger_mode_changed)
        dialog.show()
    
    def _on_ledger_mode_changed(self, new_mode: LedgerMode) -> None:
        """Handle ledger mode change"""
        try:
            response = self.http_client.post(
                f"{self.node_api_url}/api/admin/ledger-mode",
                json={'mode': new_mode.value}
            )
            
            if response.status_code == 200:
                self.current_ledger_mode = new_mode
                self.log_bootstrap_message(f"Ledger mode switched to {new_mode.value}")
            else:
                messagebox.showerror("Error", f"Failed to switch ledger mode: {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to switch ledger mode: {e}")
    
    def restart_services(self) -> None:
        """Restart appliance services"""
        if messagebox.askyesno("Confirm", "Are you sure you want to restart all services?"):
            try:
                response = self.http_client.post(f"{self.node_api_url}/api/admin/restart")
                if response.status_code == 200:
                    self.log_bootstrap_message("Services restart initiated")
                else:
                    messagebox.showerror("Error", f"Failed to restart services: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restart services: {e}")
    
    def shutdown_appliance(self) -> None:
        """Shutdown appliance"""
        if messagebox.askyesno("Confirm", "Are you sure you want to shutdown the appliance?"):
            try:
                response = self.http_client.post(f"{self.node_api_url}/api/admin/shutdown")
                if response.status_code == 200:
                    self.log_bootstrap_message("Appliance shutdown initiated")
                    self.disconnect_appliance()
                else:
                    messagebox.showerror("Error", f"Failed to shutdown appliance: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to shutdown appliance: {e}")
    
    def check_for_updates(self) -> None:
        """Check for available updates"""
        self.update_status_label.configure(text="Checking for updates...")
        
        def check_async():
            try:
                response = self.http_client.get(f"{self.node_api_url}/api/admin/updates")
                if response.status_code == 200:
                    updates = response.json()
                    self._populate_updates_tree(updates)
                    self.update_status_label.configure(text=f"Found {len(updates)} updates")
                else:
                    self.update_status_label.configure(text="Failed to check for updates")
            except Exception as e:
                self.update_status_label.configure(text=f"Error: {e}")
        
        threading.Thread(target=check_async, daemon=True).start()
    
    def _populate_updates_tree(self, updates: List[Dict[str, Any]]) -> None:
        """Populate updates tree with available updates"""
        if not hasattr(self, 'updates_tree'):
            return
        
        # Clear existing items
        for item in self.updates_tree.get_children():
            self.updates_tree.delete(item)
        
        # Add new items
        for update in updates:
            self.updates_tree.insert('', 'end', values=(
                update.get('version', ''),
                update.get('release_date', ''),
                self._format_bytes(update.get('size', 0)),
                update.get('description', ''),
                update.get('status', 'available')
            ))
    
    def install_selected_update(self) -> None:
        """Install selected update"""
        selection = self.updates_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an update to install")
            return
        
        item = self.updates_tree.item(selection[0])
        version = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Install update {version}?"):
            self._install_update(version)
    
    def _install_update(self, version: str) -> None:
        """Install specific update version"""
        self.update_status_label.configure(text=f"Installing update {version}...")
        self.update_progress.set_progress(0)
        
        def install_async():
            try:
                response = self.http_client.post(
                    f"{self.node_api_url}/api/admin/updates/install",
                    json={'version': version}
                )
                
                if response.status_code == 200:
                    # Monitor installation progress
                    self._monitor_update_progress()
                else:
                    self.update_status_label.configure(text=f"Installation failed: {response.text}")
            except Exception as e:
                self.update_status_label.configure(text=f"Installation error: {e}")
        
        threading.Thread(target=install_async, daemon=True).start()
    
    def _monitor_update_progress(self) -> None:
        """Monitor update installation progress"""
        def monitor():
            while True:
                try:
                    response = self.http_client.get(f"{self.node_api_url}/api/admin/updates/progress")
                    if response.status_code == 200:
                        progress = response.json()
                        self.update_progress.set_progress(progress.get('percent', 0))
                        self.update_status_label.configure(text=progress.get('status', 'Installing...'))
                        
                        if progress.get('completed', False):
                            break
                    time.sleep(1)
                except Exception as e:
                    self.update_status_label.configure(text=f"Progress error: {e}")
                    break
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def rollback_update(self) -> None:
        """Rollback to previous version"""
        if messagebox.askyesno("Confirm", "Rollback to previous version?"):
            try:
                response = self.http_client.post(f"{self.node_api_url}/api/admin/updates/rollback")
                if response.status_code == 200:
                    self.update_status_label.configure(text="Rollback initiated")
                else:
                    messagebox.showerror("Error", f"Failed to rollback: {response.text}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rollback: {e}")
    
    def refresh_manifests(self) -> None:
        """Refresh manifests list"""
        self.update_manifests_list()
    
    def filter_manifests(self, *args) -> None:
        """Filter manifests based on search criteria"""
        # Implementation would filter the tree based on search terms
        pass
    
    def export_selected_manifests(self) -> None:
        """Export selected manifests"""
        selection = self.manifests_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select manifests to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Manifests",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Get selected manifest data and export
                manifests_data = []
                for item_id in selection:
                    item = self.manifests_tree.item(item_id)
                    manifests_data.append(item['values'])
                
                with open(filename, 'w') as f:
                    json.dump(manifests_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Exported {len(manifests_data)} manifests to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export manifests: {e}")
    
    def view_manifest_details(self, event) -> None:
        """View detailed manifest information"""
        selection = self.manifests_tree.selection()
        if not selection:
            return
        
        item = self.manifests_tree.item(selection[0])
        session_id = item['values'][0]
        
        # Fetch detailed manifest data
        try:
            response = self.http_client.get(f"{self.node_api_url}/api/admin/manifests/{session_id}")
            if response.status_code == 200:
                manifest = response.json()
                self._display_manifest_details(manifest)
        except Exception as e:
            logger.error(f"Failed to fetch manifest details: {e}")
    
    def _display_manifest_details(self, manifest: Dict[str, Any]) -> None:
        """Display detailed manifest information"""
        if not hasattr(self, 'manifest_details_text'):
            return
        
        self.manifest_details_text.configure(state=tk.NORMAL)
        self.manifest_details_text.delete(1.0, tk.END)
        
        # Format manifest data
        details = json.dumps(manifest, indent=2)
        self.manifest_details_text.insert(1.0, details)
        self.manifest_details_text.configure(state=tk.DISABLED)
    
    def clear_bootstrap_log(self) -> None:
        """Clear bootstrap log"""
        if hasattr(self, 'bootstrap_status_text'):
            self.bootstrap_status_text.configure(state=tk.NORMAL)
            self.bootstrap_status_text.delete(1.0, tk.END)
            self.bootstrap_status_text.configure(state=tk.DISABLED)
    
    def export_bootstrap_log(self) -> None:
        """Export bootstrap log"""
        if not hasattr(self, 'bootstrap_status_text'):
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Bootstrap Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                content = self.bootstrap_status_text.get(1.0, tk.END)
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Bootstrap log exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export log: {e}")
    
    def log_bootstrap_message(self, message: str) -> None:
        """Log message to bootstrap status"""
        if hasattr(self, 'bootstrap_status_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            self.bootstrap_status_text.configure(state=tk.NORMAL)
            self.bootstrap_status_text.insert(tk.END, log_message)
            self.bootstrap_status_text.see(tk.END)
            self.bootstrap_status_text.configure(state=tk.DISABLED)
    
    def export_configuration(self) -> None:
        """Export current configuration"""
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                config_data = {
                    'appliance_info': self.appliance_info.to_dict() if self.appliance_info else None,
                    'ledger_mode': self.current_ledger_mode.value,
                    'admin_status': self.admin_status.value,
                    'node_api_url': self.node_api_url,
                    'docker_config': self.docker_config
                }
                
                with open(filename, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Configuration exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {e}")
    
    def import_configuration(self) -> None:
        """Import configuration"""
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    config_data = json.load(f)
                
                # Apply configuration
                if config_data.get('ledger_mode'):
                    self.current_ledger_mode = LedgerMode(config_data['ledger_mode'])
                
                if config_data.get('node_api_url'):
                    self.node_api_url = config_data['node_api_url']
                
                if config_data.get('docker_config'):
                    self.docker_config.update(config_data['docker_config'])
                
                messagebox.showinfo("Success", "Configuration imported successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration: {e}")
    
    def open_session_explorer(self) -> None:
        """Open session explorer window"""
        messagebox.showinfo("Info", "Session explorer functionality would be implemented here")
    
    def open_blockchain_explorer(self) -> None:
        """Open blockchain explorer window"""
        messagebox.showinfo("Info", "Blockchain explorer functionality would be implemented here")
    
    def check_tor_status(self) -> None:
        """Check Tor network status"""
        messagebox.showinfo("Info", "Tor network status functionality would be implemented here")
    
    def show_documentation(self) -> None:
        """Show documentation"""
        messagebox.showinfo("Info", "Documentation functionality would be implemented here")
    
    def show_release_notes(self) -> None:
        """Show release notes"""
        messagebox.showinfo("Info", "Release notes functionality would be implemented here")
    
    def show_changelog(self) -> None:
        """Show changelog"""
        changelog_text = """Lucid RDP Admin Interface - Changelog

Version 1.0.0 (Current)
• Initial release with full admin interface
• Bootstrap wizard for new appliances
• Session manifest management
• Payout and wallet management
• Key rotation and backup system
• System diagnostics and monitoring
• OTA update management
• Docker environment integration
• Tor-only connectivity support
• TRON blockchain integration

Version 0.9.0 (Beta)
• Core functionality implementation
• Basic GUI framework
• Network security features
• Configuration management

For detailed changelog, visit: https://github.com/HamiGames/Lucid"""
        
        # Create changelog window
        changelog_window = tk.Toplevel(self.root)
        changelog_window.title("Changelog")
        changelog_window.geometry("600x400")
        changelog_window.resizable(True, True)
        
        # Create scrolled text widget
        text_widget = scrolledtext.ScrolledText(
            changelog_window,
            wrap=tk.WORD,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, changelog_text)
        text_widget.configure(state=tk.DISABLED)
        
        # Close button
        close_button = ttk.Button(
            changelog_window,
            text="Close",
            command=changelog_window.destroy
        )
        close_button.pack(pady=10)
    
    def show_documentation(self) -> None:
        """Show documentation"""
        doc_text = """Lucid RDP Admin Interface - Documentation

OVERVIEW
--------
The Lucid RDP Admin Interface provides comprehensive management capabilities for Lucid RDP appliances. This Tor-only, blockchain-anchored remote desktop platform ensures privacy and security through decentralized architecture.

KEY FEATURES
------------
• Bootstrap Wizard: Set up new appliances with guided configuration
• Session Management: Monitor and manage RDP sessions
• Payout System: Handle TRON blockchain transactions and rewards
• Key Management: Rotate and backup cryptographic keys
• System Diagnostics: Monitor appliance health and performance
• OTA Updates: Manage over-the-air updates safely
• Backup & Restore: Comprehensive data protection

GETTING STARTED
---------------
1. Connect to an existing appliance or bootstrap a new one
2. Configure network settings and security options
3. Set up blockchain integration (TRON Mainnet/Shasta)
4. Monitor system health and manage sessions

SECURITY FEATURES
-----------------
• Tor-only connectivity (no clearnet access)
• Certificate pinning for secure connections
• Onion address validation and enforcement
• Encrypted configuration storage
• Secure key management with rotation

BLOCKCHAIN INTEGRATION
----------------------
• TRON network support (Mainnet and Shasta testnet)
• Smart contract interaction
• Automatic payout processing
• Transaction monitoring and history

For complete documentation, visit: https://docs.lucid-rdp.com"""
        
        # Create documentation window
        doc_window = tk.Toplevel(self.root)
        doc_window.title("Documentation")
        doc_window.geometry("700x500")
        doc_window.resizable(True, True)
        
        # Create scrolled text widget
        text_widget = scrolledtext.ScrolledText(
            doc_window,
            wrap=tk.WORD,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, doc_text)
        text_widget.configure(state=tk.DISABLED)
        
        # Close button
        close_button = ttk.Button(
            doc_window,
            text="Close",
            command=doc_window.destroy
        )
        close_button.pack(pady=10)
    
    def show_about(self) -> None:
        """Show about dialog"""
        about_text = """Lucid RDP Admin Interface v1.0.0

A Tor-only, blockchain-anchored remote desktop platform.

FEATURES
• Bootstrap wizard for new appliances
• Session manifest management
• Payout and wallet management
• Key rotation and backup
• System diagnostics
• OTA updates
• Docker environment integration
• TRON blockchain integration

TECHNICAL SPECIFICATIONS
• Built with Python 3.11+ and Tkinter
• Tor-only connectivity (no clearnet access)
• TRON blockchain integration
• MongoDB backend storage
• Docker containerized deployment
• Distroless container support
• ARM64/AMD64 multi-architecture

SECURITY
• Certificate pinning
• Onion address validation
• Encrypted configuration
• Secure key management
• Zero-knowledge architecture

LICENSE
This software is proprietary and confidential.
Copyright (c) 2024 HamiGames. All rights reserved.

For more information, visit the documentation."""
        
        messagebox.showinfo("About Lucid RDP Admin", about_text)
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.monitoring_active = False
        
        # Cleanup component managers
        if self.backup_manager:
            self.backup_manager.cleanup()
        if self.diagnostics_manager:
            self.diagnostics_manager.stop_monitoring()
        if self.key_manager:
            self.key_manager.cleanup()
        if self.payouts_manager:
            self.payouts_manager.cleanup()
        
        # Close HTTP client
        if hasattr(self, 'http_client'):
            self.http_client.close()
        
        logger.info("Admin GUI cleanup completed")
    
    def validate_docker_environment(self) -> Dict[str, Any]:
        """Validate Docker environment configuration"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'config_summary': {}
        }
        
        try:
            # Check critical environment variables
            critical_env_vars = [
                'MONGO_URL',
                'TRON_NETWORK',
                'LUCID_ENV'
            ]
            
            for env_var in critical_env_vars:
                if not os.environ.get(env_var):
                    validation_results['warnings'].append(f"Missing environment variable: {env_var}")
                else:
                    validation_results['config_summary'][env_var] = os.environ.get(env_var)
            
            # Check Tor configuration
            if not os.environ.get('TOR_SOCKS'):
                validation_results['warnings'].append("TOR_SOCKS not configured")
            
            # Check blockchain configuration
            tron_network = os.environ.get('TRON_NETWORK', 'shasta')
            if tron_network == 'mainnet':
                if not os.environ.get('TRONGRID_API_KEY'):
                    validation_results['warnings'].append("TRONGRID_API_KEY recommended for mainnet")
            
            # Check onion addresses
            onion_count = sum(1 for key in os.environ.keys() if key.startswith('ONION_') and os.environ.get(key))
            if onion_count == 0:
                validation_results['warnings'].append("No onion addresses configured")
            
            # Check security configuration
            if not os.environ.get('KEY_ENC_SECRET'):
                validation_results['warnings'].append("KEY_ENC_SECRET not configured - using ephemeral key")
            
            validation_results['config_summary']['tron_network'] = tron_network
            validation_results['config_summary']['onion_addresses_count'] = onion_count
            validation_results['config_summary']['lucid_env'] = os.environ.get('LUCID_ENV', 'dev')
            
            logger.info(f"Docker environment validation completed: {validation_results}")
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {e}")
            logger.error(f"Failed to validate Docker environment: {e}")
        
        return validation_results
    
    def get_docker_status(self) -> Dict[str, Any]:
        """Get current Docker environment status"""
        status = {
            'environment': self.docker_config.get('lucid_env', 'unknown'),
            'plane': self.docker_config.get('lucid_plane', 'unknown'),
            'cluster_id': self.docker_config.get('lucid_cluster_id', 'unknown'),
            'debug_mode': self.docker_config.get('debug_mode', False),
            'log_level': self.docker_config.get('log_level', 'INFO'),
            'api_url': self.node_api_url,
            'mongo_configured': bool(self.docker_config.get('mongo_url')),
            'tron_network': self.docker_config.get('tron_network', 'unknown'),
            'tor_configured': bool(self.docker_config.get('tor_socks')),
            'onion_addresses': []
        }
        
        # Collect onion addresses
        for key, value in self.docker_config.items():
            if key.startswith('onion_') and value:
                status['onion_addresses'].append(f"{key}: {value}")
        
        return status


# Main entry point for standalone execution
def main():
    """Main entry point for standalone execution"""
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/var/log/lucid/admin-gui.log')
        ]
    )
    
    # Create main window
    root = tk.Tk()
    
    try:
        # Initialize admin GUI
        admin_gui = AdminGUI(root)
        
        # Handle window close
        def on_closing():
            admin_gui.cleanup()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start GUI main loop
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Failed to start admin GUI: {e}")
        messagebox.showerror("Error", f"Failed to start admin GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

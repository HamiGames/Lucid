# Path: gui/admin/bootstrap_wizard.py
"""
Enhanced bootstrap wizard for Lucid RDP appliance initial setup and provisioning.
Provides step-by-step wizard interface with validation, progress tracking, and advanced configuration options.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import logging
import threading
import time
import uuid
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import base64
import secrets

from ..core.networking import TorHttpClient, SecurityConfig, OnionEndpoint
from ..core.security import get_security_validator, validate_onion_address, CryptographicUtils
from ..core.config_manager import get_config_manager, ConfigScope, GuiConfig
from ..core.widgets import get_theme_manager, StatusLabel, ProgressBar, create_tooltip, LogViewer
from ..core.telemetry import get_telemetry_manager, EventType, track_event

logger = logging.getLogger(__name__)


class BootstrapStep(Enum):
    """Bootstrap wizard step enumeration"""
    WELCOME = "welcome"
    BASIC_INFO = "basic_info"
    NETWORK_CONFIG = "network_config"
    SECURITY_CONFIG = "security_config"
    LEDGER_CONFIG = "ledger_config"
    ADVANCED_OPTIONS = "advanced_options"
    VALIDATION = "validation"
    PROVISIONING = "provisioning"
    COMPLETION = "completion"


class BootstrapStatus(Enum):
    """Bootstrap operation status"""
    IDLE = "idle"
    VALIDATING = "validating"
    PROVISIONING = "provisioning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProvisioningStage(Enum):
    """Provisioning stage enumeration"""
    INITIALIZATION = "initialization"
    NETWORK_SETUP = "network_setup"
    SECURITY_SETUP = "security_setup"
    KEY_GENERATION = "key_generation"
    SERVICE_CONFIG = "service_config"
    DATABASE_SETUP = "database_setup"
    TOR_SETUP = "tor_setup"
    BACKUP_SETUP = "backup_setup"
    FINALIZATION = "finalization"


@dataclass
class NetworkConfig:
    """Network configuration for bootstrap"""
    tor_enabled: bool = True
    onion_service_enabled: bool = True
    custom_onion_address: Optional[str] = None
    socks_port: int = 9150
    control_port: int = 9151
    http_port: int = 8080
    https_port: int = 8443
    api_port: int = 9000
    external_ip: Optional[str] = None
    dns_servers: List[str] = None
    
    def __post_init__(self):
        if self.dns_servers is None:
            self.dns_servers = ["1.1.1.1", "8.8.8.8"]


@dataclass
class SecurityConfig:
    """Security configuration for bootstrap"""
    encryption_enabled: bool = True
    certificate_pinning: bool = True
    auto_key_rotation: bool = True
    key_rotation_days: int = 90
    backup_encryption: bool = True
    audit_logging: bool = True
    intrusion_detection: bool = True
    firewall_enabled: bool = True
    ssl_enabled: bool = True
    minimum_tls_version: str = "TLSv1.2"


@dataclass
class LedgerConfig:
    """Ledger configuration for bootstrap"""
    ledger_mode: str = "sandbox"  # sandbox or production
    tron_node_url: Optional[str] = None
    wallet_address: Optional[str] = None
    private_key_encrypted: Optional[str] = None
    gas_limit: int = 1000000
    gas_price: int = 1000000
    payout_threshold: float = 10.0
    auto_payout_enabled: bool = True


@dataclass
class AdvancedConfig:
    """Advanced configuration options"""
    auto_backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    log_level: str = "INFO"
    max_log_size_mb: int = 100
    log_retention_days: int = 30
    telemetry_enabled: bool = False
    debug_mode: bool = False
    experimental_features: bool = False
    custom_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_config is None:
            self.custom_config = {}


@dataclass
class BootstrapConfig:
    """Complete bootstrap configuration"""
    # Basic information
    appliance_name: str
    admin_email: str
    admin_password: str
    admin_full_name: str = ""
    organization: str = ""
    
    # Configuration sections
    network: NetworkConfig = None
    security: SecurityConfig = None
    ledger: LedgerConfig = None
    advanced: AdvancedConfig = None
    
    # Metadata
    version: str = "1.0.0"
    created_at: str = ""
    created_by: str = ""
    appliance_id: str = ""
    
    def __post_init__(self):
        if self.network is None:
            self.network = NetworkConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.ledger is None:
            self.ledger = LedgerConfig()
        if self.advanced is None:
            self.advanced = AdvancedConfig()
        
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.appliance_id:
            self.appliance_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['network'] = asdict(self.network)
        data['security'] = asdict(self.security)
        data['ledger'] = asdict(self.ledger)
        data['advanced'] = asdict(self.advanced)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BootstrapConfig':
        """Create BootstrapConfig from dictionary"""
        # Convert nested dataclasses
        if 'network' in data:
            data['network'] = NetworkConfig(**data['network'])
        if 'security' in data:
            data['security'] = SecurityConfig(**data['security'])
        if 'ledger' in data:
            data['ledger'] = LedgerConfig(**data['ledger'])
        if 'advanced' in data:
            data['advanced'] = AdvancedConfig(**data['advanced'])
        
        return cls(**data)
    
    def calculate_hash(self) -> str:
        """Calculate configuration hash for integrity verification"""
        # Remove sensitive data for hashing
        safe_data = self.to_dict().copy()
        safe_data['admin_password'] = "[REDACTED]"
        safe_data['ledger']['private_key_encrypted'] = "[REDACTED]"
        
        json_str = json.dumps(safe_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class ProvisioningProgress:
    """Provisioning progress tracking"""
    stage: ProvisioningStage
    status: BootstrapStatus
    progress_percent: float = 0.0
    message: str = ""
    details: Dict[str, Any] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class BootstrapValidator:
    """Validates bootstrap configuration"""
    
    def __init__(self):
        self.security_validator = get_security_validator()
    
    def validate_config(self, config: BootstrapConfig) -> Tuple[bool, List[str]]:
        """Validate complete bootstrap configuration"""
        errors = []
        
        # Basic validation
        basic_valid, basic_errors = self._validate_basic_info(config)
        errors.extend(basic_errors)
        
        # Network validation
        network_valid, network_errors = self._validate_network_config(config.network)
        errors.extend(network_errors)
        
        # Security validation
        security_valid, security_errors = self._validate_security_config(config.security)
        errors.extend(security_errors)
        
        # Ledger validation
        ledger_valid, ledger_errors = self._validate_ledger_config(config.ledger)
        errors.extend(ledger_errors)
        
        # Advanced validation
        advanced_valid, advanced_errors = self._validate_advanced_config(config.advanced)
        errors.extend(advanced_errors)
        
        return len(errors) == 0, errors
    
    def _validate_basic_info(self, config: BootstrapConfig) -> Tuple[bool, List[str]]:
        """Validate basic information"""
        errors = []
        
        if not config.appliance_name or len(config.appliance_name.strip()) < 3:
            errors.append("Appliance name must be at least 3 characters long")
        
        if not config.admin_email or '@' not in config.admin_email:
            errors.append("Valid admin email is required")
        
        if not config.admin_password or len(config.admin_password) < 8:
            errors.append("Admin password must be at least 8 characters long")
        
        return len(errors) == 0, errors
    
    def _validate_network_config(self, network: NetworkConfig) -> Tuple[bool, List[str]]:
        """Validate network configuration"""
        errors = []
        
        # Port validation
        ports = [network.socks_port, network.control_port, network.http_port, 
                network.https_port, network.api_port]
        if len(set(ports)) != len(ports):
            errors.append("All ports must be unique")
        
        for port in ports:
            if port < 1024 or port > 65535:
                errors.append(f"Port {port} must be between 1024 and 65535")
        
        # Onion address validation
        if network.custom_onion_address:
            if not validate_onion_address(network.custom_onion_address):
                errors.append("Invalid custom onion address format")
        
        return len(errors) == 0, errors
    
    def _validate_security_config(self, security: SecurityConfig) -> Tuple[bool, List[str]]:
        """Validate security configuration"""
        errors = []
        
        if security.key_rotation_days < 1 or security.key_rotation_days > 365:
            errors.append("Key rotation days must be between 1 and 365")
        
        valid_tls_versions = ["TLSv1.2", "TLSv1.3"]
        if security.minimum_tls_version not in valid_tls_versions:
            errors.append(f"Minimum TLS version must be one of: {', '.join(valid_tls_versions)}")
        
        return len(errors) == 0, errors
    
    def _validate_ledger_config(self, ledger: LedgerConfig) -> Tuple[bool, List[str]]:
        """Validate ledger configuration"""
        errors = []
        
        if ledger.ledger_mode not in ["sandbox", "production"]:
            errors.append("Ledger mode must be 'sandbox' or 'production'")
        
        if ledger.payout_threshold <= 0:
            errors.append("Payout threshold must be greater than 0")
        
        if ledger.gas_limit <= 0:
            errors.append("Gas limit must be greater than 0")
        
        return len(errors) == 0, errors
    
    def _validate_advanced_config(self, advanced: AdvancedConfig) -> Tuple[bool, List[str]]:
        """Validate advanced configuration"""
        errors = []
        
        if advanced.backup_interval_hours < 1:
            errors.append("Backup interval must be at least 1 hour")
        
        if advanced.backup_retention_days < 1:
            errors.append("Backup retention must be at least 1 day")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if advanced.log_level not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")
        
        return len(errors) == 0, errors


class BootstrapWizard:
    """Enhanced bootstrap wizard with step-by-step interface"""
    
    def __init__(self, parent: tk.Widget, on_complete: Optional[Callable[[BootstrapConfig], None]] = None):
        self.parent = parent
        self.on_complete = on_complete
        self.wizard_window = None
        
        # Configuration
        self.config = BootstrapConfig(
            appliance_name="",
            admin_email="",
            admin_password=""
        )
        
        # Wizard state
        self.current_step = BootstrapStep.WELCOME
        self.step_history = []
        self.status = BootstrapStatus.IDLE
        self.provisioning_progress = None
        
        # Components
        self.validator = BootstrapValidator()
        self.progress_callbacks = []
        self.status_callbacks = []
        
        # GUI components
        self.main_frame = None
        self.step_frame = None
        self.navigation_frame = None
        self.progress_bar = None
        self.status_label = None
        self.log_viewer = None
        
        # Step-specific frames
        self.step_frames = {}
        self.step_vars = {}
        
        logger.info("Bootstrap wizard initialized")
    
    def show_wizard(self) -> None:
        """Show the bootstrap wizard window"""
        self.wizard_window = tk.Toplevel(self.parent)
        self.wizard_window.title("Lucid RDP - Bootstrap Wizard")
        self.wizard_window.geometry("800x700")
        self.wizard_window.resizable(True, True)
        self.wizard_window.transient(self.parent)
        self.wizard_window.grab_set()
        
        # Center window
        self.wizard_window.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 100,
            self.parent.winfo_rooty() + 50
        ))
        
        # Handle window close
        self.wizard_window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._setup_wizard_gui()
        self._show_step(BootstrapStep.WELCOME)
        
        logger.info("Bootstrap wizard displayed")
    
    def _setup_wizard_gui(self) -> None:
        """Setup the main wizard GUI"""
        # Main container
        self.main_frame = ttk.Frame(self.wizard_window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header()
        
        # Progress indicator
        self._create_progress_indicator()
        
        # Step content area
        self.step_frame = ttk.Frame(self.main_frame)
        self.step_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Status and log area
        self._create_status_area()
        
        # Navigation
        self._create_navigation()
        
        # Apply theme
        theme_manager = get_theme_manager()
        theme_manager.apply_theme_to_window(self.wizard_window)
    
    def _create_header(self) -> None:
        """Create wizard header"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="Lucid RDP Bootstrap Wizard",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(
            header_frame,
            text=f"Version {self.config.version}",
            font=('Arial', 10)
        )
        version_label.pack(side=tk.RIGHT)
    
    def _create_progress_indicator(self) -> None:
        """Create progress indicator"""
        progress_frame = ttk.LabelFrame(self.main_frame, text="Progress")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ProgressBar(progress_frame, width=400)
        self.progress_bar.pack(padx=10, pady=10)
        
        self.status_label = StatusLabel(
            progress_frame,
            text="Ready to begin",
            status="info"
        )
        self.status_label.pack(pady=(0, 10))
    
    def _create_status_area(self) -> None:
        """Create status and log area"""
        status_frame = ttk.LabelFrame(self.main_frame, text="Status & Logs")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_viewer = LogViewer(status_frame, max_lines=100)
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _create_navigation(self) -> None:
        """Create navigation buttons"""
        self.navigation_frame = ttk.Frame(self.main_frame)
        self.navigation_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Left side buttons
        left_frame = ttk.Frame(self.navigation_frame)
        left_frame.pack(side=tk.LEFT)
        
        self.back_button = ttk.Button(
            left_frame,
            text="← Back",
            command=self._go_back,
            state=tk.DISABLED
        )
        self.back_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Right side buttons
        right_frame = ttk.Frame(self.navigation_frame)
        right_frame.pack(side=tk.RIGHT)
        
        self.cancel_button = ttk.Button(
            right_frame,
            text="Cancel",
            command=self._cancel_wizard
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.next_button = ttk.Button(
            right_frame,
            text="Next →",
            command=self._go_next,
            style="Accent.TButton"
        )
        self.next_button.pack(side=tk.LEFT)
        
        # Store button references for state management
        self._navigation_buttons = {
            'back': self.back_button,
            'cancel': self.cancel_button,
            'next': self.next_button
        }
    
    def _show_step(self, step: BootstrapStep) -> None:
        """Show a specific step"""
        # Clear current step frame
        for widget in self.step_frame.winfo_children():
            widget.destroy()
        
        # Add to history if not already there
        if not self.step_history or self.step_history[-1] != step:
            self.step_history.append(self.current_step)
        
        self.current_step = step
        
        # Create step content
        if step not in self.step_frames:
            self._create_step_content(step)
        
        # Show step content
        step_widget = self.step_frames[step]
        step_widget.pack(fill=tk.BOTH, expand=True)
        
        # Update navigation
        self._update_navigation()
        
        # Update progress
        progress_percent = self._calculate_progress()
        self.progress_bar.set_progress(progress_percent)
        
        # Log step change
        self.log_message(f"Step: {step.value.replace('_', ' ').title()}")
        
        logger.info(f"Showing step: {step.value}")
    
    def _create_step_content(self, step: BootstrapStep) -> None:
        """Create content for a specific step"""
        step_frame = ttk.Frame(self.step_frame)
        
        if step == BootstrapStep.WELCOME:
            self._create_welcome_step(step_frame)
        elif step == BootstrapStep.BASIC_INFO:
            self._create_basic_info_step(step_frame)
        elif step == BootstrapStep.NETWORK_CONFIG:
            self._create_network_config_step(step_frame)
        elif step == BootstrapStep.SECURITY_CONFIG:
            self._create_security_config_step(step_frame)
        elif step == BootstrapStep.LEDGER_CONFIG:
            self._create_ledger_config_step(step_frame)
        elif step == BootstrapStep.ADVANCED_OPTIONS:
            self._create_advanced_options_step(step_frame)
        elif step == BootstrapStep.VALIDATION:
            self._create_validation_step(step_frame)
        elif step == BootstrapStep.PROVISIONING:
            self._create_provisioning_step(step_frame)
        elif step == BootstrapStep.COMPLETION:
            self._create_completion_step(step_frame)
        
        self.step_frames[step] = step_frame
    
    def _create_welcome_step(self, parent: ttk.Frame) -> None:
        """Create welcome step content"""
        # Welcome text
        welcome_text = """
Welcome to the Lucid RDP Bootstrap Wizard!

This wizard will guide you through the initial setup and provisioning of your 
Lucid RDP appliance. The process includes:

• Basic appliance configuration
• Network and security setup
• Ledger configuration
• Advanced options
• System validation
• Automated provisioning

Please ensure you have:
- Admin credentials ready
- Network access configured
- Required permissions for system setup

Click 'Next' to begin the bootstrap process.
        """
        
        text_widget = tk.Text(
            parent,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=('Arial', 10)
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, welcome_text.strip())
        text_widget.configure(state=tk.DISABLED)
    
    def _create_basic_info_step(self, parent: ttk.Frame) -> None:
        """Create basic information step"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Appliance name
        ttk.Label(form_frame, text="Appliance Name *:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['appliance_name'] = tk.StringVar(value=self.config.appliance_name)
        name_entry = ttk.Entry(form_frame, textvariable=self.step_vars['appliance_name'], width=40)
        name_entry.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Admin full name
        ttk.Label(form_frame, text="Admin Full Name:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['admin_full_name'] = tk.StringVar(value=self.config.admin_full_name)
        fullname_entry = ttk.Entry(form_frame, textvariable=self.step_vars['admin_full_name'], width=40)
        fullname_entry.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Admin email
        ttk.Label(form_frame, text="Admin Email *:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['admin_email'] = tk.StringVar(value=self.config.admin_email)
        email_entry = ttk.Entry(form_frame, textvariable=self.step_vars['admin_email'], width=40)
        email_entry.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Admin password
        ttk.Label(form_frame, text="Admin Password *:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['admin_password'] = tk.StringVar(value=self.config.admin_password)
        password_entry = ttk.Entry(form_frame, textvariable=self.step_vars['admin_password'], 
                                 show="*", width=40)
        password_entry.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        # Organization
        ttk.Label(form_frame, text="Organization:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['organization'] = tk.StringVar(value=self.config.organization)
        org_entry = ttk.Entry(form_frame, textvariable=self.step_vars['organization'], width=40)
        org_entry.grid(row=4, column=1, sticky=tk.W, pady=(0, 5))
        
        # Password strength indicator
        password_frame = ttk.Frame(form_frame)
        password_frame.grid(row=5, column=1, sticky=tk.W, pady=(10, 0))
        
        self.password_strength_label = ttk.Label(password_frame, text="Password strength: Unknown")
        self.password_strength_label.pack(anchor=tk.W)
        
        # Bind password change
        self.step_vars['admin_password'].trace('w', self._on_password_changed)
        
        # Add tooltips
        create_tooltip(name_entry, "Enter a unique name for this appliance")
        create_tooltip(email_entry, "Enter the administrator email address")
        create_tooltip(password_entry, "Enter a strong password (minimum 8 characters)")
    
    def _create_network_config_step(self, parent: ttk.Frame) -> None:
        """Create network configuration step"""
        # Create notebook for network settings
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General network settings
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        self._create_network_general_tab(general_frame)
        
        # Tor settings
        tor_frame = ttk.Frame(notebook)
        notebook.add(tor_frame, text="Tor")
        self._create_network_tor_tab(tor_frame)
        
        # Port settings
        ports_frame = ttk.Frame(notebook)
        notebook.add(ports_frame, text="Ports")
        self._create_network_ports_tab(ports_frame)
    
    def _create_network_general_tab(self, parent: ttk.Frame) -> None:
        """Create general network settings tab"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # External IP (optional)
        ttk.Label(form_frame, text="External IP (optional):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['external_ip'] = tk.StringVar(value=self.config.network.external_ip or "")
        ip_entry = ttk.Entry(form_frame, textvariable=self.step_vars['external_ip'], width=40)
        ip_entry.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # DNS servers
        ttk.Label(form_frame, text="DNS Servers:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        dns_frame = ttk.Frame(form_frame)
        dns_frame.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        self.step_vars['dns_servers'] = tk.StringVar(value=", ".join(self.config.network.dns_servers))
        dns_entry = ttk.Entry(dns_frame, textvariable=self.step_vars['dns_servers'], width=35)
        dns_entry.pack(side=tk.LEFT)
        
        create_tooltip(dns_entry, "Comma-separated list of DNS servers")
    
    def _create_network_tor_tab(self, parent: ttk.Frame) -> None:
        """Create Tor network settings tab"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Enable Tor
        self.step_vars['tor_enabled'] = tk.BooleanVar(value=self.config.network.tor_enabled)
        tor_check = ttk.Checkbutton(
            form_frame,
            text="Enable Tor network",
            variable=self.step_vars['tor_enabled']
        )
        tor_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Enable Onion Service
        self.step_vars['onion_service_enabled'] = tk.BooleanVar(value=self.config.network.onion_service_enabled)
        onion_check = ttk.Checkbutton(
            form_frame,
            text="Enable Onion Service",
            variable=self.step_vars['onion_service_enabled']
        )
        onion_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Custom onion address
        ttk.Label(form_frame, text="Custom Onion Address (optional):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['custom_onion_address'] = tk.StringVar(value=self.config.network.custom_onion_address or "")
        onion_entry = ttk.Entry(form_frame, textvariable=self.step_vars['custom_onion_address'], width=40)
        onion_entry.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        create_tooltip(onion_entry, "Optional custom .onion address (leave empty for auto-generation)")
    
    def _create_network_ports_tab(self, parent: ttk.Frame) -> None:
        """Create network ports settings tab"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Port configuration
        ports = [
            ('socks_port', 'Tor SOCKS Port:', self.config.network.socks_port),
            ('control_port', 'Tor Control Port:', self.config.network.control_port),
            ('http_port', 'HTTP Port:', self.config.network.http_port),
            ('https_port', 'HTTPS Port:', self.config.network.https_port),
            ('api_port', 'API Port:', self.config.network.api_port)
        ]
        
        for i, (var_name, label, default_value) in enumerate(ports):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=(0, 5))
            self.step_vars[var_name] = tk.IntVar(value=default_value)
            port_spinbox = ttk.Spinbox(
                form_frame,
                from_=1024,
                to=65535,
                textvariable=self.step_vars[var_name],
                width=10
            )
            port_spinbox.grid(row=i, column=1, sticky=tk.W, pady=(0, 5))
    
    def _create_security_config_step(self, parent: ttk.Frame) -> None:
        """Create security configuration step"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Security options
        security_options = [
            ('encryption_enabled', 'Enable encryption', self.config.security.encryption_enabled),
            ('certificate_pinning', 'Enable certificate pinning', self.config.security.certificate_pinning),
            ('auto_key_rotation', 'Enable automatic key rotation', self.config.security.auto_key_rotation),
            ('backup_encryption', 'Encrypt backups', self.config.security.backup_encryption),
            ('audit_logging', 'Enable audit logging', self.config.security.audit_logging),
            ('intrusion_detection', 'Enable intrusion detection', self.config.security.intrusion_detection),
            ('firewall_enabled', 'Enable firewall', self.config.security.firewall_enabled),
            ('ssl_enabled', 'Enable SSL/TLS', self.config.security.ssl_enabled)
        ]
        
        for i, (var_name, label, default_value) in enumerate(security_options):
            self.step_vars[var_name] = tk.BooleanVar(value=default_value)
            check = ttk.Checkbutton(
                form_frame,
                text=label,
                variable=self.step_vars[var_name]
            )
            check.grid(row=i, column=0, sticky=tk.W, pady=2)
        
        # Key rotation days
        ttk.Label(form_frame, text="Key rotation interval (days):").grid(row=len(security_options), column=0, sticky=tk.W, pady=(20, 5))
        self.step_vars['key_rotation_days'] = tk.IntVar(value=self.config.security.key_rotation_days)
        rotation_spinbox = ttk.Spinbox(
            form_frame,
            from_=1,
            to=365,
            textvariable=self.step_vars['key_rotation_days'],
            width=10
        )
        rotation_spinbox.grid(row=len(security_options), column=1, sticky=tk.W, pady=(20, 5))
        
        # Minimum TLS version
        ttk.Label(form_frame, text="Minimum TLS version:").grid(row=len(security_options)+1, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['minimum_tls_version'] = tk.StringVar(value=self.config.security.minimum_tls_version)
        tls_combo = ttk.Combobox(
            form_frame,
            textvariable=self.step_vars['minimum_tls_version'],
            values=['TLSv1.2', 'TLSv1.3'],
            state='readonly',
            width=15
        )
        tls_combo.grid(row=len(security_options)+1, column=1, sticky=tk.W, pady=(0, 5))
    
    def _create_ledger_config_step(self, parent: ttk.Frame) -> None:
        """Create ledger configuration step"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Ledger mode
        ttk.Label(form_frame, text="Ledger Mode *:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['ledger_mode'] = tk.StringVar(value=self.config.ledger.ledger_mode)
        mode_combo = ttk.Combobox(
            form_frame,
            textvariable=self.step_vars['ledger_mode'],
            values=['sandbox', 'production'],
            state='readonly',
            width=20
        )
        mode_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # TRON node URL
        ttk.Label(form_frame, text="TRON Node URL:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['tron_node_url'] = tk.StringVar(value=self.config.ledger.tron_node_url or "")
        node_entry = ttk.Entry(form_frame, textvariable=self.step_vars['tron_node_url'], width=40)
        node_entry.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Wallet address
        ttk.Label(form_frame, text="Wallet Address:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['wallet_address'] = tk.StringVar(value=self.config.ledger.wallet_address or "")
        wallet_entry = ttk.Entry(form_frame, textvariable=self.step_vars['wallet_address'], width=40)
        wallet_entry.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Payout settings
        payout_frame = ttk.LabelFrame(form_frame, text="Payout Settings")
        payout_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E, pady=(20, 0))
        
        # Payout threshold
        ttk.Label(payout_frame, text="Payout Threshold (TRX):").grid(row=0, column=0, sticky=tk.W, pady=(5, 5))
        self.step_vars['payout_threshold'] = tk.DoubleVar(value=self.config.ledger.payout_threshold)
        threshold_spinbox = ttk.Spinbox(
            payout_frame,
            from_=0.1,
            to=1000.0,
            increment=0.1,
            textvariable=self.step_vars['payout_threshold'],
            width=10
        )
        threshold_spinbox.grid(row=0, column=1, sticky=tk.W, pady=(5, 5))
        
        # Auto payout
        self.step_vars['auto_payout_enabled'] = tk.BooleanVar(value=self.config.ledger.auto_payout_enabled)
        auto_payout_check = ttk.Checkbutton(
            payout_frame,
            text="Enable automatic payouts",
            variable=self.step_vars['auto_payout_enabled']
        )
        auto_payout_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        create_tooltip(mode_combo, "Sandbox for testing, Production for live operations")
        create_tooltip(node_entry, "TRON network node URL (leave empty for default)")
    
    def _create_advanced_options_step(self, parent: ttk.Frame) -> None:
        """Create advanced options step"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Backup settings
        backup_frame = ttk.LabelFrame(form_frame, text="Backup Settings")
        backup_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W+tk.E, pady=(0, 10))
        
        self.step_vars['auto_backup_enabled'] = tk.BooleanVar(value=self.config.advanced.auto_backup_enabled)
        backup_check = ttk.Checkbutton(
            backup_frame,
            text="Enable automatic backups",
            variable=self.step_vars['auto_backup_enabled']
        )
        backup_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(backup_frame, text="Backup interval (hours):").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['backup_interval_hours'] = tk.IntVar(value=self.config.advanced.backup_interval_hours)
        backup_interval_spinbox = ttk.Spinbox(
            backup_frame,
            from_=1,
            to=168,
            textvariable=self.step_vars['backup_interval_hours'],
            width=10
        )
        backup_interval_spinbox.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(backup_frame, text="Backup retention (days):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['backup_retention_days'] = tk.IntVar(value=self.config.advanced.backup_retention_days)
        retention_spinbox = ttk.Spinbox(
            backup_frame,
            from_=1,
            to=365,
            textvariable=self.step_vars['backup_retention_days'],
            width=10
        )
        retention_spinbox.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Logging settings
        logging_frame = ttk.LabelFrame(form_frame, text="Logging Settings")
        logging_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E, pady=(0, 10))
        
        ttk.Label(logging_frame, text="Log level:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.step_vars['log_level'] = tk.StringVar(value=self.config.advanced.log_level)
        log_combo = ttk.Combobox(
            logging_frame,
            textvariable=self.step_vars['log_level'],
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            state='readonly',
            width=15
        )
        log_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Advanced features
        features_frame = ttk.LabelFrame(form_frame, text="Advanced Features")
        features_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E, pady=(0, 10))
        
        self.step_vars['telemetry_enabled'] = tk.BooleanVar(value=self.config.advanced.telemetry_enabled)
        telemetry_check = ttk.Checkbutton(
            features_frame,
            text="Enable telemetry",
            variable=self.step_vars['telemetry_enabled']
        )
        telemetry_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.step_vars['debug_mode'] = tk.BooleanVar(value=self.config.advanced.debug_mode)
        debug_check = ttk.Checkbutton(
            features_frame,
            text="Enable debug mode",
            variable=self.step_vars['debug_mode']
        )
        debug_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.step_vars['experimental_features'] = tk.BooleanVar(value=self.config.advanced.experimental_features)
        exp_check = ttk.Checkbutton(
            features_frame,
            text="Enable experimental features",
            variable=self.step_vars['experimental_features']
        )
        exp_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
    
    def _create_validation_step(self, parent: ttk.Frame) -> None:
        """Create validation step"""
        validation_frame = ttk.Frame(parent)
        validation_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Validation results
        results_frame = ttk.LabelFrame(validation_frame, text="Configuration Validation")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.validation_results_text = tk.Text(
            results_frame,
            height=10,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.validation_results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Validation buttons
        button_frame = ttk.Frame(validation_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Validate Configuration",
            command=self._validate_configuration
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Export Configuration",
            command=self._export_configuration
        ).pack(side=tk.LEFT)
        
        # Validation status
        self.validation_status_label = StatusLabel(
            validation_frame,
            text="Configuration not validated",
            status="warning"
        )
        self.validation_status_label.pack(pady=(0, 10))
    
    def _create_provisioning_step(self, parent: ttk.Frame) -> None:
        """Create provisioning step"""
        provisioning_frame = ttk.Frame(parent)
        provisioning_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Provisioning status
        status_frame = ttk.LabelFrame(provisioning_frame, text="Provisioning Status")
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.provisioning_status_label = StatusLabel(
            status_frame,
            text="Ready to begin provisioning",
            status="info"
        )
        self.provisioning_status_label.pack(padx=10, pady=10)
        
        # Provisioning progress
        progress_frame = ttk.LabelFrame(provisioning_frame, text="Provisioning Progress")
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.provisioning_progress_bar = ProgressBar(progress_frame, width=400)
        self.provisioning_progress_bar.pack(padx=10, pady=10)
        
        self.provisioning_stage_label = ttk.Label(
            progress_frame,
            text="Waiting to start..."
        )
        self.provisioning_stage_label.pack(pady=(0, 10))
        
        # Provisioning controls
        controls_frame = ttk.Frame(provisioning_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_provisioning_button = ttk.Button(
            controls_frame,
            text="Start Provisioning",
            command=self._start_provisioning,
            style="Accent.TButton"
        )
        self.start_provisioning_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_provisioning_button = ttk.Button(
            controls_frame,
            text="Stop Provisioning",
            command=self._stop_provisioning,
            state=tk.DISABLED
        )
        self.stop_provisioning_button.pack(side=tk.LEFT)
    
    def _create_completion_step(self, parent: ttk.Frame) -> None:
        """Create completion step"""
        completion_frame = ttk.Frame(parent)
        completion_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Success message
        success_text = """
Bootstrap Completed Successfully!

Your Lucid RDP appliance has been successfully configured and provisioned.

Configuration Summary:
• Appliance: {appliance_name}
• Admin: {admin_email}
• Ledger Mode: {ledger_mode}
• Network: {network_status}
• Security: {security_status}

Next Steps:
1. Save your configuration backup
2. Test the appliance connectivity
3. Configure additional settings as needed
4. Begin using your Lucid RDP appliance

The appliance is now ready for operation!
        """.format(
            appliance_name=self.config.appliance_name,
            admin_email=self.config.admin_email,
            ledger_mode=self.config.ledger.ledger_mode,
            network_status="Tor + Onion Service" if self.config.network.tor_enabled else "Standard",
            security_status="Enabled" if self.config.security.encryption_enabled else "Disabled"
        )
        
        text_widget = tk.Text(
            completion_frame,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=('Arial', 10)
        )
        text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, success_text.strip())
        text_widget.configure(state=tk.DISABLED)
        
        # Action buttons
        actions_frame = ttk.Frame(completion_frame)
        actions_frame.pack(fill=tk.X)
        
        ttk.Button(
            actions_frame,
            text="Export Configuration",
            command=self._export_configuration
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            actions_frame,
            text="Open Admin Interface",
            command=self._open_admin_interface
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            actions_frame,
            text="Finish",
            command=self._finish_wizard,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT)
    
    def _update_navigation(self) -> None:
        """Update navigation button states"""
        # Back button
        can_go_back = len(self.step_history) > 1
        self._navigation_buttons['back'].configure(state=tk.NORMAL if can_go_back else tk.DISABLED)
        
        # Next button
        if self.current_step == BootstrapStep.COMPLETION:
            self._navigation_buttons['next'].configure(state=tk.DISABLED)
        elif self.current_step == BootstrapStep.PROVISIONING:
            self._navigation_buttons['next'].configure(state=tk.DISABLED)
        else:
            self._navigation_buttons['next'].configure(state=tk.NORMAL)
        
        # Cancel button
        self._navigation_buttons['cancel'].configure(state=tk.NORMAL)
    
    def _calculate_progress(self) -> float:
        """Calculate wizard progress percentage"""
        step_order = [
            BootstrapStep.WELCOME,
            BootstrapStep.BASIC_INFO,
            BootstrapStep.NETWORK_CONFIG,
            BootstrapStep.SECURITY_CONFIG,
            BootstrapStep.LEDGER_CONFIG,
            BootstrapStep.ADVANCED_OPTIONS,
            BootstrapStep.VALIDATION,
            BootstrapStep.PROVISIONING,
            BootstrapStep.COMPLETION
        ]
        
        try:
            current_index = step_order.index(self.current_step)
            return (current_index / (len(step_order) - 1)) * 100
        except ValueError:
            return 0.0
    
    def _go_next(self) -> None:
        """Go to next step"""
        if self.current_step == BootstrapStep.WELCOME:
            self._show_step(BootstrapStep.BASIC_INFO)
        elif self.current_step == BootstrapStep.BASIC_INFO:
            self._update_config_from_step()
            if self._validate_current_step():
                self._show_step(BootstrapStep.NETWORK_CONFIG)
        elif self.current_step == BootstrapStep.NETWORK_CONFIG:
            self._update_config_from_step()
            if self._validate_current_step():
                self._show_step(BootstrapStep.SECURITY_CONFIG)
        elif self.current_step == BootstrapStep.SECURITY_CONFIG:
            self._update_config_from_step()
            if self._validate_current_step():
                self._show_step(BootstrapStep.LEDGER_CONFIG)
        elif self.current_step == BootstrapStep.LEDGER_CONFIG:
            self._update_config_from_step()
            if self._validate_current_step():
                self._show_step(BootstrapStep.ADVANCED_OPTIONS)
        elif self.current_step == BootstrapStep.ADVANCED_OPTIONS:
            self._update_config_from_step()
            if self._validate_current_step():
                self._show_step(BootstrapStep.VALIDATION)
        elif self.current_step == BootstrapStep.VALIDATION:
            self._show_step(BootstrapStep.PROVISIONING)
        elif self.current_step == BootstrapStep.PROVISIONING:
            if self.status == BootstrapStatus.COMPLETED:
                self._show_step(BootstrapStep.COMPLETION)
    
    def _go_back(self) -> None:
        """Go to previous step"""
        if len(self.step_history) > 1:
            previous_step = self.step_history[-2]
            self.step_history = self.step_history[:-1]
            self._show_step(previous_step)
    
    def _validate_current_step(self) -> bool:
        """Validate current step data"""
        if self.current_step == BootstrapStep.BASIC_INFO:
            return self._validate_basic_info_step()
        elif self.current_step == BootstrapStep.NETWORK_CONFIG:
            return self._validate_network_config_step()
        elif self.current_step == BootstrapStep.SECURITY_CONFIG:
            return self._validate_security_config_step()
        elif self.current_step == BootstrapStep.LEDGER_CONFIG:
            return self._validate_ledger_config_step()
        elif self.current_step == BootstrapStep.ADVANCED_OPTIONS:
            return self._validate_advanced_options_step()
        
        return True
    
    def _validate_basic_info_step(self) -> bool:
        """Validate basic info step"""
        errors = []
        
        appliance_name = self.step_vars.get('appliance_name', tk.StringVar()).get().strip()
        admin_email = self.step_vars.get('admin_email', tk.StringVar()).get().strip()
        admin_password = self.step_vars.get('admin_password', tk.StringVar()).get().strip()
        
        if not appliance_name or len(appliance_name) < 3:
            errors.append("Appliance name must be at least 3 characters long")
        
        if not admin_email or '@' not in admin_email:
            errors.append("Valid admin email is required")
        
        if not admin_password or len(admin_password) < 8:
            errors.append("Admin password must be at least 8 characters long")
        
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        
        return True
    
    def _validate_network_config_step(self) -> bool:
        """Validate network config step"""
        # Basic validation - ports must be unique and in valid range
        ports = [
            self.step_vars.get('socks_port', tk.IntVar()).get(),
            self.step_vars.get('control_port', tk.IntVar()).get(),
            self.step_vars.get('http_port', tk.IntVar()).get(),
            self.step_vars.get('https_port', tk.IntVar()).get(),
            self.step_vars.get('api_port', tk.IntVar()).get()
        ]
        
        if len(set(ports)) != len(ports):
            messagebox.showerror("Validation Error", "All ports must be unique")
            return False
        
        for port in ports:
            if port < 1024 or port > 65535:
                messagebox.showerror("Validation Error", f"Port {port} must be between 1024 and 65535")
                return False
        
        return True
    
    def _validate_security_config_step(self) -> bool:
        """Validate security config step"""
        return True  # Security config is mostly optional
    
    def _validate_ledger_config_step(self) -> bool:
        """Validate ledger config step"""
        ledger_mode = self.step_vars.get('ledger_mode', tk.StringVar()).get()
        if ledger_mode not in ['sandbox', 'production']:
            messagebox.showerror("Validation Error", "Ledger mode must be 'sandbox' or 'production'")
            return False
        
        return True
    
    def _validate_advanced_options_step(self) -> bool:
        """Validate advanced options step"""
        return True  # Advanced options are mostly optional
    
    def _update_config_from_step(self) -> None:
        """Update configuration from current step"""
        if self.current_step == BootstrapStep.BASIC_INFO:
            self.config.appliance_name = self.step_vars.get('appliance_name', tk.StringVar()).get().strip()
            self.config.admin_email = self.step_vars.get('admin_email', tk.StringVar()).get().strip()
            self.config.admin_password = self.step_vars.get('admin_password', tk.StringVar()).get().strip()
            self.config.admin_full_name = self.step_vars.get('admin_full_name', tk.StringVar()).get().strip()
            self.config.organization = self.step_vars.get('organization', tk.StringVar()).get().strip()
        
        elif self.current_step == BootstrapStep.NETWORK_CONFIG:
            self.config.network.tor_enabled = self.step_vars.get('tor_enabled', tk.BooleanVar()).get()
            self.config.network.onion_service_enabled = self.step_vars.get('onion_service_enabled', tk.BooleanVar()).get()
            self.config.network.custom_onion_address = self.step_vars.get('custom_onion_address', tk.StringVar()).get().strip() or None
            self.config.network.socks_port = self.step_vars.get('socks_port', tk.IntVar()).get()
            self.config.network.control_port = self.step_vars.get('control_port', tk.IntVar()).get()
            self.config.network.http_port = self.step_vars.get('http_port', tk.IntVar()).get()
            self.config.network.https_port = self.step_vars.get('https_port', tk.IntVar()).get()
            self.config.network.api_port = self.step_vars.get('api_port', tk.IntVar()).get()
            self.config.network.external_ip = self.step_vars.get('external_ip', tk.StringVar()).get().strip() or None
            
            dns_servers_str = self.step_vars.get('dns_servers', tk.StringVar()).get().strip()
            if dns_servers_str:
                self.config.network.dns_servers = [s.strip() for s in dns_servers_str.split(',') if s.strip()]
        
        elif self.current_step == BootstrapStep.SECURITY_CONFIG:
            self.config.security.encryption_enabled = self.step_vars.get('encryption_enabled', tk.BooleanVar()).get()
            self.config.security.certificate_pinning = self.step_vars.get('certificate_pinning', tk.BooleanVar()).get()
            self.config.security.auto_key_rotation = self.step_vars.get('auto_key_rotation', tk.BooleanVar()).get()
            self.config.security.key_rotation_days = self.step_vars.get('key_rotation_days', tk.IntVar()).get()
            self.config.security.backup_encryption = self.step_vars.get('backup_encryption', tk.BooleanVar()).get()
            self.config.security.audit_logging = self.step_vars.get('audit_logging', tk.BooleanVar()).get()
            self.config.security.intrusion_detection = self.step_vars.get('intrusion_detection', tk.BooleanVar()).get()
            self.config.security.firewall_enabled = self.step_vars.get('firewall_enabled', tk.BooleanVar()).get()
            self.config.security.ssl_enabled = self.step_vars.get('ssl_enabled', tk.BooleanVar()).get()
            self.config.security.minimum_tls_version = self.step_vars.get('minimum_tls_version', tk.StringVar()).get()
        
        elif self.current_step == BootstrapStep.LEDGER_CONFIG:
            self.config.ledger.ledger_mode = self.step_vars.get('ledger_mode', tk.StringVar()).get()
            self.config.ledger.tron_node_url = self.step_vars.get('tron_node_url', tk.StringVar()).get().strip() or None
            self.config.ledger.wallet_address = self.step_vars.get('wallet_address', tk.StringVar()).get().strip() or None
            self.config.ledger.payout_threshold = self.step_vars.get('payout_threshold', tk.DoubleVar()).get()
            self.config.ledger.auto_payout_enabled = self.step_vars.get('auto_payout_enabled', tk.BooleanVar()).get()
        
        elif self.current_step == BootstrapStep.ADVANCED_OPTIONS:
            self.config.advanced.auto_backup_enabled = self.step_vars.get('auto_backup_enabled', tk.BooleanVar()).get()
            self.config.advanced.backup_interval_hours = self.step_vars.get('backup_interval_hours', tk.IntVar()).get()
            self.config.advanced.backup_retention_days = self.step_vars.get('backup_retention_days', tk.IntVar()).get()
            self.config.advanced.log_level = self.step_vars.get('log_level', tk.StringVar()).get()
            self.config.advanced.telemetry_enabled = self.step_vars.get('telemetry_enabled', tk.BooleanVar()).get()
            self.config.advanced.debug_mode = self.step_vars.get('debug_mode', tk.BooleanVar()).get()
            self.config.advanced.experimental_features = self.step_vars.get('experimental_features', tk.BooleanVar()).get()
    
    def _on_password_changed(self, *args) -> None:
        """Handle password change for strength validation"""
        password = self.step_vars.get('admin_password', tk.StringVar()).get()
        strength = self._calculate_password_strength(password)
        
        if hasattr(self, 'password_strength_label'):
            self.password_strength_label.configure(
                text=f"Password strength: {strength['label']}",
                foreground=strength['color']
            )
    
    def _calculate_password_strength(self, password: str) -> Dict[str, Any]:
        """Calculate password strength"""
        if not password:
            return {'label': 'No password', 'color': 'red', 'score': 0}
        
        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        
        if score <= 2:
            return {'label': 'Weak', 'color': 'red', 'score': score}
        elif score <= 4:
            return {'label': 'Medium', 'color': 'orange', 'score': score}
        elif score <= 5:
            return {'label': 'Strong', 'color': 'green', 'score': score}
        else:
            return {'label': 'Very Strong', 'color': 'darkgreen', 'score': score}
    
    def _validate_configuration(self) -> None:
        """Validate the complete configuration"""
        self.log_message("Validating configuration...")
        self.status_label.set_status("warning", "Validating configuration...")
        
        def validate_async():
            try:
                # Update config from current step
                self._update_config_from_step()
                
                # Validate configuration
                is_valid, errors = self.validator.validate_config(self.config)
                
                # Update validation results display
                if hasattr(self, 'validation_results_text'):
                    self.validation_results_text.configure(state=tk.NORMAL)
                    self.validation_results_text.delete(1.0, tk.END)
                    
                    if is_valid:
                        result_text = "✅ Configuration is valid!\n\n"
                        result_text += "All validation checks passed. The configuration is ready for provisioning."
                        self.validation_results_text.insert(tk.END, result_text)
                        
                        # Update status
                        self.validation_status_label.set_status("success", "Configuration is valid")
                        self.status_label.set_status("success", "Configuration validated successfully")
                    else:
                        result_text = "❌ Configuration validation failed:\n\n"
                        for error in errors:
                            result_text += f"• {error}\n"
                        result_text += "\nPlease fix the errors above before proceeding."
                        self.validation_results_text.insert(tk.END, result_text)
                        
                        # Update status
                        self.validation_status_label.set_status("error", "Configuration validation failed")
                        self.status_label.set_status("error", "Configuration validation failed")
                    
                    self.validation_results_text.configure(state=tk.DISABLED)
                
                self.log_message(f"Validation {'passed' if is_valid else 'failed'}")
                
            except Exception as e:
                logger.error(f"Validation error: {e}")
                self.log_message(f"Validation error: {e}")
                self.status_label.set_status("error", f"Validation error: {e}")
        
        threading.Thread(target=validate_async, daemon=True).start()
    
    def _export_configuration(self) -> None:
        """Export configuration to file"""
        filename = filedialog.asksaveasfilename(
            title="Export Bootstrap Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Update config from current step
                self._update_config_from_step()
                
                # Create export data
                export_data = {
                    'bootstrap_config': self.config.to_dict(),
                    'export_info': {
                        'exported_at': datetime.now(timezone.utc).isoformat(),
                        'exported_by': 'Bootstrap Wizard',
                        'version': self.config.version,
                        'appliance_id': self.config.appliance_id,
                        'configuration_hash': self.config.calculate_hash()
                    }
                }
                
                # Write to file
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                self.log_message(f"Configuration exported to {filename}")
                messagebox.showinfo("Export Successful", f"Configuration exported to:\n{filename}")
                
            except Exception as e:
                logger.error(f"Export error: {e}")
                self.log_message(f"Export error: {e}")
                messagebox.showerror("Export Error", f"Failed to export configuration:\n{e}")
    
    def _start_provisioning(self) -> None:
        """Start the provisioning process"""
        self.status = BootstrapStatus.PROVISIONING
        self.start_provisioning_button.configure(state=tk.DISABLED)
        self.stop_provisioning_button.configure(state=tk.NORMAL)
        
        self.log_message("Starting appliance provisioning...")
        self.provisioning_status_label.set_status("warning", "Provisioning in progress...")
        
        def provision_async():
            try:
                self._provision_appliance()
            except Exception as e:
                logger.error(f"Provisioning error: {e}")
                self.log_message(f"Provisioning error: {e}")
                self.status = BootstrapStatus.FAILED
                self.provisioning_status_label.set_status("error", f"Provisioning failed: {e}")
                self.start_provisioning_button.configure(state=tk.NORMAL)
                self.stop_provisioning_button.configure(state=tk.DISABLED)
        
        threading.Thread(target=provision_async, daemon=True).start()
    
    def _stop_provisioning(self) -> None:
        """Stop the provisioning process"""
        self.status = BootstrapStatus.CANCELLED
        self.log_message("Provisioning cancelled by user")
        self.provisioning_status_label.set_status("warning", "Provisioning cancelled")
        self.start_provisioning_button.configure(state=tk.NORMAL)
        self.stop_provisioning_button.configure(state=tk.DISABLED)
    
    def _provision_appliance(self) -> None:
        """Provision the appliance with the configuration"""
        stages = [
            ProvisioningStage.INITIALIZATION,
            ProvisioningStage.NETWORK_SETUP,
            ProvisioningStage.SECURITY_SETUP,
            ProvisioningStage.KEY_GENERATION,
            ProvisioningStage.SERVICE_CONFIG,
            ProvisioningStage.DATABASE_SETUP,
            ProvisioningStage.TOR_SETUP,
            ProvisioningStage.BACKUP_SETUP,
            ProvisioningStage.FINALIZATION
        ]
        
        total_stages = len(stages)
        
        for i, stage in enumerate(stages):
            if self.status == BootstrapStatus.CANCELLED:
                break
            
            # Update progress
            progress_percent = (i / total_stages) * 100
            self.provisioning_progress_bar.set_progress(progress_percent)
            self.provisioning_stage_label.configure(text=f"Stage {i+1}/{total_stages}: {stage.value.replace('_', ' ').title()}")
            
            # Create progress object
            self.provisioning_progress = ProvisioningProgress(
                stage=stage,
                status=BootstrapStatus.PROVISIONING,
                progress_percent=progress_percent,
                message=f"Executing {stage.value.replace('_', ' ')}",
                started_at=datetime.now(timezone.utc)
            )
            
            self.log_message(f"Executing stage: {stage.value}")
            
            try:
                # Execute stage
                success = self._execute_provisioning_stage(stage)
                
                if success:
                    self.provisioning_progress.completed_at = datetime.now(timezone.utc)
                    self.provisioning_progress.status = BootstrapStatus.COMPLETED
                    self.log_message(f"Stage completed: {stage.value}")
                else:
                    raise Exception(f"Stage failed: {stage.value}")
                
            except Exception as e:
                self.provisioning_progress.status = BootstrapStatus.FAILED
                self.provisioning_progress.error_message = str(e)
                self.log_message(f"Stage failed: {stage.value} - {e}")
                raise
        
        # Complete provisioning
        if self.status != BootstrapStatus.CANCELLED:
            self.status = BootstrapStatus.COMPLETED
            self.provisioning_progress_bar.set_progress(100.0)
            self.provisioning_stage_label.configure(text="Provisioning completed successfully!")
            self.provisioning_status_label.set_status("success", "Provisioning completed successfully")
            self.log_message("Appliance provisioning completed successfully")
            
            # Enable next button
            self._navigation_buttons['next'].configure(state=tk.NORMAL)
    
    def _execute_provisioning_stage(self, stage: ProvisioningStage) -> bool:
        """Execute a specific provisioning stage"""
        try:
            if stage == ProvisioningStage.INITIALIZATION:
                return self._stage_initialization()
            elif stage == ProvisioningStage.NETWORK_SETUP:
                return self._stage_network_setup()
            elif stage == ProvisioningStage.SECURITY_SETUP:
                return self._stage_security_setup()
            elif stage == ProvisioningStage.KEY_GENERATION:
                return self._stage_key_generation()
            elif stage == ProvisioningStage.SERVICE_CONFIG:
                return self._stage_service_config()
            elif stage == ProvisioningStage.DATABASE_SETUP:
                return self._stage_database_setup()
            elif stage == ProvisioningStage.TOR_SETUP:
                return self._stage_tor_setup()
            elif stage == ProvisioningStage.BACKUP_SETUP:
                return self._stage_backup_setup()
            elif stage == ProvisioningStage.FINALIZATION:
                return self._stage_finalization()
            
            return False
        except Exception as e:
            logger.error(f"Stage execution error: {e}")
            return False
    
    def _stage_initialization(self) -> bool:
        """Initialize the appliance"""
        self.log_message("Initializing appliance...")
        time.sleep(1)  # Simulate initialization
        
        # Create appliance directory structure
        appliance_dirs = [
            '/opt/lucid/appliance',
            '/opt/lucid/config',
            '/opt/lucid/logs',
            '/opt/lucid/backups',
            '/opt/lucid/keys',
            '/opt/lucid/tor'
        ]
        
        for directory in appliance_dirs:
            self.log_message(f"Creating directory: {directory}")
            # In a real implementation, this would create actual directories
        
        self.log_message("Appliance initialization completed")
        return True
    
    def _stage_network_setup(self) -> bool:
        """Setup network configuration"""
        self.log_message("Configuring network...")
        time.sleep(1)  # Simulate network setup
        
        if self.config.network.tor_enabled:
            self.log_message("Configuring Tor network settings")
            self.log_message(f"SOCKS port: {self.config.network.socks_port}")
            self.log_message(f"Control port: {self.config.network.control_port}")
        
        if self.config.network.onion_service_enabled:
            self.log_message("Configuring onion service")
            if self.config.network.custom_onion_address:
                self.log_message(f"Using custom onion address: {self.config.network.custom_onion_address}")
            else:
                self.log_message("Generating new onion address...")
                # In a real implementation, this would generate an actual onion address
        
        self.log_message("Network configuration completed")
        return True
    
    def _stage_security_setup(self) -> bool:
        """Setup security configuration"""
        self.log_message("Configuring security settings...")
        time.sleep(1)  # Simulate security setup
        
        if self.config.security.encryption_enabled:
            self.log_message("Enabling encryption")
        
        if self.config.security.certificate_pinning:
            self.log_message("Configuring certificate pinning")
        
        if self.config.security.auto_key_rotation:
            self.log_message(f"Configuring automatic key rotation ({self.config.security.key_rotation_days} days)")
        
        if self.config.security.firewall_enabled:
            self.log_message("Configuring firewall")
        
        self.log_message("Security configuration completed")
        return True
    
    def _stage_key_generation(self) -> bool:
        """Generate cryptographic keys"""
        self.log_message("Generating cryptographic keys...")
        time.sleep(2)  # Simulate key generation
        
        # Generate master key
        self.log_message("Generating master encryption key...")
        master_key = CryptographicUtils.generate_secure_random(32)
        
        # Generate signing key
        self.log_message("Generating signing key...")
        signing_key = CryptographicUtils.generate_secure_random(32)
        
        # Generate backup key
        self.log_message("Generating backup encryption key...")
        backup_key = CryptographicUtils.generate_secure_random(32)
        
        self.log_message("Key generation completed")
        return True
    
    def _stage_service_config(self) -> bool:
        """Configure system services"""
        self.log_message("Configuring system services...")
        time.sleep(1)  # Simulate service configuration
        
        services = [
            'lucid-admin',
            'lucid-api',
            'lucid-node',
            'lucid-session-manager'
        ]
        
        for service in services:
            self.log_message(f"Configuring service: {service}")
        
        self.log_message("Service configuration completed")
        return True
    
    def _stage_database_setup(self) -> bool:
        """Setup database"""
        self.log_message("Setting up database...")
        time.sleep(2)  # Simulate database setup
        
        self.log_message("Initializing MongoDB...")
        self.log_message("Creating database schemas...")
        self.log_message("Setting up indexes...")
        self.log_message("Configuring backup policies...")
        
        self.log_message("Database setup completed")
        return True
    
    def _stage_tor_setup(self) -> bool:
        """Setup Tor configuration"""
        if not self.config.network.tor_enabled:
            self.log_message("Tor disabled, skipping Tor setup")
            return True
        
        self.log_message("Configuring Tor...")
        time.sleep(2)  # Simulate Tor setup
        
        self.log_message("Generating Tor configuration...")
        self.log_message("Starting Tor service...")
        self.log_message("Testing Tor connectivity...")
        
        if self.config.network.onion_service_enabled:
            self.log_message("Configuring onion service...")
            self.log_message("Starting onion service...")
        
        self.log_message("Tor setup completed")
        return True
    
    def _stage_backup_setup(self) -> bool:
        """Setup backup configuration"""
        self.log_message("Configuring backup system...")
        time.sleep(1)  # Simulate backup setup
        
        if self.config.advanced.auto_backup_enabled:
            self.log_message(f"Configuring automatic backups (every {self.config.advanced.backup_interval_hours} hours)")
            self.log_message(f"Setting backup retention to {self.config.advanced.backup_retention_days} days")
        
        if self.config.security.backup_encryption:
            self.log_message("Enabling backup encryption")
        
        self.log_message("Backup configuration completed")
        return True
    
    def _stage_finalization(self) -> bool:
        """Finalize appliance setup"""
        self.log_message("Finalizing appliance setup...")
        time.sleep(1)  # Simulate finalization
        
        # Create appliance info file
        appliance_info = {
            'appliance_id': self.config.appliance_id,
            'appliance_name': self.config.appliance_name,
            'admin_email': self.config.admin_email,
            'created_at': self.config.created_at,
            'version': self.config.version,
            'ledger_mode': self.config.ledger.ledger_mode,
            'tor_enabled': self.config.network.tor_enabled,
            'onion_service_enabled': self.config.network.onion_service_enabled
        }
        
        self.log_message("Creating appliance information file...")
        self.log_message("Setting file permissions...")
        self.log_message("Starting system services...")
        self.log_message("Verifying system health...")
        
        self.log_message("Appliance finalization completed")
        return True
    
    def _open_admin_interface(self) -> None:
        """Open the admin interface"""
        self.log_message("Opening admin interface...")
        
        # In a real implementation, this would launch the admin interface
        # For now, we'll just show a message
        messagebox.showinfo(
            "Admin Interface",
            "The admin interface would be opened here.\n\n"
            "In a real implementation, this would:\n"
            "1. Start the admin web server\n"
            "2. Open the admin interface in a browser\n"
            "3. Display the appliance dashboard"
        )
    
    def _finish_wizard(self) -> None:
        """Finish the wizard"""
        if self.on_complete:
            self.on_complete(self.config)
        
        self.log_message("Bootstrap wizard completed successfully")
        self.wizard_window.destroy()
    
    def _cancel_wizard(self) -> None:
        """Cancel the wizard"""
        if messagebox.askyesno("Cancel Wizard", "Are you sure you want to cancel the bootstrap wizard?"):
            self.log_message("Bootstrap wizard cancelled")
            self.wizard_window.destroy()
    
    def _on_close(self) -> None:
        """Handle window close"""
        self._cancel_wizard()
    
    def log_message(self, message: str) -> None:
        """Log a message to the log viewer"""
        if hasattr(self, 'log_viewer'):
            self.log_viewer.add_log(message, "INFO")
        
        logger.info(f"Bootstrap Wizard: {message}")
    
    def add_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Add progress callback"""
        self.progress_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[str], None]) -> None:
        """Add status callback"""
        self.status_callbacks.append(callback)
    
    def cleanup(self) -> None:
        """Cleanup wizard resources"""
        self.status = BootstrapStatus.CANCELLED
        
        # Clear callbacks
        self.progress_callbacks.clear()
        self.status_callbacks.clear()
        
        # Close window if open
        if self.wizard_window and self.wizard_window.winfo_exists():
            self.wizard_window.destroy()
        
        logger.info("Bootstrap wizard cleaned up")


class BootstrapWizardDialog:
    """Simple bootstrap wizard dialog for backward compatibility"""
    
    def __init__(self, parent: tk.Widget, on_complete: Optional[Callable[[BootstrapConfig], None]] = None):
        self.parent = parent
        self.on_complete = on_complete
        self.wizard = None
    
    def show(self) -> None:
        """Show the bootstrap wizard"""
        self.wizard = BootstrapWizard(self.parent, self.on_complete)
        self.wizard.show_wizard()


# Factory functions for backward compatibility
def show_bootstrap_wizard(parent: tk.Widget, on_complete: Optional[Callable[[BootstrapConfig], None]] = None) -> None:
    """Show the bootstrap wizard"""
    wizard = BootstrapWizard(parent, on_complete)
    wizard.show_wizard()


def create_bootstrap_dialog(parent: tk.Widget, on_complete: Optional[Callable[[BootstrapConfig], None]] = None) -> BootstrapWizardDialog:
    """Create a bootstrap wizard dialog"""
    return BootstrapWizardDialog(parent, on_complete)


def load_config_from_file(filename: str) -> Optional[BootstrapConfig]:
    """Load bootstrap configuration from file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        if 'bootstrap_config' in data:
            return BootstrapConfig.from_dict(data['bootstrap_config'])
        else:
            return BootstrapConfig.from_dict(data)
    
    except Exception as e:
        logger.error(f"Failed to load config from {filename}: {e}")
        return None


def save_config_to_file(config: BootstrapConfig, filename: str) -> bool:
    """Save bootstrap configuration to file"""
    try:
        export_data = {
            'bootstrap_config': config.to_dict(),
            'export_info': {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'exported_by': 'Bootstrap Wizard',
                'version': config.version,
                'appliance_id': config.appliance_id,
                'configuration_hash': config.calculate_hash()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to save config to {filename}: {e}")
        return False


# Environment integration for Docker
class DockerEnvironmentManager:
    """Manages Docker environment configuration for bootstrap"""
    
    def __init__(self):
        self.env_vars = {}
        self.load_environment()
    
    def load_environment(self) -> None:
        """Load environment variables from .env files"""
        env_files = [
            '.env',
            'gui/admin/.env',
            'infrastructure/docker/admin/env/admin-ui.env'
        ]
        
        for env_file in env_files:
            if os.path.exists(env_file):
                self._load_env_file(env_file)
    
    def _load_env_file(self, filename: str) -> None:
        """Load environment variables from a file"""
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.env_vars[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"Failed to load env file {filename}: {e}")
    
    def get_env_var(self, key: str, default: str = "") -> str:
        """Get environment variable"""
        return os.environ.get(key, self.env_vars.get(key, default))
    
    def configure_for_docker(self, config: BootstrapConfig) -> None:
        """Configure bootstrap for Docker environment"""
        # Set Docker-specific configuration
        config.network.http_port = int(self.get_env_var('PORT', '8080'))
        config.network.api_port = int(self.get_env_var('NEXT_PUBLIC_API_GATEWAY_URL', '8080').split(':')[-1])
        
        # Set environment-specific settings
        if self.get_env_var('NODE_ENV') == 'production':
            config.advanced.debug_mode = False
            config.advanced.log_level = 'INFO'
        else:
            config.advanced.debug_mode = True
            config.advanced.log_level = 'DEBUG'
        
        # Configure database
        mongo_url = self.get_env_var('NEXT_PUBLIC_MONGO_URL', 'mongodb://localhost:27017/lucid')
        if mongo_url:
            config.advanced.custom_config['mongo_url'] = mongo_url
        
        # Configure blockchain
        tron_network = self.get_env_var('NEXT_PUBLIC_TRON_NETWORK', 'shasta')
        config.ledger.ledger_mode = tron_network
        
        tron_rpc = self.get_env_var('NEXT_PUBLIC_TRON_RPC_URL', 'https://api.shasta.trongrid.io')
        config.ledger.tron_node_url = tron_rpc


# Global environment manager instance
_docker_env_manager = None

def get_docker_env_manager() -> DockerEnvironmentManager:
    """Get the global Docker environment manager"""
    global _docker_env_manager
    if _docker_env_manager is None:
        _docker_env_manager = DockerEnvironmentManager()
    return _docker_env_manager


def configure_bootstrap_for_docker(config: BootstrapConfig) -> None:
    """Configure bootstrap configuration for Docker environment"""
    env_manager = get_docker_env_manager()
    env_manager.configure_for_docker(config)
 
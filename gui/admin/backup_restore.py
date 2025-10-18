# Path: gui/admin/backup_restore.py
"""
Comprehensive backup and restore operations for Lucid RDP GUI.
Provides system-wide backup functionality for configurations, keys, sessions, and user data.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import logging
import os
import shutil
import zipfile
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any, List, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib
import secrets
from contextlib import contextmanager

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from ..core.config_manager import get_config_manager, ConfigScope
from ..core.security import get_security_validator, CryptographicUtils

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Backup type enumeration"""
    FULL = "full"                    # Complete system backup
    CONFIG = "config"               # Configuration only
    KEYS = "keys"                   # Cryptographic keys only
    SESSIONS = "sessions"           # Session data only
    USER_DATA = "user_data"         # User-specific data
    DIAGNOSTICS = "diagnostics"     # Diagnostic logs and history
    CUSTOM = "custom"               # Custom selection


class BackupStatus(Enum):
    """Backup status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RestoreStatus(Enum):
    """Restore status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupItem:
    """Individual backup item"""
    item_id: str
    item_type: str
    source_path: str
    relative_path: str
    size_bytes: int
    checksum: str
    included: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupItem':
        """Create BackupItem from dictionary"""
        return cls(**data)


@dataclass
class BackupManifest:
    """Backup manifest containing metadata"""
    backup_id: str
    backup_name: str
    backup_type: BackupType
    created_at: datetime
    created_by: str
    version: str = "1.0.0"
    description: str = ""
    encryption_enabled: bool = True
    compression_enabled: bool = True
    total_size: int = 0
    item_count: int = 0
    checksum: str = ""
    items: List[BackupItem] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['backup_type'] = self.backup_type.value
        data['items'] = [item.to_dict() for item in self.items]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupManifest':
        """Create BackupManifest from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['backup_type'] = BackupType(data['backup_type'])
        data['items'] = [BackupItem.from_dict(item) for item in data.get('items', [])]
        return cls(**data)


@dataclass
class BackupOperation:
    """Backup operation tracking"""
    operation_id: str
    operation_type: str  # "backup" or "restore"
    status: Union[BackupStatus, RestoreStatus]
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0
    current_item: str = ""
    error_message: str = ""
    manifest: Optional[BackupManifest] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        data['status'] = self.status.value
        if self.manifest:
            data['manifest'] = self.manifest.to_dict()
        return data


class BackupEncryption:
    """Handles encryption for backup files"""
    
    def __init__(self, password: Optional[str] = None):
        self.password = password
        self._key = None
        if password:
            self._derive_key()
    
    def _derive_key(self) -> None:
        """Derive encryption key from password"""
        salt = b'lucid_backup_salt'  # In production, use random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self._key = kdf.derive(self.password.encode())
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using ChaCha20-Poly1305"""
        if not self._key:
            return data
        
        nonce = secrets.token_bytes(12)
        cipher = ChaCha20Poly1305(self._key)
        encrypted_data = cipher.encrypt(nonce, data, None)
        return nonce + encrypted_data
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using ChaCha20-Poly1305"""
        if not self._key:
            return encrypted_data
        
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        cipher = ChaCha20Poly1305(self._key)
        return cipher.decrypt(nonce, ciphertext, None)


class BackupManager:
    """Main backup and restore manager"""
    
    def __init__(self, parent_frame: tk.Frame, node_api_url: str = "http://localhost:8080"):
        self.parent_frame = parent_frame
        self.node_api_url = node_api_url.rstrip('/')
        
        # Configuration
        self.config_manager = get_config_manager()
        self.security_validator = get_security_validator()
        
        # Data storage
        self.backup_operations: List[BackupOperation] = []
        self.backup_manifests: List[BackupManifest] = []
        self.current_operation: Optional[BackupOperation] = None
        
        # Backup settings
        self.backup_directory = Path.home() / ".lucid" / "backups"
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        # Callbacks
        self.progress_callbacks: List[Callable[[float, str], None]] = []
        self.status_callbacks: List[Callable[[str], None]] = []
        
        # Setup GUI
        self.setup_gui()
        
        # Load backup history
        self.load_backup_history()
    
    def setup_gui(self) -> None:
        """Setup the backup/restore GUI."""
        # Main container
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_backup_tab()
        self.create_restore_tab()
        self.create_schedule_tab()
        self.create_history_tab()
        self.create_settings_tab()
    
    def create_backup_tab(self) -> None:
        """Create backup configuration tab."""
        self.backup_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.backup_frame, text="Backup")
        
        # Backup type selection
        type_frame = ttk.LabelFrame(self.backup_frame, text="Backup Type")
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.backup_type_var = tk.StringVar(value=BackupType.FULL.value)
        backup_types = [
            (BackupType.FULL.value, "Full System Backup"),
            (BackupType.CONFIG.value, "Configuration Only"),
            (BackupType.KEYS.value, "Keys Only"),
            (BackupType.SESSIONS.value, "Sessions Only"),
            (BackupType.USER_DATA.value, "User Data Only"),
            (BackupType.DIAGNOSTICS.value, "Diagnostics Only"),
            (BackupType.CUSTOM.value, "Custom Selection")
        ]
        
        for value, text in backup_types:
            ttk.Radiobutton(type_frame, text=text, variable=self.backup_type_var, 
                           value=value, command=self.on_backup_type_changed).pack(anchor=tk.W, padx=5, pady=2)
        
        # Backup details
        details_frame = ttk.LabelFrame(self.backup_frame, text="Backup Details")
        details_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Backup name
        name_frame = ttk.Frame(details_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(name_frame, text="Backup Name:").pack(side=tk.LEFT)
        self.backup_name_var = tk.StringVar(value=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        name_entry = ttk.Entry(name_frame, textvariable=self.backup_name_var)
        name_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Description
        desc_frame = ttk.Frame(details_frame)
        desc_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(desc_frame, text="Description:").pack(anchor=tk.W)
        self.backup_desc_text = tk.Text(desc_frame, height=3, wrap=tk.WORD)
        self.backup_desc_text.pack(fill=tk.X, pady=(2, 0))
        
        # Backup options
        options_frame = ttk.LabelFrame(self.backup_frame, text="Backup Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Encryption
        encrypt_frame = ttk.Frame(options_frame)
        encrypt_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.encrypt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(encrypt_frame, text="Encrypt backup", variable=self.encrypt_var).pack(anchor=tk.W)
        
        # Compression
        comp_frame = ttk.Frame(options_frame)
        comp_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.compress_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(comp_frame, text="Compress backup", variable=self.compress_var).pack(anchor=tk.W)
        
        # Custom selection (initially hidden)
        self.custom_frame = ttk.LabelFrame(self.backup_frame, text="Custom Selection")
        
        # Backup actions
        actions_frame = ttk.Frame(self.backup_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(actions_frame, text="Start Backup", command=self.start_backup).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Preview Items", command=self.preview_backup_items).pack(side=tk.LEFT, padx=5)
        
        # Progress display
        progress_frame = ttk.LabelFrame(self.backup_frame, text="Backup Progress")
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(pady=5)
        
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_restore_tab(self) -> None:
        """Create restore configuration tab."""
        self.restore_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.restore_frame, text="Restore")
        
        # Available backups
        backups_frame = ttk.LabelFrame(self.restore_frame, text="Available Backups")
        backups_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Backup list
        columns = ('name', 'type', 'date', 'size', 'items')
        self.restore_tree = ttk.Treeview(backups_frame, columns=columns, show='headings')
        
        self.restore_tree.heading('name', text='Backup Name')
        self.restore_tree.heading('type', text='Type')
        self.restore_tree.heading('date', text='Date')
        self.restore_tree.heading('size', text='Size')
        self.restore_tree.heading('items', text='Items')
        
        restore_scroll = ttk.Scrollbar(backups_frame, orient=tk.VERTICAL, command=self.restore_tree.yview)
        self.restore_tree.configure(yscrollcommand=restore_scroll.set)
        
        self.restore_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        restore_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Restore options
        options_frame = ttk.LabelFrame(self.restore_frame, text="Restore Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Overwrite existing
        overwrite_frame = ttk.Frame(options_frame)
        overwrite_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(overwrite_frame, text="Overwrite existing files", variable=self.overwrite_var).pack(anchor=tk.W)
        
        # Restore actions
        actions_frame = ttk.Frame(self.restore_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(actions_frame, text="Restore Selected", command=self.start_restore).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Import Backup", command=self.import_backup).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="View Details", command=self.view_backup_details).pack(side=tk.LEFT, padx=5)
        
        # Restore progress
        progress_frame = ttk.LabelFrame(self.restore_frame, text="Restore Progress")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.restore_progress_var = tk.DoubleVar()
        self.restore_progress_bar = ttk.Progressbar(progress_frame, variable=self.restore_progress_var, maximum=100)
        self.restore_progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.restore_status_label = ttk.Label(progress_frame, text="Ready")
        self.restore_status_label.pack(pady=5)
    
    def create_schedule_tab(self) -> None:
        """Create backup scheduling tab."""
        self.schedule_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.schedule_frame, text="Schedule")
        
        # Schedule settings
        settings_frame = ttk.LabelFrame(self.schedule_frame, text="Scheduled Backups")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Enable scheduled backups
        enable_frame = ttk.Frame(settings_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.schedule_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(enable_frame, text="Enable scheduled backups", variable=self.schedule_enabled_var).pack(anchor=tk.W)
        
        # Schedule frequency
        freq_frame = ttk.Frame(settings_frame)
        freq_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(freq_frame, text="Frequency:").pack(side=tk.LEFT)
        self.schedule_freq_var = tk.StringVar(value="daily")
        freq_combo = ttk.Combobox(freq_frame, textvariable=self.schedule_freq_var,
                                 values=["hourly", "daily", "weekly", "monthly"], width=15)
        freq_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Schedule time
        time_frame = ttk.Frame(settings_frame)
        time_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(time_frame, text="Time:").pack(side=tk.LEFT)
        self.schedule_time_var = tk.StringVar(value="02:00")
        time_entry = ttk.Entry(time_frame, textvariable=self.schedule_time_var, width=10)
        time_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Schedule actions
        actions_frame = ttk.Frame(self.schedule_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(actions_frame, text="Save Schedule", command=self.save_schedule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Test Schedule", command=self.test_schedule).pack(side=tk.LEFT, padx=5)
        
        # Schedule status
        status_frame = ttk.LabelFrame(self.schedule_frame, text="Schedule Status")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.schedule_status_text = scrolledtext.ScrolledText(status_frame, height=6, wrap=tk.WORD)
        self.schedule_status_text.pack(fill=tk.X, padx=5, pady=5)
    
    def create_history_tab(self) -> None:
        """Create backup history tab."""
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="History")
        
        # History list
        history_frame = ttk.LabelFrame(self.history_frame, text="Backup History")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('operation', 'name', 'type', 'status', 'date', 'size')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings')
        
        self.history_tree.heading('operation', text='Operation')
        self.history_tree.heading('name', text='Name')
        self.history_tree.heading('type', text='Type')
        self.history_tree.heading('status', text='Status')
        self.history_tree.heading('date', text='Date')
        self.history_tree.heading('size', text='Size')
        
        history_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # History actions
        actions_frame = ttk.Frame(self.history_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(actions_frame, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Export History", command=self.export_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Clear History", command=self.clear_history).pack(side=tk.LEFT, padx=5)
    
    def create_settings_tab(self) -> None:
        """Create backup settings tab."""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Backup location
        location_frame = ttk.LabelFrame(self.settings_frame, text="Backup Location")
        location_frame.pack(fill=tk.X, padx=10, pady=5)
        
        loc_frame = ttk.Frame(location_frame)
        loc_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(loc_frame, text="Directory:").pack(side=tk.LEFT)
        self.backup_dir_var = tk.StringVar(value=str(self.backup_directory))
        dir_entry = ttk.Entry(loc_frame, textvariable=self.backup_dir_var)
        dir_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        ttk.Button(loc_frame, text="Browse", command=self.browse_backup_directory).pack(side=tk.RIGHT)
        
        # Retention settings
        retention_frame = ttk.LabelFrame(self.settings_frame, text="Retention Settings")
        retention_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Keep backups for
        keep_frame = ttk.Frame(retention_frame)
        keep_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(keep_frame, text="Keep backups for:").pack(side=tk.LEFT)
        self.retention_days_var = tk.StringVar(value="30")
        keep_entry = ttk.Entry(keep_frame, textvariable=self.retention_days_var, width=10)
        keep_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(keep_frame, text="days").pack(side=tk.LEFT, padx=(5, 0))
        
        # Maximum backups
        max_frame = ttk.Frame(retention_frame)
        max_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(max_frame, text="Maximum backups:").pack(side=tk.LEFT)
        self.max_backups_var = tk.StringVar(value="10")
        max_entry = ttk.Entry(max_frame, textvariable=self.max_backups_var, width=10)
        max_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Settings actions
        actions_frame = ttk.Frame(self.settings_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(actions_frame, text="Save Settings", command=self.save_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions_frame, text="Reset to Defaults", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
    
    def on_backup_type_changed(self) -> None:
        """Handle backup type selection change."""
        backup_type = self.backup_type_var.get()
        
        if backup_type == BackupType.CUSTOM.value:
            self.custom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            self.create_custom_selection()
        else:
            self.custom_frame.pack_forget()
    
    def create_custom_selection(self) -> None:
        """Create custom backup selection interface."""
        # Clear existing widgets
        for widget in self.custom_frame.winfo_children():
            widget.destroy()
        
        # Create treeview for custom selection
        columns = ('item', 'type', 'size', 'included')
        self.custom_tree = ttk.Treeview(self.custom_frame, columns=columns, show='headings')
        
        self.custom_tree.heading('item', text='Item')
        self.custom_tree.heading('type', text='Type')
        self.custom_tree.heading('size', text='Size')
        self.custom_tree.heading('included', text='Included')
        
        custom_scroll = ttk.Scrollbar(self.custom_frame, orient=tk.VERTICAL, command=self.custom_tree.yview)
        self.custom_tree.configure(yscrollcommand=custom_scroll.set)
        
        self.custom_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        custom_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Populate with available items
        self.populate_custom_items()
        
        # Double-click to toggle inclusion
        self.custom_tree.bind('<Double-1>', self.toggle_custom_item)
    
    def populate_custom_items(self) -> None:
        """Populate custom selection with available items."""
        items = self.get_backup_items()
        
        for item in items:
            included_text = "Yes" if item.included else "No"
            size_str = self.format_bytes(item.size_bytes)
            
            self.custom_tree.insert('', 'end', values=(
                item.relative_path,
                item.item_type,
                size_str,
                included_text
            ), tags=(item.item_id,))
    
    def toggle_custom_item(self, event) -> None:
        """Toggle custom item inclusion."""
        selection = self.custom_tree.selection()
        if not selection:
            return
        
        item = self.custom_tree.item(selection[0])
        item_id = item['tags'][0]
        
        # Find and toggle the item
        for backup_item in self.get_backup_items():
            if backup_item.item_id == item_id:
                backup_item.included = not backup_item.included
                break
        
        # Refresh display
        self.populate_custom_items()
    
    def get_backup_items(self) -> List[BackupItem]:
        """Get list of items available for backup."""
        items = []
        
        # Configuration files
        config_dir = Path.home() / ".lucid" / "config"
        if config_dir.exists():
            for config_file in config_dir.glob("*.json"):
                items.append(BackupItem(
                    item_id=f"config_{config_file.name}",
                    item_type="Configuration",
                    source_path=str(config_file),
                    relative_path=f"config/{config_file.name}",
                    size_bytes=config_file.stat().st_size,
                    checksum=self.calculate_file_checksum(config_file)
                ))
        
        # Key files
        keys_dir = Path.home() / ".lucid" / "keys"
        if keys_dir.exists():
            for key_file in keys_dir.glob("*"):
                items.append(BackupItem(
                    item_id=f"key_{key_file.name}",
                    item_type="Key",
                    source_path=str(key_file),
                    relative_path=f"keys/{key_file.name}",
                    size_bytes=key_file.stat().st_size,
                    checksum=self.calculate_file_checksum(key_file)
                ))
        
        # Session data
        sessions_dir = Path.home() / ".lucid" / "sessions"
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*"):
                items.append(BackupItem(
                    item_id=f"session_{session_file.name}",
                    item_type="Session",
                    source_path=str(session_file),
                    relative_path=f"sessions/{session_file.name}",
                    size_bytes=session_file.stat().st_size,
                    checksum=self.calculate_file_checksum(session_file)
                ))
        
        return items
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def start_backup(self) -> None:
        """Start backup operation."""
        backup_name = self.backup_name_var.get().strip()
        if not backup_name:
            messagebox.showerror("Error", "Please enter a backup name")
            return
        
        backup_type = BackupType(self.backup_type_var.get())
        
        # Create backup operation
        operation = BackupOperation(
            operation_id=str(uuid.uuid4()),
            operation_type="backup",
            status=BackupStatus.PENDING,
            started_at=datetime.now(timezone.utc)
        )
        
        self.current_operation = operation
        self.backup_operations.append(operation)
        
        # Start backup in separate thread
        backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
        backup_thread.start()
    
    def _backup_worker(self) -> None:
        """Backup worker thread."""
        try:
            operation = self.current_operation
            operation.status = BackupStatus.IN_PROGRESS
            
            # Get backup items
            if self.backup_type_var.get() == BackupType.CUSTOM.value:
                items = [item for item in self.get_backup_items() if item.included]
            else:
                items = self.get_backup_items_for_type(BackupType(self.backup_type_var.get()))
            
            # Create manifest
            manifest = BackupManifest(
                backup_id=operation.operation_id,
                backup_name=self.backup_name_var.get(),
                backup_type=BackupType(self.backup_type_var.get()),
                created_at=datetime.now(timezone.utc),
                created_by="admin",
                description=self.backup_desc_text.get("1.0", tk.END).strip(),
                encryption_enabled=self.encrypt_var.get(),
                compression_enabled=self.compress_var.get(),
                items=items
            )
            
            operation.manifest = manifest
            
            # Create backup file
            backup_file = self.create_backup_file(manifest, operation)
            
            operation.status = BackupStatus.COMPLETED
            operation.completed_at = datetime.now(timezone.utc)
            
            self.update_progress(100, "Backup completed successfully")
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            if self.current_operation:
                self.current_operation.status = BackupStatus.FAILED
                self.current_operation.error_message = str(e)
            self.update_progress(0, f"Backup failed: {e}")
    
    def get_backup_items_for_type(self, backup_type: BackupType) -> List[BackupItem]:
        """Get backup items for specific backup type."""
        items = []
        
        if backup_type == BackupType.FULL:
            items = self.get_backup_items()
        elif backup_type == BackupType.CONFIG:
            config_dir = Path.home() / ".lucid" / "config"
            if config_dir.exists():
                for config_file in config_dir.glob("*.json"):
                    items.append(BackupItem(
                        item_id=f"config_{config_file.name}",
                        item_type="Configuration",
                        source_path=str(config_file),
                        relative_path=f"config/{config_file.name}",
                        size_bytes=config_file.stat().st_size,
                        checksum=self.calculate_file_checksum(config_file)
                    ))
        elif backup_type == BackupType.KEYS:
            keys_dir = Path.home() / ".lucid" / "keys"
            if keys_dir.exists():
                for key_file in keys_dir.glob("*"):
                    items.append(BackupItem(
                        item_id=f"key_{key_file.name}",
                        item_type="Key",
                        source_path=str(key_file),
                        relative_path=f"keys/{key_file.name}",
                        size_bytes=key_file.stat().st_size,
                        checksum=self.calculate_file_checksum(key_file)
                    ))
        
        return items
    
    def create_backup_file(self, manifest: BackupManifest, operation: BackupOperation) -> Path:
        """Create the actual backup file."""
        backup_filename = f"{manifest.backup_name}_{manifest.created_at.strftime('%Y%m%d_%H%M%S')}.lbackup"
        backup_path = self.backup_directory / backup_filename
        
        # Create temporary directory for backup contents
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy files to temporary directory
            total_items = len(manifest.items)
            for i, item in enumerate(manifest.items):
                self.update_progress(
                    (i / total_items) * 90,
                    f"Backing up {item.relative_path}"
                )
                
                source_path = Path(item.source_path)
                dest_path = temp_path / item.relative_path
                
                # Create destination directory
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, dest_path)
                
                # Update manifest with actual size
                item.size_bytes = dest_path.stat().st_size
                manifest.total_size += item.size_bytes
            
            # Save manifest
            manifest.item_count = len(manifest.items)
            manifest_path = temp_path / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest.to_dict(), f, indent=2)
            
            # Create backup archive
            self.update_progress(90, "Creating backup archive")
            
            if manifest.compression_enabled:
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_path)
                            zipf.write(file_path, arcname)
            else:
                with zipfile.ZipFile(backup_path, 'w') as zipf:
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_path)
                            zipf.write(file_path, arcname)
            
            # Encrypt if requested
            if manifest.encryption_enabled:
                self.update_progress(95, "Encrypting backup")
                self.encrypt_backup_file(backup_path)
        
        # Calculate final checksum
        manifest.checksum = self.calculate_file_checksum(backup_path)
        
        # Save manifest to backup history
        self.backup_manifests.append(manifest)
        self.save_backup_history()
        
        return backup_path
    
    def encrypt_backup_file(self, backup_path: Path) -> None:
        """Encrypt backup file."""
        # In a real implementation, you would prompt for password
        # For now, use a default password
        password = "lucid_backup_password"  # This should be user-provided
        
        encryption = BackupEncryption(password)
        
        # Read file
        with open(backup_path, 'rb') as f:
            data = f.read()
        
        # Encrypt
        encrypted_data = encryption.encrypt_data(data)
        
        # Write encrypted data
        encrypted_path = backup_path.with_suffix('.encrypted')
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Replace original with encrypted
        backup_path.unlink()
        encrypted_path.rename(backup_path)
    
    def update_progress(self, percent: float, message: str) -> None:
        """Update backup progress."""
        self.progress_var.set(percent)
        self.status_label.configure(text=message)
        
        # Add to log
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        # Notify callbacks
        for callback in self.progress_callbacks:
            try:
                callback(percent, message)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def start_restore(self) -> None:
        """Start restore operation."""
        selection = self.restore_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a backup to restore")
            return
        
        item = self.restore_tree.item(selection[0])
        backup_name = item['values'][0]
        
        # Find manifest
        manifest = None
        for m in self.backup_manifests:
            if m.backup_name == backup_name:
                manifest = m
                break
        
        if not manifest:
            messagebox.showerror("Error", "Backup manifest not found")
            return
        
        # Confirm restore
        result = messagebox.askyesno(
            "Confirm Restore",
            f"Are you sure you want to restore backup '{backup_name}'?\n"
            f"This will overwrite existing files if the option is enabled."
        )
        
        if not result:
            return
        
        # Create restore operation
        operation = BackupOperation(
            operation_id=str(uuid.uuid4()),
            operation_type="restore",
            status=RestoreStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            manifest=manifest
        )
        
        self.current_operation = operation
        self.backup_operations.append(operation)
        
        # Start restore in separate thread
        restore_thread = threading.Thread(target=self._restore_worker, daemon=True)
        restore_thread.start()
    
    def _restore_worker(self) -> None:
        """Restore worker thread."""
        try:
            operation = self.current_operation
            operation.status = RestoreStatus.IN_PROGRESS
            
            manifest = operation.manifest
            backup_filename = f"{manifest.backup_name}_{manifest.created_at.strftime('%Y%m%d_%H%M%S')}.lbackup"
            backup_path = self.backup_directory / backup_filename
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Decrypt if necessary
            if manifest.encryption_enabled:
                self.update_restore_progress(10, "Decrypting backup")
                self.decrypt_backup_file(backup_path)
            
            # Extract and restore files
            total_items = len(manifest.items)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract backup
                self.update_restore_progress(20, "Extracting backup")
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_path)
                
                # Restore files
                for i, item in enumerate(manifest.items):
                    self.update_restore_progress(
                        20 + (i / total_items) * 70,
                        f"Restoring {item.relative_path}"
                    )
                    
                    source_path = temp_path / item.relative_path
                    dest_path = Path.home() / ".lucid" / item.relative_path
                    
                    if source_path.exists():
                        # Create destination directory
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Check if file exists and overwrite setting
                        if dest_path.exists() and not self.overwrite_var.get():
                            logger.warning(f"Skipping existing file: {dest_path}")
                            continue
                        
                        # Copy file
                        shutil.copy2(source_path, dest_path)
            
            operation.status = RestoreStatus.COMPLETED
            operation.completed_at = datetime.now(timezone.utc)
            
            self.update_restore_progress(100, "Restore completed successfully")
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            if self.current_operation:
                self.current_operation.status = RestoreStatus.FAILED
                self.current_operation.error_message = str(e)
            self.update_restore_progress(0, f"Restore failed: {e}")
    
    def decrypt_backup_file(self, backup_path: Path) -> None:
        """Decrypt backup file."""
        # In a real implementation, you would prompt for password
        password = "lucid_backup_password"  # This should be user-provided
        
        encryption = BackupEncryption(password)
        
        # Read encrypted file
        with open(backup_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Decrypt
        decrypted_data = encryption.decrypt_data(encrypted_data)
        
        # Write decrypted data
        decrypted_path = backup_path.with_suffix('.decrypted')
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)
        
        # Replace encrypted with decrypted
        backup_path.unlink()
        decrypted_path.rename(backup_path)
    
    def update_restore_progress(self, percent: float, message: str) -> None:
        """Update restore progress."""
        self.restore_progress_var.set(percent)
        self.restore_status_label.configure(text=message)
    
    def preview_backup_items(self) -> None:
        """Preview items that will be backed up."""
        backup_type = BackupType(self.backup_type_var.get())
        
        if backup_type == BackupType.CUSTOM:
            items = [item for item in self.get_backup_items() if item.included]
        else:
            items = self.get_backup_items_for_type(backup_type)
        
        total_size = sum(item.size_bytes for item in items)
        
        preview_text = f"Backup Preview ({len(items)} items, {self.format_bytes(total_size)}):\n\n"
        
        for item in items:
            preview_text += f"• {item.relative_path} ({item.item_type}, {self.format_bytes(item.size_bytes)})\n"
        
        messagebox.showinfo("Backup Preview", preview_text)
    
    def import_backup(self) -> None:
        """Import backup from file."""
        filename = filedialog.askopenfilename(
            filetypes=[("Lucid Backup", "*.lbackup"), ("All files", "*.*")],
            title="Import Backup"
        )
        
        if filename:
            try:
                # Extract and read manifest
                with zipfile.ZipFile(filename, 'r') as zipf:
                    manifest_data = json.loads(zipf.read("manifest.json"))
                
                manifest = BackupManifest.from_dict(manifest_data)
                self.backup_manifests.append(manifest)
                self.save_backup_history()
                self.refresh_restore_list()
                
                messagebox.showinfo("Success", "Backup imported successfully")
                
            except Exception as e:
                logger.error(f"Import failed: {e}")
                messagebox.showerror("Error", f"Failed to import backup: {e}")
    
    def view_backup_details(self) -> None:
        """View detailed backup information."""
        selection = self.restore_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a backup to view")
            return
        
        item = self.restore_tree.item(selection[0])
        backup_name = item['values'][0]
        
        # Find manifest
        manifest = None
        for m in self.backup_manifests:
            if m.backup_name == backup_name:
                manifest = m
                break
        
        if not manifest:
            messagebox.showerror("Error", "Backup manifest not found")
            return
        
        # Create details dialog
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title(f"Backup Details - {manifest.backup_name}")
        dialog.geometry("600x500")
        
        # Details text
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=70, height=25)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format details
        details = f"""Backup Name: {manifest.backup_name}
Type: {manifest.backup_type.value}
Created: {manifest.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
Created By: {manifest.created_by}
Description: {manifest.description}
Encryption: {'Enabled' if manifest.encryption_enabled else 'Disabled'}
Compression: {'Enabled' if manifest.compression_enabled else 'Disabled'}
Total Size: {self.format_bytes(manifest.total_size)}
Item Count: {manifest.item_count}
Checksum: {manifest.checksum}

Items:
"""
        
        for item in manifest.items:
            details += f"• {item.relative_path} ({item.item_type}, {self.format_bytes(item.size_bytes)})\n"
        
        details_text.insert(tk.END, details)
        details_text.configure(state=tk.DISABLED)
        
        # Close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def refresh_restore_list(self) -> None:
        """Refresh restore list display."""
        # Clear existing items
        for item in self.restore_tree.get_children():
            self.restore_tree.delete(item)
        
        # Add manifests
        for manifest in self.backup_manifests:
            date_str = manifest.created_at.strftime("%Y-%m-%d %H:%M")
            size_str = self.format_bytes(manifest.total_size)
            
            self.restore_tree.insert('', 'end', values=(
                manifest.backup_name,
                manifest.backup_type.value,
                date_str,
                size_str,
                str(manifest.item_count)
            ))
    
    def refresh_history(self) -> None:
        """Refresh history display."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Add operations
        for operation in self.backup_operations:
            date_str = operation.started_at.strftime("%Y-%m-%d %H:%M")
            name = operation.manifest.backup_name if operation.manifest else "Unknown"
            backup_type = operation.manifest.backup_type.value if operation.manifest else "Unknown"
            size = self.format_bytes(operation.manifest.total_size) if operation.manifest else "Unknown"
            
            self.history_tree.insert('', 'end', values=(
                operation.operation_type.title(),
                name,
                backup_type,
                operation.status.value.title(),
                date_str,
                size
            ))
    
    def save_schedule(self) -> None:
        """Save backup schedule settings."""
        schedule_data = {
            "enabled": self.schedule_enabled_var.get(),
            "frequency": self.schedule_freq_var.get(),
            "time": self.schedule_time_var.get()
        }
        
        self.config_manager.save_config("backup_schedule", schedule_data)
        messagebox.showinfo("Success", "Schedule settings saved")
    
    def test_schedule(self) -> None:
        """Test backup schedule."""
        messagebox.showinfo("Test", "Schedule test functionality would be implemented here")
    
    def save_settings(self) -> None:
        """Save backup settings."""
        settings_data = {
            "backup_directory": self.backup_dir_var.get(),
            "retention_days": int(self.retention_days_var.get()),
            "max_backups": int(self.max_backups_var.get())
        }
        
        self.config_manager.save_config("backup_settings", settings_data)
        messagebox.showinfo("Success", "Settings saved")
    
    def reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.backup_dir_var.set(str(Path.home() / ".lucid" / "backups"))
        self.retention_days_var.set("30")
        self.max_backups_var.set("10")
    
    def browse_backup_directory(self) -> None:
        """Browse for backup directory."""
        directory = filedialog.askdirectory(
            title="Select Backup Directory",
            initialdir=self.backup_dir_var.get()
        )
        
        if directory:
            self.backup_dir_var.set(directory)
            self.backup_directory = Path(directory)
    
    def export_history(self) -> None:
        """Export backup history."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Backup History"
        )
        
        if filename:
            try:
                history_data = {
                    "operations": [op.to_dict() for op in self.backup_operations],
                    "manifests": [manifest.to_dict() for manifest in self.backup_manifests]
                }
                
                with open(filename, 'w') as f:
                    json.dump(history_data, f, indent=2)
                
                messagebox.showinfo("Success", f"History exported to {filename}")
                
            except Exception as e:
                logger.error(f"Export failed: {e}")
                messagebox.showerror("Error", f"Failed to export history: {e}")
    
    def clear_history(self) -> None:
        """Clear backup history."""
        result = messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all backup history?")
        
        if result:
            self.backup_operations.clear()
            self.backup_manifests.clear()
            self.save_backup_history()
            self.refresh_history()
            self.refresh_restore_list()
    
    def load_backup_history(self) -> None:
        """Load backup history from storage."""
        try:
            # Load operations
            operations_data = self.config_manager.load_config("backup_operations", default_data=[])
            self.backup_operations.clear()
            
            for op_dict in operations_data:
                if op_dict['operation_type'] == 'backup':
                    op_dict['status'] = BackupStatus(op_dict['status'])
                else:
                    op_dict['status'] = RestoreStatus(op_dict['status'])
                
                op_dict['started_at'] = datetime.fromisoformat(op_dict['started_at'])
                if op_dict.get('completed_at'):
                    op_dict['completed_at'] = datetime.fromisoformat(op_dict['completed_at'])
                
                if op_dict.get('manifest'):
                    op_dict['manifest'] = BackupManifest.from_dict(op_dict['manifest'])
                
                operation = BackupOperation(**{k: v for k, v in op_dict.items() if k != 'manifest'})
                operation.manifest = op_dict.get('manifest')
                self.backup_operations.append(operation)
            
            # Load manifests
            manifests_data = self.config_manager.load_config("backup_manifests", default_data=[])
            self.backup_manifests.clear()
            
            for manifest_dict in manifests_data:
                manifest = BackupManifest.from_dict(manifest_dict)
                self.backup_manifests.append(manifest)
            
            logger.info(f"Loaded backup history: {len(self.backup_operations)} operations, {len(self.backup_manifests)} manifests")
            
        except Exception as e:
            logger.error(f"Failed to load backup history: {e}")
    
    def save_backup_history(self) -> None:
        """Save backup history to storage."""
        try:
            # Save operations
            operations_data = [op.to_dict() for op in self.backup_operations[-100:]]  # Last 100 operations
            self.config_manager.save_config("backup_operations", operations_data)
            
            # Save manifests
            manifests_data = [manifest.to_dict() for manifest in self.backup_manifests]
            self.config_manager.save_config("backup_manifests", manifests_data)
            
            logger.debug(f"Saved backup history: {len(self.backup_operations)} operations, {len(self.backup_manifests)} manifests")
            
        except Exception as e:
            logger.error(f"Failed to save backup history: {e}")
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def add_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Add progress callback."""
        self.progress_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[str], None]) -> None:
        """Add status callback."""
        self.status_callbacks.append(callback)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.current_operation and self.current_operation.status in [BackupStatus.IN_PROGRESS, RestoreStatus.IN_PROGRESS]:
            self.current_operation.status = BackupStatus.CANCELLED if isinstance(self.current_operation.status, BackupStatus) else RestoreStatus.CANCELLED
            self.current_operation.completed_at = datetime.now(timezone.utc)
        
        self.save_backup_history()


def get_backup_manager(parent_frame: Optional[tk.Frame] = None, node_api_url: str = "http://localhost:8080") -> BackupManager:
    """Get or create backup manager instance."""
    global _backup_manager_instance
    
    if _backup_manager_instance is None:
        if parent_frame is None:
            raise ValueError("parent_frame is required for initial creation")
        _backup_manager_instance = BackupManager(parent_frame, node_api_url)
    
    return _backup_manager_instance


def cleanup_backup_manager() -> None:
    """Cleanup backup manager instance."""
    global _backup_manager_instance
    
    if _backup_manager_instance:
        _backup_manager_instance.cleanup()
        _backup_manager_instance = None


# Global instance
_backup_manager_instance: Optional[BackupManager] = None

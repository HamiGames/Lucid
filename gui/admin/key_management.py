# Path: gui/admin/key_management.py
"""
Key management interface for Lucid RDP GUI.
Provides key rotation, backup, and recovery operations for cryptographic keys.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import logging
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
import os
from pathlib import Path

from ..core.networking import TorHttpClient, SecurityConfig
from ..core.security import get_security_validator, CryptographicUtils
from ..core.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """Key type enumeration"""
    MASTER = "master"
    ENCRYPTION = "encryption"
    SIGNING = "signing"
    AUTHENTICATION = "authentication"
    BACKUP = "backup"


class KeyStatus(Enum):
    """Key status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    BACKUP = "backup"


class KeyRotationSchedule(Enum):
    """Key rotation schedule enumeration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    MANUAL = "manual"


@dataclass
class KeyInfo:
    """Key information container"""
    key_id: str
    key_type: KeyType
    status: KeyStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    fingerprint: str
    algorithm: str = "ChaCha20-Poly1305"
    key_size: int = 256
    usage_count: int = 0
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['key_type'] = self.key_type.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        if self.last_used:
            data['last_used'] = self.last_used.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyInfo':
        """Create KeyInfo from dictionary"""
        data['key_type'] = KeyType(data['key_type'])
        data['status'] = KeyStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        if data.get('last_used'):
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        return cls(**data)


@dataclass
class BackupInfo:
    """Backup information container"""
    backup_id: str
    timestamp: datetime
    key_count: int
    total_size: int
    encryption_enabled: bool
    checksum: str
    file_path: str
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupInfo':
        """Create BackupInfo from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class KeyManager:
    """
    Key management interface for cryptographic keys.
    
    Provides functionality for:
    - Key generation and rotation
    - Key backup and recovery
    - Key status monitoring
    - Automatic key rotation scheduling
    """
    
    def __init__(self, parent_frame: tk.Frame, node_api_url: str = "http://localhost:8080"):
        self.parent_frame = parent_frame
        self.node_api_url = node_api_url.rstrip('/')
        
        # Data storage
        self.keys: Dict[str, KeyInfo] = {}
        self.backups: List[BackupInfo] = []
        self.rotation_schedule = KeyRotationSchedule.MANUAL
        
        # Configuration
        self.config_manager = get_config_manager()
        self.security_validator = get_security_validator()
        
        # Setup GUI
        self.setup_gui()
        self.setup_networking()
        
        # Load existing data
        self.load_keys()
        self.load_backups()
        
        # Start monitoring
        self.start_monitoring()
    
    def setup_gui(self) -> None:
        """Setup the key manager GUI."""
        # Main container
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_keys_tab()
        self.create_rotation_tab()
        self.create_backup_tab()
        self.create_recovery_tab()
    
    def create_keys_tab(self) -> None:
        """Create keys management tab."""
        self.keys_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.keys_frame, text="Keys")
        
        # Toolbar
        toolbar = ttk.Frame(self.keys_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Generate New Key", command=self.generate_key_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Rotate Key", command=self.rotate_key_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Revoke Key", command=self.revoke_key_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_keys).pack(side=tk.LEFT, padx=5)
        
        # Filter options
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.key_filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.key_filter_var,
                                  values=["all", "active", "inactive", "expired", "revoked"],
                                  width=10, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(5, 0))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_key_filter)
        
        # Keys treeview
        columns = ('id', 'type', 'status', 'created', 'expires', 'fingerprint', 'usage')
        self.keys_tree = ttk.Treeview(self.keys_frame, columns=columns, show='headings')
        
        # Configure columns
        self.keys_tree.heading('id', text='Key ID')
        self.keys_tree.heading('type', text='Type')
        self.keys_tree.heading('status', text='Status')
        self.keys_tree.heading('created', text='Created')
        self.keys_tree.heading('expires', text='Expires')
        self.keys_tree.heading('fingerprint', text='Fingerprint')
        self.keys_tree.heading('usage', text='Usage Count')
        
        # Column widths
        self.keys_tree.column('id', width=120)
        self.keys_tree.column('type', width=100)
        self.keys_tree.column('status', width=80)
        self.keys_tree.column('created', width=120)
        self.keys_tree.column('expires', width=120)
        self.keys_tree.column('fingerprint', width=150)
        self.keys_tree.column('usage', width=80)
        
        # Scrollbar
        keys_scroll = ttk.Scrollbar(self.keys_frame, orient=tk.VERTICAL, command=self.keys_tree.yview)
        self.keys_tree.configure(yscrollcommand=keys_scroll.set)
        
        self.keys_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        keys_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to view details
        self.keys_tree.bind('<Double-1>', self.view_key_details)
    
    def create_rotation_tab(self) -> None:
        """Create key rotation tab."""
        self.rotation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rotation_frame, text="Rotation")
        
        # Rotation settings
        settings_frame = ttk.LabelFrame(self.rotation_frame, text="Rotation Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Schedule selection
        schedule_frame = ttk.Frame(settings_frame)
        schedule_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(schedule_frame, text="Rotation Schedule:").pack(side=tk.LEFT)
        self.rotation_schedule_var = tk.StringVar(value="manual")
        schedule_combo = ttk.Combobox(schedule_frame, textvariable=self.rotation_schedule_var,
                                    values=["manual", "daily", "weekly", "monthly", "quarterly"],
                                    state="readonly")
        schedule_combo.pack(side=tk.LEFT, padx=(5, 0))
        schedule_combo.bind('<<ComboboxSelected>>', self.update_rotation_schedule)
        
        # Key type selection
        type_frame = ttk.Frame(settings_frame)
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(type_frame, text="Key Type:").pack(side=tk.LEFT)
        self.rotation_key_type_var = tk.StringVar(value="encryption")
        type_combo = ttk.Combobox(type_frame, textvariable=self.rotation_key_type_var,
                                values=["encryption", "signing", "authentication", "master"],
                                state="readonly")
        type_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Next rotation info
        info_frame = ttk.LabelFrame(self.rotation_frame, text="Next Rotation")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.next_rotation_label = ttk.Label(info_frame, text="Next rotation: Not scheduled")
        self.next_rotation_label.pack(padx=5, pady=5)
        
        # Manual rotation
        manual_frame = ttk.LabelFrame(self.rotation_frame, text="Manual Rotation")
        manual_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(manual_frame, text="Rotate All Keys", command=self.rotate_all_keys).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(manual_frame, text="Rotate Expired Keys", command=self.rotate_expired_keys).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Rotation history
        history_frame = ttk.LabelFrame(self.rotation_frame, text="Rotation History")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('timestamp', 'key_id', 'action', 'result')
        self.rotation_tree = ttk.Treeview(history_frame, columns=columns, show='headings')
        
        self.rotation_tree.heading('timestamp', text='Timestamp')
        self.rotation_tree.heading('key_id', text='Key ID')
        self.rotation_tree.heading('action', text='Action')
        self.rotation_tree.heading('result', text='Result')
        
        rotation_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.rotation_tree.yview)
        self.rotation_tree.configure(yscrollcommand=rotation_scroll.set)
        
        self.rotation_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        rotation_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def create_backup_tab(self) -> None:
        """Create backup tab."""
        self.backup_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.backup_frame, text="Backup")
        
        # Backup settings
        settings_frame = ttk.LabelFrame(self.backup_frame, text="Backup Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Auto backup
        auto_frame = ttk.Frame(settings_frame)
        auto_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_backup_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(auto_frame, text="Enable Auto Backup", variable=self.auto_backup_var)
        auto_check.pack(side=tk.LEFT)
        
        # Backup interval
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(interval_frame, text="Backup Interval:").pack(side=tk.LEFT)
        self.backup_interval_var = tk.StringVar(value="daily")
        interval_combo = ttk.Combobox(interval_frame, textvariable=self.backup_interval_var,
                                    values=["hourly", "daily", "weekly"],
                                    state="readonly")
        interval_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Manual backup
        manual_frame = ttk.LabelFrame(self.backup_frame, text="Manual Backup")
        manual_frame.pack(fill=tk.X, padx=10, pady=5)
        
        backup_button_frame = ttk.Frame(manual_frame)
        backup_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(backup_button_frame, text="Create Backup", command=self.create_backup_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(backup_button_frame, text="Export Keys", command=self.export_keys_dialog).pack(side=tk.LEFT, padx=5)
        
        # Backup list
        list_frame = ttk.LabelFrame(self.backup_frame, text="Backup History")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('timestamp', 'key_count', 'size', 'encrypted', 'checksum')
        self.backup_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        self.backup_tree.heading('timestamp', text='Timestamp')
        self.backup_tree.heading('key_count', text='Keys')
        self.backup_tree.heading('size', text='Size')
        self.backup_tree.heading('encrypted', text='Encrypted')
        self.backup_tree.heading('checksum', text='Checksum')
        
        backup_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.backup_tree.yview)
        self.backup_tree.configure(yscrollcommand=backup_scroll.set)
        
        self.backup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        backup_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to restore
        self.backup_tree.bind('<Double-1>', self.restore_backup_dialog)
    
    def create_recovery_tab(self) -> None:
        """Create recovery tab."""
        self.recovery_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.recovery_frame, text="Recovery")
        
        # Recovery options
        options_frame = ttk.LabelFrame(self.recovery_frame, text="Recovery Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Import backup
        import_frame = ttk.Frame(options_frame)
        import_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(import_frame, text="Import Backup File", command=self.import_backup_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(import_frame, text="Import Keys", command=self.import_keys_dialog).pack(side=tk.LEFT, padx=5)
        
        # Emergency recovery
        emergency_frame = ttk.LabelFrame(self.recovery_frame, text="Emergency Recovery")
        emergency_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(emergency_frame, text="Warning: Emergency recovery will reset all keys!", 
                 foreground="red").pack(padx=5, pady=2)
        
        ttk.Button(emergency_frame, text="Emergency Key Reset", 
                  command=self.emergency_reset_dialog).pack(padx=5, pady=5)
        
        # Recovery status
        status_frame = ttk.LabelFrame(self.recovery_frame, text="Recovery Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.recovery_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, height=10)
        self.recovery_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Recovery log
        log_frame = ttk.Frame(status_frame)
        log_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(log_frame, text="Clear Log", command=self.clear_recovery_log).pack(side=tk.LEFT)
        ttk.Button(log_frame, text="Export Log", command=self.export_recovery_log).pack(side=tk.LEFT, padx=(5, 0))
    
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
    
    def start_monitoring(self) -> None:
        """Start key monitoring."""
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                self.check_key_expiration()
                self.check_rotation_schedule()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Key monitoring error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def generate_key_dialog(self) -> None:
        """Show key generation dialog."""
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title("Generate New Key")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        
        # Key type
        type_frame = ttk.Frame(dialog)
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(type_frame, text="Key Type:").pack(anchor=tk.W)
        key_type_var = tk.StringVar(value="encryption")
        type_combo = ttk.Combobox(type_frame, textvariable=key_type_var,
                                values=["encryption", "signing", "authentication", "master"],
                                state="readonly")
        type_combo.pack(fill=tk.X, pady=(2, 0))
        
        # Algorithm
        algo_frame = ttk.Frame(dialog)
        algo_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(algo_frame, text="Algorithm:").pack(anchor=tk.W)
        algo_var = tk.StringVar(value="ChaCha20-Poly1305")
        algo_combo = ttk.Combobox(algo_frame, textvariable=algo_var,
                                values=["ChaCha20-Poly1305", "AES-256-GCM", "Ed25519"],
                                state="readonly")
        algo_combo.pack(fill=tk.X, pady=(2, 0))
        
        # Key size
        size_frame = ttk.Frame(dialog)
        size_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(size_frame, text="Key Size:").pack(anchor=tk.W)
        size_var = tk.StringVar(value="256")
        size_combo = ttk.Combobox(size_frame, textvariable=size_var,
                                values=["128", "192", "256", "512"],
                                state="readonly")
        size_combo.pack(fill=tk.X, pady=(2, 0))
        
        # Expiration
        exp_frame = ttk.Frame(dialog)
        exp_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(exp_frame, text="Expiration (days, 0 = never):").pack(anchor=tk.W)
        exp_var = tk.StringVar(value="90")
        exp_entry = ttk.Entry(exp_frame, textvariable=exp_var)
        exp_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Notes
        notes_frame = ttk.Frame(dialog)
        notes_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(notes_frame, text="Notes (optional):").pack(anchor=tk.W)
        notes_entry = ttk.Entry(notes_frame)
        notes_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def generate():
            try:
                key_type = KeyType(key_type_var.get())
                algorithm = algo_var.get()
                key_size = int(size_var.get())
                expiration_days = int(exp_var.get())
                notes = notes_entry.get().strip()
                
                if expiration_days < 0:
                    raise ValueError("Expiration days must be non-negative")
                
                self.generate_key(key_type, algorithm, key_size, expiration_days, notes)
                dialog.destroy()
                messagebox.showinfo("Success", "Key generated successfully")
                self.refresh_keys()
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {e}")
            except Exception as e:
                logger.error(f"Key generation failed: {e}")
                messagebox.showerror("Error", f"Failed to generate key: {e}")
        
        ttk.Button(button_frame, text="Generate", command=generate).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def generate_key(self, key_type: KeyType, algorithm: str, key_size: int, 
                    expiration_days: int, notes: str = "") -> str:
        """Generate a new cryptographic key."""
        key_id = CryptographicUtils.generate_secure_token(16)
        
        # Calculate expiration
        expires_at = None
        if expiration_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiration_days)
        
        # Generate fingerprint
        key_data = CryptographicUtils.generate_secure_random(key_size // 8)
        fingerprint = hashlib.sha256(key_data).hexdigest()[:16]
        
        # Create key info
        key_info = KeyInfo(
            key_id=key_id,
            key_type=key_type,
            status=KeyStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            last_used=None,
            fingerprint=fingerprint,
            algorithm=algorithm,
            key_size=key_size,
            usage_count=0,
            notes=notes
        )
        
        # Store key
        self.keys[key_id] = key_info
        self.save_keys()
        
        # Log generation
        self.log_recovery_action(f"Generated new {key_type.value} key: {key_id}")
        
        return key_id
    
    def rotate_key_dialog(self) -> None:
        """Show key rotation dialog."""
        selection = self.keys_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a key to rotate")
            return
        
        item = self.keys_tree.item(selection[0])
        key_id = item['values'][0]
        
        if key_id not in self.keys:
            messagebox.showerror("Error", "Selected key not found")
            return
        
        key_info = self.keys[key_id]
        
        result = messagebox.askyesno("Confirm Rotation", 
                                   f"Are you sure you want to rotate key {key_id}?\n"
                                   f"Type: {key_info.key_type.value}\n"
                                   f"Status: {key_info.status.value}")
        
        if result:
            self.rotate_key(key_id)
    
    def rotate_key(self, key_id: str) -> bool:
        """Rotate a specific key."""
        if key_id not in self.keys:
            return False
        
        try:
            old_key = self.keys[key_id]
            
            # Create new key with same parameters
            new_key_id = self.generate_key(
                old_key.key_type,
                old_key.algorithm,
                old_key.key_size,
                90,  # Default 90 days
                f"Rotated from {key_id}"
            )
            
            # Mark old key as backup
            old_key.status = KeyStatus.BACKUP
            old_key.notes += f" (Rotated to {new_key_id})"
            
            # Update usage
            new_key = self.keys[new_key_id]
            new_key.usage_count = old_key.usage_count
            
            self.save_keys()
            self.log_recovery_action(f"Rotated key {key_id} to {new_key_id}")
            
            messagebox.showinfo("Success", f"Key rotated successfully\nOld: {key_id}\nNew: {new_key_id}")
            self.refresh_keys()
            
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            messagebox.showerror("Error", f"Failed to rotate key: {e}")
            return False
    
    def revoke_key_dialog(self) -> None:
        """Show key revocation dialog."""
        selection = self.keys_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a key to revoke")
            return
        
        item = self.keys_tree.item(selection[0])
        key_id = item['values'][0]
        
        if key_id not in self.keys:
            messagebox.showerror("Error", "Selected key not found")
            return
        
        key_info = self.keys[key_id]
        
        result = messagebox.askyesno("Confirm Revocation", 
                                   f"Are you sure you want to revoke key {key_id}?\n"
                                   f"Type: {key_info.key_type.value}\n"
                                   f"This action cannot be undone!")
        
        if result:
            self.revoke_key(key_id)
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke a specific key."""
        if key_id not in self.keys:
            return False
        
        try:
            key_info = self.keys[key_id]
            key_info.status = KeyStatus.REVOKED
            key_info.notes += f" (Revoked on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            
            self.save_keys()
            self.log_recovery_action(f"Revoked key: {key_id}")
            
            messagebox.showinfo("Success", "Key revoked successfully")
            self.refresh_keys()
            
            return True
            
        except Exception as e:
            logger.error(f"Key revocation failed: {e}")
            messagebox.showerror("Error", f"Failed to revoke key: {e}")
            return False
    
    def refresh_keys(self) -> None:
        """Refresh keys display."""
        # Clear existing items
        for item in self.keys_tree.get_children():
            self.keys_tree.delete(item)
        
        # Add keys
        for key_info in self.keys.values():
            # Apply filter
            if self.key_filter_var.get() != "all" and key_info.status.value != self.key_filter_var.get():
                continue
            
            # Format dates
            created_str = key_info.created_at.strftime("%Y-%m-%d %H:%M")
            expires_str = key_info.expires_at.strftime("%Y-%m-%d %H:%M") if key_info.expires_at else "Never"
            
            # Status color
            status_colors = {
                "active": "green",
                "inactive": "orange",
                "expired": "red",
                "revoked": "red",
                "backup": "blue"
            }
            
            item = self.keys_tree.insert('', 'end', values=(
                key_info.key_id,
                key_info.key_type.value.title(),
                key_info.status.value.title(),
                created_str,
                expires_str,
                key_info.fingerprint,
                str(key_info.usage_count)
            ))
    
    def apply_key_filter(self, event=None) -> None:
        """Apply filter to keys display."""
        self.refresh_keys()
    
    def view_key_details(self, event) -> None:
        """View detailed key information."""
        selection = self.keys_tree.selection()
        if not selection:
            return
        
        item = self.keys_tree.item(selection[0])
        key_id = item['values'][0]
        
        if key_id not in self.keys:
            return
        
        key_info = self.keys[key_id]
        
        # Create details dialog
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title(f"Key Details - {key_id}")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        
        # Details text
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=60, height=20)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format details
        details = f"""Key ID: {key_info.key_id}
Type: {key_info.key_type.value.title()}
Status: {key_info.status.value.title()}
Algorithm: {key_info.algorithm}
Key Size: {key_info.key_size} bits
Fingerprint: {key_info.fingerprint}
Created: {key_info.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
Expires: {key_info.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC") if key_info.expires_at else "Never"}
Last Used: {key_info.last_used.strftime("%Y-%m-%d %H:%M:%S UTC") if key_info.last_used else "Never"}
Usage Count: {key_info.usage_count}
Notes: {key_info.notes}
"""
        
        details_text.insert(tk.END, details)
        details_text.configure(state=tk.DISABLED)
        
        # Close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def create_backup_dialog(self) -> None:
        """Show backup creation dialog."""
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title("Create Backup")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        
        # Backup name
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(name_frame, text="Backup Name:").pack(anchor=tk.W)
        name_entry = ttk.Entry(name_frame)
        name_entry.pack(fill=tk.X, pady=(2, 0))
        name_entry.insert(0, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Encryption
        enc_frame = ttk.Frame(dialog)
        enc_frame.pack(fill=tk.X, padx=10, pady=5)
        
        encrypt_var = tk.BooleanVar(value=True)
        encrypt_check = ttk.Checkbutton(enc_frame, text="Encrypt backup", variable=encrypt_var)
        encrypt_check.pack(anchor=tk.W)
        
        # Notes
        notes_frame = ttk.Frame(dialog)
        notes_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(notes_frame, text="Notes (optional):").pack(anchor=tk.W)
        notes_entry = ttk.Entry(notes_frame)
        notes_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def create_backup():
            try:
                backup_name = name_entry.get().strip()
                encrypt = encrypt_var.get()
                notes = notes_entry.get().strip()
                
                if not backup_name:
                    raise ValueError("Backup name is required")
                
                self.create_backup(backup_name, encrypt, notes)
                dialog.destroy()
                messagebox.showinfo("Success", "Backup created successfully")
                self.refresh_backups()
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {e}")
            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                messagebox.showerror("Error", f"Failed to create backup: {e}")
        
        ttk.Button(button_frame, text="Create", command=create_backup).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def create_backup(self, backup_name: str, encrypt: bool = True, notes: str = "") -> str:
        """Create a backup of all keys."""
        backup_id = CryptographicUtils.generate_secure_token(16)
        
        # Prepare backup data
        backup_data = {
            "backup_id": backup_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "keys": {key_id: key_info.to_dict() for key_id, key_info in self.keys.items()},
            "metadata": {
                "version": "1.0.0",
                "key_count": len(self.keys),
                "encrypted": encrypt
            }
        }
        
        # Serialize to JSON
        json_data = json.dumps(backup_data, indent=2)
        data_bytes = json_data.encode('utf-8')
        
        # Calculate checksum
        checksum = hashlib.sha256(data_bytes).hexdigest()
        
        # Encrypt if requested
        if encrypt:
            key = CryptographicUtils.generate_secure_random(32)
            nonce, encrypted_data = CryptographicUtils.encrypt_data(data_bytes, key)
            final_data = {
                "encrypted": True,
                "nonce": base64.b64encode(nonce).decode('ascii'),
                "data": base64.b64encode(encrypted_data).decode('ascii'),
                "key_hint": base64.b64encode(key[:16]).decode('ascii')  # First 16 bytes as hint
            }
            data_bytes = json.dumps(final_data).encode('utf-8')
        
        # Save backup file
        backup_dir = Path.home() / ".lucid" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"{backup_name}.lkb"  # Lucid Key Backup
        with open(backup_file, 'wb') as f:
            f.write(data_bytes)
        
        # Create backup info
        backup_info = BackupInfo(
            backup_id=backup_id,
            timestamp=datetime.now(timezone.utc),
            key_count=len(self.keys),
            total_size=len(data_bytes),
            encryption_enabled=encrypt,
            checksum=checksum,
            file_path=str(backup_file),
            notes=notes
        )
        
        self.backups.append(backup_info)
        self.save_backups()
        
        self.log_recovery_action(f"Created backup: {backup_name} ({len(self.keys)} keys)")
        
        return backup_id
    
    def export_keys_dialog(self) -> None:
        """Show export keys dialog."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".lke",  # Lucid Key Export
            filetypes=[("Lucid Key Export", "*.lke"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Keys"
        )
        
        if filename:
            try:
                self.export_keys(filename)
                messagebox.showinfo("Success", f"Keys exported to {filename}")
            except Exception as e:
                logger.error(f"Key export failed: {e}")
                messagebox.showerror("Error", f"Failed to export keys: {e}")
    
    def export_keys(self, filename: str) -> None:
        """Export keys to file."""
        export_data = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "keys": {key_id: key_info.to_dict() for key_id, key_info in self.keys.items()}
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.log_recovery_action(f"Exported {len(self.keys)} keys to {filename}")
    
    def refresh_backups(self) -> None:
        """Refresh backups display."""
        # Clear existing items
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)
        
        # Add backups
        for backup in self.backups:
            timestamp_str = backup.timestamp.strftime("%Y-%m-%d %H:%M")
            size_str = self.format_bytes(backup.total_size)
            encrypted_str = "Yes" if backup.encryption_enabled else "No"
            checksum_short = backup.checksum[:16] + "..."
            
            item = self.backup_tree.insert('', 'end', values=(
                timestamp_str,
                str(backup.key_count),
                size_str,
                encrypted_str,
                checksum_short
            ))
    
    def restore_backup_dialog(self, event=None) -> None:
        """Show backup restoration dialog."""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a backup to restore")
            return
        
        item = self.backup_tree.item(selection[0])
        timestamp = item['values'][0]
        
        # Find backup
        backup = None
        for b in self.backups:
            if b.timestamp.strftime("%Y-%m-%d %H:%M") == timestamp:
                backup = b
                break
        
        if not backup:
            messagebox.showerror("Error", "Backup not found")
            return
        
        result = messagebox.askyesno("Confirm Restore", 
                                   f"Are you sure you want to restore backup from {timestamp}?\n"
                                   f"This will overwrite all current keys!")
        
        if result:
            self.restore_backup(backup)
    
    def restore_backup(self, backup: BackupInfo) -> bool:
        """Restore keys from backup."""
        try:
            if not Path(backup.file_path).exists():
                raise FileNotFoundError(f"Backup file not found: {backup.file_path}")
            
            # Read backup file
            with open(backup.file_path, 'rb') as f:
                data = f.read()
            
            # Decrypt if necessary
            if backup.encryption_enabled:
                # For encrypted backups, we'd need the key
                # This is a simplified implementation
                messagebox.showwarning("Warning", "Encrypted backups require the encryption key")
                return False
            
            # Parse JSON
            backup_data = json.loads(data.decode('utf-8'))
            
            # Restore keys
            restored_count = 0
            for key_id, key_dict in backup_data.get('keys', {}).items():
                key_info = KeyInfo.from_dict(key_dict)
                self.keys[key_id] = key_info
                restored_count += 1
            
            self.save_keys()
            self.log_recovery_action(f"Restored backup: {backup.backup_id} ({restored_count} keys)")
            
            messagebox.showinfo("Success", f"Restored {restored_count} keys from backup")
            self.refresh_keys()
            
            return True
            
        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            messagebox.showerror("Error", f"Failed to restore backup: {e}")
            return False
    
    def import_backup_dialog(self) -> None:
        """Show import backup dialog."""
        filename = filedialog.askopenfilename(
            filetypes=[("Lucid Key Backup", "*.lkb"), ("Lucid Key Export", "*.lke"), ("All files", "*.*")],
            title="Import Backup"
        )
        
        if filename:
            try:
                self.import_backup(filename)
                messagebox.showinfo("Success", "Backup imported successfully")
                self.refresh_keys()
                self.refresh_backups()
            except Exception as e:
                logger.error(f"Backup import failed: {e}")
                messagebox.showerror("Error", f"Failed to import backup: {e}")
    
    def import_backup(self, filename: str) -> None:
        """Import backup from file."""
        with open(filename, 'rb') as f:
            data = f.read()
        
        # Try to parse as JSON first (export format)
        try:
            import_data = json.loads(data.decode('utf-8'))
            
            if 'keys' in import_data:
                # Export format
                imported_count = 0
                for key_id, key_dict in import_data['keys'].items():
                    key_info = KeyInfo.from_dict(key_dict)
                    self.keys[key_id] = key_info
                    imported_count += 1
                
                self.save_keys()
                self.log_recovery_action(f"Imported {imported_count} keys from {filename}")
                
            else:
                raise ValueError("Invalid export format")
                
        except json.JSONDecodeError:
            # Try as backup format (encrypted)
            messagebox.showwarning("Warning", "Encrypted backups require the encryption key")
            return
    
    def import_keys_dialog(self) -> None:
        """Show import keys dialog."""
        filename = filedialog.askopenfilename(
            filetypes=[("Lucid Key Export", "*.lke"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Keys"
        )
        
        if filename:
            try:
                self.import_keys(filename)
                messagebox.showinfo("Success", "Keys imported successfully")
                self.refresh_keys()
            except Exception as e:
                logger.error(f"Key import failed: {e}")
                messagebox.showerror("Error", f"Failed to import keys: {e}")
    
    def import_keys(self, filename: str) -> None:
        """Import keys from file."""
        with open(filename, 'r') as f:
            import_data = json.load(f)
        
        imported_count = 0
        for key_id, key_dict in import_data.get('keys', {}).items():
            key_info = KeyInfo.from_dict(key_dict)
            self.keys[key_id] = key_info
            imported_count += 1
        
        self.save_keys()
        self.log_recovery_action(f"Imported {imported_count} keys from {filename}")
    
    def emergency_reset_dialog(self) -> None:
        """Show emergency reset dialog."""
        result = messagebox.askyesno("Emergency Reset", 
                                   "WARNING: This will delete ALL keys and reset the system!\n"
                                   "This action cannot be undone!\n\n"
                                   "Are you absolutely sure?")
        
        if result:
            # Double confirmation
            result2 = messagebox.askyesno("Final Confirmation", 
                                        "This is your final warning!\n"
                                        "All keys will be permanently deleted!\n\n"
                                        "Type 'RESET' in the next dialog to confirm.")
            
            if result2:
                self.emergency_reset()
    
    def emergency_reset(self) -> None:
        """Emergency reset of all keys."""
        try:
            # Clear all keys
            self.keys.clear()
            self.save_keys()
            
            # Generate new master key
            master_key_id = self.generate_key(
                KeyType.MASTER,
                "ChaCha20-Poly1305",
                256,
                0,  # Never expires
                "Emergency reset master key"
            )
            
            self.log_recovery_action("EMERGENCY RESET: All keys deleted and new master key generated")
            
            messagebox.showinfo("Reset Complete", 
                              "Emergency reset completed.\n"
                              f"New master key: {master_key_id}\n"
                              "Please backup your keys immediately!")
            
            self.refresh_keys()
            
        except Exception as e:
            logger.error(f"Emergency reset failed: {e}")
            messagebox.showerror("Error", f"Emergency reset failed: {e}")
    
    def rotate_all_keys(self) -> None:
        """Rotate all active keys."""
        try:
            rotated_count = 0
            for key_id, key_info in self.keys.items():
                if key_info.status == KeyStatus.ACTIVE:
                    if self.rotate_key(key_id):
                        rotated_count += 1
            
            messagebox.showinfo("Rotation Complete", f"Rotated {rotated_count} keys")
            
        except Exception as e:
            logger.error(f"Bulk rotation failed: {e}")
            messagebox.showerror("Error", f"Failed to rotate keys: {e}")
    
    def rotate_expired_keys(self) -> None:
        """Rotate all expired keys."""
        try:
            rotated_count = 0
            current_time = datetime.now(timezone.utc)
            
            for key_id, key_info in self.keys.items():
                if (key_info.status == KeyStatus.ACTIVE and 
                    key_info.expires_at and 
                    key_info.expires_at < current_time):
                    
                    key_info.status = KeyStatus.EXPIRED
                    if self.rotate_key(key_id):
                        rotated_count += 1
            
            self.save_keys()
            messagebox.showinfo("Rotation Complete", f"Rotated {rotated_count} expired keys")
            self.refresh_keys()
            
        except Exception as e:
            logger.error(f"Expired key rotation failed: {e}")
            messagebox.showerror("Error", f"Failed to rotate expired keys: {e}")
    
    def update_rotation_schedule(self, event=None) -> None:
        """Update rotation schedule."""
        schedule = self.rotation_schedule_var.get()
        self.rotation_schedule = KeyRotationSchedule(schedule)
        
        # Update next rotation display
        if schedule == "manual":
            self.next_rotation_label.configure(text="Next rotation: Not scheduled")
        else:
            # Calculate next rotation time
            now = datetime.now()
            if schedule == "daily":
                next_rotation = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            elif schedule == "weekly":
                next_rotation = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)
            elif schedule == "monthly":
                next_rotation = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)
                next_rotation = next_rotation.replace(day=1)
            elif schedule == "quarterly":
                next_rotation = now.replace(month=((now.month-1)//3)*3+1, day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=93)
            
            self.next_rotation_label.configure(text=f"Next rotation: {next_rotation.strftime('%Y-%m-%d %H:%M')}")
    
    def check_key_expiration(self) -> None:
        """Check for expired keys."""
        current_time = datetime.now(timezone.utc)
        expired_count = 0
        
        for key_info in self.keys.values():
            if (key_info.status == KeyStatus.ACTIVE and 
                key_info.expires_at and 
                key_info.expires_at < current_time):
                
                key_info.status = KeyStatus.EXPIRED
                expired_count += 1
        
        if expired_count > 0:
            self.save_keys()
            self.log_recovery_action(f"Marked {expired_count} keys as expired")
    
    def check_rotation_schedule(self) -> None:
        """Check rotation schedule and perform automatic rotation."""
        if self.rotation_schedule == KeyRotationSchedule.MANUAL:
            return
        
        # This would implement automatic rotation based on schedule
        # For now, we'll just log the check
        logger.debug(f"Checking rotation schedule: {self.rotation_schedule.value}")
    
    def clear_recovery_log(self) -> None:
        """Clear recovery log."""
        self.recovery_text.delete(1.0, tk.END)
    
    def export_recovery_log(self) -> None:
        """Export recovery log."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Recovery Log"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.recovery_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Recovery log exported to {filename}")
            except Exception as e:
                logger.error(f"Recovery log export failed: {e}")
                messagebox.showerror("Error", f"Failed to export recovery log: {e}")
    
    def log_recovery_action(self, message: str) -> None:
        """Log a recovery action."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.recovery_text.insert(tk.END, log_message)
        self.recovery_text.see(tk.END)
        
        logger.info(f"Recovery action: {message}")
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes as human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    
    def load_keys(self) -> None:
        """Load keys from storage."""
        try:
            keys_data = self.config_manager.load_config("keys", default_data={})
            self.keys.clear()
            
            for key_id, key_dict in keys_data.items():
                key_info = KeyInfo.from_dict(key_dict)
                self.keys[key_id] = key_info
            
            logger.info(f"Loaded {len(self.keys)} keys")
            
        except Exception as e:
            logger.error(f"Failed to load keys: {e}")
    
    def save_keys(self) -> None:
        """Save keys to storage."""
        try:
            keys_data = {key_id: key_info.to_dict() for key_id, key_info in self.keys.items()}
            self.config_manager.save_config("keys", keys_data)
            
            logger.debug(f"Saved {len(self.keys)} keys")
            
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")
    
    def load_backups(self) -> None:
        """Load backup information."""
        try:
            backups_data = self.config_manager.load_config("key_backups", default_data=[])
            self.backups.clear()
            
            for backup_dict in backups_data:
                backup_info = BackupInfo.from_dict(backup_dict)
                self.backups.append(backup_info)
            
            logger.info(f"Loaded {len(self.backups)} backup records")
            
        except Exception as e:
            logger.error(f"Failed to load backups: {e}")
    
    def save_backups(self) -> None:
        """Save backup information."""
        try:
            backups_data = [backup.to_dict() for backup in self.backups]
            self.config_manager.save_config("key_backups", backups_data)
            
            logger.debug(f"Saved {len(self.backups)} backup records")
            
        except Exception as e:
            logger.error(f"Failed to save backups: {e}")

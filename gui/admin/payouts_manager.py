# Path: gui/admin/payouts_manager.py
"""
TRON payout management interface for Lucid RDP GUI.
Provides TRON blockchain payout operations, wallet management, and transaction monitoring.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import threading
import time

from ..core.networking import TorHttpClient, SecurityConfig
from ..core.security import get_security_validator
from ..core.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class PayoutStatus(Enum):
    """Payout transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayoutType(Enum):
    """Payout types"""
    WORK_REWARD = "work_reward"
    STAKING_REWARD = "staking_reward"
    REFERRAL_BONUS = "referral_bonus"
    MANUAL = "manual"


@dataclass
class PayoutTransaction:
    """Payout transaction data structure"""
    transaction_id: str
    recipient_address: str
    amount_trx: float
    amount_usdt: float
    payout_type: PayoutType
    status: PayoutStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    blockchain_tx_hash: Optional[str] = None
    gas_fee: float = 0.0
    notes: str = ""


@dataclass
class WalletInfo:
    """Wallet information"""
    address: str
    balance_trx: float
    balance_usdt: float
    is_connected: bool
    last_sync: datetime
    transaction_count: int = 0


class PayoutsManager:
    """
    TRON payout management interface.
    
    Handles TRON blockchain operations including:
    - Wallet connection and balance monitoring
    - Payout transaction creation and management
    - Transaction history and status tracking
    - Gas fee estimation and optimization
    """
    
    def __init__(self, parent_frame: tk.Frame, node_api_url: str = "http://localhost:8080"):
        self.parent_frame = parent_frame
        self.node_api_url = node_api_url.rstrip('/')
        
        # Data storage
        self.wallet_info: Optional[WalletInfo] = None
        self.payout_history: List[PayoutTransaction] = []
        self.pending_payouts: List[PayoutTransaction] = []
        
        # Configuration
        self.config_manager = get_config_manager()
        self.security_validator = get_security_validator()
        
        # Setup GUI
        self.setup_gui()
        self.setup_networking()
        
        # Start monitoring
        self.start_monitoring()
    
    def setup_gui(self) -> None:
        """Setup the payout manager GUI."""
        # Main container
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_wallet_tab()
        self.create_payout_tab()
        self.create_history_tab()
        self.create_settings_tab()
    
    def create_wallet_tab(self) -> None:
        """Create wallet management tab."""
        self.wallet_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.wallet_frame, text="Wallet")
        
        # Wallet connection section
        connection_frame = ttk.LabelFrame(self.wallet_frame, text="Wallet Connection")
        connection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Connection status
        status_frame = ttk.Frame(connection_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        self.wallet_status_label = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.wallet_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Wallet address
        address_frame = ttk.Frame(connection_frame)
        address_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(address_frame, text="Address:").pack(side=tk.LEFT)
        self.wallet_address_label = ttk.Label(address_frame, text="N/A", font=('Consolas', 9))
        self.wallet_address_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Connection buttons
        button_frame = ttk.Frame(connection_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Connect Wallet", command=self.connect_wallet).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Disconnect", command=self.disconnect_wallet).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_wallet).pack(side=tk.LEFT, padx=5)
        
        # Balance section
        balance_frame = ttk.LabelFrame(self.wallet_frame, text="Wallet Balance")
        balance_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # TRX balance
        trx_frame = ttk.Frame(balance_frame)
        trx_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(trx_frame, text="TRX Balance:").pack(side=tk.LEFT)
        self.trx_balance_label = ttk.Label(trx_frame, text="0.00 TRX", font=('Arial', 10, 'bold'))
        self.trx_balance_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # USDT balance
        usdt_frame = ttk.Frame(balance_frame)
        usdt_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(usdt_frame, text="USDT Balance:").pack(side=tk.LEFT)
        self.usdt_balance_label = ttk.Label(usdt_frame, text="0.00 USDT", font=('Arial', 10, 'bold'))
        self.usdt_balance_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Transaction info
        tx_frame = ttk.Frame(balance_frame)
        tx_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(tx_frame, text="Transactions:").pack(side=tk.LEFT)
        self.tx_count_label = ttk.Label(tx_frame, text="0")
        self.tx_count_label.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(tx_frame, text="Last Sync:").pack(side=tk.LEFT, padx=(20, 0))
        self.last_sync_label = ttk.Label(tx_frame, text="N/A")
        self.last_sync_label.pack(side=tk.LEFT, padx=(5, 0))
    
    def create_payout_tab(self) -> None:
        """Create payout creation tab."""
        self.payout_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.payout_frame, text="Create Payout")
        
        # Payout form
        form_frame = ttk.LabelFrame(self.payout_frame, text="Payout Details")
        form_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Recipient address
        recipient_frame = ttk.Frame(form_frame)
        recipient_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(recipient_frame, text="Recipient Address:").pack(anchor=tk.W)
        self.recipient_entry = ttk.Entry(recipient_frame, width=50, font=('Consolas', 9))
        self.recipient_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Amount selection
        amount_frame = ttk.Frame(form_frame)
        amount_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(amount_frame, text="Amount:").pack(anchor=tk.W)
        
        amount_input_frame = ttk.Frame(amount_frame)
        amount_input_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.amount_entry = ttk.Entry(amount_input_frame, width=15)
        self.amount_entry.pack(side=tk.LEFT)
        
        self.currency_var = tk.StringVar(value="TRX")
        currency_combo = ttk.Combobox(amount_input_frame, textvariable=self.currency_var, 
                                    values=["TRX", "USDT"], width=10, state="readonly")
        currency_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Payout type
        type_frame = ttk.Frame(form_frame)
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(type_frame, text="Payout Type:").pack(anchor=tk.W)
        self.payout_type_var = tk.StringVar(value="work_reward")
        type_combo = ttk.Combobox(type_frame, textvariable=self.payout_type_var,
                                values=["work_reward", "staking_reward", "referral_bonus", "manual"],
                                state="readonly")
        type_combo.pack(fill=tk.X, pady=(2, 0))
        
        # Notes
        notes_frame = ttk.Frame(form_frame)
        notes_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(notes_frame, text="Notes (optional):").pack(anchor=tk.W)
        self.notes_entry = ttk.Entry(notes_frame, width=50)
        self.notes_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Gas fee estimation
        gas_frame = ttk.LabelFrame(form_frame, text="Gas Fee Estimation")
        gas_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.gas_fee_label = ttk.Label(gas_frame, text="Estimated Gas Fee: Calculating...")
        self.gas_fee_label.pack(pady=5)
        
        # Action buttons
        action_frame = ttk.Frame(form_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(action_frame, text="Estimate Gas Fee", command=self.estimate_gas_fee).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Create Payout", command=self.create_payout).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=5)
    
    def create_history_tab(self) -> None:
        """Create payout history tab."""
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="Payout History")
        
        # Toolbar
        toolbar = ttk.Frame(self.history_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Export", command=self.export_history).pack(side=tk.LEFT, padx=5)
        
        # Filter options
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                  values=["all", "pending", "completed", "failed"],
                                  width=10, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(5, 0))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_filter)
        
        # History treeview
        columns = ('date', 'recipient', 'amount', 'currency', 'type', 'status', 'tx_hash')
        self.history_tree = ttk.Treeview(self.history_frame, columns=columns, show='headings')
        
        # Configure columns
        self.history_tree.heading('date', text='Date')
        self.history_tree.heading('recipient', text='Recipient')
        self.history_tree.heading('amount', text='Amount')
        self.history_tree.heading('currency', text='Currency')
        self.history_tree.heading('type', text='Type')
        self.history_tree.heading('status', text='Status')
        self.history_tree.heading('tx_hash', text='Transaction Hash')
        
        # Column widths
        self.history_tree.column('date', width=120)
        self.history_tree.column('recipient', width=200)
        self.history_tree.column('amount', width=100)
        self.history_tree.column('currency', width=60)
        self.history_tree.column('type', width=120)
        self.history_tree.column('status', width=80)
        self.history_tree.column('tx_hash', width=200)
        
        # Scrollbar
        history_scroll = ttk.Scrollbar(self.history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to view details
        self.history_tree.bind('<Double-1>', self.view_payout_details)
    
    def create_settings_tab(self) -> None:
        """Create payout settings tab."""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Auto-payout settings
        auto_frame = ttk.LabelFrame(self.settings_frame, text="Auto-Payout Settings")
        auto_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.auto_payout_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(auto_frame, text="Enable Auto-Payout", variable=self.auto_payout_var)
        auto_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Threshold settings
        threshold_frame = ttk.Frame(auto_frame)
        threshold_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(threshold_frame, text="Minimum Balance Threshold:").pack(side=tk.LEFT)
        self.threshold_entry = ttk.Entry(threshold_frame, width=10)
        self.threshold_entry.insert(0, "100.0")
        self.threshold_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(threshold_frame, text="TRX").pack(side=tk.LEFT, padx=(2, 0))
        
        # Gas price settings
        gas_frame = ttk.LabelFrame(self.settings_frame, text="Gas Price Settings")
        gas_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.gas_price_var = tk.StringVar(value="medium")
        ttk.Label(gas_frame, text="Gas Price Priority:").pack(anchor=tk.W, padx=5, pady=2)
        
        gas_radio_frame = ttk.Frame(gas_frame)
        gas_radio_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(gas_radio_frame, text="Low (Slow)", variable=self.gas_price_var, value="low").pack(anchor=tk.W)
        ttk.Radiobutton(gas_radio_frame, text="Medium (Normal)", variable=self.gas_price_var, value="medium").pack(anchor=tk.W)
        ttk.Radiobutton(gas_radio_frame, text="High (Fast)", variable=self.gas_price_var, value="high").pack(anchor=tk.W)
        
        # Save settings button
        settings_button_frame = ttk.Frame(self.settings_frame)
        settings_button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(settings_button_frame, text="Save Settings", command=self.save_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(settings_button_frame, text="Reset to Defaults", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
    
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
        """Start wallet and payout monitoring."""
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                if self.wallet_info and self.wallet_info.is_connected:
                    self.refresh_wallet()
                    self.refresh_pending_payouts()
                
                time.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def connect_wallet(self) -> None:
        """Connect to TRON wallet."""
        try:
            # This would typically involve wallet connection logic
            # For now, we'll simulate a connection
            
            response = self._make_api_request("GET", "/api/payouts/wallet/connect")
            if response:
                self.wallet_info = WalletInfo(
                    address=response.get("address", ""),
                    balance_trx=response.get("balance_trx", 0.0),
                    balance_usdt=response.get("balance_usdt", 0.0),
                    is_connected=True,
                    last_sync=datetime.now(timezone.utc),
                    transaction_count=response.get("transaction_count", 0)
                )
                
                self.update_wallet_display()
                messagebox.showinfo("Success", "Wallet connected successfully")
            else:
                messagebox.showerror("Error", "Failed to connect wallet")
                
        except Exception as e:
            logger.error(f"Wallet connection failed: {e}")
            messagebox.showerror("Error", f"Failed to connect wallet: {e}")
    
    def disconnect_wallet(self) -> None:
        """Disconnect from TRON wallet."""
        try:
            self._make_api_request("POST", "/api/payouts/wallet/disconnect")
            self.wallet_info = None
            self.update_wallet_display()
            messagebox.showinfo("Success", "Wallet disconnected")
        except Exception as e:
            logger.error(f"Wallet disconnection failed: {e}")
            messagebox.showerror("Error", f"Failed to disconnect wallet: {e}")
    
    def refresh_wallet(self) -> None:
        """Refresh wallet information."""
        if not self.wallet_info:
            return
        
        try:
            response = self._make_api_request("GET", "/api/payouts/wallet/balance")
            if response:
                self.wallet_info.balance_trx = response.get("balance_trx", 0.0)
                self.wallet_info.balance_usdt = response.get("balance_usdt", 0.0)
                self.wallet_info.last_sync = datetime.now(timezone.utc)
                self.wallet_info.transaction_count = response.get("transaction_count", 0)
                
                self.update_wallet_display()
        except Exception as e:
            logger.error(f"Failed to refresh wallet: {e}")
    
    def update_wallet_display(self) -> None:
        """Update wallet display information."""
        if self.wallet_info and self.wallet_info.is_connected:
            self.wallet_status_label.configure(text="Connected", foreground="green")
            self.wallet_address_label.configure(text=self.wallet_info.address)
            self.trx_balance_label.configure(text=f"{self.wallet_info.balance_trx:.6f} TRX")
            self.usdt_balance_label.configure(text=f"{self.wallet_info.balance_usdt:.2f} USDT")
            self.tx_count_label.configure(text=str(self.wallet_info.transaction_count))
            self.last_sync_label.configure(text=self.wallet_info.last_sync.strftime("%H:%M:%S"))
        else:
            self.wallet_status_label.configure(text="Disconnected", foreground="red")
            self.wallet_address_label.configure(text="N/A")
            self.trx_balance_label.configure(text="0.00 TRX")
            self.usdt_balance_label.configure(text="0.00 USDT")
            self.tx_count_label.configure(text="0")
            self.last_sync_label.configure(text="N/A")
    
    def estimate_gas_fee(self) -> None:
        """Estimate gas fee for payout transaction."""
        try:
            amount = float(self.amount_entry.get())
            currency = self.currency_var.get()
            
            if not amount or amount <= 0:
                messagebox.showerror("Error", "Please enter a valid amount")
                return
            
            # Simulate gas fee estimation
            gas_fee = 1.0  # Base gas fee in TRX
            if currency == "USDT":
                gas_fee += 0.5  # Additional fee for USDT transactions
            
            self.gas_fee_label.configure(text=f"Estimated Gas Fee: {gas_fee:.6f} TRX")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount")
        except Exception as e:
            logger.error(f"Gas fee estimation failed: {e}")
            messagebox.showerror("Error", f"Failed to estimate gas fee: {e}")
    
    def create_payout(self) -> None:
        """Create a new payout transaction."""
        try:
            # Validate input
            recipient = self.recipient_entry.get().strip()
            amount_str = self.amount_entry.get().strip()
            payout_type = self.payout_type_var.get()
            notes = self.notes_entry.get().strip()
            
            if not recipient:
                messagebox.showerror("Error", "Please enter recipient address")
                return
            
            if not amount_str:
                messagebox.showerror("Error", "Please enter amount")
                return
            
            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid amount")
                return
            
            # Check wallet balance
            currency = self.currency_var.get()
            if currency == "TRX" and self.wallet_info.balance_trx < amount + 1.0:  # +1 TRX for gas
                messagebox.showerror("Error", "Insufficient TRX balance")
                return
            elif currency == "USDT" and self.wallet_info.balance_usdt < amount:
                messagebox.showerror("Error", "Insufficient USDT balance")
                return
            
            # Create payout transaction
            payout_data = {
                "recipient_address": recipient,
                "amount": amount,
                "currency": currency,
                "payout_type": payout_type,
                "notes": notes
            }
            
            response = self._make_api_request("POST", "/api/payouts/create", payout_data)
            if response:
                messagebox.showinfo("Success", "Payout transaction created successfully")
                self.clear_form()
                self.refresh_history()
            else:
                messagebox.showerror("Error", "Failed to create payout transaction")
                
        except Exception as e:
            logger.error(f"Payout creation failed: {e}")
            messagebox.showerror("Error", f"Failed to create payout: {e}")
    
    def clear_form(self) -> None:
        """Clear the payout form."""
        self.recipient_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self.gas_fee_label.configure(text="Estimated Gas Fee: Calculating...")
    
    def refresh_history(self) -> None:
        """Refresh payout history."""
        try:
            response = self._make_api_request("GET", "/api/payouts/history")
            if response:
                self.payout_history = []
                for payout_data in response.get("payouts", []):
                    payout = PayoutTransaction(
                        transaction_id=payout_data.get("transaction_id", ""),
                        recipient_address=payout_data.get("recipient_address", ""),
                        amount_trx=payout_data.get("amount_trx", 0.0),
                        amount_usdt=payout_data.get("amount_usdt", 0.0),
                        payout_type=PayoutType(payout_data.get("payout_type", "manual")),
                        status=PayoutStatus(payout_data.get("status", "pending")),
                        created_at=datetime.fromisoformat(payout_data.get("created_at", "")),
                        completed_at=datetime.fromisoformat(payout_data.get("completed_at", "")) if payout_data.get("completed_at") else None,
                        blockchain_tx_hash=payout_data.get("blockchain_tx_hash"),
                        gas_fee=payout_data.get("gas_fee", 0.0),
                        notes=payout_data.get("notes", "")
                    )
                    self.payout_history.append(payout)
                
                self.update_history_display()
        except Exception as e:
            logger.error(f"Failed to refresh history: {e}")
    
    def update_history_display(self) -> None:
        """Update history display."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Add payout transactions
        for payout in self.payout_history:
            # Apply filter
            if self.filter_var.get() != "all" and payout.status.value != self.filter_var.get():
                continue
            
            # Determine currency and amount
            if payout.amount_usdt > 0:
                currency = "USDT"
                amount = payout.amount_usdt
            else:
                currency = "TRX"
                amount = payout.amount_trx
            
            # Format date
            date_str = payout.created_at.strftime("%Y-%m-%d %H:%M")
            
            # Truncate long addresses
            recipient_short = payout.recipient_address[:20] + "..." if len(payout.recipient_address) > 20 else payout.recipient_address
            
            # Status color
            status_colors = {
                "pending": "orange",
                "processing": "blue", 
                "completed": "green",
                "failed": "red",
                "cancelled": "gray"
            }
            
            item = self.history_tree.insert('', 'end', values=(
                date_str,
                recipient_short,
                f"{amount:.6f}",
                currency,
                payout.payout_type.value.replace('_', ' ').title(),
                payout.status.value.title(),
                payout.blockchain_tx_hash[:20] + "..." if payout.blockchain_tx_hash and len(payout.blockchain_tx_hash) > 20 else (payout.blockchain_tx_hash or "")
            ))
    
    def apply_filter(self, event=None) -> None:
        """Apply filter to history display."""
        self.update_history_display()
    
    def refresh_pending_payouts(self) -> None:
        """Refresh pending payouts status."""
        try:
            response = self._make_api_request("GET", "/api/payouts/pending")
            if response:
                # Update pending payout statuses
                for payout_data in response.get("payouts", []):
                    # Find matching payout in history and update status
                    for payout in self.payout_history:
                        if payout.transaction_id == payout_data.get("transaction_id"):
                            payout.status = PayoutStatus(payout_data.get("status", "pending"))
                            if payout_data.get("blockchain_tx_hash"):
                                payout.blockchain_tx_hash = payout_data["blockchain_tx_hash"]
                            break
                
                # Refresh display
                self.update_history_display()
        except Exception as e:
            logger.error(f"Failed to refresh pending payouts: {e}")
    
    def view_payout_details(self, event) -> None:
        """View detailed payout information."""
        selection = self.history_tree.selection()
        if not selection:
            return
        
        item = self.history_tree.item(selection[0])
        values = item['values']
        
        # Find the payout transaction
        date_str = values[0]
        recipient = values[1]
        
        payout = None
        for p in self.payout_history:
            if (p.created_at.strftime("%Y-%m-%d %H:%M") == date_str and 
                p.recipient_address.startswith(recipient.split('...')[0])):
                payout = p
                break
        
        if not payout:
            return
        
        # Create details dialog
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title("Payout Details")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        
        # Details text
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=60, height=20)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format details
        details = f"""Transaction ID: {payout.transaction_id}
Recipient: {payout.recipient_address}
Amount TRX: {payout.amount_trx:.6f}
Amount USDT: {payout.amount_usdt:.2f}
Payout Type: {payout.payout_type.value.replace('_', ' ').title()}
Status: {payout.status.value.title()}
Created: {payout.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
Completed: {payout.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if payout.completed_at else "N/A"}
Blockchain TX: {payout.blockchain_tx_hash or "N/A"}
Gas Fee: {payout.gas_fee:.6f} TRX
Notes: {payout.notes}
"""
        
        details_text.insert(tk.END, details)
        details_text.configure(state=tk.DISABLED)
        
        # Close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def export_history(self) -> None:
        """Export payout history to file."""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    self._export_csv(filename)
                else:
                    self._export_json(filename)
                
                messagebox.showinfo("Success", f"History exported to {filename}")
            except Exception as e:
                logger.error(f"Export failed: {e}")
                messagebox.showerror("Error", f"Failed to export history: {e}")
    
    def _export_csv(self, filename: str) -> None:
        """Export history to CSV format."""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Date', 'Recipient', 'Amount TRX', 'Amount USDT', 'Type', 
                'Status', 'Transaction Hash', 'Gas Fee', 'Notes'
            ])
            
            for payout in self.payout_history:
                writer.writerow([
                    payout.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    payout.recipient_address,
                    payout.amount_trx,
                    payout.amount_usdt,
                    payout.payout_type.value,
                    payout.status.value,
                    payout.blockchain_tx_hash or "",
                    payout.gas_fee,
                    payout.notes
                ])
    
    def _export_json(self, filename: str) -> None:
        """Export history to JSON format."""
        data = []
        for payout in self.payout_history:
            payout_dict = {
                "transaction_id": payout.transaction_id,
                "recipient_address": payout.recipient_address,
                "amount_trx": payout.amount_trx,
                "amount_usdt": payout.amount_usdt,
                "payout_type": payout.payout_type.value,
                "status": payout.status.value,
                "created_at": payout.created_at.isoformat(),
                "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
                "blockchain_tx_hash": payout.blockchain_tx_hash,
                "gas_fee": payout.gas_fee,
                "notes": payout.notes
            }
            data.append(payout_dict)
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def save_settings(self) -> None:
        """Save payout settings."""
        try:
            settings = {
                "auto_payout_enabled": self.auto_payout_var.get(),
                "threshold_trx": float(self.threshold_entry.get()),
                "gas_price_priority": self.gas_price_var.get()
            }
            
            self.config_manager.save_config("payout_settings", settings)
            messagebox.showinfo("Success", "Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.auto_payout_var.set(False)
        self.threshold_entry.delete(0, tk.END)
        self.threshold_entry.insert(0, "100.0")
        self.gas_price_var.set("medium")
        messagebox.showinfo("Success", "Settings reset to defaults")
    
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

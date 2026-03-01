# Path: gui/user/proofs_viewer.py
"""
Session proofs display and export for Lucid RDP GUI.
Provides comprehensive proof viewing, validation, and export capabilities for RDP session recordings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import hashlib
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import csv
import threading
import time

from ..core.config_manager import get_config_manager
from ..core.security import get_security_validator, CryptographicUtils
from ..core.networking import TorHttpClient, SecurityConfig

logger = logging.getLogger(__name__)


class ProofType(Enum):
    """Types of session proofs"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_INTERACTION = "user_interaction"
    FILE_TRANSFER = "file_transfer"
    CLIPBOARD_ACCESS = "clipboard_access"
    SCREENSHOT = "screenshot"
    AUDIO_CAPTURE = "audio_capture"
    POLICY_VIOLATION = "policy_violation"
    AUTHENTICATION = "authentication"
    HEARTBEAT = "heartbeat"


class ProofStatus(Enum):
    """Proof validation status"""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    TAMPERED = "tampered"
    PENDING = "pending"
    UNVERIFIED = "unverified"


@dataclass
class ProofData:
    """Individual proof data structure"""
    proof_id: str
    proof_type: ProofType
    session_id: str
    timestamp: datetime
    data_hash: str
    signature: str
    metadata: Dict[str, Any]
    status: ProofStatus = ProofStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['proof_type'] = self.proof_type.value
        data['status'] = self.status.value
        return data
    
    def calculate_hash(self) -> str:
        """Calculate hash of proof data"""
        data_to_hash = {
            'proof_id': self.proof_id,
            'proof_type': self.proof_type.value,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
        json_str = json.dumps(data_to_hash, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class SessionProofs:
    """Complete session proofs container"""
    session_id: str
    session_start: datetime
    session_end: Optional[datetime]
    participant_pubkeys: List[str]
    policy_hash: str
    root_hash: str
    proofs: List[ProofData]
    total_chunks: int
    recorder_version: str
    device_fingerprint: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['session_start'] = self.session_start.isoformat()
        data['session_end'] = self.session_end.isoformat() if self.session_end else None
        data['proofs'] = [proof.to_dict() for proof in self.proofs]
        return data
    
    def get_proofs_by_type(self, proof_type: ProofType) -> List[ProofData]:
        """Get proofs filtered by type"""
        return [proof for proof in self.proofs if proof.proof_type == proof_type]
    
    def get_proofs_by_status(self, status: ProofStatus) -> List[ProofData]:
        """Get proofs filtered by status"""
        return [proof for proof in self.proofs if proof.status == status]
    
    def calculate_session_hash(self) -> str:
        """Calculate overall session hash"""
        session_data = {
            'session_id': self.session_id,
            'participant_pubkeys': sorted(self.participant_pubkeys),
            'policy_hash': self.policy_hash,
            'total_chunks': self.total_chunks,
            'recorder_version': self.recorder_version,
            'proof_hashes': [proof.data_hash for proof in sorted(self.proofs, key=lambda p: p.timestamp)]
        }
        json_str = json.dumps(session_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


class ProofValidator:
    """Validates proof integrity and authenticity"""
    
    def __init__(self):
        self.security_validator = get_security_validator()
        self.validation_results: Dict[str, Dict[str, Any]] = {}
    
    def validate_proof(self, proof: ProofData, public_key: Optional[str] = None) -> Tuple[ProofStatus, str]:
        """Validate individual proof"""
        try:
            # Check timestamp validity
            if proof.timestamp > datetime.now(timezone.utc):
                return ProofStatus.INVALID, "Future timestamp"
            
            # Check hash integrity
            calculated_hash = proof.calculate_hash()
            if calculated_hash != proof.data_hash:
                return ProofStatus.TAMPERED, "Hash mismatch"
            
            # Validate signature if public key provided
            if public_key and proof.signature:
                if not self._verify_signature(proof, public_key):
                    return ProofStatus.INVALID, "Invalid signature"
            
            # Check if proof is expired (older than 30 days)
            if (datetime.now(timezone.utc) - proof.timestamp).days > 30:
                return ProofStatus.EXPIRED, "Proof expired"
            
            return ProofStatus.VALID, "Proof valid"
            
        except Exception as e:
            logger.error(f"Proof validation failed: {e}")
            return ProofStatus.INVALID, f"Validation error: {e}"
    
    def validate_session_proofs(self, session_proofs: SessionProofs) -> Dict[str, Any]:
        """Validate complete session proofs"""
        validation_results = {
            'session_id': session_proofs.session_id,
            'overall_status': ProofStatus.VALID,
            'proof_validations': {},
            'summary': {
                'total_proofs': len(session_proofs.proofs),
                'valid_proofs': 0,
                'invalid_proofs': 0,
                'expired_proofs': 0,
                'tampered_proofs': 0
            }
        }
        
        # Validate each proof
        for proof in session_proofs.proofs:
            status, message = self.validate_proof(proof)
            validation_results['proof_validations'][proof.proof_id] = {
                'status': status.value,
                'message': message
            }
            
            # Update summary
            if status == ProofStatus.VALID:
                validation_results['summary']['valid_proofs'] += 1
            elif status == ProofStatus.INVALID:
                validation_results['summary']['invalid_proofs'] += 1
            elif status == ProofStatus.EXPIRED:
                validation_results['summary']['expired_proofs'] += 1
            elif status == ProofStatus.TAMPERED:
                validation_results['summary']['tampered_proofs'] += 1
        
        # Determine overall status
        if validation_results['summary']['tampered_proofs'] > 0:
            validation_results['overall_status'] = ProofStatus.TAMPERED
        elif validation_results['summary']['invalid_proofs'] > 0:
            validation_results['overall_status'] = ProofStatus.INVALID
        elif validation_results['summary']['expired_proofs'] > len(session_proofs.proofs) // 2:
            validation_results['overall_status'] = ProofStatus.EXPIRED
        
        return validation_results
    
    def _verify_signature(self, proof: ProofData, public_key: str) -> bool:
        """Verify proof signature"""
        try:
            # This would implement actual signature verification
            # For now, we'll do a basic check
            if not proof.signature:
                return False
            
            # Decode signature and verify
            signature_data = base64.b64decode(proof.signature)
            # Actual verification would use the public key here
            return len(signature_data) > 0  # Placeholder
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


class ProofsViewer:
    """Main proofs viewer interface"""
    
    def __init__(self, parent_frame: tk.Widget):
        self.parent_frame = parent_frame
        self.validator = ProofValidator()
        self.config_manager = get_config_manager()
        
        # Data storage
        self.current_session_proofs: Optional[SessionProofs] = None
        self.proof_filters: Dict[str, Any] = {}
        
        # Setup GUI
        self.setup_gui()
        
        logger.info("Proofs viewer initialized")
    
    def setup_gui(self) -> None:
        """Setup the proofs viewer GUI"""
        # Main container
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_overview_tab()
        self.create_proofs_tab()
        self.create_validation_tab()
        self.create_export_tab()
    
    def create_overview_tab(self) -> None:
        """Create session overview tab"""
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Overview")
        
        # Session info section
        info_frame = ttk.LabelFrame(self.overview_frame, text="Session Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Session details
        details_frame = ttk.Frame(info_frame)
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Session ID
        ttk.Label(details_frame, text="Session ID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.session_id_label = ttk.Label(details_frame, text="N/A", font=('Consolas', 9))
        self.session_id_label.grid(row=0, column=1, sticky=tk.W)
        
        # Duration
        ttk.Label(details_frame, text="Duration:").grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        self.duration_label = ttk.Label(details_frame, text="N/A")
        self.duration_label.grid(row=0, column=3, sticky=tk.W)
        
        # Total proofs
        ttk.Label(details_frame, text="Total Proofs:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.total_proofs_label = ttk.Label(details_frame, text="0")
        self.total_proofs_label.grid(row=1, column=1, sticky=tk.W)
        
        # Valid proofs
        ttk.Label(details_frame, text="Valid Proofs:").grid(row=1, column=2, sticky=tk.W, padx=(20, 10))
        self.valid_proofs_label = ttk.Label(details_frame, text="0", foreground="green")
        self.valid_proofs_label.grid(row=1, column=3, sticky=tk.W)
        
        # Session hash
        ttk.Label(details_frame, text="Session Hash:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.session_hash_label = ttk.Label(details_frame, text="N/A", font=('Consolas', 8))
        self.session_hash_label.grid(row=2, column=1, columnspan=3, sticky=tk.W)
        
        # Proof type breakdown
        breakdown_frame = ttk.LabelFrame(self.overview_frame, text="Proof Type Breakdown")
        breakdown_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for proof types
        columns = ('type', 'count', 'valid', 'invalid')
        self.breakdown_tree = ttk.Treeview(breakdown_frame, columns=columns, show='headings')
        
        self.breakdown_tree.heading('type', text='Proof Type')
        self.breakdown_tree.heading('count', text='Count')
        self.breakdown_tree.heading('valid', text='Valid')
        self.breakdown_tree.heading('invalid', text='Invalid')
        
        self.breakdown_tree.column('type', width=150)
        self.breakdown_tree.column('count', width=80)
        self.breakdown_tree.column('valid', width=80)
        self.breakdown_tree.column('invalid', width=80)
        
        breakdown_scroll = ttk.Scrollbar(breakdown_frame, orient=tk.VERTICAL, command=self.breakdown_tree.yview)
        self.breakdown_tree.configure(yscrollcommand=breakdown_scroll.set)
        
        self.breakdown_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        breakdown_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
    
    def create_proofs_tab(self) -> None:
        """Create detailed proofs tab"""
        self.proofs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.proofs_frame, text="Proofs")
        
        # Toolbar
        toolbar = ttk.Frame(self.proofs_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self.refresh_proofs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Validate All", command=self.validate_all_proofs).pack(side=tk.LEFT, padx=5)
        
        # Filter controls
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                  values=["all", "valid", "invalid", "expired", "tampered"],
                                  width=10, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(5, 0))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_proof_filter)
        
        # Proofs treeview
        columns = ('timestamp', 'type', 'status', 'hash', 'metadata')
        self.proofs_tree = ttk.Treeview(self.proofs_frame, columns=columns, show='headings')
        
        self.proofs_tree.heading('timestamp', text='Timestamp')
        self.proofs_tree.heading('type', text='Type')
        self.proofs_tree.heading('status', text='Status')
        self.proofs_tree.heading('hash', text='Hash')
        self.proofs_tree.heading('metadata', text='Metadata')
        
        self.proofs_tree.column('timestamp', width=150)
        self.proofs_tree.column('type', width=120)
        self.proofs_tree.column('status', width=80)
        self.proofs_tree.column('hash', width=200)
        self.proofs_tree.column('metadata', width=300)
        
        proofs_scroll = ttk.Scrollbar(self.proofs_frame, orient=tk.VERTICAL, command=self.proofs_tree.yview)
        self.proofs_tree.configure(yscrollcommand=proofs_scroll.set)
        
        self.proofs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        proofs_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Double-click to view details
        self.proofs_tree.bind('<Double-1>', self.view_proof_details)
    
    def create_validation_tab(self) -> None:
        """Create validation results tab"""
        self.validation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.validation_frame, text="Validation")
        
        # Validation controls
        controls_frame = ttk.Frame(self.validation_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(controls_frame, text="Run Full Validation", 
                  command=self.run_full_validation).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Export Validation Report", 
                  command=self.export_validation_report).pack(side=tk.LEFT, padx=5)
        
        # Validation results
        results_frame = ttk.LabelFrame(self.validation_frame, text="Validation Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.validation_text = scrolledtext.ScrolledText(
            results_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=20,
            font=('Consolas', 9)
        )
        self.validation_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_export_tab(self) -> None:
        """Create export options tab"""
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="Export")
        
        # Export options
        options_frame = ttk.LabelFrame(self.export_frame, text="Export Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Export format
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(format_frame, text="Format:").pack(side=tk.LEFT)
        self.export_format_var = tk.StringVar(value="json")
        format_combo = ttk.Combobox(format_frame, textvariable=self.export_format_var,
                                  values=["json", "csv", "xml", "pdf"], state="readonly")
        format_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # Include options
        include_frame = ttk.Frame(options_frame)
        include_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.include_metadata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(include_frame, text="Include Metadata", 
                       variable=self.include_metadata_var).pack(side=tk.LEFT)
        
        self.include_validation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(include_frame, text="Include Validation Results", 
                       variable=self.include_validation_var).pack(side=tk.LEFT, padx=(20, 0))
        
        # Export buttons
        button_frame = ttk.Frame(self.export_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Export Session Proofs", 
                  command=self.export_session_proofs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Export Proof Details", 
                  command=self.export_proof_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Summary Report", 
                  command=self.export_summary_report).pack(side=tk.LEFT, padx=5)
    
    def load_session_proofs(self, session_proofs: SessionProofs) -> None:
        """Load session proofs for display"""
        self.current_session_proofs = session_proofs
        self.update_overview_display()
        self.update_proofs_display()
        logger.info(f"Loaded proofs for session: {session_proofs.session_id}")
    
    def update_overview_display(self) -> None:
        """Update overview tab display"""
        if not self.current_session_proofs:
            return
        
        session = self.current_session_proofs
        
        # Update session info
        self.session_id_label.configure(text=session.session_id[:20] + "...")
        self.session_hash_label.configure(text=session.calculate_session_hash()[:32] + "...")
        
        # Calculate duration
        if session.session_end:
            duration = session.session_end - session.session_start
            duration_str = str(duration).split('.')[0]  # Remove microseconds
        else:
            duration_str = "Ongoing"
        self.duration_label.configure(text=duration_str)
        
        # Update proof counts
        total_proofs = len(session.proofs)
        valid_proofs = len(session.get_proofs_by_status(ProofStatus.VALID))
        
        self.total_proofs_label.configure(text=str(total_proofs))
        self.valid_proofs_label.configure(text=str(valid_proofs))
        
        # Update breakdown
        self.update_proof_breakdown()
    
    def update_proof_breakdown(self) -> None:
        """Update proof type breakdown display"""
        if not self.current_session_proofs:
            return
        
        # Clear existing items
        for item in self.breakdown_tree.get_children():
            self.breakdown_tree.delete(item)
        
        # Group proofs by type
        type_counts = {}
        for proof in self.current_session_proofs.proofs:
            proof_type = proof.proof_type.value
            if proof_type not in type_counts:
                type_counts[proof_type] = {'total': 0, 'valid': 0, 'invalid': 0}
            
            type_counts[proof_type]['total'] += 1
            if proof.status == ProofStatus.VALID:
                type_counts[proof_type]['valid'] += 1
            else:
                type_counts[proof_type]['invalid'] += 1
        
        # Add to tree
        for proof_type, counts in type_counts.items():
            self.breakdown_tree.insert('', 'end', values=(
                proof_type.replace('_', ' ').title(),
                counts['total'],
                counts['valid'],
                counts['invalid']
            ))
    
    def update_proofs_display(self) -> None:
        """Update proofs tab display"""
        if not self.current_session_proofs:
            return
        
        # Clear existing items
        for item in self.proofs_tree.get_children():
            self.proofs_tree.delete(item)
        
        # Add proofs
        for proof in self.current_session_proofs.proofs:
            # Apply filter
            if self.filter_var.get() != "all" and proof.status.value != self.filter_var.get():
                continue
            
            # Format metadata
            metadata_str = json.dumps(proof.metadata, indent=None, separators=(',', ':'))[:50]
            if len(json.dumps(proof.metadata)) > 50:
                metadata_str += "..."
            
            # Status color
            status_colors = {
                "valid": "green",
                "invalid": "red",
                "expired": "orange",
                "tampered": "red",
                "pending": "blue",
                "unverified": "gray"
            }
            
            item = self.proofs_tree.insert('', 'end', values=(
                proof.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                proof.proof_type.value.replace('_', ' ').title(),
                proof.status.value.title(),
                proof.data_hash[:16] + "...",
                metadata_str
            ))
    
    def apply_proof_filter(self, event=None) -> None:
        """Apply filter to proofs display"""
        self.update_proofs_display()
    
    def refresh_proofs(self) -> None:
        """Refresh proofs display"""
        if self.current_session_proofs:
            self.update_proofs_display()
            messagebox.showinfo("Success", "Proofs refreshed")
    
    def validate_all_proofs(self) -> None:
        """Validate all proofs"""
        if not self.current_session_proofs:
            messagebox.showwarning("Warning", "No session proofs loaded")
            return
        
        def validate_async():
            try:
                # Run validation
                results = self.validator.validate_session_proofs(self.current_session_proofs)
                
                # Update proof statuses
                for proof in self.current_session_proofs.proofs:
                    if proof.proof_id in results['proof_validations']:
                        validation = results['proof_validations'][proof.proof_id]
                        proof.status = ProofStatus(validation['status'])
                
                # Update displays
                self.parent_frame.after(0, lambda: self.update_proofs_display())
                self.parent_frame.after(0, lambda: self.update_overview_display())
                
                self.parent_frame.after(0, lambda: messagebox.showinfo(
                    "Validation Complete", 
                    f"Validated {results['summary']['total_proofs']} proofs. "
                    f"Valid: {results['summary']['valid_proofs']}, "
                    f"Invalid: {results['summary']['invalid_proofs']}"
                ))
                
            except Exception as e:
                self.parent_frame.after(0, lambda: messagebox.showerror("Validation Error", str(e)))
        
        # Run validation in background
        threading.Thread(target=validate_async, daemon=True).start()
    
    def run_full_validation(self) -> None:
        """Run full validation and display results"""
        if not self.current_session_proofs:
            messagebox.showwarning("Warning", "No session proofs loaded")
            return
        
        def validate_async():
            try:
                results = self.validator.validate_session_proofs(self.current_session_proofs)
                
                # Format results for display
                report = f"""Validation Report for Session: {results['session_id']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Overall Status: {results['overall_status'].value.upper()}

Summary:
- Total Proofs: {results['summary']['total_proofs']}
- Valid Proofs: {results['summary']['valid_proofs']}
- Invalid Proofs: {results['summary']['invalid_proofs']}
- Expired Proofs: {results['summary']['expired_proofs']}
- Tampered Proofs: {results['summary']['tampered_proofs']}

Detailed Results:
"""
                
                for proof_id, validation in results['proof_validations'].items():
                    report += f"\nProof {proof_id[:8]}...: {validation['status'].upper()} - {validation['message']}"
                
                # Update display
                self.parent_frame.after(0, lambda: self.validation_text.delete(1.0, tk.END))
                self.parent_frame.after(0, lambda: self.validation_text.insert(tk.END, report))
                
            except Exception as e:
                self.parent_frame.after(0, lambda: messagebox.showerror("Validation Error", str(e)))
        
        # Run validation in background
        threading.Thread(target=validate_async, daemon=True).start()
    
    def view_proof_details(self, event) -> None:
        """View detailed proof information"""
        selection = self.proofs_tree.selection()
        if not selection:
            return
        
        item = self.proofs_tree.item(selection[0])
        values = item['values']
        
        # Find the proof
        timestamp_str = values[0]
        proof_type = values[1]
        
        proof = None
        for p in self.current_session_proofs.proofs:
            if (p.timestamp.strftime("%Y-%m-%d %H:%M:%S") == timestamp_str and 
                p.proof_type.value.replace('_', ' ').title() == proof_type):
                proof = p
                break
        
        if not proof:
            return
        
        # Create details dialog
        dialog = tk.Toplevel(self.parent_frame)
        dialog.title("Proof Details")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        
        # Details text
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=70, height=25)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format details
        details = f"""Proof ID: {proof.proof_id}
Proof Type: {proof.proof_type.value}
Session ID: {proof.session_id}
Timestamp: {proof.timestamp.isoformat()}
Status: {proof.status.value}
Data Hash: {proof.data_hash}
Signature: {proof.signature[:50]}...

Metadata:
{json.dumps(proof.metadata, indent=2)}
"""
        
        details_text.insert(tk.END, details)
        details_text.configure(state=tk.DISABLED)
        
        # Close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def export_session_proofs(self) -> None:
        """Export complete session proofs"""
        if not self.current_session_proofs:
            messagebox.showwarning("Warning", "No session proofs loaded")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{self.export_format_var.get()}",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("XML files", "*.xml"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    self._export_json(filename)
                elif filename.endswith('.csv'):
                    self._export_csv(filename)
                elif filename.endswith('.xml'):
                    self._export_xml(filename)
                
                messagebox.showinfo("Success", f"Proofs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export proofs: {e}")
    
    def export_proof_details(self) -> None:
        """Export detailed proof information"""
        if not self.current_session_proofs:
            messagebox.showwarning("Warning", "No session proofs loaded")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Export detailed proof data
                detailed_data = {
                    'session_info': self.current_session_proofs.to_dict(),
                    'validation_results': self.validator.validate_session_proofs(self.current_session_proofs),
                    'export_metadata': {
                        'exported_at': datetime.now(timezone.utc).isoformat(),
                        'exporter_version': '1.0.0'
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(detailed_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Detailed proofs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export detailed proofs: {e}")
    
    def export_summary_report(self) -> None:
        """Export summary report"""
        if not self.current_session_proofs:
            messagebox.showwarning("Warning", "No session proofs loaded")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                session = self.current_session_proofs
                
                # Generate summary
                summary = f"""Lucid RDP Session Proofs Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SESSION INFORMATION:
- Session ID: {session.session_id}
- Start Time: {session.session_start.isoformat()}
- End Time: {session.session_end.isoformat() if session.session_end else 'Ongoing'}
- Duration: {str(session.session_end - session.session_start).split('.')[0] if session.session_end else 'Ongoing'}
- Total Chunks: {session.total_chunks}
- Recorder Version: {session.recorder_version}
- Device Fingerprint: {session.device_fingerprint}

PROOF STATISTICS:
- Total Proofs: {len(session.proofs)}
- Valid Proofs: {len(session.get_proofs_by_status(ProofStatus.VALID))}
- Invalid Proofs: {len(session.get_proofs_by_status(ProofStatus.INVALID))}
- Expired Proofs: {len(session.get_proofs_by_status(ProofStatus.EXPIRED))}
- Tampered Proofs: {len(session.get_proofs_by_status(ProofStatus.TAMPERED))}

PROOF TYPE BREAKDOWN:
"""
                
                # Add proof type breakdown
                type_counts = {}
                for proof in session.proofs:
                    proof_type = proof.proof_type.value
                    type_counts[proof_type] = type_counts.get(proof_type, 0) + 1
                
                for proof_type, count in sorted(type_counts.items()):
                    summary += f"- {proof_type.replace('_', ' ').title()}: {count}\n"
                
                summary += f"\nSESSION HASH: {session.calculate_session_hash()}\n"
                
                with open(filename, 'w') as f:
                    f.write(summary)
                
                messagebox.showinfo("Success", f"Summary report exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export summary report: {e}")
    
    def export_validation_report(self) -> None:
        """Export validation report"""
        content = self.validation_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "No validation results to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Validation report exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export validation report: {e}")
    
    def _export_json(self, filename: str) -> None:
        """Export to JSON format"""
        data = self.current_session_proofs.to_dict()
        if self.include_validation_var.get():
            data['validation_results'] = self.validator.validate_session_proofs(self.current_session_proofs)
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _export_csv(self, filename: str) -> None:
        """Export to CSV format"""
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Proof ID', 'Type', 'Timestamp', 'Status', 'Hash', 'Metadata'])
            
            for proof in self.current_session_proofs.proofs:
                metadata_str = json.dumps(proof.metadata) if self.include_metadata_var.get() else ""
                writer.writerow([
                    proof.proof_id,
                    proof.proof_type.value,
                    proof.timestamp.isoformat(),
                    proof.status.value,
                    proof.data_hash,
                    metadata_str
                ])
    
    def _export_xml(self, filename: str) -> None:
        """Export to XML format"""
        import xml.etree.ElementTree as ET
        
        root = ET.Element("SessionProofs")
        root.set("session_id", self.current_session_proofs.session_id)
        root.set("exported_at", datetime.now(timezone.utc).isoformat())
        
        for proof in self.current_session_proofs.proofs:
            proof_elem = ET.SubElement(root, "Proof")
            proof_elem.set("id", proof.proof_id)
            proof_elem.set("type", proof.proof_type.value)
            proof_elem.set("timestamp", proof.timestamp.isoformat())
            proof_elem.set("status", proof.status.value)
            proof_elem.set("hash", proof.data_hash)
            
            if self.include_metadata_var.get():
                metadata_elem = ET.SubElement(proof_elem, "Metadata")
                for key, value in proof.metadata.items():
                    meta_elem = ET.SubElement(metadata_elem, key)
                    meta_elem.text = str(value)
        
        tree = ET.ElementTree(root)
        tree.write(filename, encoding='utf-8', xml_declaration=True)
    
    def cleanup(self) -> None:
        """Cleanup proofs viewer"""
        self.current_session_proofs = None
        logger.info("Proofs viewer cleaned up")


# Global proofs viewer instance
_proofs_viewer: Optional[ProofsViewer] = None


def get_proofs_viewer(parent_frame: Optional[tk.Widget] = None) -> ProofsViewer:
    """Get global proofs viewer instance"""
    global _proofs_viewer
    
    if _proofs_viewer is None and parent_frame is not None:
        _proofs_viewer = ProofsViewer(parent_frame)
    
    return _proofs_viewer


def cleanup_proofs_viewer() -> None:
    """Cleanup global proofs viewer"""
    global _proofs_viewer
    
    if _proofs_viewer:
        _proofs_viewer.cleanup()
        _proofs_viewer = None

# Path: gui/user/session_manager.py
"""
Session connection and management for Lucid RDP GUI.
Provides session lifecycle management, connection handling, and session monitoring.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import time
import uuid

from ..core import TorHttpClient, SecurityConfig, get_http_client
from ..core.config_manager import get_config_manager, ConfigScope
from ..core.widgets import StatusLabel, ProgressBar, LogViewer, create_tooltip

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class SessionRole(Enum):
    """Session role enumeration"""
    CLIENT = "client"
    HOST = "host"
    VIEWER = "viewer"
    PARTICIPANT = "participant"


@dataclass
class SessionConfig:
    """Session configuration parameters"""
    session_id: str = ""
    target_onion: str = ""
    target_port: int = 8080
    role: SessionRole = SessionRole.CLIENT
    authentication_token: str = ""
    encryption_enabled: bool = True
    compression_enabled: bool = True
    quality_level: int = 80  # 1-100
    frame_rate: int = 30
    resolution: str = "1920x1080"
    audio_enabled: bool = True
    clipboard_enabled: bool = True
    file_transfer_enabled: bool = True
    connection_timeout: int = 30
    heartbeat_interval: int = 5
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())


@dataclass
class SessionInfo:
    """Session information container"""
    session_id: str
    status: SessionStatus
    role: SessionRole
    target_onion: str
    connected_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    frame_count: int = 0
    error_count: int = 0
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        if self.connected_at:
            data['connected_at'] = self.connected_at.isoformat()
        if self.last_heartbeat:
            data['last_heartbeat'] = self.last_heartbeat.isoformat()
        data['status'] = self.status.value
        data['role'] = self.role.value
        return data


class SessionConnection:
    """Manages individual session connection"""
    
    def __init__(self, config: SessionConfig, http_client: TorHttpClient):
        self.config = config
        self.http_client = http_client
        self.info = SessionInfo(
            session_id=config.session_id,
            status=SessionStatus.DISCONNECTED,
            role=config.role,
            target_onion=config.target_onion
        )
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._callbacks: List[Callable[[SessionInfo], None]] = []
    
    def add_callback(self, callback: Callable[[SessionInfo], None]) -> None:
        """Add status change callback"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self) -> None:
        """Notify all callbacks of status change"""
        for callback in self._callbacks:
            try:
                callback(self.info)
            except Exception as e:
                logger.error(f"Session callback error: {e}")
    
    async def connect(self) -> bool:
        """Establish session connection"""
        try:
            self.info.status = SessionStatus.CONNECTING
            self._notify_callbacks()
            
            # Validate target onion address
            if not self.config.target_onion.endswith('.onion'):
                raise ValueError("Target must be a .onion address")
            
            # Attempt connection to session endpoint
            session_url = f"https://{self.config.target_onion}:{self.config.target_port}/api/session/connect"
            
            connection_data = {
                "session_id": self.config.session_id,
                "role": self.config.role.value,
                "authentication_token": self.config.authentication_token,
                "client_capabilities": {
                    "encryption": self.config.encryption_enabled,
                    "compression": self.config.compression_enabled,
                    "audio": self.config.audio_enabled,
                    "clipboard": self.config.clipboard_enabled,
                    "file_transfer": self.config.file_transfer_enabled
                },
                "display_settings": {
                    "quality": self.config.quality_level,
                    "frame_rate": self.config.frame_rate,
                    "resolution": self.config.resolution
                }
            }
            
            response = self.http_client.post(session_url, json=connection_data)
            
            if response.status_code == 200:
                response_data = response.json()
                
                self.info.status = SessionStatus.CONNECTED
                self.info.connected_at = datetime.now(timezone.utc)
                
                # Start heartbeat monitoring
                self._start_heartbeat()
                
                logger.info(f"Session {self.config.session_id} connected successfully")
                self._notify_callbacks()
                return True
            else:
                raise Exception(f"Connection failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Session connection failed: {e}")
            self.info.status = SessionStatus.ERROR
            self.info.error_count += 1
            self._notify_callbacks()
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect session"""
        try:
            self.info.status = SessionStatus.DISCONNECTING
            self._notify_callbacks()
            
            # Stop heartbeat
            self._shutdown_event.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=5)
            
            # Send disconnect request
            if self.info.status in [SessionStatus.CONNECTED, SessionStatus.AUTHENTICATED, SessionStatus.ACTIVE]:
                session_url = f"https://{self.config.target_onion}:{self.config.target_port}/api/session/disconnect"
                disconnect_data = {"session_id": self.config.session_id}
                
                try:
                    self.http_client.post(session_url, json=disconnect_data)
                except Exception as e:
                    logger.warning(f"Disconnect request failed: {e}")
            
            self.info.status = SessionStatus.DISCONNECTED
            logger.info(f"Session {self.config.session_id} disconnected")
            self._notify_callbacks()
            return True
            
        except Exception as e:
            logger.error(f"Session disconnect failed: {e}")
            self.info.status = SessionStatus.ERROR
            self._notify_callbacks()
            return False
    
    def _start_heartbeat(self) -> None:
        """Start heartbeat monitoring thread"""
        self._shutdown_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self._heartbeat_thread.start()
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                start_time = time.time()
                
                # Send heartbeat
                heartbeat_url = f"https://{self.config.target_onion}:{self.config.target_port}/api/session/heartbeat"
                heartbeat_data = {
                    "session_id": self.config.session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                response = self.http_client.post(heartbeat_url, json=heartbeat_data)
                
                if response.status_code == 200:
                    response_data = response.json()
                    self.info.last_heartbeat = datetime.now(timezone.utc)
                    self.info.latency_ms = (time.time() - start_time) * 1000
                    
                    # Update session info from response
                    if 'session_info' in response_data:
                        session_info = response_data['session_info']
                        self.info.bytes_sent = session_info.get('bytes_sent', self.info.bytes_sent)
                        self.info.bytes_received = session_info.get('bytes_received', self.info.bytes_received)
                        self.info.frame_count = session_info.get('frame_count', self.info.frame_count)
                    
                    self._notify_callbacks()
                else:
                    logger.warning(f"Heartbeat failed: {response.status_code}")
                    self.info.error_count += 1
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.info.error_count += 1
            
            # Wait for next heartbeat
            self._shutdown_event.wait(self.config.heartbeat_interval)


class SessionManager:
    """Main session manager for GUI applications"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.config_manager = get_config_manager()
        self.http_client = get_http_client()
        
        # Active sessions
        self.active_sessions: Dict[str, SessionConnection] = {}
        self.session_callbacks: List[Callable[[SessionInfo], None]] = []
        
        # GUI components
        self.session_frame: Optional[tk.Frame] = None
        self.sessions_tree: Optional[ttk.Treeview] = None
        self.status_label: Optional[StatusLabel] = None
        self.progress_bar: Optional[ProgressBar] = None
        self.log_viewer: Optional[LogViewer] = None
        
        self._setup_gui()
    
    def _setup_gui(self) -> None:
        """Setup session manager GUI components"""
        self.session_frame = tk.Frame(self.parent)
        
        # Session controls
        controls_frame = tk.Frame(self.session_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(controls_frame, text="New Session", command=self._new_session_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(controls_frame, text="Connect", command=self._connect_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(controls_frame, text="Disconnect", command=self._disconnect_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(controls_frame, text="Remove", command=self._remove_selected).pack(side=tk.LEFT, padx=5)
        
        # Sessions list
        sessions_frame = tk.Frame(self.session_frame)
        sessions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.sessions_tree = ttk.Treeview(
            sessions_frame,
            columns=('status', 'role', 'target', 'uptime', 'latency'),
            show='tree headings'
        )
        
        self.sessions_tree.heading('#0', text='Session ID')
        self.sessions_tree.heading('status', text='Status')
        self.sessions_tree.heading('role', text='Role')
        self.sessions_tree.heading('target', text='Target')
        self.sessions_tree.heading('uptime', text='Uptime')
        self.sessions_tree.heading('latency', text='Latency')
        
        self.sessions_tree.column('#0', width=200)
        self.sessions_tree.column('status', width=100)
        self.sessions_tree.column('role', width=80)
        self.sessions_tree.column('target', width=250)
        self.sessions_tree.column('uptime', width=100)
        self.sessions_tree.column('latency', width=80)
        
        sessions_scroll = ttk.Scrollbar(sessions_frame, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=sessions_scroll.set)
        
        self.sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sessions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status and progress
        status_frame = tk.Frame(self.session_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = StatusLabel(status_frame, "Ready", "info")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ProgressBar(status_frame, width=200, height=20)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
        # Log viewer
        self.log_viewer = LogViewer(self.session_frame, max_lines=500)
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind events
        self.sessions_tree.bind('<<TreeviewSelect>>', self._on_session_select)
        self.sessions_tree.bind('<Double-1>', self._on_session_double_click)
    
    def _new_session_dialog(self) -> None:
        """Show new session dialog"""
        from .connection_dialog import ConnectionDialog
        
        dialog = ConnectionDialog(self.parent, self._on_session_created)
        dialog.show()
    
    def _on_session_created(self, config: SessionConfig) -> None:
        """Handle new session creation"""
        session_id = config.session_id
        
        if session_id in self.active_sessions:
            messagebox.showerror("Error", "Session already exists")
            return
        
        # Create session connection
        session = SessionConnection(config, self.http_client)
        session.add_callback(self._on_session_status_changed)
        
        self.active_sessions[session_id] = session
        
        # Add to tree view
        self._update_sessions_display()
        
        self.log_viewer.add_log(f"Created session: {session_id}", "INFO")
        self.status_label.set_status("info", f"Session {session_id[:8]}... created")
    
    def _connect_selected(self) -> None:
        """Connect selected session"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session")
            return
        
        session_id = self.sessions_tree.item(selection[0])['text']
        session = self.active_sessions.get(session_id)
        
        if not session:
            messagebox.showerror("Error", "Session not found")
            return
        
        if session.info.status != SessionStatus.DISCONNECTED:
            messagebox.showwarning("Warning", "Session is already connected or connecting")
            return
        
        # Start connection in background
        self.progress_bar.set_progress(0.1)
        self.status_label.set_status("warning", "Connecting...")
        
        def connect_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(session.connect())
                if result:
                    self.status_label.set_status("success", "Connected")
                    self.progress_bar.set_progress(1.0)
                else:
                    self.status_label.set_status("error", "Connection failed")
                    self.progress_bar.set_progress(0.0)
            finally:
                loop.close()
        
        threading.Thread(target=connect_async, daemon=True).start()
    
    def _disconnect_selected(self) -> None:
        """Disconnect selected session"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session")
            return
        
        session_id = self.sessions_tree.item(selection[0])['text']
        session = self.active_sessions.get(session_id)
        
        if not session:
            messagebox.showerror("Error", "Session not found")
            return
        
        if session.info.status == SessionStatus.DISCONNECTED:
            messagebox.showwarning("Warning", "Session is already disconnected")
            return
        
        # Start disconnection in background
        self.status_label.set_status("warning", "Disconnecting...")
        
        def disconnect_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(session.disconnect())
                if result:
                    self.status_label.set_status("info", "Disconnected")
                else:
                    self.status_label.set_status("error", "Disconnect failed")
            finally:
                loop.close()
        
        threading.Thread(target=disconnect_async, daemon=True).start()
    
    def _remove_selected(self) -> None:
        """Remove selected session"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session")
            return
        
        session_id = self.sessions_tree.item(selection[0])['text']
        session = self.active_sessions.get(session_id)
        
        if not session:
            messagebox.showerror("Error", "Session not found")
            return
        
        if session.info.status not in [SessionStatus.DISCONNECTED, SessionStatus.ERROR]:
            if not messagebox.askyesno("Confirm", "Disconnect and remove session?"):
                return
            
            # Disconnect first
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(session.disconnect())
            finally:
                loop.close()
        
        # Remove session
        del self.active_sessions[session_id]
        self._update_sessions_display()
        
        self.log_viewer.add_log(f"Removed session: {session_id}", "INFO")
        self.status_label.set_status("info", "Session removed")
    
    def _on_session_select(self, event=None) -> None:
        """Handle session selection"""
        selection = self.sessions_tree.selection()
        if selection:
            session_id = self.sessions_tree.item(selection[0])['text']
            session = self.active_sessions.get(session_id)
            if session:
                self._update_session_details(session)
    
    def _on_session_double_click(self, event=None) -> None:
        """Handle session double-click"""
        self._connect_selected()
    
    def _on_session_status_changed(self, session_info: SessionInfo) -> None:
        """Handle session status changes"""
        self._update_sessions_display()
        
        # Notify external callbacks
        for callback in self.session_callbacks:
            try:
                callback(session_info)
            except Exception as e:
                logger.error(f"Session callback error: {e}")
        
        # Update log
        self.log_viewer.add_log(
            f"Session {session_info.session_id[:8]}... status: {session_info.status.value}",
            "INFO"
        )
    
    def _update_sessions_display(self) -> None:
        """Update sessions tree view"""
        # Clear existing items
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        
        # Add active sessions
        for session in self.active_sessions.values():
            info = session.info
            
            # Calculate uptime
            uptime_str = "N/A"
            if info.connected_at:
                uptime = datetime.now(timezone.utc) - info.connected_at
                uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            # Format latency
            latency_str = f"{info.latency_ms:.1f}ms" if info.latency_ms > 0 else "N/A"
            
            self.sessions_tree.insert('', 'end',
                text=info.session_id,
                values=(
                    info.status.value.title(),
                    info.role.value.title(),
                    info.target_onion,
                    uptime_str,
                    latency_str
                )
            )
    
    def _update_session_details(self, session: SessionConnection) -> None:
        """Update session details display"""
        info = session.info
        
        details_text = f"""
Session ID: {info.session_id}
Status: {info.status.value}
Role: {info.role.value}
Target: {info.target_onion}
Connected: {info.connected_at.isoformat() if info.connected_at else 'N/A'}
Last Heartbeat: {info.last_heartbeat.isoformat() if info.last_heartbeat else 'N/A'}
Bytes Sent: {info.bytes_sent:,}
Bytes Received: {info.bytes_received:,}
Frames: {info.frame_count:,}
Errors: {info.error_count}
Latency: {info.latency_ms:.1f}ms
"""
        
        # Update status label with details
        self.status_label.set_status("info", f"Session: {info.session_id[:8]}... - {info.status.value}")
    
    def add_session_callback(self, callback: Callable[[SessionInfo], None]) -> None:
        """Add session status change callback"""
        self.session_callbacks.append(callback)
    
    def get_session(self, session_id: str) -> Optional[SessionConnection]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self) -> List[SessionConnection]:
        """Get all active sessions"""
        return list(self.active_sessions.values())
    
    def save_sessions_config(self) -> None:
        """Save sessions configuration"""
        try:
            sessions_data = {}
            for session_id, session in self.active_sessions.items():
                sessions_data[session_id] = {
                    'config': asdict(session.config),
                    'info': session.info.to_dict()
                }
            
            self.config_manager.save_config(
                "sessions",
                sessions_data,
                ConfigScope.USER
            )
            
            logger.info("Sessions configuration saved")
            
        except Exception as e:
            logger.error(f"Failed to save sessions config: {e}")
    
    def load_sessions_config(self) -> None:
        """Load sessions configuration"""
        try:
            sessions_data = self.config_manager.load_config(
                "sessions",
                ConfigScope.USER,
                {}
            )
            
            for session_id, data in sessions_data.items():
                config_data = data.get('config', {})
                config = SessionConfig(**config_data)
                
                session = SessionConnection(config, self.http_client)
                session.add_callback(self._on_session_status_changed)
                
                self.active_sessions[session_id] = session
            
            self._update_sessions_display()
            logger.info(f"Loaded {len(sessions_data)} sessions")
            
        except Exception as e:
            logger.error(f"Failed to load sessions config: {e}")
    
    def cleanup(self) -> None:
        """Cleanup session manager"""
        # Disconnect all sessions
        for session in self.active_sessions.values():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(session.disconnect())
                loop.close()
            except Exception as e:
                logger.error(f"Error disconnecting session {session.config.session_id}: {e}")
        
        self.active_sessions.clear()
        logger.info("Session manager cleaned up")

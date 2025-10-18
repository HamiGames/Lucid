# Path: RDP/recorder/__init__.py
# Lucid RDP Recorder Module - Session recording and monitoring
# Implements R-MUST-003: Remote Desktop Host Support with recording capabilities
# LUCID-STRICT Layer 2 Service Integration

"""
RDP Recorder Module

This module provides session recording and monitoring functionality including:
- Session recording management
- Clipboard handling and transfer
- File transfer management
- Wayland integration
- RDP host service management
"""

from .clipboard_handler import ClipboardHandler, ClipboardConfig, ClipboardDirection
from .file_transfer_handler import FileTransferHandler, FileTransferConfig, FileTransferDirection
from .rdp_host import RDPHostService, RDPHostConfig
from .wayland_integration import WaylandIntegration, WaylandSessionConfig

__all__ = [
    "ClipboardHandler",
    "ClipboardConfig",
    "ClipboardDirection",
    "FileTransferHandler", 
    "FileTransferConfig",
    "FileTransferDirection",
    "RDPHostService",
    "RDPHostConfig",
    "WaylandIntegration",
    "WaylandSessionConfig"
]

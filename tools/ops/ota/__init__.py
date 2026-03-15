"""
Over-The-Air (OTA) update management module for Lucid RDP.

This module provides comprehensive OTA update capabilities including:
- Version tracking and management
- Update deployment and rollback
- System health monitoring during updates
- Security validation of updates

Components:
- VersionManager: Version tracking and update management
path: ..tools.ops.ota
file: tools/ops/ota/__init__.py
the ota calls the ota
"""

from .version_manager import VersionManager, get_version_manager, create_version_manager

__all__ = [
    "VersionManager",
    "get_version_manager",
    "create_version_manager"
]

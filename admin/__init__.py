# Admin Module
# All modules related to operations used by administrators

# Only import existing modules
from .system import *

# Path: admin/__init__.py
"""
Admin package for Lucid RDP.
Handles administrative operations, provisioning, and key management.
"""

# Import only what exists
try:
    from .system import *
except ImportError:
    pass

__all__ = []

# Path: sessions/__init__.py
"""
Session system package for Lucid RDP.
Handles session recording, encryption, manifest anchoring, and chunk management.
"""

# Package marker - individual modules import what they need directly
# This avoids import errors when modules are in subdirectories (recorder/, processor/, etc.)
__all__ = []
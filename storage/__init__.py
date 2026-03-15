# Path: storage/__init__.py  
"""
Storage package for Lucid RDP.
Manages MongoDB volumes, sharding, and data persistence.
path: .storage
file: storage/__init__.py
the storage calls the storage
"""

from .mongodb_volume import MongoVolumeManager

__all__ = ["MongoVolumeManager"]

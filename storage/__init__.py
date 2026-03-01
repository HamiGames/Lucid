# Path: storage/__init__.py  
"""
Storage package for Lucid RDP.
Manages MongoDB volumes, sharding, and data persistence.
"""

from storage.mongodb_volume import MongoVolumeManager

__all__ = ["MongoVolumeManager"]

# Path: storage/__init__.py
"""
Lucid storage package: storage plane (capacity / layout) plus optional database helpers.
MongoVolumeManager is loaded lazily so `import storage.plane` does not require motor/pymongo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["MongoVolumeManager"]

if TYPE_CHECKING:
    from .mongodb_volume import MongoVolumeManager as MongoVolumeManagerType


def __getattr__(name: str) -> Any:
    if name == "MongoVolumeManager":
        from .mongodb_volume import MongoVolumeManager

        return MongoVolumeManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

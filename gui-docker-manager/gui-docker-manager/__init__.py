"""
GUI Docker Manager Service Package
File: gui-docker-manager/gui-docker-manager/__init__.py
"""

__version__ = "1.0.0"
__author__ = "Lucid Project"
__description__ = "Docker container management service for Electron GUI"

from .config import get_config, DockerManagerSettings, DockerManagerConfigManager

__all__ = [
    "get_config",
    "DockerManagerSettings",
    "DockerManagerConfigManager",
]

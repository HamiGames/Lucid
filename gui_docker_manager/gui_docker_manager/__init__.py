"""
File: /app/gui_docker_manager/gui_docker_manager/__init__.py
x-lucid-file-path: /app/gui_docker_manager/gui_docker_manager/__init__.py
x-lucid-file-type: python

GUI Docker Manager Service Package
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

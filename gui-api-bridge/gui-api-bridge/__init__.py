"""
GUI API Bridge Service Package
File: gui-api-bridge/gui-api-bridge/__init__.py
"""

__version__ = "1.0.0"
__author__ = "Lucid Project"
__description__ = "API bridge service for Electron GUI integration"

from .config import get_config, GuiAPIBridgeSettings, GuiAPIBridgeConfigManager

__all__ = [
    "get_config",
    "GuiAPIBridgeSettings", 
    "GuiAPIBridgeConfigManager",
]

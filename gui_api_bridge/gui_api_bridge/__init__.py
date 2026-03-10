"""
GUI API Bridge Service Package
File: gui_api_bridge/gui_api_bridge/__init__.py
"""

__version__ = "1.0.0"
__author__ = "Lucid Project"
__description__ = "API bridge service for Electron GUI integration"

from gui_api_bridge.gui_api_bridge.config import get_config, GuiAPIBridgeSettings, GuiAPIBridgeConfigManager

__all__ = [
    "get_config",
    "GuiAPIBridgeSettings", 
    "GuiAPIBridgeConfigManager",
]

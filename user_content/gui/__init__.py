# GUI Module for user interface components
# Note: Main user GUI is implemented in gui/user/user_gui.py

# Import from the main GUI module
"""
File: /app/user_content/gui/__init__.py
x-lucid-file-path: /app/user_content/gui/__init__.py
x-lucid-file-type: python
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "gui" / "user"))

try:
    from user_gui import UserGUI
    __all__ = ["UserGUI"]
except ImportError:
    __all__ = []

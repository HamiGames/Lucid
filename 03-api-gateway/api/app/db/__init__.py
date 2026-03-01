# app/db/__init__.py
from .connection import (
    get_db,
    get_client,
    ping,
    close_client,
)  # re-export for stable imports

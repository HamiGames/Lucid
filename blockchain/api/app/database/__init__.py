"""
Blockchain API Database Package
Provides database connection and repository classes for blockchain data.
"""

from .connection import DatabaseConnection, get_database_connection
from .repositories.block_repository import BlockRepository
from .repositories.transaction_repository import TransactionRepository
from .repositories.anchoring_repository import AnchoringRepository

# Import database initialization functions from parent database.py module
import importlib.util
from pathlib import Path

# Load database.py from parent directory
parent_dir = Path(__file__).parent.parent
database_module_path = parent_dir / "database.py"
spec = importlib.util.spec_from_file_location("database_module", database_module_path)
database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)

# Export the functions
init_database = database_module.init_database
close_database = database_module.close_database

__all__ = [
    'DatabaseConnection',
    'get_database_connection',
    'BlockRepository',
    'TransactionRepository', 
    'AnchoringRepository',
    'init_database',
    'close_database'
]

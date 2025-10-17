"""
Database Repositories Package

Repository pattern implementation for data access layer.
Provides abstraction over database operations for Lucid entities.

Repositories:
- UserRepository: User data access
- SessionRepository: Session data access
- BlockRepository: Block data access

All repositories follow async/await patterns for MongoDB operations.
"""

from .user_repository import UserRepository
from .session_repository import SessionRepository
from .block_repository import BlockRepository

__all__ = [
    'UserRepository',
    'SessionRepository',
    'BlockRepository',
]

__version__ = '1.0.0'


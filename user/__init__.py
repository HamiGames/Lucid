# Path: user/__init__.py
"""
User package for Lucid RDP.
Manages user profiles, authentication, and activity logging.
"""

from user.user_manager import UserManager, UserProfile

__all__ = ["UserManager", "UserProfile"]

"""
Lucid API Module

A comprehensive FastAPI-based API gateway for the Lucid blockchain-integrated
remote desktop access application.

This module provides:
- User management and authentication
- Blockchain service integration
- Database operations and health monitoring
- Comprehensive logging and middleware
- Development utilities and scripts

Key Components:
- Routes: API endpoints for auth, users, blockchain, health, meta
- Schemas: Pydantic models for request/response validation
- Services: Business logic and external service integration
- Database: MongoDB connection and repository patterns
- Middleware: Authentication, logging, and request processing
- Utils: Configuration, logging, and helper functions
- Scripts: Database setup and development utilities

Usage:
    from src.api.main import app
    
    # Run with uvicorn
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""

from .main import app, create_app
from .config import Settings, get_settings

__version__ = "0.1.0"
__all__ = [
    "app",
    "create_app", 
    "Settings",
    "get_settings",
]

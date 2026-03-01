"""
Data Models Package

Contains all Pydantic models for request/response validation and serialization.

Model Categories:
- common: Shared models and base classes
- user: User-related models
- session: Session-related models
- auth: Authentication-related models

All models follow Pydantic V2 conventions and include:
- Type validation
- Field constraints
- JSON serialization
- Documentation strings
"""

__version__ = "1.0.0"
__all__ = [
    "common",
    "user",
    "session",
    "auth",
]


"""
CORS Middleware Configuration for GUI Tor Manager
Enables cross-origin requests for Electron GUI
"""

from fastapi.middleware.cors import CORSMiddleware
from ..config import get_config


def setup_cors_middleware(app, allowed_origins: list[str] = None):
    """
    Setup CORS middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins (from environment)
    """
    if allowed_origins is None:
        # Build allowed origins from environment configuration
        # These come from the docker-compose service definitions
        allowed_origins = [
            "http://user-interface:3001",      # User Interface (docker)
            "http://node-interface:3002",      # Node Interface (docker)
            "http://admin-interface:8120",     # Admin Interface (docker)
            "http://localhost:3001",           # Local development
            "http://localhost:3002",           # Local development
            "http://localhost:8120",           # Local development
            "http://127.0.0.1:3001",          # Local development
            "http://127.0.0.1:3002",          # Local development
            "http://127.0.0.1:8120",          # Local development
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
        max_age=86400,  # 24 hours
    )

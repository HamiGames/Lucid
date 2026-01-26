"""
CORS Middleware Configuration for GUI Tor Manager
Enables cross-origin requests for Electron GUI
"""

from fastapi.middleware.cors import CORSMiddleware


def setup_cors_middleware(app, allowed_origins: list[str] = None):
    """
    Setup CORS middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins (default: local GUI origins)
    """
    if allowed_origins is None:
        allowed_origins = [
            "http://localhost:3001",  # User Interface
            "http://localhost:3002",  # Node Interface
            "http://localhost:8120",  # Admin Interface
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:8120",
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

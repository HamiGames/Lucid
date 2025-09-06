"""
Lucid API - FastAPI main entrypoint
Path: 03-api-gateway/api/app/main.py
"""

from fastapi import FastAPI
from datetime import datetime

# Import routers
from app.routes import health

# --- FastAPI app instance ---
app = FastAPI(
    title="Lucid API",
    version="0.1.0",
    description="Core Lucid API service running under FastAPI",
)


# --- Include routers ---
app.include_router(health.router, prefix="/health", tags=["Health"])


# --- Root route ---
@app.get("/")
async def root():
    """
    Basic root endpoint to verify service is alive.
    """
    return {
        "status": "ok",
        "service": "lucid_api",
        "time": datetime.utcnow().isoformat() + "Z",
    }

"""Distroless entrypoint for Lucid overlord containers (uvicorn)."""
from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("OVERLORD_HOST", "0.0.0.0")
    port = int(os.environ.get("OVERLORD_PORT", "8130"))
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )

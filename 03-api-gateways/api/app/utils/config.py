# 03-api-gateway/api/app/utils/config.py
from __future__ import annotations

import os
import os.path


def in_container() -> bool:
    """
    Heuristic to detect containerized/devcontainer runtime.
    """
    return os.path.exists("/.dockerenv") or bool(
        os.getenv("CODESPACES") or os.getenv("IN_DEVCONTAINER")
    )


def mongo_conn_str() -> str:
    """
    Single source of truth for MongoDB connection string.
    Prefer MONGO_URI, but allow common fallbacks if the env varies.
    If nothing is set, choose a smart default that works both on host and devcontainer.
    """
    url = (
        os.getenv("MONGO_URI")
        or os.getenv("MONGO_URL")
        or os.getenv("MONGODB_URI")
        or os.getenv("DATABASE_URL")
    )
    if url:
        return url

    # Smart default by runtime location
    host = "host.docker.internal" if in_container() else "127.0.0.1"
    # Use explicit auth + direct connection to avoid SRV/discovery pitfalls.
    return (
        f"mongodb://lucid:lucid@{host}:27017/"
        f"lucid?authSource=admin&retryWrites=false&directConnection=true"
    )


def service_name() -> str:
    return os.getenv("SERVICE_NAME", "lucid-api")


def service_version() -> str:
    # Keep the project’s version fallback aligned with prior health output
    return os.getenv("LUCID_API_VERSION", "0.1.0")


def mongo_timeouts_ms() -> tuple[int, int]:
    """
    Return (serverSelectionTimeoutMS, connectTimeoutMS).
    Defaults mirror prior logs (20s).
    """
    sst = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "20000"))
    cto = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "20000"))
    return sst, cto

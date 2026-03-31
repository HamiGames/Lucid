"""
File: /app/database/admin/admin_connection.py
x-lucid-file-path: /app/database/admin/admin_connection.py
x-lucid-file-directory: /app/database/admin
x-lucid-file-type: python

MongoDB admin connection helpers for Lucid.

Builds URIs from the same environment variables used in
infrastructure/containers/admin/Dockerfile.* and
configs/docker/databases/Dockerfile.* (MONGODB_URL, LUCID_MONGODB_SERVICE,
LUCID_MONGODB_PORT). Default host/port align with host-config.yml lucid_mongodb.

For FastAPI + Tor bootstrap + Redis, prefer wiring through
03_api_gateway/api/app/database/connection.py in the gateway process; this module
focuses on synchronous pymongo admin access (list databases, admin commands).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from common.load_host_config import (
    default_host_config_path,
    endpoint_by_service_name,
    load_host_registry,
)

try:
    from pymongo import MongoClient
    from pymongo.database import Database
except ImportError:  # pragma: no cover
    MongoClient = None  # type: ignore[misc, assignment]
    Database = None  # type: ignore[misc, assignment]


def _expand_mongodb_password(uri: str) -> str:
    if "{MONGODB_PASSWORD}" not in uri:
        return uri
    pwd = os.environ.get("MONGODB_PASSWORD", "")
    if not pwd:
        raise RuntimeError(
            "MONGODB_PASSWORD must be set when the connection string contains {MONGODB_PASSWORD}"
        )
    return uri.replace("{MONGODB_PASSWORD}", pwd)


def resolve_mongodb_admin_uri(
    *,
    host_config_path: Optional[str] = None,
) -> str:
    """Resolve MongoDB URI: MONGODB_URL | MONGODB_URI | MONGO_URL, or compose from LUCID_MONGODB_* + credentials."""
    for key in ("MONGODB_URL", "MONGODB_URI", "MONGO_URL"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return _expand_mongodb_password(raw)

    user = os.environ.get("MONGODB_USER", os.environ.get("MONGO_INITDB_ROOT_USERNAME", "lucid")).strip()
    password = os.environ.get("MONGODB_PASSWORD", os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "")).strip()
    db = os.environ.get("MONGODB_DATABASE", os.environ.get("LUCID_MONGO_DB", "lucid")).strip() or "lucid"
    auth_source = os.environ.get("MONGODB_AUTH_SOURCE", "admin").strip() or "admin"

    host = os.environ.get("LUCID_MONGODB_SERVICE", "").strip()
    port_str = os.environ.get("LUCID_MONGODB_PORT", "").strip()

    if not host or not port_str.isdigit():
        _, reg = load_host_registry(host_config_path or default_host_config_path())
        ep = endpoint_by_service_name(reg, "lucid-mongodb")
        if ep:
            host = host or ep.service_name
            if not port_str.isdigit():
                port_str = str(ep.port)

    if not host:
        host = "lucid-mongodb"
    if not port_str.isdigit():
        port_str = "27017"
    port = int(port_str)

    if password:
        u = quote_plus(user)
        p = quote_plus(password)
        return f"mongodb://{u}:{p}@{host}:{port}/{db}?authSource={auth_source}"
    return f"mongodb://{host}:{port}/{db}"


@dataclass
class AdminMongoConnection:
    """Sync pymongo client for admin operations against lucid-mongodb."""

    uri: str
    default_db_name: str = "lucid"
    server_selection_timeout_ms: int = 10_000

    _client: Any = None

    def __post_init__(self) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for database.admin.AdminMongoConnection")

    @classmethod
    def from_environment(
        cls,
        *,
        default_db_name: Optional[str] = None,
        host_config_path: Optional[str] = None,
    ) -> "AdminMongoConnection":
        uri = resolve_mongodb_admin_uri(host_config_path=host_config_path)
        dbn = (
            default_db_name
            or os.environ.get("MONGODB_DATABASE", "").strip()
            or os.environ.get("LUCID_MONGO_DB", "").strip()
            or "lucid"
        )
        return cls(uri=uri, default_db_name=dbn)

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
            )
        return self._client

    def ping(self) -> Dict[str, Any]:
        return self.client.admin.command("ping")

    def list_database_names(self) -> List[str]:
        return sorted(self.client.list_database_names())

    def get_database(self, name: Optional[str] = None) -> Any:
        return self.client[name or self.default_db_name]

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "AdminMongoConnection":
        self.ping()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def mongodb_service_endpoint_url(
    scheme: str = "mongodb",
    host_config_path: Optional[str] = None,
) -> str:
    """Template-style service location (no credentials); matches host-config lucid_mongodb."""
    _, reg = load_host_registry(host_config_path or default_host_config_path())
    ep = endpoint_by_service_name(reg, "lucid-mongodb")
    if ep:
        return f"{scheme}://{ep.service_name}:{ep.port}"
    host = os.environ.get("LUCID_MONGODB_SERVICE", "lucid-mongodb").strip()
    port = int(os.environ.get("LUCID_MONGODB_PORT", "27017") or "27017")
    return f"{scheme}://{host}:{port}"

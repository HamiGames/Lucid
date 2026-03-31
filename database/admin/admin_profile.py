"""
File: /app/database/admin/admin_profile.py
x-lucid-file-path: /app/database/admin/admin_profile.py
x-lucid-file-directory: /app/database/admin
x-lucid-file-type: python

Admin profile model and host-config alignment for Lucid.

Uses admin_schema.json for JSON Schema shape. Validates with Pydantic; optional
jsonschema if installed. Resolves lucid-auth-service from
infrastructure/containers/host-config.yml via common.load_host_config (same as
Dockerfile.* LUCID_MONGODB_* / service mesh wiring).
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from common.load_host_config import (
    default_host_config_path,
    endpoint_by_service_name,
    load_host_registry,
)

_SCHEMA_PATH = Path(__file__).resolve().parent / "admin_schema.json"


class AdminRole(str, Enum):
    """Admin roles aligned with database.models.user.UserRole."""

    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AdminHostRegistryPins(BaseModel):
    """Defaults match host-config.yml registry keys lucid_mongodb, lucid_auth_service, database_overlord, admin_overlord."""

    model_config = ConfigDict(use_enum_values=True)

    mongodb_service: str = "lucid-mongodb"
    mongodb_port: int = 27017
    auth_service: str = "lucid-auth-service"
    auth_service_port: int = 8089
    database_overlord_service: str = "database-overlord"
    database_overlord_port: int = 8120
    admin_overlord_service: str = "admin-overlord"
    admin_overlord_port: int = 8140


class AdminProfileDocument(BaseModel):
    """Validated admin profile payload (MongoDB or service config)."""

    model_config = ConfigDict(use_enum_values=True)

    user_id: str = Field(..., min_length=1)
    email: Optional[EmailStr] = None
    role: AdminRole
    contact_profile_key: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    host_registry: AdminHostRegistryPins = Field(default_factory=AdminHostRegistryPins)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def strip_empty_email(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("email") in ("",):
            data = {**data, "email": None}
        return data


def load_admin_schema_dict() -> Dict[str, Any]:
    """Load admin_schema.json (JSON only; path: database/admin/admin_schema.json)."""
    if not _SCHEMA_PATH.is_file():
        return {}
    with _SCHEMA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def validate_document_against_json_schema(instance: Mapping[str, Any]) -> None:
    """Optional jsonschema validation when the package is installed."""
    schema = load_admin_schema_dict()
    if not schema:
        return
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return
    jsonschema.validate(instance=dict(instance), schema=schema)


def auth_service_base_url(
    scheme: str = "http",
    host_config_path: Optional[Path] = None,
) -> str:
    """Base URL for lucid-auth-service (host-config: port 8089)."""
    _, reg = load_host_registry(host_config_path or default_host_config_path())
    ep = endpoint_by_service_name(reg, "lucid-auth-service")
    if ep:
        return ep.base_url(scheme=scheme)
    env_host = os.environ.get("LUCID_AUTH_SERVICE", "").strip()
    env_port = os.environ.get("LUCID_AUTH_SERVICE_PORT", "").strip()
    if env_host and env_port.isdigit():
        return f"{scheme}://{env_host}:{int(env_port)}"
    return f"{scheme}://lucid-auth-service:8089"


def admin_overlord_base_url(
    scheme: str = "http",
    host_config_path: Optional[Path] = None,
) -> str:
    """Base URL for admin-overlord (host-config: port 8140)."""
    _, reg = load_host_registry(host_config_path or default_host_config_path())
    ep = endpoint_by_service_name(reg, "admin-overlord")
    if ep:
        return ep.base_url(scheme=scheme)
    return f"{scheme}://admin-overlord:8140"


def database_overlord_base_url(
    scheme: str = "http",
    host_config_path: Optional[Path] = None,
) -> str:
    """Base URL for database-overlord (host-config: port 8120)."""
    _, reg = load_host_registry(host_config_path or default_host_config_path())
    ep = endpoint_by_service_name(reg, "database-overlord")
    if ep:
        return ep.base_url(scheme=scheme)
    return f"{scheme}://database-overlord:8120"


def parse_admin_profile(
    data: Mapping[str, Any],
    *,
    use_jsonschema: bool = False,
) -> AdminProfileDocument:
    """Parse and validate admin profile dict."""
    if use_jsonschema:
        validate_document_against_json_schema(data)
    return AdminProfileDocument.model_validate(data)


def is_admin_role(role: str) -> bool:
    return role in (AdminRole.ADMIN.value, AdminRole.SUPER_ADMIN.value)

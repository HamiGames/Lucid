"""
File: /app/database/config/load_host_config.py
x-lucid-file-path: /app/database/config/load_host_config.py
x-lucid-file-type: python

Loads host config for Lucid database services.

Aligns with host-config keys: lucid_mongodb, lucid_redis, main_lucid_gateway, etc.
Service overlay: database.yml under LUCID_DATABASE_SERVICE_CONFIG_DIR.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from common.load_host_config import (
    ServiceEndpoint,
    default_host_config_path,
    endpoint_by_service_name,
    load_host_registry,
    load_yaml_file,
    merge_config_layers,
    resolve_service_config_path,
)

ENV_DB_SERVICE_DIR = "LUCID_DATABASE_SERVICE_CONFIG_DIR"
ENV_DB_SERVICE_FILE = "LUCID_DATABASE_SERVICE_YML"
DEFAULT_SERVICE_DIR = Path("/app/service-configs")
DEFAULT_DB_YML = "database.yml"


def resolve_database_service_config_dir() -> Path:
    env = os.environ.get(ENV_DB_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    alt = Path("/app/service_configs")
    if DEFAULT_SERVICE_DIR.is_dir():
        return DEFAULT_SERVICE_DIR
    if alt.is_dir():
        return alt
    return Path(__file__).resolve().parent


def resolve_database_yml_path() -> Optional[Path]:
    name = os.environ.get(ENV_DB_SERVICE_FILE, "").strip() or DEFAULT_DB_YML
    return resolve_service_config_path(resolve_database_service_config_dir(), name)


def load_database_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    sp = resolve_database_yml_path()
    overlay = load_yaml_file(sp) if sp else {}
    return raw, registry, overlay


def load_database_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, db_overlay = load_database_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "database_service": db_overlay},
    )


def mongodb_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "lucid-mongodb")


def redis_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "lucid-redis")


def database_overlord_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "database-overlord")

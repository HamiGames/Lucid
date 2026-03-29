"""
File: /app/auth/config/load_host_config.py
x-lucid-file-path: /app/auth/config/load_host_config.py
x-lucid-file-type: python

Load host config for Lucid Authentication Service.

Host registry: /app/configs/host-config.yml. Service overlay: auth-service.yml
under LUCID_AUTH_SERVICE_CONFIG_DIR (/app/service_configs by default).
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

ENV_AUTH_SERVICE_DIR = "LUCID_AUTH_SERVICE_CONFIG_DIR"
ENV_AUTH_SERVICE_FILE = "LUCID_AUTH_SERVICE_YML"
DEFAULT_SERVICE_DIR = Path("/app/service_configs")
DEFAULT_AUTH_YML = "auth-service.yml"


def resolve_auth_service_config_dir() -> Path:
    env = os.environ.get(ENV_AUTH_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    alt = Path("/app/service-configs")
    if DEFAULT_SERVICE_DIR.is_dir():
        return DEFAULT_SERVICE_DIR
    if alt.is_dir():
        return alt
    return Path(__file__).resolve().parent


def resolve_auth_service_yml_path() -> Optional[Path]:
    name = os.environ.get(ENV_AUTH_SERVICE_FILE, "").strip() or DEFAULT_AUTH_YML
    return resolve_service_config_path(resolve_auth_service_config_dir(), name)


def load_auth_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    sp = resolve_auth_service_yml_path()
    overlay = load_yaml_file(sp) if sp else {}
    return raw, registry, overlay


def load_auth_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, auth_overlay = load_auth_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "auth_service": auth_overlay},
    )


def lucid_auth_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "lucid-auth-service")

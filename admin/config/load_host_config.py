"""Load host config for Lucid Admin services.

Host registry: ``/app/configs/host-config.yml`` (``LUCID_HOST_CONFIG_PATH``).
Service overlay YAMLs live under ``/app/configs/services/*`` by default
(``LUCID_ADMIN_SERVICE_CONFIG_DIR``); default file is ``admin-interface.yml``
(``LUCID_ADMIN_SERVICE_YML``). See infrastructure/containers/services/container-runtime-layout.yml.

File: admin/config/load_host_config.py
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

ENV_ADMIN_SERVICE_DIR = "LUCID_ADMIN_SERVICE_CONFIG_DIR"
ENV_ADMIN_SERVICE_FILE = "LUCID_ADMIN_SERVICE_YML"
DEFAULT_SERVICE_DIR = Path("/app/configs/services")
DEFAULT_ADMIN_YML = "admin-interface.yml"
_LEGACY_ADMIN_YML = "admin-service.yml"


def resolve_admin_service_config_dir() -> Path:
    env = os.environ.get(ENV_ADMIN_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (
        DEFAULT_SERVICE_DIR,
        Path("/app/service-configs"),
        Path("/app/service_configs"),
    ):
        if cand.is_dir():
            return cand
    return Path(__file__).resolve().parent


def resolve_admin_service_yml_path() -> Optional[Path]:
    d = resolve_admin_service_config_dir()
    name = os.environ.get(ENV_ADMIN_SERVICE_FILE, "").strip() or DEFAULT_ADMIN_YML
    primary = resolve_service_config_path(d, name)
    if primary:
        return primary
    if name == DEFAULT_ADMIN_YML:
        return resolve_service_config_path(d, _LEGACY_ADMIN_YML)
    return None


def load_admin_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    sp = resolve_admin_service_yml_path()
    overlay = load_yaml_file(sp) if sp else {}
    return raw, registry, overlay


def load_admin_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, admin_overlay = load_admin_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "admin_service": admin_overlay},
    )


def admin_ui_backend_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "admin-ui-backend")


def admin_system_gateway_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "admin-system-gateway")

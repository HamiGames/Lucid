"""
File: /app/gui_tor_manager/gui_tor_manager/config/load_host_config.py
x-lucid-file-path: /app/gui_tor_manager/gui_tor_manager/config/load_host_config.py
x-lucid-file-directory: /app/gui_tor_manager/gui_tor_manager/config
x-lucid-file-type: python
"""
#create a modified version of load_host_config.py from any directory that matches the x-lucid-file-path, name, and directory
#the modified version should be in the same directory as the original load_host_config.py
#the modified version should be named load_host_config_modified.py
#the modified version should be a copy of the original load_host_config.py
#the modified version should be a copy of the original load_host_config.py
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

ENV_TOR_MANAGER_SERVICE_DIR = "LUCID_TOR_MANAGER_SERVICE_CONFIG_DIR"
ENV_TOR_MANAGER_ENDPOINTS_FILE = "LUCID_TOR_MANAGER_ENDPOINTS_FILE"
DEFAULT_SERVICE_DIR = Path("/app/service_configs")
DEFAULT_ENDPOINTS_FILE = "tor-manager-endpoints.yml"


def _tor_manager_package_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_tor_manager_service_config_dir() -> Path:
    env = os.environ.get(ENV_TOR_MANAGER_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (
        DEFAULT_SERVICE_DIR,
        Path("/app/service-configs"),
        Path("/app/configs"),
    ):
        if cand.is_dir():
            return cand
    return _tor_manager_package_dir()


def resolve_tor_manager_endpoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_TOR_MANAGER_ENDPOINTS_FILE, "").strip() or DEFAULT_ENDPOINTS_FILE
    return resolve_service_config_path(
        resolve_tor_manager_service_config_dir(),
        name,
        fallbacks=(_tor_manager_package_dir() / name,),
    )


def load_tor_manager_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    """Host registry + merged tor-manager-endpoints (if present)."""
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    endpoints_path = resolve_tor_manager_endpoints_path()
    endpoints = load_yaml_file(endpoints_path) if endpoints_path else {}
    return raw, registry, endpoints


def load_tor_manager_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Single dict: host metadata + services snapshot + tor manager endpoints (flexible consumers)."""
    raw, registry, tor_manager = load_tor_manager_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "tor_manager_endpoints": tor_manager},
    )


def tor_manager_gateway_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    """Prefer tor-manager service_name from host-config (tor_manager)."""
    return endpoint_by_service_name(registry, "tor-manager")
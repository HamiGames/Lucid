"""
File: /app/service_mesh/config/load_host_config.py
x-lucid-file-path: /app/service_mesh/config/load_host_config.py
x-lucid-file-directory: /app/service_mesh/config
x-lucid-file-type: python
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

ENV_SERVICE_MESH_SERVICE_DIR = "LUCID_SERVICE_MESH_SERVICE_CONFIG_DIR"
ENV_SERVICE_MESH_ENDPOINTS_FILE = "LUCID_SERVICE_MESH_ENDPOINTS_FILE"
DEFAULT_SERVICE_DIR = Path("/app/service_configs")
DEFAULT_ENDPOINTS_FILE = "service-mesh-endpoints.yml"


def _service_mesh_package_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_service_mesh_service_config_dir() -> Path:
    env = os.environ.get(ENV_SERVICE_MESH_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (
        DEFAULT_SERVICE_DIR,
        Path("/app/service-configs"),
        Path("/app/configs"),
    ):
        if cand.is_dir():
            return cand
    return _service_mesh_package_dir()


def resolve_service_mesh_endpoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_SERVICE_MESH_ENDPOINTS_FILE, "").strip() or DEFAULT_ENDPOINTS_FILE
    return resolve_service_config_path(
        resolve_service_mesh_service_config_dir(),
        name,
        fallbacks=(_service_mesh_package_dir() / name,),
    )


def load_service_mesh_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    """Host registry + merged service-mesh-endpoints (if present)."""
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    endpoints_path = resolve_service_mesh_endpoints_path()
    endpoints = load_yaml_file(endpoints_path) if endpoints_path else {}
    return raw, registry, endpoints


def load_service_mesh_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Single dict: host metadata + services snapshot + service mesh endpoints (flexible consumers)."""
    raw, registry, service_mesh = load_service_mesh_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "service_mesh_endpoints": service_mesh},
    )


def service_mesh_gateway_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    """Prefer service mesh service_name from host-config (service_mesh)."""
    return endpoint_by_service_name(registry, "service_mesh")
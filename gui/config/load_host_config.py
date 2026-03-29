"""Loads host config for Lucid GUI services.

file: /app/gui/config/load_host_config.py
x-lucid-file-path: /app/gui/config/load_host_config.py
x-lucid-file-type: python

Uses /app/configs/host-config.yml (or LUCID_HOST_CONFIG_PATH) plus optional
GUI endpoint YAML (gui-endpoints.yml under LUCID_GUI_SERVICE_CONFIG_DIR —
default ``/app/configs/services`` — or beside this package).
File: gui/config/load_host_config.py
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

ENV_GUI_SERVICE_DIR = "LUCID_GUI_SERVICE_CONFIG_DIR"
ENV_GUI_ENDPOINTS_FILE = "LUCID_GUI_ENDPOINTS_FILE"
DEFAULT_SERVICE_DIR = Path("/app/configs/services")
DEFAULT_ENDPOINTS_FILE = "gui-endpoints.yml"


def _gui_package_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_gui_service_config_dir() -> Path:
    env = os.environ.get(ENV_GUI_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (
        DEFAULT_SERVICE_DIR,
        Path("/app/service-configs"),
        Path("/app/service_configs"),
    ):
        if cand.is_dir():
            return cand
    return _gui_package_dir()


def resolve_gui_endpoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_GUI_ENDPOINTS_FILE, "").strip() or DEFAULT_ENDPOINTS_FILE
    return resolve_service_config_path(
        resolve_gui_service_config_dir(),
        name,
        fallbacks=(_gui_package_dir() / name,),
    )


def load_gui_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    """Host registry + merged gui-endpoints (if present)."""
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    endpoints_path = resolve_gui_endpoints_path()
    endpoints = load_yaml_file(endpoints_path) if endpoints_path else {}
    return raw, registry, endpoints


def load_gui_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Single dict: host metadata + services snapshot + gui endpoints (flexible consumers)."""
    raw, registry, gui = load_gui_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "gui_endpoints": gui},
    )


def gui_gateway_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    """Prefer api-gateway service_name from host-config (main_lucid_gateway)."""
    return endpoint_by_service_name(registry, "api-gateway")

"""Loads host config for Lucid Electron GUI.

Host registry: /app/configs/host-config.yml. Optional electron-gui.yml and
local configs/electron-endpoints.yml (repo layout).
File: electron_gui/utils/load_host_config.py
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

ENV_ELECTRON_SERVICE_DIR = "LUCID_ELECTRON_SERVICE_CONFIG_DIR"
ENV_ELECTRON_YML = "LUCID_ELECTRON_SERVICE_YML"
ENV_ELECTRON_ENDPOINTS = "LUCID_ELECTRON_ENDPOINTS_FILE"
DEFAULT_SERVICE_DIR = Path("/app/service-configs")
DEFAULT_SERVICE_YML = "electron-gui.yml"
DEFAULT_ENDPOINTS_FILE = "electron-endpoints.yml"


def _electron_repo_configs() -> Path:
    return Path(__file__).resolve().parents[1] / "configs"


def resolve_electron_service_config_dir() -> Path:
    env = os.environ.get(ENV_ELECTRON_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    if DEFAULT_SERVICE_DIR.is_dir():
        return DEFAULT_SERVICE_DIR
    return _electron_repo_configs()


def resolve_electron_service_yml_path() -> Optional[Path]:
    name = os.environ.get(ENV_ELECTRON_YML, "").strip() or DEFAULT_SERVICE_YML
    return resolve_service_config_path(
        resolve_electron_service_config_dir(),
        name,
        fallbacks=(_electron_repo_configs() / name,),
    )


def resolve_electron_endpoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_ELECTRON_ENDPOINTS, "").strip() or DEFAULT_ENDPOINTS_FILE
    return resolve_service_config_path(
        resolve_electron_service_config_dir(),
        name,
        fallbacks=(_electron_repo_configs() / name,),
    )


def load_electron_gui_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    sy = resolve_electron_service_yml_path()
    ep = resolve_electron_endpoints_path()
    service_layer = load_yaml_file(sy) if sy else {}
    endpoints_layer = load_yaml_file(ep) if ep else {}
    return raw, registry, service_layer, endpoints_layer


def load_electron_gui_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, svc, endpoints = load_electron_gui_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "electron_service": svc, "electron_endpoints": endpoints},
    )


def electron_gui_user_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "electron-gui-user")


def electron_gui_node_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "electron-gui-node")

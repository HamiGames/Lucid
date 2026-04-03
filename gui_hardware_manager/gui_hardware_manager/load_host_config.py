"""
File: /app/gui_hardware_manager/gui_hardware_manager/load_host_config.py
x-lucid-file-path: /app/gui_hardware_manager/gui_hardware_manager/load_host_config.py
x-lucid-file-directory: /app/gui_hardware_manager/gui_hardware_manager
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

ENV_HARDWARE_MANAGER_SERVICE_DIR = "LUCID_GUI_HARDWARE_MANAGER_SERVICE_CONFIG_DIR"
ENV_HARDWARE_MANAGER_ENTRYPOINTS_FILE = "LUCID_GUI_HARDWARE_MANAGER_ENTRYPOINTS_FILE"
DEFAULT_SERVICE_DIR = Path("/app/service_configs")
DEFAULT_ENTRYPOINTS_FILE = "gui-hardware-manager-entrypoints.yml"


def _hardware_manager_package_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_hardware_manager_service_config_dir() -> Path:
    env = os.environ.get(ENV_HARDWARE_MANAGER_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (
        DEFAULT_SERVICE_DIR,
        Path("/app/service-configs"),
        Path("/app/configs"),
    ):
        if cand.is_dir():
            return cand
    return _hardware_manager_package_dir()


def resolve_hardware_manager_entrypoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_HARDWARE_MANAGER_ENTRYPOINTS_FILE, "").strip() or DEFAULT_ENTRYPOINTS_FILE
    return resolve_service_config_path(
        resolve_hardware_manager_service_config_dir(),
        name,
        fallbacks=(_hardware_manager_package_dir() / name,),
    )


def load_hardware_manager_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    """Host registry plus parsed ``gui-hardware-manager-entrypoints`` overlay (if present)."""
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    ep = resolve_hardware_manager_entrypoints_path()
    entrypoints = load_yaml_file(ep) if ep else {}
    return raw, registry, entrypoints


def load_bridge_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Host metadata, flattened ``services`` snapshot, and hardware manager entrypoints."""
    raw, registry, hardware_manager = load_hardware_manager_host_context(host_config_path)
    snap = {
        k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip}
        for k, v in registry.items()
    }
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "gui_hardware_manager_entrypoints": hardware_manager},
    )


def gui_hardware_manager_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "gui_hardware_manager")
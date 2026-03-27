"""Load host config for Lucid GUI API Bridge.

Host registry: ``/app/configs/host-config.yml`` (override with ``LUCID_HOST_CONFIG_PATH``).
Service bundles: ``/app/configs/services/*`` (override with
``LUCID_GUI_API_BRIDGE_SERVICE_CONFIG_DIR`` — see
infrastructure/containers/services/container-runtime-layout.yml).
Entrypoints overlay: ``gui-bridge-entrypoints.yml`` resolved from that directory or
beside this package (override filename with ``LUCID_GUI_API_BRIDGE_ENTRYPOINTS_FILE``).

File: gui_api_bridge/config/load_host_config.py
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

ENV_BRIDGE_SERVICE_DIR = "LUCID_GUI_API_BRIDGE_SERVICE_CONFIG_DIR"
ENV_BRIDGE_ENTRYPOINTS_FILE = "LUCID_GUI_API_BRIDGE_ENTRYPOINTS_FILE"
DEFAULT_SERVICE_DIR = Path("/app/configs/services")
DEFAULT_ENTRYPOINTS_FILE = "gui-bridge-entrypoints.yml"


def _bridge_package_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_bridge_service_config_dir() -> Path:
    env = os.environ.get(ENV_BRIDGE_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (
        DEFAULT_SERVICE_DIR,
        Path("/app/service-configs"),
        Path("/app/service_configs"),
    ):
        if cand.is_dir():
            return cand
    return _bridge_package_dir()


def resolve_bridge_entrypoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_BRIDGE_ENTRYPOINTS_FILE, "").strip() or DEFAULT_ENTRYPOINTS_FILE
    return resolve_service_config_path(
        resolve_bridge_service_config_dir(),
        name,
        fallbacks=(_bridge_package_dir() / name,),
    )


def load_bridge_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    """Host registry plus parsed ``gui-bridge-entrypoints`` overlay (if present)."""
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    ep = resolve_bridge_entrypoints_path()
    entrypoints = load_yaml_file(ep) if ep else {}
    return raw, registry, entrypoints


def load_bridge_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Host metadata, flattened ``services`` snapshot, and bridge entrypoints."""
    raw, registry, bridge = load_bridge_host_context(host_config_path)
    snap = {
        k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip}
        for k, v in registry.items()
    }
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "gui_bridge_entrypoints": bridge},
    )


def gui_api_bridge_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "gui-api-bridge")

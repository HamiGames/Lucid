"""
Loads host config for Lucid api-gateway service.

Host registry: /app/configs/host-config.yml (main_lucid_gateway -> api-gateway).
Service overlay: api-gateway.yml under LUCID_API_GATEWAY_SERVICE_CONFIG_DIR.
File: 03_api_gateway/config/load_host_config.py
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

ENV_GATEWAY_SERVICE_DIR = "LUCID_API_GATEWAY_SERVICE_CONFIG_DIR"
ENV_GATEWAY_YML = "LUCID_API_GATEWAY_SERVICE_YML"
DEFAULT_SERVICE_DIR = Path("/app/service-configs")
DEFAULT_GATEWAY_YML = "api-gateway.yml"


def resolve_api_gateway_service_config_dir() -> Path:
    env = os.environ.get(ENV_GATEWAY_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    alt = Path("/app/service_configs")
    if DEFAULT_SERVICE_DIR.is_dir():
        return DEFAULT_SERVICE_DIR
    if alt.is_dir():
        return alt
    return Path(__file__).resolve().parent


def resolve_api_gateway_yml_path() -> Optional[Path]:
    name = os.environ.get(ENV_GATEWAY_YML, "").strip() or DEFAULT_GATEWAY_YML
    return resolve_service_config_path(resolve_api_gateway_service_config_dir(), name)


def load_api_gateway_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    sp = resolve_api_gateway_yml_path()
    overlay = load_yaml_file(sp) if sp else {}
    return raw, registry, overlay


def load_api_gateway_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, gw = load_api_gateway_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "api_gateway_service": gw},
    )


def main_api_gateway_endpoint(registry: Dict[str, ServiceEndpoint]) -> Optional[ServiceEndpoint]:
    return endpoint_by_service_name(registry, "api-gateway")

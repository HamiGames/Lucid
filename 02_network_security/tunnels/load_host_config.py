"""Loads host config for Lucid tunnels service.

Emphasizes tor-socks, tor-control, tunnel-tools from host-config; env overrides
match Dockerfile.tunnels patterns (TOR_SOCKS_HOST, TUNNEL_PORT, etc.).
File: 02_network_security/tunnels/load_host_config.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from common.load_host_config import (
    ServiceEndpoint,
    default_host_config_path,
    load_host_registry,
    load_yaml_file,
    merge_config_layers,
    resolve_service_config_path,
)

ENV_TUNNELS_SERVICE_DIR = "LUCID_TUNNELS_SERVICE_CONFIG_DIR"
ENV_TUNNELS_YML = "LUCID_TUNNELS_SERVICE_YML"
DEFAULT_SERVICE_DIR = Path("/app/service-configs")
DEFAULT_TUNNELS_YML = "tunnels.yml"


def resolve_tunnels_service_config_dir() -> Path:
    env = os.environ.get(ENV_TUNNELS_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    alt = Path("/app/service_configs")
    if DEFAULT_SERVICE_DIR.is_dir():
        return DEFAULT_SERVICE_DIR
    if alt.is_dir():
        return alt
    return Path(__file__).resolve().parent


def resolve_tunnels_yml_path() -> Optional[Path]:
    name = os.environ.get(ENV_TUNNELS_YML, "").strip() or DEFAULT_TUNNELS_YML
    return resolve_service_config_path(resolve_tunnels_service_config_dir(), name)


def load_tunnels_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    sp = resolve_tunnels_yml_path()
    overlay = load_yaml_file(sp) if sp else {}
    return raw, registry, overlay


def load_tunnels_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, tun = load_tunnels_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "tunnels_service": tun},
    )


def tunnel_mesh_from_registry(registry: Dict[str, ServiceEndpoint]) -> Dict[str, Any]:
    """Concrete host/port dict with env overrides (flexible for Tor/compose aliases)."""

    def _row(*keys: str) -> Optional[ServiceEndpoint]:
        for k in keys:
            if k in registry:
                return registry[k]
        return None

    tor_socks = _row("tor_socks")
    tor_ctrl = _row("tor_control")
    tunnel = _row("tunnel_tools")

    return {
        "socks_host": os.environ.get("TOR_SOCKS_HOST") or (tor_socks.service_name if tor_socks else "tor-socks"),
        "socks_port": int(os.environ.get("TOR_SOCKS_PORT") or (tor_socks.port if tor_socks else 9050)),
        "control_host": os.environ.get("CONTROL_HOST") or (tor_ctrl.service_name if tor_ctrl else "tor-control"),
        "control_port": int(os.environ.get("CONTROL_PORT") or (tor_ctrl.port if tor_ctrl else 9051)),
        "tunnel_tools_host": os.environ.get("TUNNEL_TOOLS_HOST")
        or (tunnel.service_name if tunnel else "tunnel-tools"),
        "tunnel_tools_port": int(os.environ.get("TUNNEL_PORT") or (tunnel.port if tunnel else 7000)),
        "tor_proxy_compose_service": os.environ.get("TOR_PROXY_COMPOSE_SERVICE", "tor-proxy"),
    }

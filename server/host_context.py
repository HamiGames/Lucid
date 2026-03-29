"""
File: /app/server/host_context.py
x-lucid-file-path: /app/server/host_context.py
x-lucid-file-type: python

Host registry + master-endpoint resolution for the Lucid server pack.

Aligns with infrastructure/containers/host-config.yml and
infrastructure/containers/services/master-endpoint.yml (see meta.host_config_path).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from common.load_host_config import (
    ServiceEndpoint,
    default_host_config_path,
    load_host_registry,
    load_yaml_file,
)

ENV_MASTER_ENDPOINT = "LUCID_MASTER_ENDPOINT_PATH"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_master_endpoint_path() -> Path:
    env = os.environ.get(ENV_MASTER_ENDPOINT, "").strip()
    if env:
        return Path(env)
    for cand in (
        Path("/app/service_configs/master-endpoint.yml"),
        Path("/app/service_configs/services/master-endpoint.yml"),
    ):
        if cand.is_file():
            return cand
    return (
        _repo_root()
        / "infrastructure"
        / "containers"
        / "services"
        / "master-endpoint.yml"
    )


@dataclass(frozen=True)
class ServerHostBundle:
    host_config_path: Path
    master_endpoint_path: Path
    host_raw: Mapping[str, Any]
    registry: Dict[str, ServiceEndpoint]
    master_raw: Mapping[str, Any]


def load_server_bundle(
    host_config_path: Optional[Path | str] = None,
    master_endpoint_path: Optional[Path | str] = None,
) -> ServerHostBundle:
    hp = Path(host_config_path) if host_config_path else default_host_config_path()
    mp = Path(master_endpoint_path) if master_endpoint_path else default_master_endpoint_path()
    raw, registry = load_host_registry(hp)
    master = load_yaml_file(mp)
    return ServerHostBundle(
        host_config_path=hp,
        master_endpoint_path=mp,
        host_raw=raw,
        registry=registry,
        master_raw=master,
    )


def _norm_ip(v: Any) -> Optional[str]:
    if v is None or v == "":
        return None
    return str(v)


def validate_master_endpoint_registry(
    bundle: ServerHostBundle,
) -> List[str]:
    """Return human-readable errors if master-endpoint ``services`` diverges from host-config."""
    errors: List[str] = []
    meta = bundle.master_raw.get("meta")
    if isinstance(meta, dict):
        declared = meta.get("host_config_path")
        if declared:
            try:
                rel = Path(str(declared))
                if rel.name and bundle.host_config_path.name != rel.name:
                    errors.append(
                        f"host-config filename mismatch: master meta declares {declared!r}, "
                        f"loaded {bundle.host_config_path}"
                    )
            except Exception:
                pass

    master_services = bundle.master_raw.get("services")
    if not isinstance(master_services, dict):
        return errors + ["master-endpoint.yml missing top-level 'services' mapping"]

    for key, blob in master_services.items():
        if not isinstance(blob, dict):
            continue
        host_ep = bundle.registry.get(str(key))
        if host_ep is None:
            errors.append(f"registry key {key!r} in master-endpoint but not in host-config services")
            continue
        m_name = blob.get("service_name")
        m_port = blob.get("port")
        m_ip = _norm_ip(blob.get("host_ip"))
        if m_name is not None and str(m_name) != host_ep.service_name:
            errors.append(
                f"{key}: service_name master={m_name!r} host-config={host_ep.service_name!r}"
            )
        if m_port is not None and int(m_port) != host_ep.port:
            errors.append(f"{key}: port master={m_port} host-config={host_ep.port}")
        h_ip = host_ep.host_ip
        if m_ip is not None and h_ip is not None and m_ip != h_ip:
            errors.append(f"{key}: host_ip master={m_ip!r} host-config={h_ip!r}")

    return errors


def endpoint_for_registry_key(
    registry: Dict[str, ServiceEndpoint],
    key: str,
) -> ServiceEndpoint:
    ep = registry.get(key)
    if ep is None:
        raise KeyError(f"Unknown host-config registry key: {key!r}")
    return ep


# Keys documented in master-endpoint ``developer`` audience (host_registry_keys).
ROLE_LUCID_SERVER_MANAGER = "lucid_server_manager"
ROLE_LUCID_SERVER_CORE = "lucid_server_core"
ROLE_MAIN_GATEWAY = "main_lucid_gateway"


def resolve_role_registry_key(role: str) -> str:
    r = (role or ROLE_LUCID_SERVER_MANAGER).strip().lower().replace("-", "_")
    if r in ("manager", "lucid_server_manager", "server_manager"):
        return ROLE_LUCID_SERVER_MANAGER
    if r in ("core", "lucid_server_core", "server_core"):
        return ROLE_LUCID_SERVER_CORE
    if r in ("gateway", "api_gateway", "main_lucid_gateway"):
        return ROLE_MAIN_GATEWAY
    return r

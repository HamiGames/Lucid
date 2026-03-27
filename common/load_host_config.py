"""Loads host config for Lucid common services.

Aligns with infrastructure/containers/host-config.yml (mounted at
/app/configs/host-config.yml in container images). See also
service_mesh.service_mesh_translator.load_host_registry for mesh vocabulary.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterator, Mapping, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

ENV_HOST_CONFIG = "LUCID_HOST_CONFIG_PATH"
DEFAULT_CONTAINER_HOST_CONFIG = Path("/app/configs/host-config.yml")


@dataclass(frozen=True)
class ServiceEndpoint:
    """One entry under host-config ``services`` (top-level YAML key = ``key``)."""

    key: str
    service_name: str
    port: int
    host_ip: Optional[str]
    http_path_template: Optional[str]
    tags: FrozenSet[str] = field(default_factory=frozenset)
    labels: Mapping[str, str] = field(default_factory=dict)

    def base_url(self, scheme: str = "http") -> str:
        return f"{scheme}://{self.service_name}:{self.port}"


def _repo_root_from_here() -> Path:
    """Lucid repo root: common/load_host_config.py -> parents[1]."""
    return Path(__file__).resolve().parents[1]


def default_host_config_path() -> Path:
    """Resolve host-config: env override, then container path, then repo file."""
    env = os.environ.get(ENV_HOST_CONFIG, "").strip()
    if env:
        return Path(env)
    if DEFAULT_CONTAINER_HOST_CONFIG.is_file():
        return DEFAULT_CONTAINER_HOST_CONFIG
    candidate = _repo_root_from_here() / "infrastructure" / "containers" / "host-config.yml"
    return candidate


def _parse_services_blob(raw: Mapping[str, Any]) -> Dict[str, ServiceEndpoint]:
    out: Dict[str, ServiceEndpoint] = {}
    services = raw.get("services") or {}
    for key, blob in services.items():
        if not isinstance(blob, dict):
            continue
        name = blob.get("service_name")
        port = blob.get("port")
        if not name or port is None:
            continue
        tags = blob.get("tags") or []
        labels = blob.get("labels") or {}
        hip = blob.get("host_ip")
        out[str(key)] = ServiceEndpoint(
            key=str(key),
            service_name=str(name),
            port=int(port),
            host_ip=str(hip) if hip not in (None, "") else None,
            http_path_template=str(blob.get("http_path") or "") or None,
            tags=frozenset(str(t) for t in tags),
            labels={str(k): str(v) for k, v in labels.items()},
        )
    return out


def load_host_registry(
    path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint]]:
    """Load raw host-config YAML and parsed service index by registry key."""
    p = Path(path) if path else default_host_config_path()
    if yaml is None:
        raise RuntimeError("PyYAML is required to load host-config")
    if not p.is_file():
        return {}, {}
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        return {}, {}
    return raw, _parse_services_blob(raw)


def load_yaml_file(path: Path | str) -> Mapping[str, Any]:
    """Load a YAML file; missing path returns empty dict."""
    p = Path(path)
    if yaml is None or not p.is_file():
        return {}
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def resolve_service_config_path(
    directory: Path | str,
    filename: str,
    fallbacks: Optional[Iterator[Path]] = None,
) -> Optional[Path]:
    """Pick first existing path from ``directory/filename`` then ``fallbacks``."""
    d = Path(directory)
    primary = d / filename
    if primary.is_file():
        return primary
    if fallbacks:
        for fb in fallbacks:
            if fb.is_file():
                return fb
    return None


def merge_config_layers(*layers: Mapping[str, Any]) -> Dict[str, Any]:
    """Shallow merge rightmost wins for top-level keys only."""
    out: Dict[str, Any] = {}
    for layer in layers:
        for k, v in layer.items():
            out[k] = v
    return out


def endpoints_for_tags(
    registry: Dict[str, ServiceEndpoint],
    *tags: str,
) -> Dict[str, ServiceEndpoint]:
    """Filter registry entries that contain any of the given tags (flexible wiring)."""
    tagset = {t.lower() for t in tags}
    if not tagset:
        return dict(registry)
    return {
        k: ep
        for k, ep in registry.items()
        if tagset.intersection(x.lower() for x in ep.tags)
    }


def endpoint_by_service_name(
    registry: Dict[str, ServiceEndpoint],
    service_name: str,
) -> Optional[ServiceEndpoint]:
    for ep in registry.values():
        if ep.service_name == service_name:
            return ep
    return None


# Optional shared service / endpoints YAML (flexible layout: hyphen or underscore dir)
ENV_COMMON_SERVICE_DIR = "LUCID_COMMON_SERVICE_CONFIG_DIR"
ENV_COMMON_ENDPOINTS_FILE = "LUCID_COMMON_ENDPOINTS_FILE"
_DEFAULT_COMMON_ENDPOINTS = "common-endpoints.yml"


def resolve_common_service_config_dir() -> Path:
    env = os.environ.get(ENV_COMMON_SERVICE_DIR, "").strip()
    if env:
        return Path(env)
    for cand in (Path("/app/service-configs"), Path("/app/service_configs")):
        if cand.is_dir():
            return cand
    return Path(__file__).resolve().parent


def resolve_common_endpoints_path() -> Optional[Path]:
    name = os.environ.get(ENV_COMMON_ENDPOINTS_FILE, "").strip() or _DEFAULT_COMMON_ENDPOINTS
    return resolve_service_config_path(resolve_common_service_config_dir(), name)


def load_common_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    ep = resolve_common_endpoints_path()
    extra = load_yaml_file(ep) if ep else {}
    return raw, registry, extra


def load_common_merged_config(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    raw, registry, common_endpoints = load_common_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {"services": snap, "common_endpoints": common_endpoints},
    )

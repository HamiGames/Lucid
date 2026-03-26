"""
Lucid service mesh connection translator.

Maps user/admin/node traffic described in
infrastructure/containers/server/service-mesh-translator.txt into concrete
Docker DNS targets using infrastructure/containers/host-config.yml.

Aligns with:
- Dockerfile.service-mesh-controller: /app/configs/host-config.yml, mesh ports 8500/8088
- Dockerfile.server-manager: LUCID_HOST_CONFIG_PATH, lucid-server-manager:8081 orchestration
- Dockerfile.tor-proxy-02 + Dockerfile.tunnels: tor SOCKS/control + tunnel-tools interop

File: service_mesh/service_mesh_translator.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, Mapping, MutableMapping, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - builder/runtime always has PyYAML
    yaml = None  # type: ignore


# Default host registry path (matches server-manager + service-mesh-controller images)
_DEFAULT_HOST_CONFIG = "/app/configs/host-config.yml"
_ENV_HOST_CONFIG = "LUCID_HOST_CONFIG_PATH"


class MeshPrincipal(str, Enum):
    """Mesh identity after lucid-auth-service validation (service-mesh-translator.txt)."""

    RDP_USER = "rdp_user"
    NODE_USER = "node_user"
    ADMIN_USER = "admin_user"


# Logical service ids (translator vocabulary) -> Docker DNS service_name from host-config
LOGICAL_TO_SERVICE_NAME: Dict[str, str] = {
    "api-gateway": "api-gateway",
    "admin-system-gateway": "admin-system-gateway",
    "session-api": "session-api",
    "database": "lucid-mongodb",
    "rdp-server": "rdp-server-manager-http",
    "wallet_manager": "wallet-manager",
    "block-ledger": "data-chain",
    "user-target": "api-gateway",
    "session-api-admin": "session-api",
    "node-target": "node-overlord",
    "database-overlord": "database-overlord",
    "payment-gateway": "tron-payment-service",
    "server-system-core": "lucid-server-core",
    "node-system-gateway": "node-overlord",
    "api-gateway-admin": "api-gateway",
    "block-ledger-admin": "data-chain",
    "node-database": "lucid-mongodb",
    "node-pool": "node-registry",
    "block-manager": "block-manager",
    "data-chain": "data-chain",
    "lucid-auth-service": "lucid-auth-service",
    "lucid-server-manager": "lucid-server-manager",
    "lucid-service-mesh-controller": "lucid-service-mesh-controller",
}


@dataclass(frozen=True)
class ServiceEndpoint:
    """Single row from host-config services.*"""

    key: str
    service_name: str
    port: int
    http_path_template: Optional[str]
    tags: FrozenSet[str] = field(default_factory=frozenset)
    labels: Mapping[str, str] = field(default_factory=dict)

    @property
    def tor_compatible(self) -> bool:
        return self.labels.get("com.lucid.tor.compatible", "").lower() == "true"

    @property
    def tor_inherent(self) -> bool:
        return self.labels.get("com.lucid.tor.inherent", "").lower() == "true"


@dataclass(frozen=True)
class TorTunnelMeshEndpoints:
    """
    Tor + tunnel alignment (Dockerfile.tor-proxy-02 / Dockerfile.tunnels).

    Docker Compose often names the proxy service ``tor-proxy`` while host-config
    uses ``tor-socks`` / ``tor-control`` as DNS names — both patterns are supported via env.
    """

    socks_host: str
    socks_port: int
    control_host: str
    control_port: int
    tunnel_tools_host: str
    tunnel_tools_port: int
    compose_tor_alias: str

    def socks_uri(self) -> str:
        return f"socks5h://{self.socks_host}:{self.socks_port}"

    def control_addr(self) -> Tuple[str, int]:
        return self.control_host, self.control_port


def _parse_services_blob(raw: Mapping[str, Any]) -> Dict[str, ServiceEndpoint]:
    out: Dict[str, ServiceEndpoint] = {}
    services = raw.get("services") or {}
    http_tpl = raw.get("http_path_template")
    for key, blob in services.items():
        if not isinstance(blob, dict):
            continue
        name = blob.get("service_name")
        port = blob.get("port")
        if not name or port is None:
            continue
        tags = blob.get("tags") or []
        labels = blob.get("labels") or {}
        out[key] = ServiceEndpoint(
            key=key,
            service_name=str(name),
            port=int(port),
            http_path_template=str(blob.get("http_path") or "") or None,
            tags=frozenset(str(t) for t in tags),
            labels={str(k): str(v) for k, v in labels.items()},
        )
    return out


def load_host_registry(
    path: Optional[str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint]]:
    """
    Load raw host-config YAML plus parsed ServiceEndpoint index (by top-level key).
    """
    p = Path(path or os.environ.get(_ENV_HOST_CONFIG, "") or _DEFAULT_HOST_CONFIG)
    if yaml is None:
        raise RuntimeError("PyYAML is required to load host-config")
    if not p.is_file():
        return {}, {}
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        return {}, {}
    return raw, _parse_services_blob(raw)


def endpoints_from_registry(registry: Dict[str, ServiceEndpoint]) -> TorTunnelMeshEndpoints:
    """Derive Tor/tunnel endpoints from registry with Dockerfile.tunnels-style env overrides."""

    def _pick(*keys: str) -> Optional[ServiceEndpoint]:
        for k in keys:
            if k in registry:
                return registry[k]
        return None

    tor_socks = _pick("tor_socks")
    tor_ctrl = _pick("tor_control")
    tunnel = _pick("tunnel_tools")

    socks_host = os.environ.get("TOR_SOCKS_HOST") or (
        tor_socks.service_name if tor_socks else "tor-socks"
    )
    socks_port = int(os.environ.get("TOR_SOCKS_PORT") or (tor_socks.port if tor_socks else 9050))

    control_host = os.environ.get("CONTROL_HOST") or (
        tor_ctrl.service_name if tor_ctrl else "tor-control"
    )
    control_port = int(os.environ.get("CONTROL_PORT") or (tor_ctrl.port if tor_ctrl else 9051))

    tt_host = os.environ.get("TUNNEL_TOOLS_HOST") or (
        tunnel.service_name if tunnel else "tunnel-tools"
    )
    tt_port = int(os.environ.get("TUNNEL_PORT") or (tunnel.port if tunnel else 7000))

    compose_alias = os.environ.get("TOR_PROXY_COMPOSE_SERVICE", "tor-proxy")

    return TorTunnelMeshEndpoints(
        socks_host=socks_host,
        socks_port=socks_port,
        control_host=control_host,
        control_port=control_port,
        tunnel_tools_host=tt_host,
        tunnel_tools_port=tt_port,
        compose_tor_alias=compose_alias,
    )


RouteKey = Tuple[str, str]


def _freeze_verbs(*verbs: str) -> FrozenSet[str]:
    return frozenset(verbs)


# --- Allowed edges (source logical id -> target logical id) from service-mesh-translator.txt ---

USER_MESH_ROUTES: Dict[RouteKey, FrozenSet[str]] = {
    ("api-gateway", "session-api"): _freeze_verbs(
        "join_session", "create_session", "lodge_session", "leave", "read"
    ),
    ("api-gateway", "database"): _freeze_verbs("read", "limited_edit", "user_id_lookup"),
    ("api-gateway", "rdp-server"): _freeze_verbs(
        "setup", "read", "limited_write", "join", "leave", "rdp_protocol"
    ),
    ("api-gateway", "wallet_manager"): _freeze_verbs(
        "receive_payment", "read", "limited_edit", "join", "leave"
    ),
    ("api-gateway", "block-ledger"): _freeze_verbs("read"),
}

ADMIN_MESH_ROUTES: Dict[RouteKey, FrozenSet[str]] = {
    ("admin-system-gateway", "user-target"): _freeze_verbs(
        "audit", "edit", "investigate", "join", "leave"
    ),
    ("admin-system-gateway", "session-api-admin"): _freeze_verbs("audit", "join", "leave"),
    ("admin-system-gateway", "node-target"): _freeze_verbs(
        "join", "leave", "read", "write", "edit", "audit"
    ),
    ("admin-system-gateway", "database-overlord"): _freeze_verbs(
        "control", "trigger", "audit", "edit", "patch", "join", "leave"
    ),
    ("admin-system-gateway", "payment-gateway"): _freeze_verbs(
        "audit", "edit", "investigation", "read", "write"
    ),
    ("admin-system-gateway", "server-system-core"): _freeze_verbs(
        "audit", "dev", "admin_control", "investigate", "patch"
    ),
    ("admin-system-gateway", "node-system-gateway"): _freeze_verbs(
        "audit", "dev", "patch", "investigate", "join", "leave"
    ),
    ("admin-system-gateway", "api-gateway-admin"): _freeze_verbs(
        "audit", "edit", "patch", "investigate", "join", "leave"
    ),
    ("admin-system-gateway", "block-ledger-admin"): _freeze_verbs("read", "audit"),
}

NODE_MESH_ROUTES: Dict[RouteKey, FrozenSet[str]] = {
    ("node-system-gateway", "node-database"): _freeze_verbs(
        "read", "write", "restricted_edit", "join", "leave"
    ),
    ("node-system-gateway", "block-ledger"): _freeze_verbs("read"),
    ("node-system-gateway", "payment-gateway"): _freeze_verbs("read", "write", "join", "leave"),
    ("node_user", "node-pool"): _freeze_verbs("join", "leave"),
}

NODE_WORKER_MESH_ROUTES: Dict[RouteKey, FrozenSet[str]] = {
    ("node-system-gateway", "session-api"): _freeze_verbs(
        "join",
        "leave",
        "chunk_processor",
        "compress",
        "inspect_session_db",
    ),
    ("node-system-gateway", "block-manager"): _freeze_verbs(
        "join", "leave", "node_worker_processes"
    ),
    ("node-system-gateway", "data-chain"): _freeze_verbs(
        "join", "leave", "count", "publish", "create_block", "transfer_session_data"
    ),
}


def _routes_for_principal(principal: MeshPrincipal) -> Dict[RouteKey, FrozenSet[str]]:
    if principal == MeshPrincipal.RDP_USER:
        return USER_MESH_ROUTES
    if principal == MeshPrincipal.ADMIN_USER:
        # Admins inherit admin table + node worker paths for investigations
        m: Dict[RouteKey, FrozenSet[str]] = {**ADMIN_MESH_ROUTES}
        for k, v in NODE_MESH_ROUTES.items():
            m.setdefault(k, v)
        for k, v in NODE_WORKER_MESH_ROUTES.items():
            m.setdefault(k, v)
        return m
    if principal == MeshPrincipal.NODE_USER:
        out = {**NODE_MESH_ROUTES, **NODE_WORKER_MESH_ROUTES}
        return out
    return {}


@dataclass(frozen=True)
class ResolvedMeshConnection:
    """Concrete connection spec for proxies and auth gate-ups."""

    source_logical: str
    target_logical: str
    verb: str
    principal: MeshPrincipal
    target_service_name: str
    target_port: int
    upstream_base_url: str
    auth_validate_service: str
    auth_validate_port: int
    mesh_controller_service: str
    mesh_controller_port: int
    server_manager_service: str
    server_manager_port: int
    tor: TorTunnelMeshEndpoints


def _base_url_for(service_name: str, port: int) -> str:
    return f"http://{service_name}:{port}"


def resolve_logical_service(
    logical: str,
    registry: Dict[str, ServiceEndpoint],
) -> Tuple[str, int]:
    """Map translator logical id to (service_name, port)."""
    svc_name = LOGICAL_TO_SERVICE_NAME.get(logical, logical)
    for ep in registry.values():
        if ep.service_name == svc_name:
            return ep.service_name, ep.port
    return svc_name, 0


def mesh_route_allowed(
    principal: MeshPrincipal,
    source_logical: str,
    target_logical: str,
    verb: str,
) -> bool:
    routes = _routes_for_principal(principal)
    key: RouteKey = (source_logical, target_logical)
    allowed = routes.get(key)
    if not allowed:
        return False
    return verb in allowed


def principal_from_auth_flags(
    *,
    user_password_ok: bool,
    node_password_ok: bool,
    admin_verified: bool,
) -> Optional[MeshPrincipal]:
    """
    Mirror service-mesh-translator.txt output section (single principal wins by precedence).

    Precedence: admin > node > rdp user.
    """
    if admin_verified:
        return MeshPrincipal.ADMIN_USER
    if node_password_ok:
        return MeshPrincipal.NODE_USER
    if user_password_ok:
        return MeshPrincipal.RDP_USER
    return None


def build_connection(
    *,
    principal: MeshPrincipal,
    source_logical: str,
    target_logical: str,
    verb: str,
    registry: Optional[Dict[str, ServiceEndpoint]] = None,
    raw_config: Optional[Mapping[str, Any]] = None,
) -> Optional[ResolvedMeshConnection]:
    """
    Validate route + emit resolved connection targets using host-config alignment.

    Returns None if the principal may not perform ``verb`` on the edge.
    """
    if registry is None:
        _, registry = load_host_registry()

    if not mesh_route_allowed(principal, source_logical, target_logical, verb):
        return None

    tgt_name, tgt_port = resolve_logical_service(target_logical, registry)
    if tgt_port <= 0:
        tgt_name = LOGICAL_TO_SERVICE_NAME.get(target_logical, target_logical)
        tgt_port = int(os.environ.get("LUCID_FALLBACK_PORT", "8080"))

    auth_name, auth_port = resolve_logical_service("lucid-auth-service", registry)
    if auth_port <= 0:
        auth_name, auth_port = ("lucid-auth-service", 8089)

    mesh_name, mesh_port = resolve_logical_service("lucid-service-mesh-controller", registry)
    if mesh_port <= 0:
        mesh_name, mesh_port = ("lucid-service-mesh-controller", 8500)

    sm_name, sm_port = resolve_logical_service("lucid-server-manager", registry)
    if sm_port <= 0:
        sm_name, sm_port = ("lucid-server-manager", 8081)

    tor = endpoints_from_registry(registry)

    return ResolvedMeshConnection(
        source_logical=source_logical,
        target_logical=target_logical,
        verb=verb,
        principal=principal,
        target_service_name=tgt_name,
        target_port=tgt_port,
        upstream_base_url=_base_url_for(tgt_name, tgt_port),
        auth_validate_service=auth_name,
        auth_validate_port=auth_port,
        mesh_controller_service=mesh_name,
        mesh_controller_port=mesh_port,
        server_manager_service=sm_name,
        server_manager_port=sm_port,
        tor=tor,
    )


def list_tor_compatible_services(registry: Dict[str, ServiceEndpoint]) -> Tuple[ServiceEndpoint, ...]:
    """Services tagged com.lucid.tor.compatible in host-config (for mesh egress policy)."""
    return tuple(sorted((e for e in registry.values() if e.tor_compatible), key=lambda x: x.service_name))

"""ports.txt -> infrastructure/containers/host-config.yml

Supports:
  - Canonical ``services:`` map (stable_id -> port, service_name, tags, http_path, ...).
  - Generated ``dockerfile_services:`` list (from infrastructure/generate_ports_txt_from_dockerfiles.py).

Run from repository root (Lucid):

  python _gen_host_config.py

Merges ``host_ip`` from ``service-ip.txt`` when the stable id matches.
Reads ``ports.txt`` as UTF-8, UTF-8-BOM, or UTF-16.
"""
from __future__ import annotations

import re
import sys
import yaml
from pathlib import Path
from typing import Any

root = Path(__file__).resolve().parent
ports_path = root / "ports.txt"
out_path = root / "infrastructure" / "containers" / "host-config.yml"
service_ip_path = root / "service-ip.txt"
CONTAINERS_DIR = root / "infrastructure" / "containers"

if str(CONTAINERS_DIR) not in sys.path:
    sys.path.insert(0, str(CONTAINERS_DIR))
try:
    import _sync_dockerfile_lucid_env as lucid_sync
except ImportError:
    lucid_sync = None  # type: ignore[misc, assignment]

SERVICE_KEY_FROM_DF = re.compile(r"service_key_from_dockerfile:([a-zA-Z0-9_]+)")

# Stable registry id -> Docker DNS hostname (when Dockerfile echoes the id, not the hostname).
SERVICE_NAME_DNS: dict[str, str] = {
    "main_lucid_gateway": "api-gateway",
}

# Per stable service id (ports.txt key): Lucid cluster label (Dockerfile / align-spin-up conventions).
CLUSTER: dict[str, str] = {
    "main_lucid_gateway": "core",
    "lucid_server_gateway": "core",
    "lucid_server_manager": "core",
    "lucid_server_core": "core",
    "lucid_auth_service": "foundation",
    "lucid_gov": "foundation",
    "session_system_control": "processing",
    "session_pipeline_manager": "processing",
    "session_chunk_processor": "processing",
    "session_storage_service": "storage",
    "session_storage": "storage",
    "session_pipeline": "processing",
    "session_anchoring": "core",
    "session_recorder": "application",
    "session_processor": "processing",
    "session_merkle_tree_builder": "processing",
    "session_overlord": "processing",
    "session_api": "processing",
    "admin_params_registry": "core",
    "admin_key_rotation": "core",
    "admin_governance_client": "core",
    "admin_ui_backend": "core",
    "database_overlord": "database",
    "admin_overlord": "core",
    "admin_system_gateway": "core",
    "node_management": "application",
    "node_management_staging": "application",
    "node_worker": "application",
    "node_registry": "application",
    "node_gov": "application",
    "node_utils": "application",
    "node_overlord": "application",
    "node_system_gateway": "application",
    "blockchain_engine": "core",
    "blockchain_consensus_engine": "core",
    "block_manager": "core",
    "data_chain": "core",
    "chain_to_pay": "core",
    "payment_system_gateway": "payment",
    "tron_node_client": "payment",
    "on_system_chain_client": "payment",
    "tron_payment_service": "payment",
    "tron_client": "payment",
    "tron_client_aux": "payment",
    "payout_router": "payment",
    "wallet_manager": "payment",
    "usdt_manager": "payment",
    "rdp_server_manager_yml": "application",
    "rdp_server_manager": "application",
    "rdp_controller": "application",
    "rdp_session_controller": "application",
    "rdp_resource_monitor": "application",
    "lucid_xrdp": "application",
    "xrdp_desktop": "application",
    "xrdp_sesman": "application",
    "lucid_service_mesh_controller": "core",
    "consul_dns": "core",
    "consul_grpc": "core",
    "consul_lan_serf": "core",
    "service_mesh_http": "core",
    "gui_docker_manager": "gui-integration",
    "gui_api_bridge": "gui-integration",
    "gui_hardware_manager": "gui-integration",
    "gui_tor_manager_http": "gui-integration",
    "tor_socks": "foundation",
    "tor_control": "foundation",
    "tunnel_tools": "foundation",
    "lucid_redis": "foundation",
    "lucid_elasticsearch_http": "foundation",
    "lucid_elasticsearch_transport": "foundation",
    "lucid_mongodb": "foundation",
    "mongodb_monitoring": "foundation",
    "lucid_system_storage": "storage",
    "vm_service": "application",
    "prometheus_metrics": "monitoring",
    "electron_gui_user": "gui-integration",
    "electron_gui_node": "gui-integration",
    "database_backup": "database",
    "database_monitoring": "database",
    "timelock": "foundation",
    "wallet_key_rotation": "payment",
    "software_vault": "payment",
    "role_manager": "payment",
    "vm_manager": "application",
    "vm_orchestrator": "application",
    "vm_resource_monitor": "application",
    "base": "foundation",
    "common": "foundation",
    "rdp": "application",
}

PLANE_OPS = frozenset({"main_lucid_gateway", "tunnel_tools"})
PLANE_SUPPORT = frozenset(
    {
        "tron_node_client",
        "on_system_chain_client",
        "tron_payment_service",
        "tron_client",
        "tron_client_aux",
        "payout_router",
        "wallet_manager",
        "usdt_manager",
    }
)
API_GATEWAY = frozenset(
    {
        "session_anchoring",
        "session_pipeline_manager",
        "session_chunk_processor",
    }
)
TOR_INHERENT = frozenset({"tor_socks", "tor_control"})
TOR_COMPATIBLE = frozenset(
    {
        "tron_node_client",
        "on_system_chain_client",
        "tron_payment_service",
        "tron_client",
        "tron_client_aux",
        "payout_router",
        "wallet_manager",
        "usdt_manager",
        "tunnel_tools",
        "lucid_redis",
        "lucid_elasticsearch_http",
        "lucid_elasticsearch_transport",
        "lucid_mongodb",
        "mongodb_monitoring",
        "lucid_system_storage",
        "gui_docker_manager",
        "gui_api_bridge",
        "gui_hardware_manager",
        "gui_tor_manager_http",
        "admin_system_gateway",
    }
)
PHASE_GUI = frozenset(
    {
        "gui_docker_manager",
        "gui_api_bridge",
        "gui_hardware_manager",
        "gui_tor_manager_http",
        "electron_gui_user",
        "electron_gui_node",
    }
)
ARCH_SUPPORT = PLANE_SUPPORT | frozenset({"tunnel_tools"})


def build_labels(stable_id: str, svc: dict[str, Any]) -> dict[str, str]:
    """Docker LABEL-style com.lucid.* map aligned with infrastructure/** Dockerfiles."""
    name = svc["service_name"]
    port = svc["port"]
    cluster = CLUSTER.get(stable_id, "application")
    labels: dict[str, str] = {
        "com.lucid.service": name,
        "com.lucid.platform": "arm64",
        "com.lucid.cluster": cluster,
        "com.lucid.security": "distroless",
        "com.lucid.expose": str(port),
    }
    if stable_id in PLANE_OPS:
        labels["com.lucid.plane"] = "ops"
    elif stable_id in PLANE_SUPPORT:
        labels["com.lucid.plane"] = "support"
    if stable_id in ARCH_SUPPORT:
        labels["com.lucid.architecture"] = "linux/arm64"
        labels["com.lucid.vulnerabilities"] = "zero"
    if stable_id in API_GATEWAY:
        labels["com.lucid.api.gateway"] = "api-gateway"
    if stable_id in TOR_COMPATIBLE:
        labels["com.lucid.tor.compatible"] = "true"
    if stable_id in TOR_INHERENT:
        labels["com.lucid.tor.inherent"] = "true"
        labels["com.lucid.tor.system"] = "built-in"
    if stable_id in PHASE_GUI:
        labels["com.lucid.phase"] = "gui"
    return labels


def read_text_robust(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8-sig")


def load_service_ips(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    text = read_text_robust(path)
    idx = text.find("service_ips:")
    if idx < 0:
        return {}
    data = yaml.safe_load(text[idx:])
    if not isinstance(data, dict):
        return {}
    block = data.get("service_ips")
    if not isinstance(block, dict):
        return {}
    return {str(k): str(v) for k, v in block.items()}


def _norm_key(s: str) -> str:
    return s.replace("-", "_").strip().lower()


def service_name_to_kebab(name: str) -> str:
    s = (name or "").strip().lower()
    return s.replace("_", "-")


def stable_id_from_dockerfile_item(item: dict[str, Any]) -> str:
    src = str(item.get("service_name_source") or "")
    m = SERVICE_KEY_FROM_DF.search(src)
    if m:
        return m.group(1)
    p = str(item.get("dockerfile_path") or "").replace("\\", "/")
    if p.startswith("infrastructure/containers/") and lucid_sync:
        rel = p[len("infrastructure/containers/") :]
        name = Path(p).name
        key = lucid_sync.service_key_from_dockerfile(rel, name)
        if key:
            return key
    sn = str(item.get("service_name") or "").strip()
    if sn:
        return re.sub(r"[^a-zA-Z0-9]+", "_", sn.replace("-", "_")).strip("_").lower()
    base = Path(p).name
    if base.lower().startswith("dockerfile."):
        stem = base.split(".", 1)[1]
        return re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower() or "unknown"
    return "unknown"


def _source_dockerfile_score(path: str) -> int:
    """Prefer infrastructure/containers over infrastructure/docker; de-prioritize electron_gui."""
    if not path:
        return 0
    pl = path.lower()
    sc = 0
    if "infrastructure/containers/" in path:
        sc += 100
    if "infrastructure/docker/" in path:
        sc += 20
    if "electron_gui" in path:
        sc -= 40
    if "/storage/" in path:
        sc += 15
    elif "/database/" in path:
        sc += 5
    if "dockerfile copy" in pl or "/dockerfile copy." in pl:
        sc -= 30
    if re.search(r"/Dockerfile$", path.replace("\\", "/"), re.I):
        sc -= 5
    return sc


def resolve_docker_dns_name(sid: str, item: dict[str, Any], path_mapped: bool) -> str:
    raw = str(item.get("service_name") or "").strip()
    if path_mapped:
        if raw and _norm_key(raw) != _norm_key(sid):
            kebab_raw = service_name_to_kebab(raw)
            if ("-" in kebab_raw or kebab_raw.startswith("lucid")) and "_" not in raw:
                return kebab_raw
        return SERVICE_NAME_DNS.get(sid, sid.replace("_", "-"))
    if raw:
        return service_name_to_kebab(raw)
    return sid.replace("_", "-")


def dockerfile_services_to_map(items: Any, *, verbose: bool = True) -> dict[str, Any]:
    if not isinstance(items, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        sid = stable_id_from_dockerfile_item(item)
        p = str(item.get("dockerfile_path") or "").replace("\\", "/")
        path_mapped = bool(
            p.startswith("infrastructure/containers/")
            and lucid_sync
            and lucid_sync.service_key_from_dockerfile(
                p[len("infrastructure/containers/") :], Path(p).name
            )
        )
        pl = item.get("ports")
        ports_list = list(pl) if isinstance(pl, list) else []
        port = int(ports_list[0]) if ports_list else 0
        dns = resolve_docker_dns_name(sid, item, path_mapped)
        tags = [str(t) for t in (item.get("tags") or []) if t is not None]
        if sid not in tags:
            tags.append(sid)
        row: dict[str, Any] = {
            "port": port,
            "service_name": dns,
            "tags": tags,
            "http_path": f"http://{dns}:{port}/app",
        }
        df_path = item.get("dockerfile_path")
        df_norm = ""
        if isinstance(df_path, str) and df_path.strip():
            df_norm = df_path.strip().replace("\\", "/")
            row["source_dockerfile"] = df_norm
        if sid in out:
            old_p = str(out[sid].get("source_dockerfile") or "")
            new_sc = _source_dockerfile_score(df_norm)
            old_sc = _source_dockerfile_score(old_p)
            if old_p and new_sc < old_sc:
                if verbose:
                    print(
                        f"_gen_host_config: info: duplicate stable_id {sid!r}: "
                        f"keeping higher-precedence {old_p} (skip {df_norm})",
                        file=sys.stderr,
                    )
                continue
            if verbose:
                if old_p and new_sc == old_sc:
                    print(
                        f"_gen_host_config: warning: duplicate stable_id {sid!r} "
                        f"({df_norm}), overwriting {old_p}",
                        file=sys.stderr,
                    )
                elif old_p:
                    print(
                        f"_gen_host_config: info: duplicate stable_id {sid!r}: "
                        f"preferring {df_norm} over {old_p}",
                        file=sys.stderr,
                    )
        out[sid] = row
    return out


def load_services_map(ports_file: Path, *, verbose: bool = True) -> dict[str, Any]:
    text = read_text_robust(ports_file)
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f"_gen_host_config: invalid YAML in {ports_file}: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit("_gen_host_config: ports.txt root must be a mapping")
    if data.get("services"):
        svc = data["services"]
        if not isinstance(svc, dict):
            raise SystemExit("ports.txt: services must be a mapping")
        return svc
    if data.get("dockerfile_services"):
        items = data["dockerfile_services"]
        if not isinstance(items, list):
            raise SystemExit("ports.txt: dockerfile_services must be a list")
        return dockerfile_services_to_map(items, verbose=verbose)
    lines = text.splitlines(True)
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "services:")
    except StopIteration:
        raise SystemExit(
            "_gen_host_config: ports.txt must contain top-level 'services:' or "
            "'dockerfile_services:', or a legacy 'services:' block."
        )
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("# ====")),
        len(lines),
    )
    chunk = "".join(lines[start:end])
    legacy = yaml.safe_load(chunk)
    if not isinstance(legacy, dict) or "services" not in legacy:
        raise SystemExit("_gen_host_config: legacy slice did not produce services:")
    svc = legacy["services"]
    if not isinstance(svc, dict):
        raise SystemExit("_gen_host_config: legacy services must be a mapping")
    return svc


def main() -> None:
    service_ips = load_service_ips(service_ip_path)
    services_src = load_services_map(ports_path, verbose=True)

    unknown_cluster = sorted(set(services_src) - set(CLUSTER))
    if unknown_cluster:
        print(
            "_gen_host_config: info: unknown CLUSTER ids (using application): "
            + ", ".join(unknown_cluster),
            file=sys.stderr,
        )

    services_out: dict[str, Any] = {}
    for sid, svc in services_src.items():
        row = dict(svc)
        if sid in service_ips:
            row["host_ip"] = service_ips[sid]
        row["labels"] = build_labels(sid, row)
        services_out[sid] = row

    document = {
        "version": "1.0",
        "description": "Lucid container host registry for Docker DNS hostnames, ports, discovery URLs, and static host IPs.",
        "source": "ports.txt",
        "ip_source": "service-ip.txt",
        "path": "infrastructure/containers/host-config.yml",
        "http_path_template": "http://${service_name}:${port}/app",
        "services": services_out,
        "collision_notes": [
            "8120: admin-ui-backend and database-overlord share port — use distinct service_name hostnames.",
            "8099: node-management-staging vs gui-hardware-manager — remap host publish if co-hosted.",
            "8090: session-recorder vs rdp-server-manager-http — remap host publish if co-hosted.",
            "8080: api-gateway vs tron-payment-service — remap host publish if co-hosted.",
            "8092: payout-router vs session-merkle-tree-builder — remap host publish if co-hosted.",
            "8600: node-worker vs consul-lan-serf — remap host publish if co-hosted.",
            "8101: rdp-session-controller vs tron-client-aux — remap host publish if co-hosted.",
            "RDP: rdp-services.yml may use 8001 for rdp-server-manager; Dockerfile uses 8090 (see rdp_server_manager entries).",
            "http_path is a template; real HTTP paths are often /health or /api/v1/... not /app.",
            "Non-HTTP services (Redis, MongoDB, Tor, RDP binary) still carry http_path for uniform templating only.",
            "admin-system-gateway: primary discovery port 8155 (/health in http_path); optional portal listens "
            "28080→api-gateway:8080, 28120→admin-ui-backend:8120, 28050→admin-params-registry:8050, "
            "27000→lucid-tunnel-tools:7000 (defaults in infrastructure/containers/admin/config/"
            "admin-system-gateway.connections.json).",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# infrastructure/containers/host-config.yml\n")
        f.write(
            "# Generated from repository root ports.txt + _gen_host_config.py label rules — "
            "regenerate; do not hand-edit the service list.\n\n"
        )
        yaml.dump(
            document,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )
    print("wrote", out_path)


if __name__ == "__main__":
    main()

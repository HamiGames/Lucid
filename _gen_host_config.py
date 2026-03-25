"""One-off: ports.txt -> infrastructure/containers/host-config.yml"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

root = Path(__file__).resolve().parent
ports_path = root / "ports.txt"
out_path = root / "infrastructure" / "containers" / "host-config.yml"

# Per stable service id (ports.txt key): Lucid cluster label (Dockerfile / align-spin-up conventions).
CLUSTER: dict[str, str] = {
    "main_lucid_gateway": "core",
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
    "blockchain_engine": "core",
    "blockchain_consensus_engine": "core",
    "block_manager": "core",
    "data_chain": "core",
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


lines = ports_path.read_text(encoding="utf-8").splitlines(True)
start = next(i for i, ln in enumerate(lines) if ln.strip() == "services:")
end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("# ====")), len(lines))
chunk = "".join(lines[start:end])
data = yaml.safe_load(chunk)

extra_ids = set(data["services"]) - set(CLUSTER)
if extra_ids:
    raise SystemExit(
        "_gen_host_config: add CLUSTER entries for new ports.txt service ids: "
        + ", ".join(sorted(extra_ids))
    )

services_out: dict[str, Any] = {}
for sid, svc in data["services"].items():
    row = dict(svc)
    row["labels"] = build_labels(sid, svc)
    services_out[sid] = row

document = {
    "version": "1.0",
    "description": "Lucid container host registry for Docker DNS hostnames, ports, and discovery URLs.",
    "source": "ports.txt",
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

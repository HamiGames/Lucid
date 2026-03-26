# Sync LUCID_* host registry env vars in Dockerfiles from:
#   - infrastructure/containers/host-config.yml
#   - service-ip.txt (repo root)
#   - ports.txt (repo root) for fallback http_path / service_name / port
"""Run from repo root: python infrastructure/containers/_sync_dockerfile_lucid_env.py"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTAINERS = ROOT / "infrastructure" / "containers"

SERVICE_IP_PATH = ROOT / "service-ip.txt"
HOST_CONFIG_PATH = CONTAINERS / "host-config.yml"
PORTS_PATH = ROOT / "ports.txt"

# Relative path under infrastructure/containers -> host-config / ports service id
SERVICE_KEY_BY_REL_PATH: dict[str, str] = {
    "server/Dockerfile": "lucid_server_core",
    "server/Dockerfile.server-gateway": "lucid_server_gateway",
    "server/Dockerfile.server-manager": "lucid_server_manager",
    "server/Dockerfile.rdp-server-manager": "rdp_server_manager",
    "server/Dockerfile.service-mesh-controller": "lucid_service_mesh_controller",
    "user/Dockerfile": "main_lucid_gateway",
    "tor/Dockerfile": "tunnel_tools",
    "vm/Dockerfile.vm": "vm_service",
    "storage/Dockerfile.storage": "lucid_system_storage",
    "storage/Dockerfile.redis": "lucid_redis",
    "storage/Dockerfile.mongodb": "lucid_mongodb",
    "storage/Dockerfile.elasticsearch": "lucid_elasticsearch_http",
    "database/Dockerfile.elasticsearch": "lucid_elasticsearch_http",
    "database/Dockerfile.database": "mongodb_monitoring",
    "services/node/Dockerfile": "node_management",
    "services/node/Dockerfile.node-management": "node_management",
    "gui/Dockerfile.gui": "gui_docker_manager",
    "gui/Dockerfile copy.gui-tor-manager": "gui_tor_manager_http",
    "electron_gui/Dockerfile.admin": "admin_ui_backend",
    "electron_gui/Dockerfile.user": "electron_gui_user",
    "electron_gui/Dockerfile.node": "electron_gui_node",
    "sessions/Dockerfile.session-systems-control": "session_system_control",
    "sessions/Dockerfile.api": "session_api",
    "payment_systems/Dockerfile.payment-gateway": "payment_system_gateway",
    "tor/Dockerfile.tor-proxy-02": "tor_socks",
    "tor/Dockerfile.tunnels": "tunnel_tools",
}

# Image name segment special cases: Dockerfile.NAME -> service id
STAGE2_NAME_FIX = {
    "api": "session_api",
    "session-systems-control": "session_system_control",
    "chunk-processor": "session_chunk_processor",
    "session-pipeline-manager": "session_pipeline_manager",
    "session-storage-service": "session_storage_service",
    "merkle-tree-builder": "session_merkle_tree_builder",
    "anchoring": "session_anchoring",
    "copy.gui-tor-manager": "gui_tor_manager_http",
    "gov-client": "admin_governance_client",
    "governance-client": "admin_governance_client",
    "key-rotation": "admin_key_rotation",
    "params-registry": "admin_params_registry",
    "auth-service": "lucid_auth_service",
    "consensus-engine": "blockchain_consensus_engine",
    "data": "data_chain",
    "engine": "blockchain_engine",
    "mongodb": "lucid_mongodb",
    "redis": "lucid_redis",
    "gui-tor-manager": "gui_tor_manager_http",
    "wallet": "wallet_manager",
}

SKIP_REL_PATHS = frozenset(
    {
        ".devcontainer/Dockerfile",
        ".devcontainer/Dockerfile.simple",
        ".devcontainer/Dockerfile.network-friendly",
        "base/Dockerfile.base",
        "base/Dockerfile.java-base",
        "base/Dockerfile.python-base",
    }
)


def load_service_ips() -> dict[str, str]:
    text = SERVICE_IP_PATH.read_text(encoding="utf-8")
    idx = text.find("service_ips:")
    if idx < 0:
        raise SystemExit("service_ips: not found in service-ip.txt")
    block = text[idx:]
    data = yaml.safe_load(block)
    if not isinstance(data, dict) or "service_ips" not in data:
        raise SystemExit("invalid service_ips yaml")
    return {str(k): str(v) for k, v in data["service_ips"].items()}


def load_host_config_services() -> dict:
    data = yaml.safe_load(HOST_CONFIG_PATH.read_text(encoding="utf-8"))
    return data.get("services") or {}


def load_ports_services() -> dict[str, dict]:
    """Parse ports.txt service blocks (indent 2 = key, indent 4 = fields)."""
    text = PORTS_PATH.read_text(encoding="utf-8")
    out: dict[str, dict] = {}
    current: str | None = None
    for line in text.splitlines():
        m = re.match(r"^  ([a-z0-9_]+):\s*$", line)
        if m:
            current = m.group(1)
            out[current] = {}
            continue
        if not current or not line.startswith("    "):
            continue
        km = re.match(
            r"    (port|service_name|http_path):\s*(.+?)\s*$", line
        )
        if not km:
            continue
        fk, raw = km.group(1), km.group(2).strip()
        if fk == "port":
            try:
                out[current]["port"] = int(raw)
            except ValueError:
                pass
        elif fk == "service_name":
            out[current]["service_name"] = raw
        elif fk == "http_path":
            if raw.startswith('"') and raw.endswith('"'):
                raw = raw[1:-1]
            out[current]["http_path"] = raw
    return out


def service_key_from_dockerfile(rel: str, name: str) -> str | None:
    if rel in SERVICE_KEY_BY_REL_PATH:
        return SERVICE_KEY_BY_REL_PATH[rel]
    lower = name.lower()
    if lower.startswith("dockerfile."):
        tail = lower[len("dockerfile.") :]
    elif lower == "dockerfile":
        return None
    elif lower.startswith("dockerfile copy."):
        tail = lower[len("dockerfile copy.") :]
    elif lower.startswith("dockerfile "):
        tail = name.split(" ", 1)[1]
    else:
        return None
    tail = tail.strip()
    if not tail:
        return None
    if tail in STAGE2_NAME_FIX:
        return STAGE2_NAME_FIX[tail]
    return tail.replace("-", "_")


def merge_meta(
    key: str,
    hc_svc: dict,
    ports_svc: dict,
    ips: dict[str, str],
) -> tuple[str | None, str, str]:
    """Returns (host_ip or None, http_path, service_key) — http_path always set when possible."""
    ip = hc_svc.get("host_ip")
    if ip is None:
        ip = ips.get(key)
    if isinstance(ip, str):
        ip = ip.strip()
    else:
        ip = None
    port = hc_svc.get("port") or ports_svc.get("port")
    sn = hc_svc.get("service_name") or ports_svc.get("service_name")
    http_path = hc_svc.get("http_path") or ports_svc.get("http_path")
    if isinstance(http_path, str) and http_path.startswith('"') and http_path.endswith('"'):
        http_path = http_path[1:-1]
    if not http_path and sn and port is not None:
        http_path = f"http://{sn}:{port}/app"
    if not http_path:
        http_path = f"http://{key.replace('_', '-')}:0/app"
    return ip, str(http_path), key


TRIO_BLOCK = """    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\
    LUCID_SERVICE_HOST_IP={ip} \\
    LUCID_SERVICE_HTTP_PATH={path} \\"""

TRIO_BLOCK_NO_IP = """    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\
    LUCID_SERVICE_HTTP_PATH={path} \\"""

# Match the three lines (with optional middle IP line)
RE_TRIO = re.compile(
    r"[ \t]*LUCID_HOST_CONFIG_SERVICE_KEY=[^\\\n]+ ?\\\n"
    r"(?:[ \t]*LUCID_SERVICE_HOST_IP=[^\\\n]+ ?\\\n)?"
    r"[ \t]*LUCID_SERVICE_HTTP_PATH=[^\\\n]+ ?\\\n",
    re.MULTILINE,
)

# user-plane gateway image: extra keys between SERVICE_KEY and IP
RE_USER_BLOCK = re.compile(
    r"[ \t]*LUCID_HOST_CONFIG_SERVICE_KEY=[^\\\n]+ ?\\\n"
    r"([ \t]*LUCID_SERVICES_CONFIG_DIR=[^\\\n]+ ?\\\n)"
    r"([ \t]*LUCID_SERVICE_NAME=[^\\\n]+ ?\\\n)"
    r"[ \t]*LUCID_SERVICE_HOST_IP=[^\\\n]+ ?\\\n"
    r"[ \t]*LUCID_GATEWAY_HTTP_PATH=[^\\\n]+ ?\\\n",
    re.MULTILINE,
)


def _infer_host_config_path_env(text: str) -> str | None:
    m = re.search(
        r"host-config\.yml\s+(/app/[^\s#]+)", text
    )
    if m:
        return m.group(1)
    return None


def patch_content(text: str, key: str, ip: str | None, http_path: str) -> str:
    if ip:
        trio_mid = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"    LUCID_SERVICE_HOST_IP={ip} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path} \\\n"
        )
        trio_end = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"    LUCID_SERVICE_HOST_IP={ip} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path}\n"
        )
        trio_mid_no_ip = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path} \\\n"
        )
        trio_end_no_ip = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path}\n"
        )
    else:
        trio_mid = trio_mid_no_ip = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path} \\\n"
        )
        trio_end = trio_end_no_ip = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path}\n"
        )

    um = RE_USER_BLOCK.search(text)
    if um and ip:
        mid = um.group(1) + um.group(2)
        repl = (
            f"    LUCID_HOST_CONFIG_SERVICE_KEY={key} \\\n"
            f"{mid}"
            f"    LUCID_SERVICE_HOST_IP={ip} \\\n"
            f"    LUCID_SERVICE_HTTP_PATH={http_path} \\\n"
        )
        text = RE_USER_BLOCK.sub(repl, text, count=1)
        return text

    if RE_TRIO.search(text):
        new_block = (
            TRIO_BLOCK.format(key=key, ip=ip or "", path=http_path)
            if ip
            else TRIO_BLOCK_NO_IP.format(key=key, path=http_path)
        ) + "\n"
        return RE_TRIO.sub(new_block, text, count=1)

    sub = re.sub(
        r"(    LUCID_HOST_CONFIG_PATH=[^\n]+ \\\n)\s*LUCID_API_GATEWAY_HOST_IP=[^\n]+\n",
        r"\1" + (trio_end if ip else trio_end_no_ip),
        text,
        count=1,
    )
    if sub != text:
        return sub

    if "LUCID_HOST_CONFIG_SERVICE_KEY=" not in text:
        m = re.search(
            r"^([ \t]*LUCID_HOST_CONFIG_PATH=[^\\\n]+ \\\n)",
            text,
            re.MULTILINE,
        )
        if m:
            insert = trio_mid if ip else trio_mid_no_ip
            return text[: m.end()] + insert + text[m.end() :]

    if "LUCID_HOST_CONFIG_SERVICE_KEY=" not in text:
        sub_path_end = re.sub(
            r"(\n[ \t]*LUCID_HOST_CONFIG_PATH=[^\n\\\r]+)(\r?\n\r?\n# LUCID_IMAGE_CONFIG:)",
            r"\1 \\\n" + (trio_end if ip else trio_end_no_ip) + r"\2",
            text,
            count=1,
        )
        if sub_path_end != text:
            return sub_path_end

    if (
        "LUCID_HOST_CONFIG_SERVICE_KEY=" not in text
        and "host-config.yml" in text
    ):
        dest = _infer_host_config_path_env(text)
        if dest and "LUCID_HOST_CONFIG_PATH=" not in text:
            path_line = f"    LUCID_HOST_CONFIG_PATH={dest} \\\n"
            insert = path_line + (trio_mid if ip else trio_mid_no_ip)
            m2 = re.search(
                r"(^[ \t]*LC_ALL=C\.UTF-8 \\\n)", text, re.MULTILINE
            )
            if m2:
                return text[: m2.end()] + insert + text[m2.end() :]

    return text


def main() -> int:
    ips = load_service_ips()
    hc = load_host_config_services()
    ports = load_ports_services()

    dockerfiles = sorted(CONTAINERS.rglob("Dockerfile*"))
    updated = 0
    skipped = 0
    warnings: list[str] = []

    for df in dockerfiles:
        name = df.name
        if name.endswith(".md") or ".git" in str(df):
            continue
        try:
            rel = str(df.relative_to(CONTAINERS)).replace("\\", "/")
        except ValueError:
            continue
        if rel in SKIP_REL_PATHS:
            skipped += 1
            continue
        if "Dockerfile copy" in name and "gui-tor" not in name:
            warnings.append(f"skip unfamiliar: {rel}")
            skipped += 1
            continue

        svc_key = service_key_from_dockerfile(rel, name)
        if not svc_key:
            warnings.append(f"no service key: {rel}")
            skipped += 1
            continue

        hc_svc = hc.get(svc_key) or {}
        ports_svc = ports.get(svc_key) or {}
        if not hc_svc and not ports_svc and svc_key not in ips:
            warnings.append(f"unknown service id {svc_key} ({rel})")
            skipped += 1
            continue

        ip, http_path, _ = merge_meta(svc_key, hc_svc, ports_svc, ips)
        raw = df.read_text(encoding="utf-8")
        new_raw = patch_content(raw, svc_key, ip, http_path)
        if new_raw != raw:
            df.write_text(new_raw, encoding="utf-8", newline="\n")
            updated += 1

    for w in warnings:
        print(w, file=sys.stderr)
    print(f"updated {updated} dockerfiles, skipped {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

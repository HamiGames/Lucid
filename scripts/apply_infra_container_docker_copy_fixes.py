# Path: scripts/apply_infra_container_docker_copy_fixes.py
# Rewrites COPY sources under infrastructure/containers Dockerfiles to match repo layout (repo-root build context).
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IC = os.path.join(ROOT, "infrastructure", "containers")

SERVICE_CONFIG_MAP: dict[str, str] = {
    "admin-interface.yml": "infrastructure/containers/services/admin/admin-interface.yml",
    "api-gateway.yml": "infrastructure/containers/services/api-gateway.yml",
    "auth-service.yml": "infrastructure/containers/services/middle-ware/auth-service.yml",
    "beta-sidecar.yml": "infrastructure/containers/services/beta-sidecar.yml",
    "blockchain-core.yml": "infrastructure/containers/services/blockchain/blockchain-core.yml",
    "database.yml": "infrastructure/containers/services/database/database.yml",
    "gui-api-bridge.yml": "infrastructure/containers/services/gui/gui-api-bridge.yml",
    "gui-docker-manager-service-groups.yml": "infrastructure/containers/services/gui/gui-docker-manager-service-groups.yml",
    "gui-docker-manager.yml": "infrastructure/containers/services/gui/gui-docker-manager.yml",
    "gui-hardware-manager.yml": "infrastructure/containers/services/gui/gui-hardware-manager.yml",
    "gui-services.json": "configs/services/gui-services.json",
    "node-management.yml": "infrastructure/containers/services/node/node-management.yml",
    "rdp-services.yml": "infrastructure/containers/services/rdp/rdp-services.yml",
    "service-discovery.yml": "infrastructure/containers/services/service-discovery.yml",
    "service-registry.json": "infrastructure/containers/services/service-registry.json",
    "session-management.yml": "infrastructure/containers/services/sessions/session-management.yml",
    "tron-payment.yml": "infrastructure/containers/services/payment_services/tron-payment.yml",
}

# Order: longer / more specific first where relevant.
TEXT_SUBSTITUTIONS: list[tuple[str, str]] = [
    ("infrastructure/containers/blockblockchain/", "infrastructure/containers/blockchain/"),
    ("'./service_configs/blockblockchain/", "'./service_configs/blockchain/"),
    ("RDP/session-controller/", "RDP/session_controller/"),
    ("COPY blockchain/docker-compose.block-system.yml", "COPY infrastructure/containers/blockchain/docker-compose.block-system.yml"),
    ("COPY blockchain/docker-compose.chain.yml", "COPY infrastructure/containers/blockchain/docker-compose.chain.yml"),
    ("COPY blockchain/docker-compose.manager.yml", "COPY infrastructure/containers/blockchain/docker-compose.manager.yml"),
    ("COPY blockchain/config/blockchain-endpoints.yml", "COPY infrastructure/containers/blockchain/config/blockchain-endpoints.yml"),
    ("COPY blockchain/config/openssl-api.yml", "COPY infrastructure/containers/blockchain/config/openssl-api.yml"),
    ("COPY blockchain/config/chain-to-pay.connections.json", "COPY infrastructure/containers/blockchain/config/chain-to-pay.connections.json"),
    ("COPY blockchain/chain-to-pay ", "COPY infrastructure/containers/blockchain/chain-to-pay "),
    ("COPY blockchain/verify_runtime.py", "COPY infrastructure/containers/blockchain/verify_runtime.py"),
    ("COPY blockchain/requirements.chain-to-pay.txt", "COPY infrastructure/containers/blockchain/requirements.chain-to-pay.txt"),
    ("COPY overlord/runtime/", "COPY infrastructure/containers/overlord/runtime/"),
    ("COPY admin/docker-compose.admin.yml", "COPY infrastructure/containers/admin/docker-compose.admin.yml"),
    ("COPY admin/config/", "COPY infrastructure/containers/admin/config/"),
    ("COPY admin/admin-system-gateway/", "COPY infrastructure/containers/admin/admin-system-gateway/"),
    ("COPY admin/params-registry/requirements.txt", "COPY infrastructure/containers/admin/requirements.txt"),
    ("COPY base/docker-compose.base.yml", "COPY infrastructure/containers/base/docker-compose.base.yml"),
    ("COPY base/requirements-minimal.txt", "COPY infrastructure/containers/base/requirements-minimal.txt"),
    ("COPY node/docker-compose.node-sessions.yml", "COPY infrastructure/containers/node/docker-compose.node-sessions.yml"),
    ("COPY node/docker-compose.node-data-system.yml", "COPY infrastructure/containers/node/docker-compose.node-data-system.yml"),
    ("COPY node/docker-compose.node-gui.yml", "COPY infrastructure/containers/node/docker-compose.node-gui.yml"),
    ("COPY node/node-system-gateway/", "COPY infrastructure/containers/node/node-system-gateway/"),
    ("COPY node/config/", "COPY infrastructure/containers/node/config/"),
    ("COPY auth/docker-compose.auth.yml", "COPY infrastructure/containers/auth/docker-compose.auth.yml"),
    (
        "COPY payment_systems/docker-compose.payment-internal.yml",
        "COPY infrastructure/containers/payment_systems/docker-compose.payment-internal.yml",
    ),
    (
        "COPY payment_systems/docker-compose.payment-externals.yml",
        "COPY infrastructure/containers/payment_systems/docker-compose.payment-externals.yml",
    ),
    ("COPY rdp/docker-compose.rdp-system.yml", "COPY infrastructure/containers/rdp/docker-compose.rdp-system.yml"),
    ("COPY server/docker-compose.server-external.yml", "COPY infrastructure/containers/server/docker-compose.server-external.yml"),
    ("COPY server/docker-compose.server-images.yml", "COPY infrastructure/containers/server/docker-compose.server-images.yml"),
    ("COPY storage/elasticsearch.yml", "COPY infrastructure/containers/storage/elasticsearch.yml"),
    ("COPY storage/mongod.conf", "COPY infrastructure/containers/storage/mongod.conf"),
    ("COPY storage/redis.conf", "COPY infrastructure/containers/storage/redis.conf"),
    (
        "COPY infrastructure/containers/blockchain/config/block-pay.yml ",
        "COPY infrastructure/containers/blockchain/config/block-pay-endpoints.yml ",
    ),
]


def fix_service_config_line(line: str) -> str:
    m = re.match(r"^(\s*COPY )service_configs/([^ ]+)(\s+.*)$", line.rstrip("\r\n"))
    if not m:
        return line
    base = m.group(2)
    if base not in SERVICE_CONFIG_MAP:
        return line
    return f"{m.group(1)}{SERVICE_CONFIG_MAP[base]}{m.group(3)}\n"


def process_file(path: str) -> bool:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    orig = text
    for old, new in TEXT_SUBSTITUTIONS:
        text = text.replace(old, new)
    lines_out: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("COPY service_configs/"):
            lines_out.append(fix_service_config_line(line))
        else:
            lines_out.append(line)
    text2 = "".join(lines_out)
    if text2 != orig:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text2)
        return True
    return False


def main() -> int:
    changed = 0
    for dp, _dns, fns in os.walk(IC):
        for fn in fns:
            if ".bak" in fn:
                continue
            if not re.match(r"(?i)^dockerfile", fn):
                continue
            path = os.path.join(dp, fn)
            if process_file(path):
                changed += 1
                print(f"updated: {os.path.relpath(path, ROOT)}")
    print(f"files_modified={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate cluster calibration YAMLs from host-config.yml + x-files-listing.txt.

Run from any working directory (uses __file__ location):

  Lucid\\.venv\\Scripts\\python.exe infrastructure\\containers\\_gen_x_lucid_cluster_calibration.py

Requires: PyYAML (pip install pyyaml).
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("ERROR: PyYAML is required. Install: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1) from e


def find_repo_root(start: Path) -> Path:
    """Walk upward from start until infrastructure/containers/host-config.yml exists."""
    cur = start.resolve()
    for _ in range(24):
        candidate = cur / "infrastructure" / "containers" / "host-config.yml"
        if candidate.is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise FileNotFoundError(
        "Could not find repo root (no infrastructure/containers/host-config.yml "
        f"walking up from {start.resolve()})"
    )


SCRIPT_PATH = Path(__file__).resolve()
ROOT = find_repo_root(SCRIPT_PATH.parent)
HOST_CONFIG = ROOT / "infrastructure" / "containers" / "host-config.yml"
X_FILES = ROOT / "x-files-listing.txt"
OUT_DIR = ROOT / "infrastructure" / "containers" / "services" / "x_lucid_cluster_calibration"

# Map com.lucid.cluster -> /app/<segment> prefixes from x-files-listing.txt (first segment after /app/).
CLUSTER_APP_PREFIXES: dict[str, tuple[str, ...]] = {
    "core": (
        "02_network_security",
        "03_api_gateway",
        "blockchain",
        "admin",
        "server",
        "api",
        "common",
        "sessions",
        "apps",
        "app",
    ),
    "foundation": (
        "02_network_security",
        "auth",
        "gui_tor_manager",
        "storage",
        "database",
    ),
    "processing": (
        "sessions",
        "03_api_gateway",
    ),
    "storage": (
        "storage",
        "sessions",
        "user_content",
    ),
    "application": (
        "node",
        "RDP",
        "vm",
        "apps",
        "server",
    ),
    "database": (
        "database",
    ),
    "payment": (
        "payment_systems",
        "wallet",
        "blockchain",
    ),
    "gui-integration": (
        "electron_gui",
        "gui",
        "gui_api_bridge",
        "gui_docker_manager",
        "gui_hardware_manager",
        "user",
    ),
    "monitoring": (
        "api",
        "tools",
        "RDP",
    ),
}


def load_host_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def cluster_for_service(service: dict) -> str | None:
    labels = service.get("labels") or {}
    return labels.get("com.lucid.cluster")


def parse_x_file_paths(path: Path) -> list[str]:
    out: list[str] = []
    rx = re.compile(r"x-lucid-file-path:\s*(\S+)")
    with path.open(encoding="utf-8") as f:
        for line in f:
            m = rx.search(line)
            if m:
                out.append(m.group(1))
    return out


def filter_paths_for_cluster(
    all_paths: list[str], prefixes: tuple[str, ...]
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for p in all_paths:
        if not p.startswith("/app/"):
            continue
        if "<" in p or ">" in p:
            continue
        rest = p[5:]
        seg = rest.split("/")[0] if rest else ""
        if seg in prefixes:
            if p not in seen:
                seen.add(p)
                ordered.append(p)
    return ordered


def emit_alignment_entry(key: str, svc: dict) -> dict:
    port = svc.get("port")
    return {
        "host_config_key": key,
        "service_name": svc.get("service_name"),
        "port": port,
        "host_ip": svc.get("host_ip"),
        "http_path": svc.get("http_path"),
    }


def main() -> int:
    print("x-lucid cluster calibration generator")
    print(f"  repo root: {ROOT}")
    print(f"  host-config: {HOST_CONFIG}")
    print(f"  x-files-listing: {X_FILES}")
    print(f"  output dir: {OUT_DIR}")

    if not X_FILES.is_file():
        print(f"ERROR: missing {X_FILES}", file=sys.stderr)
        return 1
    if not HOST_CONFIG.is_file():
        print(f"ERROR: missing {HOST_CONFIG}", file=sys.stderr)
        return 1

    data = load_host_config(HOST_CONFIG)
    services: dict[str, dict] = data.get("services") or {}
    if not services:
        print("ERROR: host-config.yml has no 'services' block.", file=sys.stderr)
        return 1

    by_cluster: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for key, svc in services.items():
        cl = cluster_for_service(svc)
        if cl:
            by_cluster[cl].append((key, svc))

    all_x_paths = parse_x_file_paths(X_FILES)
    if not all_x_paths:
        print(
            "ERROR: no x-lucid-file-path lines found in x-files-listing.txt.",
            file=sys.stderr,
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for cluster in sorted(by_cluster.keys()):
        prefixes = CLUSTER_APP_PREFIXES.get(cluster, ())
        if not prefixes:
            prefixes = tuple(sorted({p.split("/")[2] for p in all_x_paths if p.startswith("/app/")}))[:20]
        calibrated_paths = filter_paths_for_cluster(all_x_paths, prefixes)

        header_line = (
            f"Runtime (container): /app/service_configs/x_lucid_cluster_calibration/"
            f"{cluster}-cluster-host-alignment.yml"
        )
        doc: dict = {
            "x-lucid-calibration": {
                "cluster": cluster,
                "source_host_config": "infrastructure/containers/host-config.yml",
                "source_x_files_listing": "x-files-listing.txt",
                "description": (
                    f"Host registry + x-lucid file paths for {cluster} cluster "
                    "(merge with docker-compose fragments for this stack)."
                ),
            },
            "x-lucid-host-config": {
                "file": "../../host-config.yml",
                "repo_path": "infrastructure/containers/host-config.yml",
                "version": data.get("version", "1.0"),
                "description": data.get("description", ""),
                "ip_source_repo_path": data.get("ip_source", "service-ip.txt"),
                "http_path_template": "http://{service_name}:{port}/app",
                "host_ip_range": "172.20.10.1–172.20.10.76",
                "in_container_path": "/app/configs/host-config.yml",
            },
            "x-lucid-host-config-alignment": {
                "registry_path": "/app/configs/host-config.yml",
                "http_path_template": "http://{service_name}:{port}/app",
                "host_ip_range": "172.20.10.1–172.20.10.76",
                "entries": {
                    k: emit_alignment_entry(k, svc) for k, svc in sorted(by_cluster[cluster])
                },
            },
            "x-lucid-x-files-calibration": {
                "cluster": cluster,
                "filter_app_prefixes": list(prefixes),
                "x_lucid_file_paths": calibrated_paths,
            },
        }

        out_path = OUT_DIR / f"{cluster}-cluster-host-alignment.yml"
        body = yaml.dump(
            doc,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        text = (
            f"# {header_line}\n"
            f"# Canonical {cluster} cluster alignment: host-config.yml + x-files-listing.txt "
            f"(merge with docker-compose for this stack).\n"
            f"{body}"
        )
        out_path.write_text(text, encoding="utf-8")
        written.append(out_path)
        print(
            f"  OK {out_path.name}: services={len(by_cluster[cluster])} "
            f"x_paths={len(calibrated_paths)}"
        )

    print(f"Done. Wrote {len(written)} file(s) under {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

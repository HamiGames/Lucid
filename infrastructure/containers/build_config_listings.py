# Full path: infrastructure/containers/build_config_listings.py
#
# Merges host-config.yml, service_id-list.json, ports.txt (tags), and service-ip.txt
# into one JSON document keyed by stable service id (host registry key).
#
# Run from repository root (Lucid):
#   python infrastructure/containers/build_config_listings.py
#   python infrastructure/containers/build_config_listings.py -o infrastructure/containers/config-listings.json
#
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTAINERS = ROOT / "infrastructure" / "containers"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import _gen_host_config as ghc  # noqa: E402


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    text = ghc.read_text_robust(path)
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def lookup_service_ids(sid_data: dict[str, Any], dockerfile_path: str) -> dict[str, Any] | None:
    if not dockerfile_path:
        return None
    norm = dockerfile_path.replace("\\", "/")
    if norm in sid_data:
        block = sid_data[norm]
        return block if isinstance(block, dict) else None
    low = norm.lower()
    for k, v in sid_data.items():
        if isinstance(k, str) and k.replace("\\", "/").lower() == low:
            return v if isinstance(v, dict) else None
    return None


def build_listings() -> dict[str, Any]:
    hc_path = CONTAINERS / "host-config.yml"
    sid_path = CONTAINERS / "service_id-list.json"
    out_ports = ghc.ports_path
    ip_path = ghc.service_ip_path

    hc = load_yaml_mapping(hc_path)
    host_services = hc.get("services") or {}
    if not isinstance(host_services, dict):
        host_services = {}

    sid_raw = sid_path.read_bytes()
    if len(sid_raw) >= 2 and sid_raw[0:2] in (b"\xff\xfe", b"\xfe\xff"):
        sid_text = sid_raw.decode("utf-16")
    else:
        sid_text = sid_raw.decode("utf-8-sig")
    sid_data = json.loads(sid_text)
    if not isinstance(sid_data, dict):
        sid_data = {}

    service_ips = ghc.load_service_ips(ip_path)
    ports_services = ghc.load_services_map(out_ports, verbose=False)
    ports_tags: dict[str, list[Any]] = {}
    for sid, row in ports_services.items():
        if not isinstance(row, dict):
            continue
        tags = row.get("tags")
        ports_tags[sid] = list(tags) if isinstance(tags, list) else []

    hc_dockerfile_paths: set[str] = set()
    services_out: dict[str, Any] = {}
    by_dns: dict[str, str] = {}

    for stable_id, row in host_services.items():
        if not isinstance(row, dict):
            continue
        dns = str(row.get("service_name") or "").strip()
        if dns:
            by_dns[dns] = stable_id
        src_df = row.get("source_dockerfile")
        src_norm = str(src_df).replace("\\", "/").strip() if src_df else ""
        if src_norm:
            hc_dockerfile_paths.add(src_norm)

        ids_block = lookup_service_ids(sid_data, src_norm)
        host_ip = row.get("host_ip") or service_ips.get(stable_id)

        services_out[stable_id] = {
            "stable_id": stable_id,
            "service_name": row.get("service_name"),
            "port": row.get("port"),
            "http_path": row.get("http_path"),
            "host_ip": host_ip,
            "source_dockerfile": src_norm or None,
            "host_config_labels": row.get("labels"),
            "tags_from_ports_txt": ports_tags.get(stable_id, []),
            "service_ids": ids_block,
        }

    sid_keys_containers = [
        k for k in sid_data if isinstance(k, str) and k.startswith("infrastructure/containers/")
    ]
    not_linked = sorted(k for k in sid_keys_containers if k not in hc_dockerfile_paths)

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "host_config": hc_path.relative_to(ROOT).as_posix(),
            "service_id_list": sid_path.relative_to(ROOT).as_posix(),
            "ports_txt": out_ports.relative_to(ROOT).as_posix(),
            "service_ip_txt": ip_path.relative_to(ROOT).as_posix(),
        },
        "notes": [
            "Each entry is keyed by stable_id (host registry / ports.txt service key).",
            "service_name is the Docker DNS hostname (kebab-case).",
            "tags_from_ports_txt come from merged ports.txt (dockerfile_services or services block).",
            "service_ids are com/onion/org Lucid Dockerfile identifiers when source_dockerfile matches service_id-list.json.",
            "host_ip is from host-config when present, else service-ip.txt for that stable_id.",
            "infrastructure/containers paths in service_id-list.json with no host-config source_dockerfile are listed under unlinked.",
        ],
        "services": services_out,
        "by_docker_dns_service_name": by_dns,
        "unlinked": {
            "service_id_list_paths_under_infrastructure_containers_not_in_host_config": not_linked,
            "count": len(not_linked),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build config-listings.json from host-config, service_id-list, ports.txt, service-ip.txt.",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=CONTAINERS / "config-listings.json",
        help="Output JSON path (default: infrastructure/containers/config-listings.json)",
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="Write JSON to stdout instead of a file",
    )
    args = ap.parse_args()
    doc = build_listings()
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        sys.stdout.write(text)
        return 0
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT)} ({len(doc['services'])} services)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

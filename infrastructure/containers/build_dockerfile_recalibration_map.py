# Merge service_id-list.json + ports.txt + x-files.json into one config map for Dockerfile recalibration.
#
# Full path: infrastructure/containers/build_dockerfile_recalibration_map.py
#
# Run from repo root (Lucid):
#   python infrastructure/containers/build_dockerfile_recalibration_map.py
#   python infrastructure/containers/build_dockerfile_recalibration_map.py -o infrastructure/containers/dockerfile_recalibration_map.json
#
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTAINERS = Path(__file__).resolve().parent

# So we can import sibling module when run as a script
if str(CONTAINERS) not in sys.path:
    sys.path.insert(0, str(CONTAINERS))

import _sync_dockerfile_lucid_env as lucid_sync  # noqa: E402

DEFAULT_SERVICE_IDS = CONTAINERS / "service_id-list.json"
DEFAULT_PORTS = ROOT / "ports.txt"
DEFAULT_X_FILES = ROOT / "x-files.json"
DEFAULT_OUT = CONTAINERS / "dockerfile_recalibration_map.json"

# Repo-relative Dockerfile paths that are NOT under infrastructure/containers/ but still
# map to a ports.txt service key. Extend this table as you wire more images.
PORTS_KEY_BY_REPO_PATH: dict[str, str] = {
    "02_network_security/tor/Dockerfile.tor-proxy": "tor_socks",
    "02_network_security/tor/Dockerfile.tor-proxy-02": "tor_socks",
    "02_network_security/tor/Dockerfile.tunnels": "tunnel_tools",
    "02_network_security/tunnels/Dockerfile": "tunnel_tools",
    "02_network_security/tunnels/Dockerfile.tunnels": "tunnel_tools",
}


def _norm_repo_path(s: str) -> str:
    return s.replace("\\", "/")


def _containers_rel_and_basename(repo_path: str) -> tuple[str | None, str]:
    p = _norm_repo_path(repo_path)
    prefix = "infrastructure/containers/"
    base = Path(p).name
    if p.startswith(prefix):
        return p[len(prefix) :], base
    return None, base


def _read_json_file(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) >= 2 and raw[0:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise SystemExit(f"error: expected JSON object in {path}")
    return data


def _rel_to_repo(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def resolve_ports_service_key(repo_path: str) -> str | None:
    if repo_path in PORTS_KEY_BY_REPO_PATH:
        return PORTS_KEY_BY_REPO_PATH[repo_path]
    rel, name = _containers_rel_and_basename(repo_path)
    if rel is None:
        return None
    return lucid_sync.service_key_from_dockerfile(rel, name)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build merged Dockerfile recalibration map (service IDs + ports + canonical paths)."
    )
    ap.add_argument("--service-ids", type=Path, default=DEFAULT_SERVICE_IDS)
    ap.add_argument("--ports", type=Path, default=DEFAULT_PORTS)
    ap.add_argument("--x-files", type=Path, default=DEFAULT_X_FILES)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sid_path: Path = args.service_ids.resolve()
    ports_path: Path = args.ports.resolve()
    xfiles_path: Path = args.x_files.resolve()
    out_path: Path = args.output.resolve()

    if not sid_path.is_file():
        print(f"error: service ids file not found: {sid_path}", file=sys.stderr)
        return 1
    if not ports_path.is_file():
        print(f"error: ports file not found: {ports_path}", file=sys.stderr)
        return 1
    if not xfiles_path.is_file():
        print(f"error: x-files not found: {xfiles_path}", file=sys.stderr)
        return 1

    service_ids = _read_json_file(sid_path)
    xdata = _read_json_file(xfiles_path)
    section_map = xdata.get("section_to_canonical") or {}
    if not isinstance(section_map, dict):
        print("error: x-files.json missing dict section_to_canonical", file=sys.stderr)
        return 1

    ports_services = lucid_sync.load_ports_services()

    dockerfiles: dict[str, dict] = {}
    stats: dict[str, int] = {
        "with_canonical": 0,
        "with_ports_key": 0,
        "with_ports_row": 0,
        "total_dockerfiles": 0,
    }

    for repo_path in sorted(service_ids.keys(), key=lambda x: x.lower()):
        ids = service_ids[repo_path]
        canon = section_map.get(repo_path)
        if isinstance(canon, str):
            stats["with_canonical"] += 1
        ports_key = resolve_ports_service_key(repo_path)
        if ports_key:
            stats["with_ports_key"] += 1
        ports_row = ports_services.get(ports_key) if ports_key else None
        if ports_row:
            stats["with_ports_row"] += 1

        rel_ic, basename = _containers_rel_and_basename(repo_path)
        dockerfiles[repo_path] = {
            "basename": basename,
            "infrastructure_containers_rel": rel_ic,
            "canonical_path": canon if isinstance(canon, str) else None,
            "in_x_files": repo_path in section_map,
            "lucid_service_ids": {
                "com_lucid_service_id": ids.get("com_lucid_service_id"),
                "onion_lucid_service_id": ids.get("onion_lucid_service_id"),
                "org_lucid_service_id": ids.get("org_lucid_service_id"),
            },
            "ports_service_key": ports_key,
            "ports": ports_row,
        }

    stats["total_dockerfiles"] = len(dockerfiles)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "service_ids": _rel_to_repo(sid_path),
            "ports": _rel_to_repo(ports_path),
            "x_files": _rel_to_repo(xfiles_path),
        },
        "stats": dict(stats),
        "dockerfiles": dockerfiles,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {out_path}")
    print(
        f"stats: total={stats['total_dockerfiles']} "
        f"canonical={stats['with_canonical']} "
        f"ports_key={stats['with_ports_key']} "
        f"ports_row={stats['with_ports_row']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

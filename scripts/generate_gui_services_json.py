#!/usr/bin/env python3
"""
File: scripts/generate_gui_services_json.py
Path (repo): Lucid/scripts/generate_gui_services_json.py

Build a JSON manifest of Lucid GUI stack services from Docker Compose files.
Services are included when their labels contain com.lucid.phase=gui (same
marking used in configs/docker/docker-compose.gui-integration.yml).

Default input: configs/docker/docker-compose.gui-integration.yml
Default output: configs/services/gui-services.json

Usage (repo root, PowerShell or bash):
  python scripts/generate_gui_services_json.py
  python scripts/generate_gui_services_json.py -o configs/services/gui-services.json
  python scripts/generate_gui_services_json.py --scan-gui-compose
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


PHASE_LABEL = "com.lucid.phase"
GUI_PHASE = "gui"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_labels(raw: Any) -> Dict[str, str]:
    if not raw:
        return {}
    out: Dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            out[str(k)] = str(v)
        return out
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, str) or "=" not in item:
            continue
        key, _, val = item.partition("=")
        out[key.strip()] = val.strip()
    return out


def _is_gui_service(labels: Dict[str, str]) -> bool:
    return labels.get(PHASE_LABEL) == GUI_PHASE


def _norm_ports(ports: Any) -> List[str]:
    if ports is None:
        return []
    if isinstance(ports, list):
        return [str(p) for p in ports]
    return [str(ports)]


def _dedupe_key(row: Dict[str, Any]) -> str:
    cn = row.get("container_name")
    if isinstance(cn, str) and cn.strip():
        return cn.strip()
    ck = row.get("compose_service") or ""
    return f"{ck}::{row.get('image', '')}"


def _extract_gui_services_from_compose(
    data: Dict[str, Any], compose_path: Path, repo_root: Path
) -> List[Dict[str, Any]]:
    services = data.get("services") or {}
    if not isinstance(services, dict):
        return []
    rel = str(compose_path.relative_to(repo_root)).replace("\\", "/")
    rows: List[Dict[str, Any]] = []
    for compose_key, spec in services.items():
        if not isinstance(spec, dict):
            continue
        labels = _parse_labels(spec.get("labels"))
        if not _is_gui_service(labels):
            continue
        rows.append(
            {
                "compose_service": compose_key,
                "container_name": spec.get("container_name"),
                "lucid_service": labels.get("com.lucid.service"),
                "cluster": labels.get("com.lucid.cluster"),
                "phase": labels.get(PHASE_LABEL),
                "profile": labels.get("com.lucid.profile"),
                "image": spec.get("image"),
                "ports": _norm_ports(spec.get("ports")),
                "compose_file": rel,
            }
        )
    return rows


def _load_compose(path: Path) -> Dict[str, Any]:
    if yaml is None:
        print(
            "error: PyYAML is required. Install with: pip install pyyaml",
            file=sys.stderr,
        )
        sys.exit(2)
    text = path.read_text(encoding="utf-8", errors="replace")
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _discover_gui_compose_files(repo_root: Path) -> List[Path]:
    patterns = ("**/docker-compose*gui*.yml", "**/docker-compose*gui*.yaml")
    seen: Set[Path] = set()
    out: List[Path] = []
    for pattern in patterns:
        for p in repo_root.glob(pattern):
            if not p.is_file():
                continue
            parts = {x.lower() for x in p.parts}
            if "node_modules" in parts or ".git" in parts:
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            out.append(rp)
    out.sort(key=lambda x: str(x).lower())
    return out


def _merge_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in rows:
        key = _dedupe_key(row)
        if key not in by_key:
            by_key[key] = {**row, "compose_files": [row["compose_file"]]}
            order.append(key)
            del by_key[key]["compose_file"]
        else:
            existing = by_key[key]
            cf = existing.setdefault("compose_files", [])
            f = row["compose_file"]
            if f not in cf:
                cf.append(f)
    return [by_key[k] for k in order]


def main() -> int:
    root = _repo_root()
    default_compose = root / "configs" / "docker" / "docker-compose.gui-integration.yml"
    default_out = root / "configs" / "services" / "gui-services.json"

    ap = argparse.ArgumentParser(
        description="Generate gui-services.json from Docker Compose GUI labels."
    )
    ap.add_argument(
        "--compose",
        action="append",
        type=Path,
        metavar="PATH",
        help="Compose file to read (repeatable). Default: configs/docker/docker-compose.gui-integration.yml",
    )
    ap.add_argument(
        "--scan-gui-compose",
        action="store_true",
        help="Also scan repo for **/docker-compose*gui*.yml|yaml and merge (dedupe by container_name).",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"Output JSON path (default: {default_out})",
    )
    args = ap.parse_args()

    compose_paths: List[Path] = []
    if args.compose:
        compose_paths.extend(Path(p).resolve() for p in args.compose)
    else:
        compose_paths.append(default_compose.resolve())

    if args.scan_gui_compose:
        extra = _discover_gui_compose_files(root)
        for p in extra:
            if p not in compose_paths:
                compose_paths.append(p)

    all_rows: List[Dict[str, Any]] = []
    sources: List[str] = []
    for cp in compose_paths:
        if not cp.is_file():
            print(f"error: compose file not found: {cp}", file=sys.stderr)
            return 1
        sources.append(str(cp.relative_to(root)).replace("\\", "/"))
        data = _load_compose(cp)
        all_rows.extend(_extract_gui_services_from_compose(data, cp, root))

    merged = _merge_rows(all_rows)
    merged.sort(key=lambda r: (r.get("compose_service") or ""))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "phase_filter": GUI_PHASE,
        "sources": sources,
        "service_count": len(merged),
        "services": merged,
    }

    out_path: Path = args.output.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(merged)} service(s) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

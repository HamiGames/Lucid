#!/usr/bin/env python3
# Path: scripts/gui_auth_realignment/generate_gui_service_source_map.py
#
# Builds/extends the alignment source map (default: configs/alignment-mats/service_source_map.json)
# for list_service_files_by_name.py → *_manifest.json → rewrite_dockerfiles_from_alignment_mats.py.
# Merges compose names from a mat (default gui-services.json) plus optional service_names.txt,
# preserves existing rich entries, and adds stub entries with optional service bundle yml under
# infrastructure/containers/services/**/.
#
# If the output file does not exist yet, entries are seeded from scripts/gui_auth_realignment/
# gui_service_source_map.json when present (GUI-curated rows), then extended for all service names.
#
# This is NOT dockerfile_recalibration_map.json (see build_dockerfile_recalibration_map.py + fixed ports.txt read).

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_HERE = Path(__file__).resolve().parent
DEFAULT_MAT = Path("configs/services/gui-services.json")
DEFAULT_NAMES_FILE = Path("configs/alignment-mats/service_names.txt")
# Full-stack map for alignment manifests (not GUI-only).
DEFAULT_OUT = Path("configs/alignment-mats/service_source_map.json")
GUI_SEED_MAP = _HERE / "gui_service_source_map.json"


def _repo_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_compose_from_mat(mat: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for row in mat.get("services") or []:
        if isinstance(row, dict):
            n = str(row.get("compose_service") or "").strip()
            if n:
                out.append(n)
    return out


def _load_names_file(path: Path) -> List[str]:
    if not path.is_file():
        return []
    out: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def _find_services_bundle_rel(repo: Path, compose_service: str) -> Optional[str]:
    """First matching bundle: flat or any subdir under infrastructure/containers/services."""
    for suffix in (".yml", ".yaml"):
        flat = repo / f"infrastructure/containers/services/{compose_service}{suffix}"
        if flat.is_file():
            try:
                return flat.relative_to(repo).as_posix()
            except ValueError:
                return None
    root = repo / "infrastructure/containers/services"
    if not root.is_dir():
        return None
    for suffix in (".yml", ".yaml"):
        name = f"{compose_service}{suffix}"
        found: List[Path] = []
        for p in root.rglob(name):
            if p.is_file() and p.name == name:
                found.append(p)
        if len(found) == 1:
            try:
                return found[0].relative_to(repo).as_posix()
            except ValueError:
                return None
        if len(found) > 1:
            found.sort(key=lambda x: len(x.as_posix()))
            try:
                return found[0].relative_to(repo).as_posix()
            except ValueError:
                return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build/extend configs/alignment-mats/service_source_map.json (all alignment services): "
            "python_dirs/yml_extra stubs + optional services bundle path; seeds from "
            "gui_service_source_map.json when the output file is missing."
        )
    )
    ap.add_argument("--repo-root", default=None)
    ap.add_argument(
        "--mat",
        type=Path,
        default=DEFAULT_MAT,
        help="JSON mat with services[].compose_service (default: configs/services/gui-services.json)",
    )
    ap.add_argument(
        "--services-from",
        type=Path,
        default=DEFAULT_NAMES_FILE,
        help="Extra names, one per line (default: configs/alignment-mats/service_names.txt); omit file with --no-services-from",
    )
    ap.add_argument(
        "--no-services-from",
        action="store_true",
        help="Do not read --services-from file",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "Output JSON path (default: configs/alignment-mats/service_source_map.json). "
            "Legacy GUI-only path: scripts/gui_auth_realignment/gui_service_source_map.json"
        ),
    )
    ap.add_argument(
        "--no-bundle-yml",
        action="store_true",
        help="Do not auto-append infrastructure/containers/services/**/{service}.yml to yml_extra for new stubs",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not write",
    )
    args = ap.parse_args()

    repo = _repo_root(args.repo_root)
    mat_path = args.mat
    if not mat_path.is_absolute():
        mat_path = repo / mat_path

    mat = _load_json(mat_path)
    if not isinstance(mat, dict):
        print(f"error: invalid or missing mat: {mat_path}", file=sys.stderr)
        return 2

    names: List[str] = []
    seen: Set[str] = set()
    for n in _collect_compose_from_mat(mat):
        k = n.casefold()
        if k not in seen:
            seen.add(k)
            names.append(n)
    if not args.no_services_from:
        sf = args.services_from
        if not sf.is_absolute():
            sf = repo / sf
        for n in _load_names_file(sf):
            k = n.casefold()
            if k not in seen:
                seen.add(k)
                names.append(n)

    names.sort(key=lambda x: x.casefold())

    out_path = args.out
    if not out_path.is_absolute():
        out_path = repo / out_path

    existing = _load_json(out_path)
    if isinstance(existing, dict) and isinstance(existing.get("services"), dict):
        doc = {
            "schema_version": int(existing.get("schema_version") or 1),
            "description": str(
                existing.get("description")
                or (
                    "Maps compose_service names to Python trees and extra YAML (full alignment mat set). "
                    "Generated/extended by generate_gui_service_source_map.py; edit rich entries by hand."
                )
            ),
            "global_python_files": list(
                existing.get("global_python_files")
                or ["common/load_host_config.py"]
            ),
            "services": dict(existing["services"]),
        }
    else:
        seed = _load_json(GUI_SEED_MAP)
        if isinstance(seed, dict) and isinstance(seed.get("services"), dict):
            doc = {
                "schema_version": int(seed.get("schema_version") or 1),
                "description": str(
                    seed.get("description")
                    or (
                        "Maps compose_service names to Python trees and extra YAML (full alignment mat set). "
                        "Seeded from gui_service_source_map.json; extended by generate_gui_service_source_map.py."
                    )
                ),
                "global_python_files": list(
                    seed.get("global_python_files") or ["common/load_host_config.py"]
                ),
                "services": dict(seed["services"]),
            }
        else:
            doc = {
                "schema_version": 1,
                "description": "Maps compose_service names to Python trees and extra YAML.",
                "global_python_files": ["common/load_host_config.py"],
                "services": {},
            }

    services: Dict[str, Any] = doc["services"]
    added = 0
    updated_bundle = 0
    for name in names:
        bundle = None if args.no_bundle_yml else _find_services_bundle_rel(repo, name)
        if name in services:
            if bundle and bundle not in (services[name].get("yml_extra") or []):
                if args.dry_run:
                    updated_bundle += 1
                    continue
                reg = dict(services[name])
                ye = list(reg.get("yml_extra") or [])
                if bundle not in ye:
                    ye.append(bundle)
                    reg["yml_extra"] = ye
                    services[name] = reg
                    updated_bundle += 1
            continue
        yml_extra: List[str] = []
        if bundle:
            yml_extra.append(bundle)
        if args.dry_run:
            added += 1
            continue
        services[name] = {"python_dirs": [], "yml_extra": yml_extra}
        added += 1

    if args.dry_run:
        print(
            f"dry-run: would add {added} new service(s), "
            f"append bundle to yml_extra on {updated_bundle} existing (of {len(names)} names)."
        )
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    try:
        disp = out_path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        disp = str(out_path)
    print(f"wrote {disp}")
    print(f"  services keys: {len(services)} (added {added} new, bundle-yml updates {updated_bundle})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

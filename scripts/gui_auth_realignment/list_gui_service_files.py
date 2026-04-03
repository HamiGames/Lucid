#!/usr/bin/env python3
"""
File: scripts/gui_auth_realignment/list_gui_service_files.py

Lists *.yml, *.yaml, *.json, and *.py files associated with each compose_service in a gui-services mat
(default: configs/services/gui-services.json).

Sources merged per service:
  - compose_files[] from the mat row
  - python_dirs + yml_extra from gui_service_source_map.json
  - global_python_files from gui_service_source_map.json
  - configs/gui-alignment/*.json from tier_a_json_targets.json (--json-manifests)
  - Optional repo scan (--discover-associated): YAML/JSON under configs/, infrastructure/containers,
    infrastructure/service_mesh, and each service python_dirs that contain service name tokens
    (hyphen/underscore/container_name), including compose files, endpoint YAML, and support JSON.

``missing_expected`` lists conventional paths (alignment JSON, infrastructure/services/<service>.yml)
that are absent. ``missing_tier_a_json`` lists tier allowlist JSON paths that are missing on disk.

Usage (repo root):
  python scripts/gui_auth_realignment/list_gui_service_files.py
  python scripts/gui_auth_realignment/list_gui_service_files.py --service gui-api-bridge
  python scripts/gui_auth_realignment/list_gui_service_files.py --format json --out .cache/gui_service_files.json
  python scripts/gui_auth_realignment/list_gui_service_files.py \\
      --service gui-docker-manager --manifest-dir configs/alignment-mats/ \\
      --manifest-suffix _manifest.json --json-manifests
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

DEFAULT_MAT = Path("configs/services/gui-services.json")
MAP_PATH = _HERE / "gui_service_source_map.json"
TIER_A_TARGETS = _HERE / "tier_a_json_targets.json"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        "target",
    }
)
DEFAULT_DISCOVERY_ROOTS = (
    "configs",
    "infrastructure/containers",
    "infrastructure/service_mesh",
)
DEFAULT_DISCOVER_MAX_BYTES = 2_000_000
MIN_NEEDLE_LEN = 6


def _repo_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_py_under(repo: Path, rel_dir: str) -> Tuple[List[Path], List[str]]:
    root = repo / rel_dir
    out: List[Path] = []
    missing: List[str] = []
    if not root.is_dir():
        missing.append(rel_dir)
        return out, missing
    for p in root.rglob("*.py"):
        if "node_modules" in p.parts:
            continue
        out.append(p)
    out.sort(key=lambda x: x.as_posix().lower())
    return out, missing


def _collect_yml(repo: Path, paths: List[str]) -> Tuple[List[str], List[str]]:
    ok: List[str] = []
    missing: List[str] = []
    for rel in paths:
        p = repo / rel
        if p.is_file() and p.suffix.lower() in (".yml", ".yaml"):
            ok.append(rel.replace("\\", "/"))
        else:
            missing.append(rel)
    ok = sorted(set(ok))
    return ok, missing


def _collect_global_py(repo: Path, rels: List[str]) -> Tuple[List[str], List[str]]:
    ok: List[str] = []
    missing: List[str] = []
    for rel in rels:
        p = repo / rel
        if p.is_file():
            ok.append(rel.replace("\\", "/"))
        else:
            missing.append(rel)
    return sorted(set(ok)), missing


def _service_needles(compose_service: str, row: Dict[str, Any]) -> List[str]:
    raw: Set[str] = {compose_service.replace("\\", "/").strip()}
    for key in ("container_name", "lucid_service"):
        v = row.get(key)
        if v:
            raw.add(str(v).strip())
    if "-" in compose_service:
        raw.add(compose_service.replace("-", "_"))
    needles = sorted({n for n in raw if len(n) >= MIN_NEEDLE_LEN}, key=len, reverse=True)
    if compose_service not in needles and compose_service.strip():
        needles.append(compose_service.strip())
    return needles


def _discovery_roots_for_service(repo: Path, py_dirs: List[str]) -> List[Path]:
    seen: Set[str] = set()
    roots: List[Path] = []
    for rel in DEFAULT_DISCOVERY_ROOTS:
        key = rel.replace("\\", "/")
        if key in seen:
            continue
        p = repo / key
        if p.is_dir():
            seen.add(key)
            roots.append(p)
    for d in py_dirs:
        key = d.replace("\\", "/")
        if key in seen:
            continue
        p = repo / key
        if p.is_dir():
            seen.add(key)
            roots.append(p)
    return roots


def _should_skip_path(p: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in p.parts)


def _read_text_limited(path: Path, max_bytes: int) -> str | None:
    try:
        data = path.read_bytes()[:max_bytes]
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def _text_matches_any_needle(text: str, needles: List[str]) -> bool:
    tl = text.casefold()
    for n in needles:
        if n.casefold() in tl:
            return True
    return False


def _discover_yml_json(
    repo: Path,
    roots: List[Path],
    needles: List[str],
    max_bytes: int,
) -> Tuple[Set[str], Set[str]]:
    yml_out: Set[str] = set()
    json_out: Set[str] = set()
    patterns = ("*.yml", "*.yaml", "*.json")
    seen_resolved: Set[Path] = set()
    repo_resolved = repo.resolve()
    for root in roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            try:
                for p in root.rglob(pat):
                    if _should_skip_path(p) or not p.is_file():
                        continue
                    try:
                        if p.stat().st_size > max_bytes * 2:
                            continue
                    except OSError:
                        continue
                    rp = p.resolve()
                    if rp in seen_resolved:
                        continue
                    seen_resolved.add(rp)
                    txt = _read_text_limited(p, max_bytes)
                    if txt is None or not _text_matches_any_needle(txt, needles):
                        continue
                    try:
                        rel = rp.relative_to(repo_resolved).as_posix()
                    except ValueError:
                        continue
                    if rel.startswith("configs/alignment-mats/") and rel.endswith(".json"):
                        continue
                    suf = p.suffix.lower()
                    if suf in (".yml", ".yaml"):
                        yml_out.add(rel)
                    elif suf == ".json":
                        json_out.add(rel)
            except OSError:
                continue
    return yml_out, json_out


def _expected_path_gaps(repo: Path, compose_service: str, tier_json_rels: List[str]) -> Tuple[List[str], List[str]]:
    miss_exp: List[str] = []
    miss_tier: List[str] = []
    conventional = [
        f"configs/gui-alignment/{compose_service}.json",
        f"infrastructure/containers/services/{compose_service}.yml",
    ]
    for rel in conventional:
        if not (repo / rel).is_file():
            miss_exp.append(rel)
    for rel in tier_json_rels:
        r = rel.replace("\\", "/")
        if not (repo / r).is_file():
            miss_tier.append(r)
    return miss_exp, miss_tier


def main() -> int:
    ap = argparse.ArgumentParser(
        description="List .yml / .yaml / .json / .py per gui-services mat entry; optional repo discovery."
    )
    ap.add_argument("--repo-root", default=None, help="Repository root")
    ap.add_argument(
        "--mat",
        default=str(DEFAULT_MAT),
        help="Path to gui-services.json (repo-relative or absolute)",
    )
    ap.add_argument("--service", default=None, help="Only this compose_service (e.g. gui-api-bridge)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--out", default=None, help="Write JSON output to this path (repo-relative)")
    ap.add_argument(
        "--json-manifests",
        action="store_true",
        help="Include Tier A alignment JSON paths from tier_a_json_targets.json in output",
    )
    ap.add_argument(
        "--manifest-dir",
        default=None,
        help="Write one JSON file per service here (repo-relative or absolute): "
        "<compose_service>.service-files.json",
    )
    ap.add_argument(
        "--manifest-suffix",
        default=".service-files.json",
        help="Appended after compose_service (default: .service-files.json -> gui-api-bridge.service-files.json)",
    )
    ap.add_argument(
        "--discover-associated",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Scan YAML/JSON under configs/, infrastructure/containers/, infrastructure/service_mesh/, "
            "and each service python_dir for name tokens (compose_service, container_name, underscore form). "
            "Default: on. Use --no-discover-associated for declared paths only."
        ),
    )
    ap.add_argument(
        "--discover-max-bytes",
        type=int,
        default=DEFAULT_DISCOVER_MAX_BYTES,
        help="Max bytes read per file for discovery (default: 2000000).",
    )
    args = ap.parse_args()
    repo = _repo_root(args.repo_root)

    mat_path = Path(args.mat)
    if not mat_path.is_absolute():
        mat_path = repo / mat_path
    mat = _load_json(mat_path)
    if not isinstance(mat, dict):
        print(f"Invalid or missing mat: {mat_path}", file=sys.stderr)
        return 2

    svc_rows = mat.get("services")
    if not isinstance(svc_rows, list):
        print("mat.services must be a list", file=sys.stderr)
        return 2

    mp = _load_json(MAP_PATH)
    if not isinstance(mp, dict):
        print(f"Invalid or missing map: {MAP_PATH}", file=sys.stderr)
        return 2
    smap = mp.get("services") or {}
    global_py = list(mp.get("global_python_files") or [])

    tier_targets: Dict[str, List[str]] = {}
    tj = _load_json(_HERE / "tier_a_json_targets.json")
    if isinstance(tj, dict):
        tier_targets = {str(k): list(v or []) for k, v in (tj.get("targets") or {}).items()}

    result: Dict[str, Any] = {}
    for row in svc_rows:
        if not isinstance(row, dict):
            continue
        name = row.get("compose_service")
        if not name:
            continue
        if args.service and name != args.service:
            continue

        compose_files = [str(x).replace("\\", "/") for x in (row.get("compose_files") or [])]
        reg = smap.get(name) or {}
        py_dirs = list(reg.get("python_dirs") or [])
        yml_extra = [str(x).replace("\\", "/") for x in (reg.get("yml_extra") or [])]

        yml_paths = compose_files + yml_extra
        yml_declared, yml_missing = _collect_yml(repo, yml_paths)

        needles = _service_needles(name, row)
        tier_rels = [str(x).replace("\\", "/") for x in (tier_targets.get(name) or [])]
        yml_from_scan: Set[str] = set()
        json_from_scan: Set[str] = set()
        if args.discover_associated and needles:
            d_roots = _discovery_roots_for_service(repo, py_dirs)
            yml_from_scan, json_from_scan = _discover_yml_json(
                repo, d_roots, needles, args.discover_max_bytes
            )

        yml_resolved = sorted(set(yml_declared) | yml_from_scan)
        miss_exp, miss_tier = _expected_path_gaps(repo, name, tier_rels)

        py_rel: List[str] = []
        py_missing_dirs: List[str] = []
        for d in py_dirs:
            found, miss = _iter_py_under(repo, d)
            py_missing_dirs.extend(miss)
            py_rel.extend(p.relative_to(repo).as_posix() for p in found)

        globs, g_miss = _collect_global_py(repo, global_py)
        py_rel.extend(globs)
        py_missing_dirs = sorted(set(py_missing_dirs))
        py_rel = sorted(set(py_rel))

        manifests: List[str] = []
        if args.json_manifests and name in tier_targets:
            for rel in tier_targets[name]:
                p = repo / rel
                if p.is_file():
                    manifests.append(rel.replace("\\", "/"))

        json_support = sorted(set(json_from_scan) | set(manifests))

        result[name] = {
            "compose_service": name,
            "yml": yml_resolved,
            "py": py_rel,
            "json": json_support,
            "associated_needles": needles,
            "missing_yml": sorted(set(yml_missing)),
            "missing_python_dirs": py_missing_dirs,
            "missing_global_py": g_miss,
            "missing_expected": miss_exp,
            "missing_tier_a_json": miss_tier,
        }
        if args.json_manifests:
            result[name]["alignment_json"] = manifests

    try:
        mat_display = mat_path.relative_to(repo).as_posix()
    except ValueError:
        mat_display = str(mat_path)

    if args.manifest_dir:
        md = Path(args.manifest_dir)
        if not md.is_absolute():
            md = repo / md
        md.mkdir(parents=True, exist_ok=True)
        suffix = args.manifest_suffix
        for svc_name, payload in sorted(result.items()):
            safe = svc_name.replace("/", "_").replace("\\", "_")
            mf_path = md / f"{safe}{suffix}"
            doc: Dict[str, Any] = {
                "schema_version": 1,
                "tool": "scripts/gui_auth_realignment/list_gui_service_files.py",
                "mat_path": mat_display,
                **payload,
            }
            mf_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(result)} service manifest(s) under {md}", flush=True)

    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = repo / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}", flush=True)

    if args.format == "json":
        print(json.dumps(result, indent=2))
        return 0

    for svc, payload in sorted(result.items()):
        print(f"## {svc}")
        print("  yaml:")
        for p in payload["yml"]:
            print(f"    {p}")
        if payload.get("json"):
            print("  json:")
            for p in payload["json"]:
                print(f"    {p}")
        print("  py:")
        for p in payload["py"]:
            print(f"    {p}")
        if payload.get("associated_needles"):
            print("  associated_needles:", ", ".join(payload["associated_needles"]))
        if payload.get("alignment_json"):
            print("  alignment_json:")
            for p in payload["alignment_json"]:
                print(f"    {p}")
        if payload.get("missing_expected"):
            print("  (missing expected conventional paths:)", file=sys.stderr)
            for p in payload["missing_expected"]:
                print(f"    - {p}", file=sys.stderr)
        if payload.get("missing_tier_a_json"):
            print("  (missing tier_a_json_targets:)", file=sys.stderr)
            for p in payload["missing_tier_a_json"]:
                print(f"    - {p}", file=sys.stderr)
        if payload["missing_yml"]:
            print("  (missing yaml refs / non-yml skipped:)", file=sys.stderr)
            for p in payload["missing_yml"]:
                print(f"    - {p}", file=sys.stderr)
        if payload["missing_python_dirs"]:
            print("  (missing python_dirs:)", file=sys.stderr)
            for p in payload["missing_python_dirs"]:
                print(f"    - {p}", file=sys.stderr)
        if payload.get("missing_global_py"):
            for p in payload["missing_global_py"]:
                print(f"  (missing global_py: {p})", file=sys.stderr)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

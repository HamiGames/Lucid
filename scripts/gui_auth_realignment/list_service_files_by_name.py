#!/usr/bin/env python3
"""
File: scripts/gui_auth_realignment/list_service_files_by_name.py

Template: scripts/gui_auth_realignment/list_gui_service_files.py

Same path-resolution rules (source map, optional repo discovery, tier_a JSON targets),
but driven by explicit ``--service NAME`` values—not by enumerating gui-services.json.

For each name you pass:
  - ``python_dirs`` / ``yml_extra`` / ``global_python_files`` come from ``--source-map`` (same JSON shape
    as gui_service_source_map.json). Missing map file → empty dirs / extras (stderr notice).
  - Optional ``--mat``: if the service appears there, ``compose_files``, ``container_name``, and
    ``lucid_service`` from that row are merged (same as the GUI list tool).
  - Discovery needles: service name plus mat fields when present; plus ``--extra-needle`` (repeatable).

``missing_expected`` can treat ``configs/gui-alignment/<service>.json`` as optional for non-GUI stacks
via ``--omit-gui-alignment-convention``.

Usage (repo root):
  python scripts/gui_auth_realignment/list_service_files_by_name.py --service auth-service
  python scripts/gui_auth_realignment/list_service_files_by_name.py \\
      --service gui-api-bridge --service chain-to-pay \\
      --mat configs/services/some-mat.json \\
      --source-map scripts/gui_auth_realignment/gui_service_source_map.json
  python scripts/gui_auth_realignment/list_service_files_by_name.py \\
      --service my-worker --omit-gui-alignment-convention --format json

  Names from a file (one per line), merged with any ``--service``:
  python scripts/gui_auth_realignment/list_service_files_by_name.py \\
      --services-from configs/alignment-mats/service_names.txt \\
      --omit-gui-alignment-convention --manifest-dir configs/alignment-mats \\
      --manifest-suffix _manifest.json
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

DEFAULT_SOURCE_MAP = _HERE / "gui_service_source_map.json"
TIER_A_TARGETS = _HERE / "tier_a_json_targets.json"
TOOL_ID = "scripts/gui_auth_realignment/list_service_files_by_name.py"

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


def _sanitize_cli_token(s: str | None) -> str:
    """Strip CR/LF and outer whitespace (Windows paste / botched heredocs)."""
    if s is None:
        return ""
    return str(s).replace("\r", "").replace("\n", "").strip()


def _load_service_names_from_file(path: Path) -> List[str]:
    """One service name per line; strip; skip empties and ``#`` comments."""
    raw_b = path.read_bytes()
    if raw_b.startswith((b"\xff\xfe", b"\xfe\xff")):
        raw = raw_b.decode("utf-16", errors="replace")
    else:
        raw = raw_b.decode("utf-8-sig", errors="replace")
    out: List[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        t = _sanitize_cli_token(line)
        if t:
            out.append(t)
    return out


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


def _expected_path_gaps(
    repo: Path,
    compose_service: str,
    tier_json_rels: List[str],
    *,
    include_gui_alignment_convention: bool,
) -> Tuple[List[str], List[str]]:
    miss_exp: List[str] = []
    miss_tier: List[str] = []
    if include_gui_alignment_convention:
        rel_ga = f"configs/gui-alignment/{compose_service}.json"
        if not (repo / rel_ga).is_file():
            miss_exp.append(rel_ga)
    rel_infra = f"infrastructure/containers/services/{compose_service}.yml"
    if not (repo / rel_infra).is_file():
        miss_exp.append(rel_infra)
    for rel in tier_json_rels:
        r = rel.replace("\\", "/")
        if not (repo / r).is_file():
            miss_tier.append(r)
    return miss_exp, miss_tier


def _mat_row_for_service(mat: Dict[str, Any], name: str) -> Dict[str, Any]:
    for row in mat.get("services") or []:
        if isinstance(row, dict) and row.get("compose_service") == name:
            return row
    return {}


def _resolve_source_map(repo: Path, path_arg: str | None) -> tuple[Dict[str, Any] | None, Path]:
    p = Path(path_arg) if path_arg else DEFAULT_SOURCE_MAP
    if not p.is_absolute():
        p = repo / p
    raw = _load_json(p)
    if raw is None:
        print(f"Notice: source map missing or unreadable: {p} (using empty services)", file=sys.stderr)
        return None, p
    if not isinstance(raw, dict):
        print(f"Invalid source map (not an object): {p}", file=sys.stderr)
        return None, p
    return raw, p


def main() -> int:
    ap = argparse.ArgumentParser(
        description="List .yml / .yaml / .json / .py for arbitrary service names (optional mat row merge)."
    )
    ap.add_argument("--repo-root", default=None, help="Repository root")
    ap.add_argument(
        "--service",
        action="append",
        dest="services",
        metavar="NAME",
        default=[],
        help="Logical / compose service name (repeat for multiple). Use with --services-from or pass at least one source.",
    )
    ap.add_argument(
        "--services-from",
        dest="services_from",
        default=None,
        metavar="PATH",
        help="Text file: one service name per line (# comments OK). Repo-relative unless absolute. Merged with --service.",
    )
    ap.add_argument(
        "--source-map",
        default=None,
        help=f"JSON like gui_service_source_map.json (default: {DEFAULT_SOURCE_MAP.name} next to this script)",
    )
    ap.add_argument(
        "--mat",
        default=None,
        help="Optional services mat (same shape as gui-services.json); merge row when compose_service matches",
    )
    ap.add_argument("--extra-needle", action="append", default=[], help="Extra discovery substring (repeatable)")
    ap.add_argument(
        "--omit-gui-alignment-convention",
        action="store_true",
        help="Do not flag missing configs/gui-alignment/<service>.json as missing_expected",
    )
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
        help="Write one JSON file per service here: <service><suffix>",
    )
    ap.add_argument(
        "--manifest-suffix",
        default=".service-files.json",
        help="Suffix after service name for --manifest-dir",
    )
    ap.add_argument(
        "--discover-associated",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Scan YAML/JSON under default roots + python_dirs for needles (default: on)",
    )
    ap.add_argument(
        "--discover-max-bytes",
        type=int,
        default=DEFAULT_DISCOVER_MAX_BYTES,
        help="Max bytes read per file for discovery (default: 2000000)",
    )
    args = ap.parse_args()

    ms = _sanitize_cli_token(args.manifest_suffix)
    args.manifest_suffix = ms if ms else ".service-files.json"

    if args.manifest_dir:
        args.manifest_dir = _sanitize_cli_token(args.manifest_dir) or None
    if args.mat:
        args.mat = _sanitize_cli_token(args.mat) or None
    if args.source_map:
        args.source_map = _sanitize_cli_token(args.source_map) or None
    if args.out:
        args.out = _sanitize_cli_token(args.out) or None
    args.repo_root = _sanitize_cli_token(args.repo_root) or None
    args.extra_needle = [_sanitize_cli_token(n) for n in (args.extra_needle or []) if _sanitize_cli_token(n)]

    repo = _repo_root(args.repo_root)

    cli_services = [_sanitize_cli_token(s) for s in (args.services or []) if _sanitize_cli_token(s)]
    sf_raw = _sanitize_cli_token(getattr(args, "services_from", None))
    merged: List[str] = []
    seen_merge: Set[str] = set()
    for s in cli_services:
        k = s.casefold()
        if k not in seen_merge:
            seen_merge.add(k)
            merged.append(s)
    if sf_raw:
        fp = Path(sf_raw)
        if not fp.is_absolute():
            fp = repo / fp
        if not fp.is_file():
            print(f"error: --services-from not found: {fp}", file=sys.stderr)
            return 2
        for s in _load_service_names_from_file(fp):
            k = s.casefold()
            if k not in seen_merge:
                seen_merge.add(k)
                merged.append(s)
    args.services = merged
    if not args.services:
        print(
            "error: no service names (use --service and/or --services-from)",
            file=sys.stderr,
        )
        return 2

    mat: Dict[str, Any] | None = None
    mat_display = ""
    if args.mat:
        mp = Path(args.mat)
        if not mp.is_absolute():
            mp = repo / mp
        loaded = _load_json(mp)
        if not isinstance(loaded, dict):
            print(f"Invalid or missing mat: {mp}", file=sys.stderr)
            return 2
        mat = loaded
        try:
            mat_display = mp.relative_to(repo).as_posix()
        except ValueError:
            mat_display = str(mp)

    mp_raw, map_path_resolved = _resolve_source_map(repo, args.source_map)
    smap: Dict[str, Any] = (mp_raw.get("services") or {}) if isinstance(mp_raw, dict) else {}
    global_py = list((mp_raw.get("global_python_files") or []) if isinstance(mp_raw, dict) else [])

    tier_targets: Dict[str, List[str]] = {}
    tj = _load_json(TIER_A_TARGETS)
    if isinstance(tj, dict):
        tier_targets = {str(k): list(v or []) for k, v in (tj.get("targets") or {}).items()}

    try:
        map_display = map_path_resolved.relative_to(repo).as_posix()
    except ValueError:
        map_display = str(map_path_resolved)

    service_names = sorted(set(args.services), key=lambda s: s.lower())
    include_gui_align = not args.omit_gui_alignment_convention

    result: Dict[str, Any] = {}
    for name in service_names:
        row = _mat_row_for_service(mat, name) if mat else {}
        reg = smap.get(name) or {}
        py_dirs = list(reg.get("python_dirs") or [])
        yml_extra = [str(x).replace("\\", "/") for x in (reg.get("yml_extra") or [])]
        compose_files = [str(x).replace("\\", "/") for x in (row.get("compose_files") or [])]

        yml_paths = compose_files + yml_extra
        yml_declared, yml_missing = _collect_yml(repo, yml_paths)

        needles = _service_needles(name, row)
        for n in args.extra_needle or []:
            if n and n.strip() and n.strip() not in needles:
                needles.append(n.strip())

        tier_rels = [str(x).replace("\\", "/") for x in (tier_targets.get(name) or [])]
        yml_from_scan: Set[str] = set()
        json_from_scan: Set[str] = set()
        if args.discover_associated and needles:
            d_roots = _discovery_roots_for_service(repo, py_dirs)
            yml_from_scan, json_from_scan = _discover_yml_json(
                repo, d_roots, needles, args.discover_max_bytes
            )

        yml_resolved = sorted(set(yml_declared) | yml_from_scan)
        miss_exp, miss_tier = _expected_path_gaps(
            repo, name, tier_rels, include_gui_alignment_convention=include_gui_align
        )

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

        payload: Dict[str, Any] = {
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
            "source_map_path": map_display,
            "mat_path": mat_display or None,
            "mat_row_matched": bool(row),
        }
        if args.json_manifests:
            payload["alignment_json"] = manifests
        result[name] = payload

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
                "tool": TOOL_ID,
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
        print(f"  source_map: {payload.get('source_map_path')}")
        print(f"  mat: {payload.get('mat_path')!s} (row matched: {payload.get('mat_row_matched')})")
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

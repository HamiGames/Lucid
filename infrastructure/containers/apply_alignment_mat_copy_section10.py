#!/usr/bin/env python3
"""
File: infrastructure/containers/apply_alignment_mat_copy_section10.py

Rewrites Dockerfile section #10 (COPY_DIRECTORIES per dockerfile_layout_structure.json) using
configs/alignment-mats/<compose_service>_manifest.json, optionally augmented by paths from
configs/alignment-mats/service_source_map.json (yml_extra only).

- Resolves ``compose_service`` from host-config ``source_dockerfile`` (full path match), then from a
  **unique Dockerfile basename** (e.g. ``database/Dockerfile.elasticsearch`` → same service as
  ``storage/Dockerfile.elasticsearch``), then the inverse of rewrite script Dockerfile fallbacks
  (``gui-strap``, ``server-common``, base images), then ``Dockerfile.<stem>`` when a matching manifest exists.
- Skips non-Dockerfiles that match ``Dockerfile*`` on Windows (``.json``, ``.py``, ``.bak``, …) and
  ``.devcontainer/`` unless ``--include-devcontainer``.
- Replaces the region between ``# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN`` and
  ``# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END`` (drops existing COPY lines inside).
  If markers are missing, inserts the block immediately after the first
  ``# LUCID_X_FILES_SKELETON_END`` line.
- Emits one plain builder-stage ``COPY <repo-rel> ./<repo-rel>`` per file (same rules as
  rewrite_dockerfiles_from_alignment_mats.py).
- Optionally checks each source path against ``x-files.json`` ``section_to_canonical`` keys
  (repo-relative); paths not listed warn, or with --strict-x-files exit non-zero.

Usage (repo root):
  python infrastructure/containers/apply_alignment_mat_copy_section10.py --dry-run
  python infrastructure/containers/apply_alignment_mat_copy_section10.py \\
      --only-dockerfile infrastructure/containers/blockchain/Dockerfile.chain-to-pay
  python infrastructure/containers/apply_alignment_mat_copy_section10.py --strict-x-files

  When the Dockerfile name does not match ``<compose>_manifest.json``, force the manifest:
  python infrastructure/containers/apply_alignment_mat_copy_section10.py \\
      --only-dockerfile infrastructure/containers/electron_gui/Dockerfile.admin \\
      --compose-service admin-interface
  python infrastructure/containers/apply_alignment_mat_copy_section10.py \\
      --only-dockerfile infrastructure/docker/common/Dockerfile.lucid-governor \\
      --compose-service lucid-gov
  python infrastructure/containers/apply_alignment_mat_copy_section10.py \\
      --only-dockerfile infrastructure/docker/payment-systems/Dockerfile.tron-client \\
      --compose-service tron-node-client
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from e

MARK_MAT_COPY_BEGIN = "# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN"
MARK_MAT_COPY_END = "# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END"
MARK_SKELETON_END = "# LUCID_X_FILES_SKELETON_END"
HERE = Path(__file__).resolve().parent
DEFAULT_LAYOUT = HERE / "dockerfile_layout_structure.json"
DEFAULT_HOST = HERE / "host-config.yml"
DEFAULT_MAT_DIR = Path("configs/alignment-mats")
DEFAULT_SOURCE_MAP = Path("configs/alignment-mats/service_source_map.json")
DEFAULT_X_FILES = Path("x-files.json")
SCAN_ROOTS = ("infrastructure/containers", "infrastructure/docker")

# Same as rewrite_dockerfiles_from_alignment_mats.MAT_COMPOSE_TO_DOCKERFILE_FALLBACK (inverted).
COMPOSE_TO_DOCKERFILE_FALLBACK: Dict[str, str] = {
    "base-runtime": "infrastructure/containers/base/Dockerfile.base",
    "gui-strap": "infrastructure/docker/distroless/gui/Dockerfile.gui",
    "java-base": "infrastructure/containers/base/Dockerfile.java-base",
    "python-base": "infrastructure/containers/base/Dockerfile.python-base",
    "server-common": "infrastructure/docker/common/Dockerfile",
}

# Dockerfiles that are not (or not yet) wired as host-config ``source_dockerfile``, or use a
# filename that does not match ``<compose_service>_manifest.json``. Keys: repo-relative POSIX.
EXPLICIT_DOCKERFILE_TO_COMPOSE: Dict[str, str] = {
    # electron_gui docker-compose.electron-gui.yml; image admin-interface (see Dockerfile header).
    "infrastructure/containers/electron_gui/Dockerfile.admin": "admin-interface",
    # Same service as auth/Dockerfile.lucid-gov; alternate path/name (see Dockerfile header).
    "infrastructure/docker/common/Dockerfile.lucid-governor": "lucid-gov",
    # Same as payment_systems/Dockerfile.tron-node-client; duplicate under infrastructure/docker (see header).
    "infrastructure/docker/payment-systems/Dockerfile.tron-client": "tron-node-client",
}

# Names that are not Dockerfiles but match case-insensitive Dockerfile* on Windows.
_FORBIDDEN_NAME_SUFFIXES = (
    ".json",
    ".py",
    ".pyc",
    ".bak",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
)


def _repo_root(cli: str | None) -> Path:
    if cli:
        return Path(cli).resolve()
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_mat_relpath(item: str) -> Optional[str]:
    p = item.replace("\\", "/").strip().lstrip("./")
    if not p or p.startswith("#"):
        return None
    return p


def collect_mat_manifest_paths(doc: Dict[str, Any]) -> List[str]:
    raw: List[str] = []
    for key in ("py", "yml", "yaml", "json", "alignment_json"):
        for item in doc.get(key) or []:
            if isinstance(item, str):
                n = _normalize_mat_relpath(item)
                if n:
                    raw.append(n)
    seen: Set[str] = set()
    out: List[str] = []
    for p in sorted(raw):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _dockerfile_copy_one(src: str, dest: str) -> str:
    needs_json = (
        " " in src
        or "\t" in src
        or '"' in src
        or " " in dest
        or "\t" in dest
        or '"' in dest
    )
    prefix = "COPY "
    if needs_json:
        return prefix + json.dumps([src, dest])
    return prefix + f"{src} {dest}"


def build_mat_copy_block_files(
    rel_files: List[str], compose_service: str, mat_basename: str
) -> str:
    lines = [
        MARK_MAT_COPY_BEGIN,
        f"# alignment-mat {mat_basename}: compose_service={compose_service!r} "
        f"— explicit manifest paths → {len(rel_files)} builder COPY line(s) "
        f"(dockerfile_layout_structure.json section #10 COPY_DIRECTORIES).",
    ]
    for rel in rel_files:
        lines.append(_dockerfile_copy_one(rel, f"./{rel}"))
    lines.append(MARK_MAT_COPY_END)
    return "\n".join(lines) + "\n"


def load_layout_section10(layout_path: Path) -> Tuple[str, int]:
    doc = _load_json(layout_path)
    for sec in doc.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        if sec.get("id") == "COPY_DIRECTORIES" and int(sec.get("number") or 0) == 10:
            return str(sec.get("name") or "COPY_DIRECTORIES"), 10
    raise SystemExit(f"{layout_path}: no section id COPY_DIRECTORIES number 10")


def _norm_dockerfile_key(dfp: str) -> str:
    return Path(dfp.strip().replace("\\", "/")).as_posix().lstrip("./")


def build_host_compose_resolution(
    host_path: Path,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    full_map: repo-relative source_dockerfile -> service_name
    basename_map: lowercased Dockerfile filename -> service_name (only when that basename is unique in host-config)
    basename_canonical: lowercased filename -> canonical repo-relative path from host-config
    """
    raw = yaml.safe_load(host_path.read_text(encoding="utf-8"))
    services = raw.get("services") or {}
    full_map: Dict[str, str] = {}
    rows: List[Tuple[str, str, str]] = []
    if not isinstance(services, dict):
        return full_map, {}, {}
    for _sid, block in services.items():
        if not isinstance(block, dict):
            continue
        dfp = block.get("source_dockerfile")
        if not isinstance(dfp, str) or not dfp.strip():
            continue
        key = _norm_dockerfile_key(dfp)
        sn = block.get("service_name")
        if not isinstance(sn, str) or not sn.strip():
            continue
        sn = sn.strip()
        full_map[key] = sn
        bn = Path(key).name.casefold()
        rows.append((key, sn, bn))
    counts = Counter(r[2] for r in rows)
    basename_map: Dict[str, str] = {}
    basename_canonical: Dict[str, str] = {}
    for key, sn, bn in rows:
        if counts[bn] != 1:
            continue
        basename_map[bn] = sn
        basename_canonical[bn] = key
    return full_map, basename_map, basename_canonical


def invert_dockerfile_fallback() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for compose, dfp in COMPOSE_TO_DOCKERFILE_FALLBACK.items():
        out[_norm_dockerfile_key(dfp)] = compose
    return out


def guess_compose_from_stem(dockerfile: Path) -> Optional[str]:
    name = dockerfile.name
    dot = name.find(".")
    if dot < 0:
        return None
    if name[:dot].casefold() != "dockerfile":
        return None
    rest = name[dot + 1 :].strip()
    if not rest:
        return None
    return rest.replace("_", "-")


def _is_real_dockerfile(p: Path, *, include_devcontainer: bool) -> bool:
    if "node_modules" in p.parts or ".git" in p.parts or "__pycache__" in p.parts:
        return False
    if not include_devcontainer and ".devcontainer" in p.parts:
        return False
    n = p.name
    cl = n.casefold()
    if cl == "dockerfile":
        return True
    if not cl.startswith("dockerfile."):
        return False
    for suf in _FORBIDDEN_NAME_SUFFIXES:
        if cl.endswith(suf):
            return False
    return True


def iter_dockerfiles(
    repo: Path, roots: Tuple[str, ...], *, include_devcontainer: bool
) -> List[Path]:
    found: List[Path] = []
    for r in roots:
        root = repo / r.replace("\\", "/")
        if not root.is_dir():
            continue
        for p in root.rglob("Dockerfile*"):
            if not p.is_file():
                continue
            if not _is_real_dockerfile(p, include_devcontainer=include_devcontainer):
                continue
            found.append(p)
    found.sort(key=lambda x: x.as_posix().lower())
    return found


def resolve_compose_service(
    repo: Path,
    df: Path,
    full_map: Dict[str, str],
    basename_map: Dict[str, str],
    basename_canonical: Dict[str, str],
    fallback_df_to_compose: Dict[str, str],
    explicit_df_to_compose: Dict[str, str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (compose_service, optional note for basename/fallback resolution).
    """
    rel = df.resolve().relative_to(repo.resolve()).as_posix()
    rel_n = rel.replace("\\", "/").lstrip("./")
    if rel_n in full_map:
        return full_map[rel_n], None
    if rel_n in explicit_df_to_compose:
        return explicit_df_to_compose[rel_n], "compose via EXPLICIT_DOCKERFILE_TO_COMPOSE (see script doc)"
    bn = df.name.casefold()
    if bn in basename_map:
        canon = basename_canonical.get(bn) or ""
        if rel_n != canon:
            return basename_map[bn], (
                f"compose via unique Dockerfile basename {df.name!r} "
                f"(host-config canonical path: {canon})"
            )
        return basename_map[bn], None
    if rel_n in fallback_df_to_compose:
        return fallback_df_to_compose[rel_n], "compose via MAT_COMPOSE_TO_DOCKERFILE_FALLBACK inverse"
    g = guess_compose_from_stem(df)
    if g:
        mf = repo / DEFAULT_MAT_DIR / f"{g}_manifest.json"
        if mf.is_file():
            return g, "compose via Dockerfile stem + existing manifest"
    return None, None


def merge_source_map_extras(
    compose: str,
    paths: List[str],
    source_map: Optional[Dict[str, Any]],
) -> List[str]:
    if not source_map:
        return paths
    services = source_map.get("services") or {}
    if not isinstance(services, dict):
        return paths
    reg = services.get(compose) or {}
    if not isinstance(reg, dict):
        return paths
    extra = reg.get("yml_extra") or []
    seen = set(paths)
    out = list(paths)
    for item in extra:
        if not isinstance(item, str):
            continue
        n = _normalize_mat_relpath(item)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    out.sort(key=lambda s: s.casefold())
    return out


def replace_or_insert_mat_region(content: str, new_block: str) -> Tuple[str, str]:
    """Returns (new_content, action) where action is 'replaced'|'inserted'|'unchanged-error'."""
    i0 = content.find(MARK_MAT_COPY_BEGIN)
    i1 = content.find(MARK_MAT_COPY_END) if i0 >= 0 else -1
    if i0 >= 0 and i1 > i0:
        j = content.find("\n", i1)
        if j < 0:
            j = len(content)
        else:
            j += 1
        return content[:i0] + new_block + content[j:], "replaced"

    k = content.find(MARK_SKELETON_END)
    if k < 0:
        return content, "no_anchor"
    nl = content.find("\n", k)
    if nl < 0:
        return content, "no_anchor"
    insert_at = nl + 1
    return content[:insert_at] + "\n" + new_block + content[insert_at:], "inserted"


def x_files_keys(repo: Path, x_path: Path) -> Set[str]:
    p = x_path if x_path.is_absolute() else repo / x_path
    doc = _load_json(p)
    m = doc.get("section_to_canonical") or {}
    if not isinstance(m, dict):
        return set()
    return {str(k).replace("\\", "/") for k in m}


def check_x_files(
    rel_files: List[str],
    keys: Set[str],
) -> Tuple[List[str], List[str]]:
    ok: List[str] = []
    bad: List[str] = []
    for rel in rel_files:
        if rel in keys:
            ok.append(rel)
        else:
            bad.append(rel)
    return ok, bad


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Rewrite LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_* (#10) from alignment manifests + "
            "optional service_source_map yml_extra; validate paths against x-files.json."
        )
    )
    ap.add_argument("--repo-root", default=None)
    ap.add_argument(
        "--layout",
        type=Path,
        default=DEFAULT_LAYOUT,
        help="dockerfile_layout_structure.json (validates section #10 id)",
    )
    ap.add_argument(
        "--host-config",
        type=Path,
        default=DEFAULT_HOST,
        help="host-config.yml for source_dockerfile → service_name",
    )
    ap.add_argument("--mat-dir", type=Path, default=DEFAULT_MAT_DIR)
    ap.add_argument(
        "--source-map",
        type=Path,
        default=DEFAULT_SOURCE_MAP,
        help="service_source_map.json (merge yml_extra); omit with --no-source-map",
    )
    ap.add_argument("--no-source-map", action="store_true")
    ap.add_argument("--x-files", type=Path, default=DEFAULT_X_FILES)
    ap.add_argument("--no-x-files-check", action="store_true")
    ap.add_argument(
        "--strict-x-files",
        action="store_true",
        help="Exit 3 if any copied path is missing from x-files section_to_canonical",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--only-dockerfile",
        action="append",
        default=[],
        metavar="REPO_REL_PATH",
        help="Limit to this Dockerfile (repo-relative POSIX); repeat allowed",
    )
    ap.add_argument(
        "--compose-service",
        default=None,
        metavar="NAME",
        help=(
            "Use configs/alignment-mats/NAME_manifest.json (ignores host-config stem). "
            "Requires exactly one Dockerfile after --only-dockerfile filtering."
        ),
    )
    ap.add_argument(
        "--include-devcontainer",
        action="store_true",
        help="Also process Dockerfiles under .devcontainer/ (default: skip)",
    )
    args = ap.parse_args()

    repo = _repo_root(args.repo_root)
    layout_path = args.layout if args.layout.is_absolute() else repo / args.layout
    sec_name, sec_num = load_layout_section10(layout_path)
    print(
        f"Layout: section #{sec_num} {sec_name} (COPY_DIRECTORIES) from {layout_path.relative_to(repo)}",
        flush=True,
    )

    host_path = args.host_config if args.host_config.is_absolute() else repo / args.host_config
    full_map, basename_map, basename_canonical = build_host_compose_resolution(host_path)
    fallback_df_to_compose = invert_dockerfile_fallback()
    explicit_map = {_norm_dockerfile_key(k): v for k, v in EXPLICIT_DOCKERFILE_TO_COMPOSE.items()}
    mat_dir = args.mat_dir if args.mat_dir.is_absolute() else repo / args.mat_dir

    sm: Optional[Dict[str, Any]] = None
    if not args.no_source_map:
        smp = args.source_map if args.source_map.is_absolute() else repo / args.source_map
        if smp.is_file():
            raw = _load_json(smp)
            sm = raw if isinstance(raw, dict) else None
        else:
            print(f"Notice: no source map at {smp} (skipping yml_extra merge)", file=sys.stderr)

    xf_keys: Set[str] = set()
    if not args.no_x_files_check:
        xfp = args.x_files if args.x_files.is_absolute() else repo / args.x_files
        if xfp.is_file():
            xf_keys = x_files_keys(repo, xfp)
        else:
            print(f"Notice: x-files.json missing at {xfp} (skipping approval check)", file=sys.stderr)

    want: Optional[Set[str]] = None
    if args.only_dockerfile:
        want = set()
        for p in args.only_dockerfile:
            want.add(Path(str(p).strip()).as_posix().lstrip("./"))

    dockerfiles = iter_dockerfiles(
        repo, SCAN_ROOTS, include_devcontainer=bool(args.include_devcontainer)
    )
    if want is not None:
        dockerfiles = [
            df
            for df in dockerfiles
            if df.resolve().relative_to(repo.resolve()).as_posix() in want
        ]

    forced_compose = (args.compose_service or "").strip() or None
    if forced_compose:
        if len(dockerfiles) != 1:
            print(
                "error: --compose-service requires exactly one target Dockerfile "
                "(use a single --only-dockerfile path that exists under scan roots)",
                file=sys.stderr,
            )
            return 2

    changed = 0
    skipped = 0
    strict_issues = 0

    for df in dockerfiles:
        rel_df = df.resolve().relative_to(repo.resolve()).as_posix()
        if forced_compose:
            compose = forced_compose
            res_note: Optional[str] = "compose via --compose-service"
        else:
            compose, res_note = resolve_compose_service(
                repo,
                df,
                full_map,
                basename_map,
                basename_canonical,
                fallback_df_to_compose,
                explicit_map,
            )
        if res_note:
            print(f"NOTE {rel_df}: {res_note}", flush=True)
        if not compose:
            print(
                f"SKIP {rel_df}: could not resolve compose_service "
                f"(host-config path, unique basename, fallback map, or Dockerfile stem + manifest)",
                flush=True,
            )
            skipped += 1
            continue
        mf = mat_dir / f"{compose}_manifest.json"
        if not mf.is_file():
            print(f"SKIP {rel_df}: no manifest {mf.relative_to(repo)}", flush=True)
            skipped += 1
            continue
        doc = _load_json(mf)
        if not isinstance(doc, dict):
            print(f"SKIP {rel_df}: invalid manifest JSON {mf.name}", flush=True)
            skipped += 1
            continue
        mcs = str(doc.get("compose_service") or "").strip()
        if mcs and mcs != compose:
            print(f"SKIP {rel_df}: manifest compose_service {mcs!r} != resolved {compose!r}", flush=True)
            skipped += 1
            continue

        paths = collect_mat_manifest_paths(doc)
        paths = merge_source_map_extras(compose, paths, sm)
        if not paths:
            print(f"SKIP {rel_df}: manifest has no py/yml/yaml/json paths", flush=True)
            skipped += 1
            continue

        bad_xf: List[str] = []
        if xf_keys:
            _ok, bad_xf = check_x_files(paths, xf_keys)
            for b in bad_xf:
                msg = f"x-files: path not in section_to_canonical: {b}"
                if args.strict_x_files:
                    print(f"ERROR {rel_df}: {msg}", file=sys.stderr)
                else:
                    print(f"WARN {rel_df}: {msg}", file=sys.stderr)
            if args.strict_x_files and bad_xf:
                strict_issues += len(bad_xf)
                skipped += 1
                continue

        new_block = build_mat_copy_block_files(paths, compose, mf.name)
        raw = df.read_text(encoding="utf-8")
        new_content, action = replace_or_insert_mat_region(raw, new_block)
        if action == "no_anchor":
            print(
                f"SKIP {rel_df}: no {MARK_MAT_COPY_BEGIN}/{MARK_MAT_COPY_END} and no {MARK_SKELETON_END}",
                flush=True,
            )
            skipped += 1
            continue
        if new_content == raw:
            print(f"UNCHANGED {rel_df}", flush=True)
            continue
        if args.dry_run:
            print(f"[dry-run] {action} #10 mat COPY in {rel_df} ({len(paths)} file(s))", flush=True)
            changed += 1
            continue
        df.write_text(new_content, encoding="utf-8", newline="\n")
        print(f"WROTE {rel_df} ({action}, {len(paths)} COPY line(s))", flush=True)
        changed += 1

    if strict_issues:
        return 3
    print(f"Done: updated {changed}, skipped {skipped}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
File: infrastructure/containers/cleanup_dockerfile_copy_alignment_mats.py

Remove builder-stage COPY lines that are not justified by the service alignment manifest
(``configs/alignment-mats/<compose_service>_manifest.json``), optionally augmented with
``service_source_map.json`` ``yml_extra`` — same path set as
``apply_alignment_mat_copy_section10.py``.

Targets (``dockerfile_layout_structure.json``):
  - **Section #10 COPY_DIRECTORIES**: region ``# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN`` … ``END``.
    Drops ``COPY`` lines whose source path is not in the manifest allowlist (per-file paths).
    Dedupes mirrored sources (keep ``infrastructure/containers/...`` over ``configs/container/...``;
    ``infrastructure/service_mesh/...`` over ``service_mesh/...``) so each logical file appears once.
  - **Post-MAT builder tail** (often ``# LUCID_X_FILES_SKELETON_BEGIN`` after MAT): plain ``COPY`` lines **after**
    ``# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END`` and **before** the next stage ``FROM`` (first ``FROM`` after MAT).
    Drops legacy whole-tree copies (e.g. ``COPY blockchain/ ./blockchain/``) when no manifest path uses that source
    tree. Short sources (``admin/config/foo.yml``) match if any manifest path equals or ends with that suffix.
  - **Section #20 COPY CONTENT** (runtime stage): region ``# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN`` …
    ``END``. Drops ``COPY --from=builder`` lines that copy **from** ``/build/<segment>/`` as a directory
    (``/build/foo/ …``) when no manifest path uses top-level segment ``foo`` (case-insensitive).
    Single-file ``/build/...`` lines and non-``/build/`` copies are left unchanged.
    Segment ``wheels`` is always kept (bootstrap layout).
  - **Runtime tail** (after the second ``FROM``): same ``/build/<seg>/`` directory rule as #20 for the entire
    remainder of the file, so stray ``COPY --from=builder`` lines outside a well-formed #20 block are removed.
  - **Runtime dedupe** (after the second ``FROM``, whole stage): removes duplicate ``COPY --from=builder`` lines
    (same source and dest) and file copies under ``/build/<dir>/`` that are already covered by an earlier
    directory copy of that tree (e.g. ``/build/configs/`` → ``/app/configs/`` then redundant single-file lines).

Optional: warn when manifest paths are missing from ``configs/x-files.json`` ``section_to_canonical``.

Default: **dry-run**. Use ``--write`` to modify files; ``--backup-ext .bak`` keeps a copy.

Usage (repo root):
  python infrastructure/containers/cleanup_dockerfile_copy_alignment_mats.py --dry-run
  python infrastructure/containers/cleanup_dockerfile_copy_alignment_mats.py \\
      --only-dockerfile infrastructure/containers/auth/Dockerfile.auth-service --write
  python infrastructure/containers/cleanup_dockerfile_copy_alignment_mats.py \\
      --compose-service lucid-auth-service --only-dockerfile infrastructure/containers/auth/Dockerfile.auth-service \\
      --write --backup-ext .cleanup.bak
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_CONTAINERS_DIR = Path(__file__).resolve().parent
if str(_CONTAINERS_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTAINERS_DIR))

import apply_alignment_mat_copy_section10 as _amat  # noqa: E402

COMPOSE_TO_DOCKERFILE_FALLBACK = _amat.COMPOSE_TO_DOCKERFILE_FALLBACK
DEFAULT_HOST = _amat.DEFAULT_HOST
DEFAULT_LAYOUT = _amat.DEFAULT_LAYOUT
DEFAULT_MAT_DIR = _amat.DEFAULT_MAT_DIR
DEFAULT_SOURCE_MAP = _amat.DEFAULT_SOURCE_MAP
DEFAULT_X_FILES = _amat.DEFAULT_X_FILES
EXPLICIT_DOCKERFILE_TO_COMPOSE = _amat.EXPLICIT_DOCKERFILE_TO_COMPOSE
MARK_MAT_COPY_BEGIN = _amat.MARK_MAT_COPY_BEGIN
MARK_MAT_COPY_END = _amat.MARK_MAT_COPY_END
SCAN_ROOTS = _amat.SCAN_ROOTS
build_host_compose_resolution = _amat.build_host_compose_resolution
check_x_files = _amat.check_x_files
collect_mat_manifest_paths = _amat.collect_mat_manifest_paths
invert_dockerfile_fallback = _amat.invert_dockerfile_fallback
iter_dockerfiles = _amat.iter_dockerfiles
merge_source_map_extras = _amat.merge_source_map_extras
resolve_compose_service = _amat.resolve_compose_service
x_files_keys = _amat.x_files_keys
_load_json = _amat._load_json
_norm_dockerfile_key = _amat._norm_dockerfile_key

MARK_RUNTIME_COPY_BEGIN = "# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN"
MARK_RUNTIME_COPY_END = "# LUCID_RUNTIME_COPY_FROM_BUILD_END"

# /build/<segment>/ … directory copies: never drop (not represented as manifest file paths).
RUNTIME_BUILD_SEGMENTS_ALWAYS_KEEP = frozenset(
    {
        "wheels",
    }
)

_TOOL = "infrastructure/containers/cleanup_dockerfile_copy_alignment_mats.py"


def _repo_root(cli: str | None) -> Path:
    if cli:
        return Path(cli).resolve()
    return Path(__file__).resolve().parents[2]


def _normalize_rel_copy_path(s: str) -> str:
    t = s.strip().strip('"').strip("'").replace("\\", "/").lstrip("./")
    return t


def parse_mat_copy_line(line: str) -> Optional[Tuple[str, str]]:
    """First COPY in section #10 (no --from). Returns (src, dst) or None."""
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if not raw.upper().startswith("COPY "):
        return None
    rest = raw[5:].lstrip()
    if rest.startswith("--"):
        return None
    if rest.startswith("<<"):
        return None
    if rest.startswith("["):
        try:
            pair = json.loads(rest)
            if isinstance(pair, list) and len(pair) >= 2:
                return _normalize_rel_copy_path(str(pair[0])), _normalize_rel_copy_path(str(pair[1]))
        except json.JSONDecodeError:
            return None
        return None
    parts = re.split(r"\s+", rest, maxsplit=1)
    if len(parts) < 2:
        return None
    return _normalize_rel_copy_path(parts[0]), _normalize_rel_copy_path(parts[1])


def _allowed_for_mat_copy(src: str, allowed: Set[str]) -> bool:
    if src in allowed:
        return True
    if src.endswith("/"):
        base = src.rstrip("/")
        if any(p == base or p.startswith(base + "/") for p in allowed):
            return True
    return False


def _copy_src_allowed_manifest(src: str, allowed: Set[str]) -> bool:
    """
    Whether a builder COPY source is justified by manifest paths (exact, dir prefix, or suffix for short paths).
    Used for post-MAT ``COPY`` lines that may use repo-short paths (``admin/config/...`` vs
    ``infrastructure/containers/admin/config/...``).
    """
    s = _normalize_rel_copy_path(src).rstrip("/")
    if not s:
        return False
    if s in allowed:
        return True
    with_slash = s + "/"
    if any(a == s or a.startswith(with_slash) for a in allowed):
        return True
    if any(a.endswith("/" + s) or a == s for a in allowed):
        return True
    first = s.split("/")[0]
    if first and any(a.startswith(first + "/") or a == first for a in allowed):
        return True
    return False


def _top_segments_from_paths(paths: Iterable[str]) -> Set[str]:
    segs: Set[str] = set()
    for p in paths:
        n = p.replace("\\", "/").strip().lstrip("./")
        if not n:
            continue
        first = n.split("/")[0]
        if first:
            segs.add(first.casefold())
    return segs


_RUNTIME_DIR_COPY = re.compile(
    r"COPY\s+--from=builder[^\n]*/build/([^/\s#]+)/",
    re.IGNORECASE,
)


def _runtime_build_dir_segment(line: str) -> Optional[str]:
    m = _RUNTIME_DIR_COPY.search(line)
    return m.group(1) if m else None


def _mat_mirror_group_key(src: str) -> str:
    """
    Group mirrored repo paths so we keep a single COPY per logical file:
    ``configs/container/<rest>`` ↔ ``infrastructure/containers/<rest>``;
    ``service_mesh/<rest>`` ↔ ``infrastructure/service_mesh/<rest>``.
    """
    n = _normalize_rel_copy_path(src).replace("\\", "/")
    if n.startswith("configs/container/"):
        return "mirror:" + n[len("configs/container/") :]
    if n.startswith("infrastructure/containers/"):
        return "mirror:" + n[len("infrastructure/containers/") :]
    if n.startswith("service_mesh/"):
        return "smirror:" + n[len("service_mesh/") :]
    if n.startswith("infrastructure/service_mesh/"):
        return "smirror:" + n[len("infrastructure/service_mesh/") :]
    return "full:" + n


def _mat_src_preference_rank(src: str) -> int:
    """Lower is better when choosing which line to keep in a mirror group."""
    n = _normalize_rel_copy_path(src).replace("\\", "/")
    if n.startswith("infrastructure/containers/") or n.startswith("infrastructure/service_mesh/"):
        return 0
    if n.startswith("configs/container/") or n.startswith("service_mesh/"):
        return 1
    return 2


def dedupe_section10_lines(lines: List[str]) -> Tuple[List[str], int]:
    """Within MAT markers, one COPY per mirror group (configs vs infrastructure, service_mesh paths)."""
    mat_start: Optional[int] = None
    mat_end: Optional[int] = None
    for i, line in enumerate(lines):
        if MARK_MAT_COPY_BEGIN in line:
            mat_start = i
        if mat_start is not None and MARK_MAT_COPY_END in line:
            mat_end = i
            break
    if mat_start is None or mat_end is None or mat_end <= mat_start + 1:
        return lines, 0

    copy_indices: List[int] = []
    for j in range(mat_start + 1, mat_end):
        if parse_mat_copy_line(lines[j]) is not None:
            copy_indices.append(j)
    if len(copy_indices) < 2:
        return lines, 0

    groups: Dict[str, List[int]] = {}
    for j in copy_indices:
        parsed = parse_mat_copy_line(lines[j])
        assert parsed is not None
        src, _dst = parsed
        gk = _mat_mirror_group_key(src)
        if gk.startswith("full:"):
            continue
        groups.setdefault(gk, []).append(j)

    drop: Set[int] = set()
    for _gk, idxs in groups.items():
        if len(idxs) <= 1:
            continue

        def _rank_at(jj: int) -> Tuple[int, str]:
            p = parse_mat_copy_line(lines[jj])
            assert p is not None
            return (_mat_src_preference_rank(p[0]), p[0])

        best = min(idxs, key=_rank_at)
        for jj in idxs:
            if jj != best:
                drop.add(jj)

    if not drop:
        return lines, 0
    out = [line for i, line in enumerate(lines) if i not in drop]
    return out, len(drop)


def parse_runtime_builder_copy(line: str) -> Optional[Tuple[str, str]]:
    """
    ``COPY --from=builder ... <src> <dest>`` with ``/build/`` in src.
    Returns (build_src, app_dest) normalized with trailing spaces stripped.
    """
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if not raw.upper().startswith("COPY "):
        return None
    if "--from=builder" not in raw.lower():
        return None
    if "#" in raw:
        raw = raw.split("#", 1)[0].rstrip()
    low = raw.lower()
    idx = low.find("/build/")
    if idx < 0:
        return None
    tail = raw[idx:].strip()
    parts = tail.split()
    if len(parts) < 2:
        return None
    build_src = parts[0]
    app_dst = parts[-1]
    return build_src, app_dst


def dedupe_runtime_build_copy_lines(lines: List[str]) -> Tuple[List[str], int]:
    """
    After the second ``FROM``: drop duplicate ``COPY --from=builder`` (same /build src and app dest)
    and file copies already covered by an earlier ``/build/<dir>/`` → ``/app/<dir>/`` directory copy.
    """
    from_idx = _second_from_line_index(lines)
    if from_idx is None:
        return lines, 0

    coverages: List[Tuple[str, str]] = []
    seen_pair: Set[Tuple[str, str]] = set()
    drop: Set[int] = set()
    removed = 0

    for i, line in enumerate(lines):
        if i <= from_idx:
            continue
        parsed = parse_runtime_builder_copy(line)
        if parsed is None:
            continue
        bsrc, adst = parsed
        bsrc_n = bsrc.rstrip()
        adst_n = adst.rstrip()
        key = (bsrc_n, adst_n)
        if key in seen_pair:
            drop.add(i)
            removed += 1
            continue

        if bsrc_n.endswith("/"):
            seen_pair.add(key)
            bp = bsrc_n if bsrc_n.endswith("/") else bsrc_n + "/"
            ap = adst_n if adst_n.endswith("/") else adst_n + "/"
            coverages.append((bp, ap))
            continue

        redundant = False
        for bdir, adir in coverages:
            if bsrc_n.startswith(bdir):
                rel = bsrc_n[len(bdir) :].lstrip("/")
                expected = adir + rel
                if adst_n == expected or adst_n.rstrip("/") == expected.rstrip("/"):
                    redundant = True
                    break
        if redundant:
            drop.add(i)
            removed += 1
            continue

        seen_pair.add(key)

    if not drop:
        return lines, 0
    out = [line for i, line in enumerate(lines) if i not in drop]
    return out, removed


def cleanup_section10_lines(lines: List[str], allowed: Set[str]) -> Tuple[List[str], int]:
    out: List[str] = []
    removed = 0
    in_block = False
    for line in lines:
        if MARK_MAT_COPY_BEGIN in line:
            in_block = True
            out.append(line)
            continue
        if in_block and MARK_MAT_COPY_END in line:
            in_block = False
            out.append(line)
            continue
        if in_block:
            parsed = parse_mat_copy_line(line)
            if parsed is not None:
                src, _dst = parsed
                if not _allowed_for_mat_copy(src, allowed):
                    removed += 1
                    continue
            out.append(line)
        else:
            out.append(line)
    return out, removed


def _post_mat_builder_slice(lines: List[str]) -> Optional[Tuple[int, int]]:
    """
    Line indices [start, end) to scan for plain COPY cleanup: after MAT_COPY_END, before next stage FROM.
    """
    mat_end_i: Optional[int] = None
    for i, line in enumerate(lines):
        if MARK_MAT_COPY_END in line:
            mat_end_i = i
            break
    if mat_end_i is None:
        return None
    for j in range(mat_end_i + 1, len(lines)):
        st = lines[j].strip()
        if len(st) >= 5 and st[:5].upper() == "FROM ":
            return (mat_end_i + 1, j)
    return None


def cleanup_post_mat_builder_copies(lines: List[str], allowed: Set[str]) -> Tuple[List[str], int]:
    sl = _post_mat_builder_slice(lines)
    if sl is None:
        return lines, 0
    start, end = sl
    out: List[str] = []
    removed = 0
    for i, line in enumerate(lines):
        if start <= i < end:
            parsed = parse_mat_copy_line(line)
            if parsed is not None:
                src, _dst = parsed
                if not _copy_src_allowed_manifest(src, allowed):
                    removed += 1
                    continue
        out.append(line)
    return out, removed


def cleanup_section20_lines(lines: List[str], needed_segments: Set[str]) -> Tuple[List[str], int]:
    out: List[str] = []
    removed = 0
    in_block = False
    for line in lines:
        if MARK_RUNTIME_COPY_BEGIN in line:
            in_block = True
            out.append(line)
            continue
        if in_block and MARK_RUNTIME_COPY_END in line:
            in_block = False
            out.append(line)
            continue
        if in_block:
            seg = _runtime_build_dir_segment(line)
            if seg is not None:
                s = seg.casefold()
                if s not in RUNTIME_BUILD_SEGMENTS_ALWAYS_KEEP and s not in needed_segments:
                    removed += 1
                    continue
            out.append(line)
        else:
            out.append(line)
    return out, removed


def _second_from_line_index(lines: List[str]) -> Optional[int]:
    """0-based index of the second ``FROM`` line (runtime stage start in typical multi-stage files)."""
    hits: List[int] = []
    for i, line in enumerate(lines):
        st = line.strip()
        if len(st) >= 5 and st[:5].upper() == "FROM ":
            hits.append(i)
    return hits[1] if len(hits) >= 2 else None


def cleanup_runtime_tail_build_dir_copies(lines: List[str], needed_segments: Set[str]) -> Tuple[List[str], int]:
    """
    After the second ``FROM``, remove any ``COPY --from=builder ... /build/<seg>/`` directory line when
    ``<seg>`` is not justified by manifest top-level segments (handles duplicate/mis-nested
    ``LUCID_RUNTIME_COPY_FROM_BUILD_*`` markers).
    """
    idx = _second_from_line_index(lines)
    if idx is None:
        return lines, 0
    out: List[str] = []
    removed = 0
    for i, line in enumerate(lines):
        if i <= idx:
            out.append(line)
            continue
        seg = _runtime_build_dir_segment(line)
        if seg is not None:
            s = seg.casefold()
            if s not in RUNTIME_BUILD_SEGMENTS_ALWAYS_KEEP and s not in needed_segments:
                removed += 1
                continue
        out.append(line)
    return out, removed


def process_dockerfile_text(
    text: str, allowed_paths: Set[str]
) -> Tuple[str, int, int, int, int, int, int]:
    needed = _top_segments_from_paths(allowed_paths)
    lines = text.splitlines(keepends=True)
    s10, r10 = cleanup_section10_lines(lines, allowed_paths)
    s10d, r10d = dedupe_section10_lines(s10)
    s_pm, r_pm = cleanup_post_mat_builder_copies(s10d, allowed_paths)
    s20, r20 = cleanup_section20_lines(s_pm, needed)
    s_tail, r_tail = cleanup_runtime_tail_build_dir_copies(s20, needed)
    s_ded, r_rtd = dedupe_runtime_build_copy_lines(s_tail)
    return "".join(s_ded), r10, r10d, r_pm, r20, r_tail, r_rtd


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Remove manifest-unlisted COPY in section #10 (MAT markers) and unneeded "
            "/build/<dir>/ runtime copies in #20 (LUCID_RUNTIME_COPY_FROM_BUILD_*)."
        )
    )
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--host-config", type=Path, default=DEFAULT_HOST)
    ap.add_argument("--mat-dir", type=Path, default=DEFAULT_MAT_DIR)
    ap.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    ap.add_argument("--no-source-map", action="store_true")
    ap.add_argument("--x-files", type=Path, default=DEFAULT_X_FILES)
    ap.add_argument("--no-x-files-check", action="store_true")
    ap.add_argument("--warn-x-files", action="store_true", help="Warn on manifest paths not in x-files keys")
    ap.add_argument("--dry-run", action="store_true", help="Preview only (default if neither --write nor --dry-run)")
    ap.add_argument("--write", action="store_true", help="Write Dockerfiles after cleanup")
    ap.add_argument("--backup-ext", default="", help="e.g. .cleanup.bak before write")
    ap.add_argument("--only-dockerfile", action="append", default=[], metavar="REPO_REL_PATH")
    ap.add_argument("--compose-service", default=None)
    ap.add_argument("--include-devcontainer", action="store_true")
    ap.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT, help="Validates section ids exist (info only)")
    args = ap.parse_args()

    if not args.write and not args.dry_run:
        args.dry_run = True

    repo = _repo_root(args.repo_root)
    layout_path = args.layout if args.layout.is_absolute() else repo / args.layout
    doc = _load_json(layout_path)
    if isinstance(doc, dict):
        ids = {str(s.get("id")) for s in (doc.get("sections") or []) if isinstance(s, dict)}
        if "COPY_DIRECTORIES" in ids and "COPY_CONTENT" in ids:
            print(
                f"{_TOOL}: layout OK (COPY_DIRECTORIES #10, COPY_CONTENT #20) {layout_path.relative_to(repo)}",
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

    xf_keys: Set[str] = set()
    if not args.no_x_files_check:
        xfp = args.x_files if args.x_files.is_absolute() else repo / args.x_files
        if xfp.is_file():
            xf_keys = x_files_keys(repo, xfp)

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

    forced = (args.compose_service or "").strip() or None
    if forced and len(dockerfiles) != 1:
        print("error: --compose-service requires exactly one Dockerfile target", file=sys.stderr)
        return 2

    changed = 0
    skipped = 0
    total_r10 = total_r10d = total_r_pm = total_r20 = total_r_tail = total_r_rtd = 0

    for df in dockerfiles:
        rel_df = df.resolve().relative_to(repo.resolve()).as_posix()
        compose = forced
        note: Optional[str] = None
        if not compose:
            compose, note = resolve_compose_service(
                repo,
                df,
                full_map,
                basename_map,
                basename_canonical,
                fallback_df_to_compose,
                explicit_map,
            )
        else:
            note = "--compose-service"
        if note:
            print(f"NOTE {rel_df}: {note}", flush=True)
        if not compose:
            print(f"SKIP {rel_df}: unresolved compose_service", flush=True)
            skipped += 1
            continue
        mf = mat_dir / f"{compose}_manifest.json"
        if not mf.is_file():
            print(f"SKIP {rel_df}: no {mf.relative_to(repo)}", flush=True)
            skipped += 1
            continue
        mdoc = _load_json(mf)
        if not isinstance(mdoc, dict):
            skipped += 1
            continue
        paths = collect_mat_manifest_paths(mdoc)
        paths = merge_source_map_extras(compose, paths, sm)
        allowed = set(paths)
        if not allowed:
            print(f"SKIP {rel_df}: empty allowlist after manifest merge", flush=True)
            skipped += 1
            continue

        if args.warn_x_files and xf_keys:
            _ok, bad = check_x_files(paths, xf_keys)
            for b in bad:
                print(f"WARN {rel_df}: not in x-files section_to_canonical: {b}", flush=True)

        raw = df.read_text(encoding="utf-8")
        if MARK_MAT_COPY_BEGIN not in raw or MARK_MAT_COPY_END not in raw:
            print(f"SKIP {rel_df}: missing MAT COPY markers (#10)", flush=True)
            skipped += 1
            continue
        if MARK_RUNTIME_COPY_BEGIN not in raw or MARK_RUNTIME_COPY_END not in raw:
            print(f"SKIP {rel_df}: missing LUCID_RUNTIME_COPY_FROM_BUILD markers (#20)", flush=True)
            skipped += 1
            continue

        new_text, r10, r10d, r_pm, r20, r_tail, r_rtd = process_dockerfile_text(raw, allowed)
        total_r10 += r10
        total_r10d += r10d
        total_r_pm += r_pm
        total_r20 += r20
        total_r_tail += r_tail
        total_r_rtd += r_rtd
        if new_text == raw:
            print(f"UNCHANGED {rel_df}", flush=True)
            continue
        print(
            f"{'[dry-run] ' if args.dry_run else ''}CLEANUP {rel_df}: "
            f"remove #10={r10} #10_dedupe={r10d} post_mat={r_pm} #20={r20} runtime_tail={r_tail} "
            f"runtime_dedupe={r_rtd} (manifest {mf.name})",
            flush=True,
        )
        changed += 1
        if args.dry_run:
            continue
        ext = (args.backup_ext or "").strip()
        if ext:
            if not ext.startswith("."):
                ext = "." + ext
            bak = df.with_name(df.name + ext)
            bak.write_text(raw, encoding="utf-8", newline="\n")
        df.write_text(new_text, encoding="utf-8", newline="\n")

    print(
        f"Done: files_with_changes={changed}, skipped={skipped}, "
        f"total_removed #10={total_r10} #10_dedupe={total_r10d} post_mat={total_r_pm} "
        f"#20={total_r20} runtime_tail={total_r_tail} runtime_dedupe={total_r_rtd}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

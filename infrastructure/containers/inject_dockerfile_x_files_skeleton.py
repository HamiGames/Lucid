#!/usr/bin/env python3
"""
Inject (1) directory skeleton under WORKDIR /build in builder stage 1, and (2) pip wheel + offline
install for requirements when missing.

When pip wheels are enabled (default), the wheel block is injected first (``/build/wheels``: cache-mounted
prep ``RUN``, ``COPY`` requirements, ``pip wheel``, then ``pip install --find-links /build/wheels``), then
the skeleton ``RUN`` is placed **immediately after** ``# LUCID_PIP_WHEELS_END`` in the builder stage.
If wheels are skipped (``--no-wheels``) or no wheel block is produced, the skeleton uses the historic
anchor: after the last apt/pip cache ``RUN`` in the skeleton slice, else before the first qualifying
plain ``COPY``.

Skeleton directories (and the optional runtime ``LUCID_RUNTIME_COPY_FROM_BUILD_*`` block) are:

- **(A)** ``x-files-listing.txt`` dirs, restricted to prefixes from plain ``COPY``/``ADD`` in the
  skeleton slice (after first ``WORKDIR /build`` through builder stage or first ``WORKDIR /app``);
  never ``COPY --from=``; ``./wheels`` omitted.
- **(B)** **union** of directory roots from those same lines, plus host ``os.walk`` for each
  single-source **directory** copy inside that slice.

Plain ``COPY``/``ADD`` **before** ``WORKDIR /build`` (e.g. apt scaffold) and anything **after**
``WORKDIR /app`` in the builder stage do not define skeleton dirs. The last/runtime ``FROM`` is never
scanned for skeleton.

**Default CLI is dry-run** (no disk writes). You must pass ``--apply`` to rewrite Dockerfiles; otherwise
the skeleton block on disk never updates.

**Insert order (skeleton):** after ``# LUCID_PIP_WHEELS_END`` when a pip-wheel block is present;
otherwise within the builder skeleton slice prefer **after** the last apt-cache ``RUN`` and **after**
any pip-cache ``RUN`` when present, else **before** the first plain ``COPY`` in that slice. Marked
blocks are stripped before re-splice.

**Stage-1 layout path corrections** (builder plain ``COPY``/``ADD``, before skeleton): see
``STAGE1_LAYOUT_COPY_REWRITE_REFERENCE`` and :func:`rewrite_stage1_layout_copy_paths_in_stage`.
Under WORKDIR ``/build``, ``./host`` / ``./hosts`` become ``./configs``; ``./configs/services`` and
``./configs/operations`` collapse to ``./service_configs/...``; ``./infrastructure/kubernetes`` and
top-level ``./kubernetes`` (and typo ``./kurbernetes``) map to ``./service_configs/kubernetes/...``.
RDP → ``rdp``. Bare ``./infrastructure`` (alone) is still omitted from skeleton materialization.

Default listing path: repo-root ``x-files-listing.txt``; override with ``--listing``.

Scans (by default) ``infrastructure/containers/**`` and ``infrastructure/docker/**`` for
``Dockerfile`` / ``Dockerfile.*`` / ``dockerfile.*``. Extra ``--containers-root`` paths are **merged**
with the default trees (so ``infrastructure/containers/database/`` stays scanned). Use
``--scan-roots-only`` to scan **only** the paths you pass.

Usage (repo root):
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --apply

Remove injections locally (no git) — strips LUCID_* marked blocks:
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --strip
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --strip --apply

Dry-run prints what would change; you must add --apply to save. One file:
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --strip --apply --only infrastructure/containers/admin/Dockerfile.gov-client

Remove redundant mkdir-only scaffolds under /build/ or ./ (any directory; not pip/apt/mounts):
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --strip-build-scaffold --apply
  (alias: --strip-build-node-scaffold)

Normalize existing runtime (final ``FROM`` stage) ``COPY --from=<first AS name>`` lines: strip stale
``# COPY …`` hints; map ``/build/<tail>`` and ``./<tail>`` (WORKDIR ``/build``) to ``/app/<tail>``
(same tail, trailing-slash rules); normalize ``RDP`` → ``rdp`` in ``/build`` paths. Handles
backslash-continued ``COPY`` as a single instruction. The first ``FROM … AS <name>`` in the file is
the builder stage name used for ``--from=``. Does not add missing COPY lines (only fixes
``src``/``dst`` on matching lines).

**Skeleton (builder only):** dirs come **only** from plain ``COPY``/``ADD`` in the slice after the
first ``WORKDIR /build`` (or first /build-layout ``COPY``) through the end of the builder stage or
first ``WORKDIR /app`` there — never from the last/runtime ``FROM`` and never from
``COPY --from=``. ``./wheels`` is excluded. Plus host ``os.walk`` for single-source **directory**
copies in that slice. ``x-files-listing.txt`` is intersected using prefixes from the same slice.

**Runtime COPY line fix** (optional, separate): normalizes ``COPY --from=<builder>`` in the **last**
``FROM`` only. Use ``--with-sync-build-app-copy`` before inject, or ``--sync-build-app-copy-only``.

  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --with-sync-build-app-copy --apply

  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --sync-build-app-copy-only --apply

Runtime stage: insert ``# LUCID_RUNTIME_COPY_FROM_BUILD_*`` with lines like
``COPY --from=<builder_stage> --chown=65532:65532 /build/<rel>/ /app/<rel>/`` (literal chown; stage name
from the first ``FROM … AS`` in the file). ``<rel>`` uses ``rdp`` not ``RDP``. Before insert, removes
``# COPY …`` lines in the final stage. Directory set is the **union** of (1) listing ∩ approved
prefixes and (2) **canonical destinations** from the **builder** stage (``COPY``/``ADD``, not
``--from=``), including new folders not yet in ``x-files-listing.txt``. The builder stage for
skeleton sources is the first ``FROM`` slice with plain ``COPY``/``ADD`` into ``/build``, else the
first slice with ``WORKDIR /build``, else the first ``FROM … AS`` name. Insert **after** the last
``ENV`` in the final stage (or last ``LABEL`` if there is no ``ENV``), same rule as
``lib_search_and_inject.py``. ``--with-sync-build-app-copy`` merges backslash-continued ``COPY`` in
the final stage, then fixes ``src``/``dst``; it warns on ``COPY --from=<first AS>`` lines before that
point.

  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --inject-runtime-copy-from-build --apply
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --with-runtime-copy-from-build --apply

  # One-shot: wheels + skeleton (from builder plain COPY between WORKDIR /build … /app) +
  # LUCID_RUNTIME_COPY_FROM_BUILD after last LABEL/ENV in the final stage, then last-FROM
  # COPY --from= path normalization (same as --with-sync-build-app-copy after inject).
  python infrastructure/containers/inject_dockerfile_x_files_skeleton.py --run-full-with-sync --apply

Runtime ``COPY --from=<first AS>`` dedupe: when replacing ``# LUCID_RUNTIME_COPY_FROM_BUILD_*``,
any other line in the **last** ``FROM`` stage that copies the same directory tree
``/build/<rel>/`` → ``/app/<rel>/`` (optional ``--chown``, ``./`` src allowed) is removed so
manual duplicates next to apt/FHS copies are not left behind.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

from lib_search_and_inject import (
    find_insert_after_workdir_arg_label_env_runtime,
    normalize_glued_lucid_marker_lines,
    resolve_path_from_repo,
    strip_commented_copy_lines_in_last_stage,
)

MARK_SKELETON_BEGIN = "# LUCID_X_FILES_SKELETON_BEGIN"
MARK_SKELETON_END = "# LUCID_X_FILES_SKELETON_END"
MARK_WHEEL_BEGIN = "# LUCID_PIP_WHEELS_BEGIN"
MARK_WHEEL_END = "# LUCID_PIP_WHEELS_END"
MARK_RUNTIME_COPY_BEGIN = "# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN"
MARK_RUNTIME_COPY_END = "# LUCID_RUNTIME_COPY_FROM_BUILD_END"

REQUIREMENTS_COPY = re.compile(
    r"^\s*COPY\s+(?!--from=)(?P<src>\S*requirements\S+)\s+(?P<dst>\S+)",
    re.IGNORECASE,
)


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def wheel_keep_marker_inner_for_dockerfile(dockerfile_path: Path) -> str:
    """
    Inner string for ``printf`` into ``/build/wheels/.keep`` (shell expands ``$(date +%s)``).

    ``Dockerfile.admin-gateway`` → ``LUCID_ADMIN_GATEWAY_WHEELS_$(date +%s)``; ``dockerfile.foo`` same.
    Bare ``Dockerfile`` → ``LUCID_WHEELS_$(date +%s)``.
    """
    name = dockerfile_path.name
    stem: str
    m = re.match(r"(?i)dockerfile\.(.+)$", name)
    if m:
        stem = m.group(1)
    else:
        stem = Path(name).stem
        if stem.lower() == "dockerfile":
            stem = "WHEELS"
    slug = re.sub(r"[^0-9A-Za-z]+", "_", stem.upper()).strip("_")
    if not slug:
        slug = "WHEELS"
    return f"LUCID_{slug}_WHEELS_$(date +%s)"


def app_abs_dir_to_build_relative(abs_dir: str) -> str | None:
    """Map /app/... from x-files-listing to ./... relative to WORKDIR /build."""
    p = PurePosixPath(abs_dir)
    app_root = PurePosixPath("/app")
    sp = str(p)
    if "<" in sp or ">" in sp:
        return None
    if not sp.startswith("/app"):
        return None
    if p == app_root:
        return "."
    try:
        rel = p.relative_to(app_root)
    except ValueError:
        return None
    return "./" + "/".join(rel.parts)


def normalize_rdp_segment_path(path: str) -> str:
    """Use ./rdp/... not ./RDP/... (repo convention for build-relative paths)."""
    if not path or path == ".":
        return "."
    parts = []
    for part in PurePosixPath(path).parts:
        if part == ".":
            continue
        parts.append("rdp" if part == "RDP" else part)
    if not parts:
        return "."
    return "./" + "/".join(parts)


# Under WORKDIR /build: never treat these top-level segments as materialized trees (listing,
# skeleton, runtime COPY roots). Typical case: COPY infra/... ./service_configs/host-config.yml only.
_BLOCKED_TOP_LEVEL_BUILD_DIRS = frozenset({"host"})

# Prune noisy subtrees when expanding skeleton from host dirs (single-source directory COPY).
_SKELETON_WALK_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        ".mypy_cache",
        ".tox",
        ".pytest_cache",
        ".ruff_cache",
        ".turbo",
    }
)


def is_blocked_top_level_build_dir_path(d: str) -> bool:
    """
    True for ``./host`` / ``./host/...`` under WORKDIR ``/build`` (and ``/build/host/...`` tails).
    Must not emit skeleton mkdir, runtime ``/build/host/…``, or per-file COPY sync for that tree.
    """
    s = d.strip().replace("\\", "/")
    if s.startswith("./"):
        s = s[2:]
    elif s.startswith("/build/"):
        s = s[len("/build/") :]
    s = s.rstrip("/")
    if not s or s == ".":
        return False
    return s.split("/")[0] in _BLOCKED_TOP_LEVEL_BUILD_DIRS


#: Reference for stage-1 WORKDIR ``/build`` layout. Same segment rules as
#: :func:`_rewrite_layout_parts` and :func:`rewrite_stage1_layout_copy_path_token`.
STAGE1_LAYOUT_COPY_REWRITE_REFERENCE = """\
Stage-1 build-relative path corrections (Dockerfile plain COPY/ADD in the builder stage, and
canonical skeleton paths under WORKDIR /build):

  ./host/...            -> ./configs/...
  ./hosts/...           -> ./configs/...
  ./configs/services/... -> ./service_configs/...
  ./configs/operations/... -> ./service_configs/...
  ./infrastructure/kubernetes/... -> ./service_configs/kubernetes/...
  ./kubernetes/...     -> ./service_configs/kubernetes/...
  ./kurbernetes/...     -> ./service_configs/kubernetes/...   (common typo)

Absolute destinations under /build/ use the same inner layout. Bare ./infrastructure (no subpath)
is omitted from skeleton materialization (not rewritten in COPY lines).
"""


def _rewrite_layout_parts(parts: list[str]) -> list[str] | None:
    """
    Return rewritten path segments for WORKDIR ``/build`` layout, or ``None`` to drop this path
    from skeleton materialization (bare ``./infrastructure`` tree).
    """
    if not parts:
        return []
    if parts == ["infrastructure"]:
        return None
    if len(parts) >= 2 and parts[0] == "infrastructure" and parts[1] == "kubernetes":
        return ["service_configs", "kubernetes"] + parts[2:]
    if parts[0] == "infrastructure":
        return None
    if len(parts) >= 2 and parts[0] == "configs" and parts[1] == "services":
        return ["service_configs"] + parts[2:]
    if len(parts) >= 2 and parts[0] == "configs" and parts[1] == "operations":
        return ["service_configs"] + parts[2:]
    if parts[0] == "host" or parts[0] == "hosts":
        return ["configs"] + parts[1:]
    if parts[0] == "kubernetes" or parts[0] == "kurbernetes":
        return ["service_configs", "kubernetes"] + parts[1:]
    return parts


def canonicalize_build_skeleton_path(rel: str) -> str | None:
    """
    Lucid layout under /build: remap ``host``/``hosts``, ``configs/*``, ``infrastructure/kubernetes``,
    and top-level ``kubernetes``; omit bare ``./infrastructure``.
    Returns None if this path should not appear in the skeleton.
    """
    rel = normalize_rdp_segment_path(rel.strip())
    p = PurePosixPath(rel)
    parts = [x for x in p.parts if x != "."]
    if parts and parts[0] == "wheels":
        return None
    if parts and parts[0] in _BLOCKED_TOP_LEVEL_BUILD_DIRS:
        return None
    rw = _rewrite_layout_parts(parts)
    if rw is None:
        return None
    if not rw:
        return "."
    return "./" + "/".join(rw)


def rewrite_stage1_layout_copy_path_token(token: str) -> str | None:
    """
    Rewrite one Docker build-context path (or ``/build/...`` dest) using :func:`_rewrite_layout_parts`.
    Returns ``None`` if unchanged or if the token must not be altered (absolute non-``/build``,
    ``..``, bare ``./infrastructure``, etc.).
    """
    raw = token.strip()
    if not raw or raw == ".":
        return None
    norm = raw.replace("\\", "/")
    try:
        if ".." in PurePosixPath(norm.rstrip("/")).parts:
            return None
    except ValueError:
        return None
    had_slash = norm.endswith("/")
    work = norm.rstrip("/")
    build_abs = False
    if work.startswith("/"):
        if work.startswith("/build/"):
            build_abs = True
            inner = work[7:]
        elif work == "/build":
            inner = ""
        else:
            return None
    else:
        inner = work
        if inner.startswith("./"):
            inner = inner[2:]
    inner = inner.lstrip("/")
    if not inner:
        return None
    parts = [p for p in PurePosixPath(inner).parts if p != "."]
    if not parts:
        return None
    rw = _rewrite_layout_parts(parts)
    if rw is None or rw == parts:
        return None
    new_inner = "/".join(rw)
    if build_abs:
        rebuilt = "/build/" + new_inner
    elif norm.startswith("./") or raw.strip().startswith("./"):
        rebuilt = "./" + new_inner
    else:
        rebuilt = new_inner
    if had_slash:
        rebuilt = rebuilt.rstrip("/") + "/"
    return rebuilt if rebuilt != norm else None


def _apply_layout_rewrite_to_copyadd_shlex_paths(parts: list[str]) -> tuple[list[str], bool]:
    """Rewrite non-flag shlex tokens (COPY/ADD path arguments). Returns (new_parts, any_change)."""
    changed = False
    out: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if p.startswith("--"):
            out.append(p)
            i += 1
            continue
        nxt = rewrite_stage1_layout_copy_path_token(p)
        if nxt is not None:
            out.append(nxt)
            changed = True
        else:
            out.append(p)
        i += 1
    return out, changed


def rewrite_merged_copy_add_layout_paths(merged: str) -> tuple[str, bool]:
    """
    Apply :func:`rewrite_stage1_layout_copy_path_token` to every path argument in a merged
    ``COPY``/``ADD`` instruction (first line only; backslash-continued args collapsed). Heredoc and
    ``COPY --from=`` are left unchanged.
    """
    first = merged.split("\n", 1)[0]
    if re.search(r"^\s*COPY\s*<<", first, re.IGNORECASE) or re.search(
        r"^\s*ADD\s*<<", first, re.IGNORECASE
    ):
        return merged, False
    if re.search(r"--from\s*=", first, re.IGNORECASE):
        return merged, False
    collapsed = re.sub(r"\\\s*\n\s*", " ", merged.strip())
    m = re.match(r"^(\s*)(COPY|ADD)\s+", collapsed, re.IGNORECASE)
    if not m:
        return merged, False
    prefix, verb = m.group(1), m.group(2)
    rest = collapsed[m.end() :]
    try:
        sp = shlex.split(rest, posix=True)
    except ValueError:
        return merged, False
    new_sp, changed = _apply_layout_rewrite_to_copyadd_shlex_paths(sp)
    if not changed:
        return merged, False
    new_collapsed = prefix + verb + " " + shlex.join(new_sp)
    return new_collapsed, True


def rewrite_stage1_layout_copy_paths_in_stage(
    lines: list[str], stage_start: int, stage_end: int
) -> tuple[list[str], int]:
    """
    Rewrite plain ``COPY``/``ADD`` path tokens in ``[stage_start, stage_end)`` (builder stage)
    using :func:`STAGE1_LAYOUT_COPY_REWRITE_REFERENCE` rules. Continued ``COPY`` lines are replaced
    by a single line when any path changes.
    """
    edits = 0
    out: list[str] = []
    out.extend(lines[:stage_start])
    i = stage_start
    while i < stage_end:
        line = lines[i]
        if not re.match(r"^\s*(COPY|ADD)\s", line, re.IGNORECASE):
            out.append(line)
            i += 1
            continue
        merged, _st, after = merge_copy_or_add_instruction(lines, i, stage_end)
        new_merged, did = rewrite_merged_copy_add_layout_paths(merged)
        if did:
            edits += 1
            out.extend(new_merged.split("\n"))
        else:
            out.extend(lines[i:after])
        i = after
    out.extend(lines[stage_end:])
    return out, edits


def parse_x_files_dirs(listing_path: Path) -> list[str]:
    text = listing_path.read_text(encoding="utf-8")
    dirs_abs: set[str] = set()
    for m in re.finditer(r"x-lucid-file-path:\s*(\S+)", text):
        fp = m.group(1).strip()
        if not fp.startswith("/"):
            continue
        p = PurePosixPath(fp)
        cur = p.parent
        while cur != PurePosixPath("/") and cur.parts:
            dirs_abs.add(str(cur))
            cur = cur.parent

    dirs_rel: set[str] = set()
    for d in dirs_abs:
        rd = app_abs_dir_to_build_relative(d)
        if rd is None:
            continue
        can = canonicalize_build_skeleton_path(rd)
        if can is not None:
            dirs_rel.add(can)
    return sorted(dirs_rel, key=lambda s: (s.count("/"), s))


def dest_to_copy_relpath_under_build(dest: str) -> str | None:
    """Normalize COPY destination to a ./... path under WORKDIR /build."""
    d = dest.strip().strip('"').strip("'")
    if d.startswith("/build/"):
        inner = d[7:].rstrip("/")
        if not inner:
            return "."
        return normalize_rdp_segment_path("./" + inner)
    if d == "/build":
        return "."
    if d.startswith("/") and not d.startswith("/build"):
        return None
    if d.startswith("./"):
        return normalize_rdp_segment_path(d)
    if not d:
        return None
    return normalize_rdp_segment_path("./" + d.lstrip("./"))


def parse_copy_or_add_dest_from_merged(merged: str) -> str | None:
    """Last path token of a ``COPY`` or ``ADD`` instruction (first line only; skips ``COPY <<``)."""
    first = merged.split("\n", 1)[0]
    s = first.strip()
    if not s or s.startswith("#"):
        return None
    if not re.match(r"^\s*(COPY|ADD)\s", s, re.IGNORECASE):
        return None
    if re.search(r"--from\s*=", s, re.IGNORECASE):
        return None
    if re.search(r"^\s*COPY\s*<<", s, re.IGNORECASE) or re.search(
        r"^\s*ADD\s*<<", s, re.IGNORECASE
    ):
        return None
    rest = re.sub(r"^\s*(COPY|ADD)\s+", "", s, flags=re.IGNORECASE)
    rest = re.sub(r"\\\s*\n\s*", " ", rest)
    try:
        parts = shlex.split(rest)
    except ValueError:
        return None
    filtered: list[str] = []
    for p in parts:
        if p.startswith("--"):
            continue
        filtered.append(p)
    if len(filtered) < 2:
        return None
    return filtered[-1]


def parse_copy_dest_from_merged(merged: str) -> str | None:
    """Backward-compatible alias for :func:`parse_copy_or_add_dest_from_merged`."""
    return parse_copy_or_add_dest_from_merged(merged)


def parse_copy_sources_and_dest_from_merged(merged: str) -> tuple[list[str], str | None]:
    """
    Path arguments for a merged ``COPY``/``ADD`` line: all sources, then destination (last token).
    Skips ``--chown=`` etc. Returns ``([], None)`` when not parseable.
    """
    first = merged.split("\n", 1)[0]
    s = first.strip()
    if not s or s.startswith("#"):
        return [], None
    if not re.match(r"^\s*(COPY|ADD)\s", s, re.IGNORECASE):
        return [], None
    if re.search(r"--from\s*=", s, re.IGNORECASE):
        return [], None
    if re.search(r"^\s*COPY\s*<<", s, re.IGNORECASE) or re.search(
        r"^\s*ADD\s*<<", s, re.IGNORECASE
    ):
        return [], None
    rest = re.sub(r"^\s*(COPY|ADD)\s+", "", s, flags=re.IGNORECASE)
    rest = re.sub(r"\\\s*\n\s*", " ", rest)
    try:
        parts = shlex.split(rest)
    except ValueError:
        return [], None
    filtered: list[str] = []
    for p in parts:
        if p.startswith("--"):
            continue
        filtered.append(p)
    if len(filtered) < 2:
        return [], None
    return filtered[:-1], filtered[-1]


def _repo_resolved_copy_source_path(repo_root: Path, source_token: str) -> Path | None:
    """Build-context path for a single COPY source; None if unsafe or outside repo."""
    raw = source_token.strip().strip('"').strip("'").replace("\\", "/")
    if not raw or raw.startswith("/"):
        return None
    try:
        p = PurePosixPath(raw)
    except ValueError:
        return None
    if ".." in p.parts:
        return None
    abs_path = (repo_root / raw).resolve()
    try:
        abs_path.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return abs_path


def collect_host_tree_skeleton_dirs_from_stage1(content: str, repo_root: Path) -> set[str]:
    """
    Like :func:`approved_skeleton_prefixes_from_stage1_copy`, but walks host directories for
    single-source directory ``COPY``/``ADD`` **only inside** :func:`skeleton_copy_scan_slice`.
    Never uses ``COPY --from=`` or lines after ``WORKDIR /app`` in the builder stage.
    """
    plain = [ln.rstrip("\r\n") for ln in content.splitlines()]
    s0, s1 = builder_stage_range(plain)
    bounds = skeleton_copy_scan_slice(plain, s0, s1)
    if bounds is None:
        return set()
    scan_lo, scan_hi = bounds
    out: set[str] = set()
    i = scan_lo
    while i < scan_hi:
        line = plain[i]
        if not re.match(r"^\s*(COPY|ADD)\s", line, re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_copy_or_add_instruction(plain, i, s1)
        i = after
        sources, raw_dest = parse_copy_sources_and_dest_from_merged(merged)
        if not sources or raw_dest is None or len(sources) != 1:
            continue
        rel = dest_to_copy_relpath_under_build(raw_dest)
        if rel is None:
            continue
        sp = _repo_resolved_copy_source_path(repo_root, sources[0])
        if sp is None or not sp.is_dir():
            continue
        dest_base = normalize_rdp_segment_path(rel.rstrip("/"))
        if dest_base in (".", ""):
            continue
        skip = _SKELETON_WALK_SKIP_DIR_NAMES
        for dirpath, dirnames, _files in os.walk(sp, topdown=True):
            dirnames[:] = [d for d in dirnames if d not in skip]
            sub = Path(dirpath).relative_to(sp)
            tail = "" if sub == Path(".") else sub.as_posix()
            if tail:
                cand = f"{dest_base}/{tail}"
            else:
                cand = dest_base
            if not cand.startswith("./"):
                cand = "./" + cand.lstrip("/")
            can = canonicalize_build_skeleton_path(cand)
            if can is None or is_blocked_top_level_build_dir_path(can):
                continue
            out.add(can)
    return out


def _copy_dest_leaf_looks_like_file(name: str) -> bool:
    """Heuristic: single-file COPY dest (exclude basename from approved roots, keep parents)."""
    if name in (".", ""):
        return False
    if name.endswith(".keep"):
        return False
    if name.startswith(".env"):
        return True
    if "." not in name:
        return False
    ext = name.rsplit(".", 1)[-1].lower()
    return ext in (
        "txt",
        "yaml",
        "yml",
        "json",
        "py",
        "md",
        "lock",
        "toml",
        "cfg",
        "ini",
        "conf",
        "pem",
        "crt",
        "key",
        "secrets",
        "master",
    )


def approved_skeleton_prefixes_from_stage1_copy(content: str) -> frozenset[str]:
    """
    Canonical ``./...`` prefixes for skeleton/listing approval from **plain** ``COPY``/``ADD`` only
    (never ``COPY --from=``), strictly between the first ``WORKDIR /build`` and the earlier of
    (end of builder stage, first ``WORKDIR /app`` in that stage). See :func:`skeleton_copy_scan_slice`.
    """
    plain = [ln.rstrip("\r\n") for ln in content.splitlines()]
    s0, s1 = builder_stage_range(plain)
    bounds = skeleton_copy_scan_slice(plain, s0, s1)
    if bounds is None:
        return frozenset()
    scan_lo, scan_hi = bounds
    out: set[str] = set()
    i = scan_lo
    while i < scan_hi:
        line = plain[i]
        if not re.match(r"^\s*(COPY|ADD)\s", line, re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_copy_or_add_instruction(plain, i, s1)
        i = after
        raw_dest = parse_copy_or_add_dest_from_merged(merged)
        if raw_dest is None:
            continue
        rel = dest_to_copy_relpath_under_build(raw_dest)
        if rel is None:
            continue
        is_dir_dest = raw_dest.rstrip().endswith(("/", "\\"))
        p = PurePosixPath(rel)
        parts = [x for x in p.parts if x != "."]
        if not parts:
            continue
        if not is_dir_dest and _copy_dest_leaf_looks_like_file(parts[-1]):
            parts = parts[:-1]
        for j in range(1, len(parts) + 1):
            cand = "./" + "/".join(parts[:j])
            can = canonicalize_build_skeleton_path(cand)
            if can is not None:
                out.add(can)
    return frozenset(out)


def filter_listing_dirs_by_copy_approval(
    listing_dirs: list[str],
    approved: frozenset[str],
) -> list[str]:
    """Keep listing dirs that sit under at least one approved ``./`` prefix (always keep ``.``)."""
    if not approved:
        return ["."]
    out: list[str] = []
    for d in listing_dirs:
        if d == ".":
            out.append(d)
            continue
        norm_d = d.rstrip("/")
        ok = False
        for a in approved:
            if a == ".":
                ok = True
                break
            na = a.rstrip("/")
            if norm_d == na or norm_d.startswith(na + "/"):
                ok = True
                break
        if ok:
            out.append(d)
    return sorted(set(out), key=lambda s: (s.count("/"), s))


def skeleton_dirs_for_dockerfile(
    content: str,
    listing_path: Path,
    repo_root: Path | None = None,
) -> list[str]:
    """
    ``parse_x_files_dirs`` restricted to builder ``COPY``/``ADD``-approved prefixes, **union**
    stage-1 destination roots (see :func:`stage1_dest_dirs_for_runtime_copy`) and **union** every
    ``./…`` path under each single-source **directory** ``COPY``/``ADD`` by walking the matching
    tree under ``repo_root`` (build context = repo root), e.g. ``COPY admin/ ./admin/``.
    """
    if repo_root is None:
        repo_root = repo_root_from_here()
    listing = parse_x_files_dirs(listing_path)
    approved = approved_skeleton_prefixes_from_stage1_copy(content)
    filtered = filter_listing_dirs_by_copy_approval(listing, approved)
    stage1 = stage1_dest_dirs_for_runtime_copy(content)
    host_dirs = collect_host_tree_skeleton_dirs_from_stage1(content, repo_root)
    merged = sorted(
        set(filtered) | set(stage1) | host_dirs,
        key=lambda s: (s.count("/"), s),
    )
    merged = [d for d in merged if not is_blocked_top_level_build_dir_path(d)]
    return merged if merged else ["."]


def stage1_dest_dirs_for_runtime_copy(content: str) -> list[str]:
    """
    One ``./...`` root per plain ``COPY``/``ADD`` in :func:`skeleton_copy_scan_slice` (same window as
    skeleton; no ``COPY --from=``; nothing after ``WORKDIR /app`` in the builder stage).
    """
    plain = [ln.rstrip("\r\n") for ln in content.splitlines()]
    s0, s1 = builder_stage_range(plain)
    bounds = skeleton_copy_scan_slice(plain, s0, s1)
    if bounds is None:
        return []
    scan_lo, scan_hi = bounds
    acc: set[str] = set()
    i = scan_lo
    while i < scan_hi:
        line = plain[i]
        if not re.match(r"^\s*(COPY|ADD)\s", line, re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_copy_or_add_instruction(plain, i, s1)
        i = after
        raw_dest = parse_copy_or_add_dest_from_merged(merged)
        if raw_dest is None:
            continue
        rel = dest_to_copy_relpath_under_build(raw_dest)
        if rel is None:
            continue
        is_dir_dest = raw_dest.rstrip().endswith(("/", "\\"))
        p = PurePosixPath(rel)
        parts = [x for x in p.parts if x != "."]
        if not parts:
            continue
        if not is_dir_dest and _copy_dest_leaf_looks_like_file(parts[-1]):
            parts = parts[:-1]
        if not parts:
            continue
        cand = "./" + "/".join(parts)
        can = canonicalize_build_skeleton_path(cand)
        if can is not None:
            acc.add(can)
    return sorted(acc, key=lambda s: (s.count("/"), s))


def shell_quote_single(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _unique_dirs_sorted(dirs: list[str]) -> list[str]:
    """Stable order, no duplicate paths (avoids doubled ``mkdir`` / ``for d in`` entries)."""
    return sorted(set(dirs), key=lambda s: (s.count("/"), s))


def build_skeleton_run_block(dirs: list[str]) -> str:
    dirs_u = _unique_dirs_sorted(dirs)
    if not dirs_u:
        dirs_u = ["."]
    lines = [
        MARK_SKELETON_BEGIN,
        "# Dirs: (listing ∩ COPY-approved) ∪ builder-stage COPY roots; after pip cache RUN or before first /build COPY",
        "RUN set -eux; \\",
    ]
    mkdir_parts = ["mkdir -p"] + [shell_quote_single(d) for d in dirs_u]
    lines.append("    " + " ".join(mkdir_parts) + "; \\")
    lines.append("    for d in \\")
    for d in dirs_u:
        lines.append(f"      {shell_quote_single(d)} \\")
    lines.append("    ; do \\")
    lines.append(
        "      printf 'LUCID_X_FILES_SKELETON_%s' \"$(date +%s)\" > \"$d/.keep\"; \\"
    )
    lines.append("      touch \"$d/.keep\"; \\")
    lines.append("    done")
    lines.append(MARK_SKELETON_END)
    return "\n".join(lines) + "\n"


def strip_marked_block(text: str, begin: str, end: str) -> str:
    """Remove one or more begin/end sections; line-based (reliable for huge RUN blocks)."""
    text = normalize_glued_lucid_marker_lines(text)
    begin_s = begin.strip()
    end_s = end.strip()
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == begin_s:
            j = i + 1
            while j < len(lines) and lines[j].strip() != end_s:
                j += 1
            if j < len(lines):
                i = j + 1
                continue
            out.append(lines[i])
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def strip_orphan_skeleton_without_begin_marker(text: str) -> str:
    """
    Remove legacy skeleton ``RUN`` blocks that end with ``# LUCID_X_FILES_SKELETON_END`` but never had
    ``# LUCID_X_FILES_SKELETON_BEGIN`` (e.g. merged tool output + inject), so ``strip_marked_block``
    cannot remove them and duplicates would accumulate.
    """
    begin_s = MARK_SKELETON_BEGIN.strip()
    end_s = MARK_SKELETON_END.strip()
    lines = text.splitlines(keepends=True)
    plain = [ln.rstrip("\r\n") for ln in lines]
    n = len(plain)
    end_indices = [i for i in range(n) if plain[i].strip() == end_s]
    remove = [False] * n
    prev_end = -1
    for ei in end_indices:
        has_begin = any(plain[j].strip() == begin_s for j in range(prev_end + 1, ei))
        if has_begin:
            prev_end = ei
            continue
        j = ei - 1
        while j >= 0 and plain[j].strip() == "":
            j -= 1
        if j < 0:
            prev_end = ei
            continue
        run_start: int | None = None
        for k in range(j, -1, -1):
            if re.match(r"^\s*RUN\s", plain[k], re.IGNORECASE):
                merged, _s, _after = merge_run_block(plain, k, ei)
                if "LUCID_X_FILES_SKELETON" in merged or (
                    "for d in" in merged and "mkdir -p" in merged
                ):
                    run_start = k
                    break
        if run_start is None:
            prev_end = ei
            continue
        start = run_start
        while start > 0 and plain[start - 1].strip().startswith("#"):
            pl = plain[start - 1]
            if "Dirs:" in pl or "stage-1" in pl.lower():
                start -= 1
            else:
                break
        for idx in range(start, ei + 1):
            remove[idx] = True
        prev_end = ei
    out = [lines[k] for k in range(n) if not remove[k]]
    return "".join(out)


def strip_all_injections(text: str) -> str:
    while True:
        t = strip_marked_block(text, MARK_SKELETON_BEGIN, MARK_SKELETON_END)
        if t == text:
            break
        text = t
    text = strip_orphan_skeleton_without_begin_marker(text)
    text = strip_marked_block(text, MARK_WHEEL_BEGIN, MARK_WHEEL_END)
    text = strip_marked_block(text, MARK_RUNTIME_COPY_BEGIN, MARK_RUNTIME_COPY_END)
    return text


def _is_redundant_build_mkdir_scaffold_run(merged: str) -> bool:
    """
    True if this RUN only creates dirs under /build/ or ./ (WORKDIR /build) with optional
    .keep markers / chown — no installs, mounts, compilers, or LUCID-injected blocks.
    """
    s = merged.strip()
    if not re.match(r"^RUN\s", s, re.IGNORECASE):
        return False
    if "LUCID_X_FILES_SKELETON" in merged or "LUCID_PIP_WHEELS" in merged:
        return False
    if "mkdir -p" not in merged:
        return False
    if "/build/" not in merged and not re.search(r"\./[\w./-]", merged):
        return False
    # Shell loops (e.g. LUCID skeleton for d in …) — use --strip on marked blocks instead
    if re.search(r"\bfor\s+d\s+in\s+", merged, re.IGNORECASE):
        return False

    lower = merged.lower()
    forbidden_patterns = [
        r"pip\s+install",
        r"pip\s+wheel",
        r"pip\s+download",
        r"pip\s+uninstall",
        r"apt-get",
        r"\bapt\s+install\b",
        r"\bcurl\b",
        r"\bwget\b",
        r"\bgcc\b",
        r"g\+\+",
        r"\bcmake\b",
        r"--mount",
        r"python\d*\.?\d*\s+-m\s+",
        r"\bconda\b",
        r"\bgit\s+clone",
        r"\bninja\b",
        r"\bpy_compile\b",
        r"\bnpm\s+",
        r"\s+make\s+",
        r"^\s*make\s+",
    ]
    for pat in forbidden_patterns:
        if re.search(pat, lower):
            return False
    return True


def strip_build_scaffold_runs(text: str) -> str:
    """
    Remove optional `# ... scaffold ...` comment plus RUN blocks that only mkdir/printf/touch/chown/chmod
    under /build/ or ./ (any subdirectory, not only node).

    Only the **first build stage** is scanned (from first FROM through the line before the second
    FROM). Scaffolds after a runtime `FROM` are left alone.
    """
    plain = text.splitlines(keepends=False)
    n = len(plain)
    s0, s1 = stage1_range(plain)
    out: list[str] = []
    i = 0
    while i < n:
        if i < s0 or i >= s1:
            out.append(plain[i])
            i += 1
            continue
        if (
            i < n - 1
            and plain[i].strip().startswith("#")
            and "scaffold" in plain[i].lower()
            and re.match(r"^\s*RUN\s", plain[i + 1], re.IGNORECASE)
        ):
            merged, _, after = merge_run_block(plain, i + 1, n)
            if _is_redundant_build_mkdir_scaffold_run(merged):
                i = after
                continue
        if re.match(r"^\s*RUN\s", plain[i], re.IGNORECASE):
            merged, _, after = merge_run_block(plain, i, n)
            if _is_redundant_build_mkdir_scaffold_run(merged):
                i = after
                continue
        out.append(plain[i])
        i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def strip_build_node_scaffold_run(text: str) -> str:
    """Backward-compatible name for strip_build_scaffold_runs."""
    return strip_build_scaffold_runs(text)


def expected_app_dest_for_build_src(src: str) -> str | None:
    """Mirror WORKDIR /build paths under /app: /build/foo/bar → /app/foo/bar."""
    if not src.startswith("/build/"):
        return None
    return "/app/" + src[len("/build/") :]


def normalize_rdp_segments_in_rel(rel: str) -> str:
    """Path segment ``RDP`` → ``rdp`` (repo convention; matches skeleton / sync)."""
    if not rel or rel == ".":
        return rel
    return "/".join("rdp" if p == "RDP" else p for p in rel.split("/"))


def normalize_rdp_in_abs_build_path(path: str) -> str:
    """Normalize ``/build/...`` so directory segment ``RDP`` becomes ``rdp``; preserve trailing ``/``."""
    p = path.strip().strip('"').strip("'")
    if not p.startswith("/build"):
        return path
    trail = p.endswith("/") and len(p) > len("/build/")
    body = p.rstrip("/")
    if body == "/build":
        return "/build/" if trail else "/build"
    rest = body[len("/build/") :]
    if not rest:
        return "/build/"
    fixed = normalize_rdp_segments_in_rel(rest)
    out = "/build/" + fixed
    if trail:
        out += "/"
    return out


def resolve_build_copy_src_for_runtime_sync(src: str) -> str | None:
    """
    Map ``COPY --from=<builder>`` source to canonical ``/build/...`` for /app dst sync.
    - ``./rel`` under WORKDIR ``/build`` → ``/build/rel``
    - Normalize ``RDP`` → ``rdp`` in the path
    Returns None for sources not under the build tree (e.g. ``/usr``, ``/etc``).
    """
    s = src.strip().strip('"').strip("'")
    if s.startswith("/build/") or s == "/build":
        return normalize_rdp_in_abs_build_path(s + ("/" if s == "/build" else ""))
    if s.startswith("./"):
        tail = s[2:].lstrip("/")
        if not tail:
            base = "/build/"
        else:
            base = "/build/" + tail
        if s.endswith("/") and not base.endswith("/"):
            base += "/"
        return normalize_rdp_in_abs_build_path(base)
    return None


def _replace_last_two_path_tokens(parts: list[str], new_src: str, new_dst: str) -> list[str] | None:
    indices = [i for i, p in enumerate(parts) if not p.startswith("--")]
    if len(indices) < 2:
        return None
    i_src, i_dst = indices[-2], indices[-1]
    out = list(parts)
    out[i_src] = new_src
    out[i_dst] = new_dst
    return out


def copy_line_matches_from_stage(line: str, builder_stage: str) -> bool:
    """True if ``COPY`` line uses ``--from=<builder_stage>`` (quoted or not, case-insensitive)."""
    m = re.search(r"--from\s*=\s*(\S+)", line, re.IGNORECASE)
    if not m:
        return False
    val = m.group(1).strip().strip('"').strip("'")
    return val.lower() == builder_stage.lower()


def build_and_app_paths_from_stage1_copy_dest(dest: str) -> tuple[str, str] | None:
    """
    Map a stage-1 COPY destination (relative ``./…`` or absolute ``/build/…`` under WORKDIR ``/build``)
    to ``(/build/…, /app/…)`` for runtime COPY. Returns None if not under ``/build`` layout.
    Directory destinations use a trailing ``/`` on both sides; files do not.
    """
    raw = dest.strip()
    rel = dest_to_copy_relpath_under_build(raw)
    if rel is None:
        return None
    rel = normalize_rdp_segment_path(rel)
    if rel == ".":
        return None
    inner = rel[2:] if rel.startswith("./") else rel.lstrip("/")
    if not inner:
        return None
    is_dir = raw.endswith("/")
    src_abs = "/build/" + inner + ("/" if is_dir else "")
    exp = expected_app_dest_for_build_src(src_abs)
    if exp is None:
        return None
    if is_dir and not exp.endswith("/"):
        exp += "/"
    return src_abs, exp


def format_sync_runtime_copy_line(builder_stage: str, chown: str, src: str, dst: str) -> str:
    """``COPY --from=<stage> --chown=<chown> <src> <dst>`` (single line, no newline)."""
    return f"COPY --from={builder_stage} --chown={chown} {src} {dst}"


def _intentional_flatten_to_app_root(dst: str) -> bool:
    """True when /build/... is copied to /app or /app/ on purpose (e.g. top_py → /app/)."""
    return PurePosixPath(dst) == PurePosixPath("/app")


def normalize_copy_build_to_app_line(line: str, builder_stage: str) -> str:
    """
    For ``COPY --from=<builder_stage> ... <src> <dst>`` where src is under ``/build/``, set dst to
    ``/app/`` + same relative tail as ``/build/`` (including trailing slash matching src).
    Other COPY lines are returned unchanged.
    Skips non-``/build`` sources (e.g. ``/usr/local``) and intentional flattens to ``/app`` or ``/app/``.
    Uses string equality for dst vs expected so ``/app/api`` and ``/app/api/`` are not treated
    as the same (Docker COPY trailing-slash semantics differ from pathlib).
    """
    if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
        return line
    if not copy_line_matches_from_stage(line, builder_stage):
        return line
    prefix_m = re.match(r"^(\s*)", line)
    prefix = prefix_m.group(1) if prefix_m else ""
    rest = line[len(prefix) :]
    if not re.match(r"^COPY\s", rest, re.IGNORECASE):
        return line
    rest_after = re.sub(r"^COPY\s+", "", rest, count=1, flags=re.IGNORECASE)
    try:
        parts = shlex.split(rest_after)
    except ValueError:
        return line
    if len(parts) < 2:
        return line
    path_args = [p for p in parts if not p.startswith("--")]
    if len(path_args) < 2:
        return line
    src, dst = path_args[-2], path_args[-1]
    resolved_src = resolve_build_copy_src_for_runtime_sync(src)
    if resolved_src is None:
        return line
    expected = expected_app_dest_for_build_src(resolved_src)
    if expected is None:
        return line
    if _intentional_flatten_to_app_root(dst):
        return line
    if resolved_src == src and dst == expected:
        return line
    new_parts = _replace_last_two_path_tokens(parts, resolved_src, expected)
    if new_parts is None:
        return line
    if line.endswith("\r\n"):
        ending = "\r\n"
    elif line.endswith("\n"):
        ending = "\n"
    else:
        ending = ""
    return prefix + "COPY " + shlex.join(new_parts) + ending


def sync_build_app_copy_paths_in_text(text: str) -> tuple[str, int]:
    """
    In the **last** ``FROM`` stage only (runtime image): remove ``# COPY …`` hint lines, then rewrite
    ``COPY --from=<first AS name>`` so ``/build/…`` (or ``./…``) src maps to matching ``/app/…``
    dst; ``RDP`` → ``rdp`` in ``/build`` paths. Does not read builder plain ``COPY`` and does not
    affect ``LUCID_X_FILES_SKELETON``.
    """
    builder_stage = extract_builder_stage_name(text)
    plain = text.splitlines(keepends=False)
    for ln, ltxt in runtime_copy_from_builder_before_label_env_violations(plain, builder_stage):
        print(
            f"warning: line {ln}: COPY --from={builder_stage} appears before last LABEL/ENV in "
            f"runtime stage (move after last ENV, or after last LABEL if no ENV): {ltxt[:120]}"
            f"{'…' if len(ltxt) > 120 else ''}",
            file=sys.stderr,
        )
    plain, n_commented_removed = strip_commented_copy_lines_in_last_stage(plain)
    plain, n_host_removed = strip_blocked_host_tree_runtime_copies_in_last_stage(plain, builder_stage)
    from_idx_rt = [i for i, line in enumerate(plain) if re.match(r"^\s*FROM\s", line, re.IGNORECASE)]
    if len(from_idx_rt) < 2:
        stage_start, stage_end = 0, len(plain)
    else:
        stage_start = from_idx_rt[-1]
        stage_end = len(plain)
    path_fixes = 0
    out: list[str] = []
    i = 0
    while i < len(plain):
        if i < stage_start or i >= stage_end:
            out.append(plain[i])
            i += 1
            continue
        line = plain[i]
        if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
            out.append(line)
            i += 1
            continue
        merged, _start, after = merge_run_block(plain, i, stage_end)
        collapsed = re.sub(r"\\\s*\n\s*", " ", merged.strip())
        new_collapsed = normalize_copy_build_to_app_line(
            collapsed + "\n", builder_stage
        ).rstrip("\n")
        if new_collapsed != collapsed:
            path_fixes += 1
            out.append(new_collapsed)
        else:
            out.extend(merged.split("\n"))
        i = after
    result = "\n".join(out)
    if text.endswith("\n"):
        result += "\n"
    return result, n_commented_removed + n_host_removed + path_fixes


def process_sync_build_app_copy(path: Path, dry_run: bool) -> tuple[bool, int]:
    """Last-``FROM`` ``COPY --from=`` normalization only; see :func:`sync_build_app_copy_paths_in_text`."""
    original = path.read_text(encoding="utf-8")
    new_text, nlines = sync_build_app_copy_paths_in_text(original)
    if new_text == original:
        return False, 0
    if not dry_run:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return True, nlines


def extract_builder_stage_name(content: str) -> str:
    """First ``FROM ... AS <name>`` in the Dockerfile (builder stage). Defaults to ``builder``."""
    m = re.search(r"^\s*FROM\s+.+\bAS\s+(\S+)", content, re.MULTILINE | re.IGNORECASE)
    return m.group(1) if m else "builder"


def workdir_token_is_build(wd: str | None) -> bool:
    """True for ``/build``, ``/build/``, quoted variants."""
    if wd is None:
        return False
    t = wd.strip().strip('"').strip("'").rstrip("/")
    return t == "/build"


def workdir_token_is_app(wd: str | None) -> bool:
    """True for ``/app``, ``/app/`` (stops skeleton COPY scan before runtime layout in-builder)."""
    if wd is None:
        return False
    t = wd.strip().strip('"').strip("'").rstrip("/")
    return t == "/app"


def _line_sets_workdir_build(line: str) -> bool:
    m = re.match(r"^\s*WORKDIR\s+(\S+)", line, re.IGNORECASE)
    if not m:
        return False
    return workdir_token_is_build(m.group(1).strip().strip('"').strip("'"))


def _stage_has_plain_copy_into_build_tree(lines: list[str], start: int, end: int) -> bool:
    """Any plain ``COPY``/``ADD`` (no ``--from=``) whose destination maps under the /build layout."""
    i = start
    while i < end:
        if not re.match(r"^\s*(COPY|ADD)\s", lines[i], re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_copy_or_add_instruction(lines, i, end)
        i = after
        first = merged.split("\n", 1)[0]
        if re.search(r"--from\s*=", first, re.IGNORECASE):
            continue
        raw = parse_copy_or_add_dest_from_merged(merged)
        if raw is None:
            continue
        if dest_to_copy_relpath_under_build(raw) is not None:
            return True
    return False


def builder_stage_range(lines: list[str]) -> tuple[int, int]:
    """
    Range of the **builder** stage for skeleton / stage-1 ``COPY`` scanning:

    1. First ``FROM`` slice that contains a plain ``COPY``/``ADD`` into the ``/build`` tree
       (dest ``/build/…`` or ``./…`` under ``WORKDIR /build``) — fixes multi-stage files where an
       earlier ``FROM … AS`` is not the Lucid build context (e.g. ``strapper`` then ``bundle-prep``).
    2. Else first slice with ``WORKDIR /build`` (``/build/`` accepted).
    3. Else ``FROM … AS`` matching :func:`extract_builder_stage_name`.
    4. Else the first ``FROM`` stage.
    """
    stages = split_build_stages(lines)
    if not stages:
        return (0, len(lines))
    for start, end in stages:
        if _stage_has_plain_copy_into_build_tree(lines, start, end):
            return (start, end)
    for start, end in stages:
        for i in range(start, end):
            if _line_sets_workdir_build(lines[i]):
                return (start, end)
    joined = "\n".join(lines)
    target = extract_builder_stage_name(joined)
    for start, end in stages:
        m = re.match(r"^\s*FROM\s+.+\bAS\s+(\S+)", lines[start], re.IGNORECASE)
        if not m:
            continue
        name = m.group(1).strip().strip('"').strip("'")
        if name.lower() == target.lower():
            return (start, end)
    return stages[0]


def stage1_range(lines: list[str]) -> tuple[int, int]:
    """Alias for :func:`builder_stage_range` (historic name)."""
    return builder_stage_range(lines)


def prune_dirs_for_runtime_copy(dirs: set[str]) -> list[str]:
    """
    Drop ``./child`` when ``./parent`` is also in the set (parent COPY covers the subtree).
    """
    candidates = [d for d in dirs if d != "."]
    if not candidates:
        return []
    candidates_sorted = sorted(candidates, key=lambda s: (s.count("/"), len(s)))
    out: list[str] = []
    for d in candidates_sorted:
        dd = d.rstrip("/")
        is_child = False
        for p in candidates:
            if p == d:
                continue
            pp = p.rstrip("/")
            if dd != pp and dd.startswith(pp + "/"):
                is_child = True
                break
        if not is_child:
            out.append(d)
    return sorted(out, key=lambda s: (s.count("/"), s))


def build_runtime_copy_block_lines(dirs: list[str], builder_stage: str) -> list[str]:
    """
    One ``COPY --from=<stage> --chown=65532:65532 ... /build/<rel>/ /app/<rel>/`` per pruned skeleton dir.
    ``dirs`` uses the same ``./...`` paths as LUCID_X_FILES_SKELETON (WORKDIR /build).
    Matches the common distroless pattern (literal ``65532:65532``, no ARG placeholders).
    """
    pruned = prune_dirs_for_runtime_copy(set(dirs))
    lines: list[str] = [
        MARK_RUNTIME_COPY_BEGIN,
        "# Generated: same directory set as LUCID_X_FILES_SKELETON (./ under WORKDIR /build).",
    ]
    seen_rel: set[str] = set()
    for d in pruned:
        if is_blocked_top_level_build_dir_path(d):
            continue
        rel = d[2:].rstrip("/") if d.startswith("./") else d.lstrip("/").rstrip("/")
        rel = normalize_rdp_segments_in_rel(rel)
        if not rel or rel in seen_rel:
            continue
        seen_rel.add(rel)
        lines.append(
            f"COPY --from={builder_stage} --chown=65532:65532 /build/{rel}/ /app/{rel}/"
        )
    lines.append(MARK_RUNTIME_COPY_END)
    lines.append("")
    return lines


def desired_runtime_build_app_dir_copy_keys(dirs: list[str]) -> set[tuple[str, str]]:
    """
    Canonical ``(/build/<rel>/, /app/<rel>/)`` pairs for directory-tree copies emitted by
    ``build_runtime_copy_block_lines`` (same prune + RDP segment rules).
    """
    pruned = prune_dirs_for_runtime_copy(set(dirs))
    keys: set[tuple[str, str]] = set()
    for d in pruned:
        if is_blocked_top_level_build_dir_path(d):
            continue
        rel = d[2:].rstrip("/") if d.startswith("./") else d.lstrip("/").rstrip("/")
        rel = normalize_rdp_segments_in_rel(rel)
        if not rel:
            continue
        keys.add((f"/build/{rel}/", f"/app/{rel}/"))
    return keys


def runtime_build_app_dir_copy_key(line: str, builder_stage: str) -> tuple[str, str] | None:
    """
    If ``line`` is a ``COPY --from=<builder_stage>`` that copies a **directory** from the build
    tree to the matching ``/app/...`` path, return the canonical ``(src, dst)`` tuple; else None.
    Ignores differences in ``--chown`` so manual lines match injected lines.
    """
    if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
        return None
    if not copy_line_matches_from_stage(line, builder_stage):
        return None
    rest = line.lstrip()
    rest_after = re.sub(r"^COPY\s+", "", rest, count=1, flags=re.IGNORECASE)
    try:
        parts = shlex.split(rest_after)
    except ValueError:
        return None
    path_args = [p for p in parts if not p.startswith("--")]
    if len(path_args) < 2:
        return None
    src, dst = path_args[-2], path_args[-1]
    resolved = resolve_build_copy_src_for_runtime_sync(src)
    if resolved is None or not resolved.endswith("/"):
        return None
    expected = expected_app_dest_for_build_src(resolved)
    if expected is None:
        return None
    if not expected.endswith("/"):
        expected += "/"
    dst_n = dst.strip().strip('"').strip("'")
    if not dst_n.endswith("/"):
        dst_n += "/"
    if PurePosixPath(dst_n.rstrip("/")) != PurePosixPath(expected.rstrip("/")):
        return None
    src_n = resolved if resolved.endswith("/") else resolved + "/"
    return (src_n, expected)


def remove_duplicate_runtime_build_app_copies_in_last_stage(
    plain: list[str],
    builder_stage: str,
    keys: set[tuple[str, str]],
) -> tuple[list[str], int]:
    """
    Drop lines in the last ``FROM`` stage whose ``COPY --from=<builder>`` matches a key in
    ``keys`` (same directory tree as the injected LUCID_RUNTIME_COPY_FROM_BUILD block).
    """
    if not keys:
        return plain, 0
    from_idx = [i for i, line in enumerate(plain) if re.match(r"^\s*FROM\s", line, re.IGNORECASE)]
    if len(from_idx) < 2:
        return plain, 0
    start = from_idx[-1]
    out: list[str] = []
    removed = 0
    for i, line in enumerate(plain):
        if i < start:
            out.append(line)
            continue
        k = runtime_build_app_dir_copy_key(line, builder_stage)
        if k is not None and k in keys:
            removed += 1
            continue
        out.append(line)
    return out, removed


def strip_blocked_host_tree_runtime_copies_in_last_stage(
    plain: list[str], builder_stage: str
) -> tuple[list[str], int]:
    """
    Remove ``COPY --from=<builder_stage>`` instructions in the last ``FROM`` stage whose source is
    under ``/build/host/`` (file drops / bogus tree copies — not generated skeleton roots).
    """
    from_idx = [i for i, line in enumerate(plain) if re.match(r"^\s*FROM\s", line, re.IGNORECASE)]
    if len(from_idx) < 2:
        return plain, 0
    stage_start = from_idx[-1]
    n = len(plain)
    out: list[str] = []
    i = 0
    removed = 0
    while i < n:
        if i < stage_start:
            out.append(plain[i])
            i += 1
            continue
        line = plain[i]
        if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
            out.append(line)
            i += 1
            continue
        merged, start_m, after = merge_copy_or_add_instruction(plain, i, n)
        first = merged.split("\n", 1)[0]
        if copy_line_matches_from_stage(first, builder_stage):
            collapsed = re.sub(r"\\\s*\n\s*", " ", first.strip())
            rest_after = re.sub(r"^COPY\s+", "", collapsed, count=1, flags=re.IGNORECASE)
            try:
                parts = shlex.split(rest_after)
            except ValueError:
                parts = []
            path_args = [p for p in parts if not p.startswith("--")]
            if len(path_args) >= 2:
                src = path_args[-2]
                resolved = resolve_build_copy_src_for_runtime_sync(src)
                check = (resolved or src).strip().strip('"').strip("'")
                if check.startswith("/build/"):
                    tail = check[len("/build/") :].rstrip("/")
                    seg = tail.split("/")[0] if tail else ""
                    if seg in _BLOCKED_TOP_LEVEL_BUILD_DIRS:
                        removed += after - start_m
                        i = after
                        continue
        out.extend(merged.split("\n"))
        i = after
    return out, removed


def runtime_copy_from_builder_before_label_env_violations(
    plain: list[str], builder_stage: str
) -> list[tuple[int, str]]:
    """
    Return ``(1-based line no, line text)`` for each ``COPY --from=<builder_stage>`` in the final
    stage that sits **before** the canonical insert point (after last ``ENV`` or ``LABEL``).
    Such lines belong *after* metadata, like ``lib_search_and_inject`` apt FHS blocks.
    """
    insert_at = find_insert_after_workdir_arg_label_env_runtime(plain)
    if insert_at is None:
        return []
    from_idx = [i for i, line in enumerate(plain) if re.match(r"^\s*FROM\s", line, re.IGNORECASE)]
    if len(from_idx) < 2:
        return []
    stage_start = from_idx[-1]
    viol: list[tuple[int, str]] = []
    for i in range(stage_start, insert_at):
        line = plain[i]
        if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
            continue
        if not copy_line_matches_from_stage(line, builder_stage):
            continue
        viol.append((i + 1, line.rstrip("\r\n")))
    return viol


def inject_runtime_copy_from_build_block(content: str, dirs: list[str], builder_stage: str) -> str:
    """
    Remove any prior ``LUCID_RUNTIME_COPY_*`` block, strip ``# COPY …`` lines in the final stage,
    remove duplicate ``COPY --from=<builder>`` lines for the same ``/build/<rel>/`` → ``/app/<rel>/``
    trees as the block about to be injected (optional ``--chown``; ``./`` sources allowed),
    then insert a new block after the last ``ENV`` (or last ``LABEL`` if no ``ENV``) in the last
    runtime stage — same insert rule as ``lib_search_and_inject.inject_apt_fhs_block_content``.
    No-op if there is no multi-stage runtime with ``WORKDIR /app``.
    """
    text = strip_marked_block(content, MARK_RUNTIME_COPY_BEGIN, MARK_RUNTIME_COPY_END)
    plain = text.splitlines(keepends=False)
    plain, _ = strip_commented_copy_lines_in_last_stage(plain)
    plain, _ = strip_blocked_host_tree_runtime_copies_in_last_stage(plain, builder_stage)
    keys = desired_runtime_build_app_dir_copy_keys(dirs)
    plain, _n_dup = remove_duplicate_runtime_build_app_copies_in_last_stage(plain, builder_stage, keys)
    insert_at = find_insert_after_workdir_arg_label_env_runtime(plain)
    if insert_at is None:
        return content
    block_lines = build_runtime_copy_block_lines(dirs, builder_stage)
    new_plain = plain[:insert_at] + block_lines + plain[insert_at:]
    out = "\n".join(new_plain)
    if text.endswith("\n"):
        out += "\n"
    return out


def process_inject_runtime_copy_from_build(
    path: Path,
    listing_path: Path,
    dry_run: bool,
    repo_root: Path | None = None,
) -> bool:
    """Insert/replace runtime COPY block (see ``dirs_for_runtime_copy_block``)."""
    original = path.read_text(encoding="utf-8")
    dirs = dirs_for_runtime_copy_block(original, listing_path, repo_root=repo_root)
    builder_stage = extract_builder_stage_name(original)
    new_text = inject_runtime_copy_from_build_block(original, dirs, builder_stage)
    if new_text == original:
        return False
    if not dry_run:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def split_build_stages(lines: list[str]) -> list[tuple[int, int]]:
    from_idx: list[int] = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            from_idx.append(i)
    if not from_idx:
        return [(0, len(lines))]
    stages = []
    for k, start in enumerate(from_idx):
        end = from_idx[k + 1] if k + 1 < len(from_idx) else len(lines)
        stages.append((start, end))
    return stages


def workdir_before_line(lines: list[str], stage_start: int, line_idx: int) -> str | None:
    """Last WORKDIR in [stage_start, line_idx)."""
    wd: str | None = None
    for i in range(stage_start, line_idx):
        m = re.match(r"^\s*WORKDIR\s+(\S+)", lines[i], re.IGNORECASE)
        if m:
            wd = m.group(1).strip().strip('"').strip("'")
    return wd


def dirs_for_runtime_copy_block(
    content: str,
    listing_path: Path,
    repo_root: Path | None = None,
) -> list[str]:
    """
    Dirs for ``LUCID_RUNTIME_COPY_FROM_BUILD``: same as :func:`skeleton_dirs_for_dockerfile`
    (listing ∩ approved ∪ builder-stage ``COPY``/``ADD`` roots ∪ host tree under single-source
    directory copies).
    """
    return skeleton_dirs_for_dockerfile(content, listing_path, repo_root=repo_root)


def has_complete_wheel_flow(stage_text: str) -> bool:
    return bool(
        re.search(
            r"pip\s+wheel\b[\s\S]{0,400}?--wheel-dir\s+(\./wheels|/build/wheels)",
            stage_text,
        )
        and re.search(r"--find-links\s+(\./wheels|/build/wheels)", stage_text)
    )


def line_index_after_last_wheel_block_end_in_stage(
    lines: list[str], stage_start: int, stage_end: int
) -> int | None:
    """
    Line index **after** the last ``# LUCID_PIP_WHEELS_END`` in ``[stage_start, stage_end)``, or
    ``None`` if no wheel end marker appears in the builder stage.
    """
    end_s = MARK_WHEEL_END.strip()
    last_ei: int | None = None
    for i in range(stage_start, min(stage_end, len(lines))):
        if lines[i].strip() == end_s:
            last_ei = i
    if last_ei is None:
        return None
    return last_ei + 1


def line_index_after_last_pip_wheel_run_in_stage(
    lines: list[str], stage_start: int, stage_end: int
) -> int | None:
    """
    Line index **after** the last merged ``RUN`` in the builder stage that runs ``pip wheel`` into
    ``/build/wheels`` (or ``./wheels``). Used when a Dockerfile already has a complete wheel flow
    but no ``# LUCID_PIP_WHEELS_*`` markers so :func:`ensure_wheel_blocks` does not splice markers.
    """
    last_after: int | None = None
    i = stage_start
    hi = min(stage_end, len(lines))
    while i < hi:
        if not re.match(r"^\s*RUN\s", lines[i], re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_run_block(lines, i, hi)
        if re.search(r"\bpip\s+wheel\b", merged, re.IGNORECASE) and (
            "/build/wheels" in merged or "./wheels" in merged
        ):
            last_after = after
        i = after
    return last_after


def extract_pip_command(install_block: str) -> str | None:
    m = re.search(
        r"(/[^\s]+/bin/pip|/opt/venv/bin/pip|python\d*(?:\.\d+)?\s+-m\s+pip|pip\d*)",
        install_block,
    )
    if m:
        return m.group(1).strip()
    return None


def merge_run_block(lines: list[str], start: int, end: int) -> tuple[str, int, int]:
    """Return (merged text, first_line_index, line_after_block)."""
    buf = [lines[start]]
    i = start + 1
    while i < end and buf[-1].rstrip().endswith("\\"):
        buf.append(lines[i])
        i += 1
    return "\n".join(buf), start, i


def _parse_copy_heredoc_delimiter(line: str) -> str | None:
    """Closing delimiter for ``COPY <<DELIM`` / ``COPY <<'DELIM'`` (first line only)."""
    if not re.search(r"^\s*COPY\s*<<", line, re.IGNORECASE):
        return None
    rest = re.sub(r"^\s*COPY\s+", "", line, flags=re.IGNORECASE)
    if not rest.startswith("<<"):
        return None
    rest = rest[2:].lstrip()
    if rest.startswith("-"):
        rest = rest[1:].lstrip()
    if rest.startswith("'"):
        end = rest.find("'", 1)
        if end > 1:
            return rest[1:end]
        return None
    if rest.startswith('"'):
        end = rest.find('"', 1)
        if end > 1:
            return rest[1:end]
        return None
    m = re.match(r"(\S+)", rest)
    return m.group(1) if m else None


def merge_copy_heredoc(lines: list[str], start: int, end: int) -> tuple[str, int, int]:
    """Merge ``COPY << …`` through the closing delimiter line."""
    first = lines[start]
    delim = _parse_copy_heredoc_delimiter(first)
    if delim is None:
        return first, start, start + 1
    j = start + 1
    while j < end:
        if lines[j].strip() == delim:
            merged = "\n".join(lines[start : j + 1])
            return merged, start, j + 1
        j += 1
    return "\n".join(lines[start:end]), start, end


def merge_copy_or_add_instruction(lines: list[str], start: int, end: int) -> tuple[str, int, int]:
    """Merge a ``COPY``/``ADD`` instruction: heredoc body, or ``\\`` line continuations."""
    first = lines[start]
    if re.match(r"^\s*COPY\s", first, re.IGNORECASE) and re.search(
        r"COPY\s*<<", first, re.IGNORECASE
    ):
        return merge_copy_heredoc(lines, start, end)
    return merge_run_block(lines, start, end)


def _workdir_token_from_line(line: str) -> str | None:
    m = re.match(r"^\s*WORKDIR\s+(\S+)", line, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def last_label_or_env_block_end_in_stage(lines: list[str], s0: int, s1: int) -> int:
    """Line index after the last ``LABEL`` or ``ENV`` block in ``[s0, s1)``; ``s0`` if none."""
    i = s0
    last_end = s0
    while i < s1:
        ln = lines[i]
        if re.match(r"^\s*LABEL\s", ln, re.IGNORECASE) or re.match(r"^\s*ENV\s", ln, re.IGNORECASE):
            _merged, _s, after = merge_run_block(lines, i, s1)
            last_end = after
            i = after
            continue
        i += 1
    return last_end


def last_workdir_build_block_end_in_stage(lines: list[str], s0: int, s1: int) -> int | None:
    """Line index after the last ``WORKDIR /build`` (or ``/build/``) block in ``[s0, s1)``."""
    i = s0
    last_after: int | None = None
    while i < s1:
        wd = _workdir_token_from_line(lines[i])
        if wd is not None:
            _merged, _s, after = merge_run_block(lines, i, s1)
            if workdir_token_is_build(wd):
                last_after = after
            i = after
            continue
        i += 1
    return last_after


def first_workdir_build_block_end_in_stage(lines: list[str], s0: int, s1: int) -> int | None:
    """Line index after the **first** ``WORKDIR /build`` block in ``[s0, s1)``."""
    i = s0
    while i < s1:
        wd = _workdir_token_from_line(lines[i])
        if wd is not None:
            _merged, _s, after = merge_run_block(lines, i, s1)
            if workdir_token_is_build(wd):
                return after
            i = after
            continue
        i += 1
    return None


def first_plain_copy_line_dest_under_build(lines: list[str], s0: int, s1: int) -> int | None:
    """First line index in ``[s0, s1)`` of a plain ``COPY``/``ADD`` whose dest maps under /build."""
    i = s0
    while i < s1:
        if not re.match(r"^\s*(COPY|ADD)\s", lines[i], re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_copy_or_add_instruction(lines, i, s1)
        first = merged.split("\n", 1)[0]
        if re.search(r"--from\s*=", first, re.IGNORECASE):
            i = after
            continue
        raw = parse_copy_or_add_dest_from_merged(merged)
        if raw is None:
            i = after
            continue
        if dest_to_copy_relpath_under_build(raw) is not None:
            return i
        i = after
    return None


def skeleton_copy_scan_slice(lines: list[str], s0: int, s1: int) -> tuple[int, int] | None:
    """
    Half-open line range ``[scan_lo, scan_hi)`` for instructions that may define
    ``LUCID_X_FILES_SKELETON`` dirs:

    - Starts after the first ``WORKDIR /build`` in the builder stage, or at the first plain
      ``COPY``/``ADD`` into the /build layout if there is no ``WORKDIR /build`` (e.g. some prep stages).
    - Ends at the builder stage boundary ``s1``, or at the first ``WORKDIR /app`` inside that stage
      (exclusive), whichever comes first.

    Never includes the runtime / last ``FROM`` stage. Plain ``COPY``/``ADD`` only; ``COPY --from=`` is
    ignored by parsers. Paths under ``./wheels`` are dropped by :func:`canonicalize_build_skeleton_path`.
    """
    floor_wb = first_workdir_build_block_end_in_stage(lines, s0, s1)
    if floor_wb is not None:
        scan_lo = floor_wb
    else:
        anchor = first_plain_copy_line_dest_under_build(lines, s0, s1)
        if anchor is None:
            return None
        scan_lo = anchor
    scan_hi = s1
    i = scan_lo
    while i < s1:
        wd = _workdir_token_from_line(lines[i])
        if wd is not None:
            _merged, _s, after = merge_run_block(lines, i, s1)
            if workdir_token_is_app(wd):
                scan_hi = i
                break
            i = after
            continue
        i += 1
    if scan_lo >= scan_hi:
        return None
    return (scan_lo, scan_hi)


def first_plain_copy_index_from(lines: list[str], s0: int, s1: int, start_at: int) -> int | None:
    """First stage-1 ``COPY`` (not ``--from=``, not heredoc ``COPY <<``) at index ``>= start_at``."""
    lo = max(s0, start_at)
    for i in range(lo, s1):
        line = lines[i]
        if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
            continue
        rest = line.lstrip()[4:].lstrip()
        if rest.upper().startswith("--FROM="):
            continue
        if re.search(r"^\s*COPY\s*<<", line, re.IGNORECASE):
            continue
        return i
    return None


def _plain_copy_merged_dest_maps_to_build(lines: list[str], copy_idx: int, s1: int) -> bool:
    merged, _s, _a = merge_copy_or_add_instruction(lines, copy_idx, s1)
    raw = parse_copy_or_add_dest_from_merged(merged)
    return raw is not None and dest_to_copy_relpath_under_build(raw) is not None


def first_plain_copy_index_build_dest(lines: list[str], s0: int, s1: int, start_at: int) -> int | None:
    """First plain ``COPY`` at ``>= start_at`` whose destination is under the /build skeleton layout."""
    lo = max(s0, start_at)
    i = lo
    while i < s1:
        line = lines[i]
        if not re.match(r"^\s*COPY\s", line, re.IGNORECASE):
            i += 1
            continue
        rest = line.lstrip()[4:].lstrip()
        if rest.upper().startswith("--FROM="):
            i += 1
            continue
        if re.search(r"^\s*COPY\s*<<", line, re.IGNORECASE):
            merged, _s, after = merge_copy_or_add_instruction(lines, i, s1)
            i = after
            continue
        if _plain_copy_merged_dest_maps_to_build(lines, i, s1):
            return i
        merged, _s, after = merge_copy_or_add_instruction(lines, i, s1)
        i = after
    return None


def last_apt_cache_mount_run_block_end(lines: list[str], s0: int, s1: int) -> int | None:
    """
    Line index **after** the last merged ``RUN`` in ``[s0, s1)`` that uses ``--mount`` with apt
    cache paths (e.g. ``target=/var/cache/apt`` / ``target=/var/lib/apt``).
    """
    last_after: int | None = None
    i = s0
    while i < s1:
        if not re.match(r"^\s*RUN\s", lines[i], re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_run_block(lines, i, s1)
        mlow = merged.lower()
        if "--mount" in mlow and (
            "/var/cache/apt" in merged
            or "/var/lib/apt" in merged
            or "target=/var/cache/apt" in mlow
            or "target=/var/lib/apt" in mlow
        ):
            last_after = after
        i = after
    return last_after


def last_pip_cache_mount_run_block_end(lines: list[str], s0: int, s1: int) -> int | None:
    """
    Line index **after** the last merged ``RUN`` in ``[s0, s1)`` that uses a cache mount targeting
    ``/root/.cache/pip`` (typical ``pip install`` / ``pip wheel``).
    """
    last_after: int | None = None
    i = s0
    while i < s1:
        if not re.match(r"^\s*RUN\s", lines[i], re.IGNORECASE):
            i += 1
            continue
        merged, _s, after = merge_run_block(lines, i, s1)
        if "--mount" in merged.lower() and "/root/.cache/pip" in merged:
            last_after = after
        i = after
    return last_after


def last_mount_anchor_line_after_for_skeleton(lines: list[str], scan_lo: int, scan_hi: int) -> int | None:
    """
    Insert the skeleton **after** apt-cache ``RUN`` blocks and after pip-cache ``RUN`` blocks when
    present: return the maximum ``after`` index among those mounts in ``[scan_lo, scan_hi)``.
    """
    apt_after = last_apt_cache_mount_run_block_end(lines, scan_lo, scan_hi)
    pip_after = last_pip_cache_mount_run_block_end(lines, scan_lo, scan_hi)
    candidates = [x for x in (apt_after, pip_after) if x is not None]
    return max(candidates) if candidates else None


def skeleton_insert_line_before_first_build_copy_fallback(
    lines: list[str], s0: int, s1: int
) -> int | None:
    """
    Insert skeleton immediately **before** the first plain ``COPY`` under ``/build`` that lies inside
    :func:`skeleton_copy_scan_slice`, using the historic ``WORKDIR /build`` + LABEL/ENV floor when
    applicable.
    """
    bounds = skeleton_copy_scan_slice(lines, s0, s1)
    if bounds is None:
        return None
    scan_lo, scan_hi = bounds
    wd_end = last_workdir_build_block_end_in_stage(lines, s0, s1)
    if wd_end is not None:
        meta_all = last_label_or_env_block_end_in_stage(lines, s0, wd_end)
        floor_strict = max(wd_end, meta_all, scan_lo)
        copy_idx = first_plain_copy_index_from(lines, scan_lo, scan_hi, floor_strict)
        if copy_idx is None:
            copy_idx = first_plain_copy_index_from(lines, scan_lo, scan_hi, wd_end)
    else:
        copy_idx = first_plain_copy_index_build_dest(lines, scan_lo, scan_hi, scan_lo)
        if copy_idx is None:
            copy_idx = first_plain_copy_index_from(lines, scan_lo, scan_hi, scan_lo)
    if copy_idx is None:
        return None
    wd = workdir_before_line(lines, s0, copy_idx)
    if workdir_token_is_build(wd):
        return copy_idx
    if _plain_copy_merged_dest_maps_to_build(lines, copy_idx, s1):
        return copy_idx
    return None


def skeleton_insert_line_stage1(lines: list[str], s0: int, s1: int) -> int | None:
    """
    Line index to splice ``LUCID_X_FILES_SKELETON`` **before** (block is inserted *after* prior lines).

    **Primary:** immediately after the **last** qualifying cache-mount ``RUN`` in
    :func:`skeleton_copy_scan_slice` — at minimum after apt ``--mount=…,target=/var/cache/apt`` (and
    ``/var/lib/apt``) blocks, and after pip ``/root/.cache/pip`` mounts when both exist (uses the
    later line so the skeleton is never placed before the apt-cache ``RUN``).

    **Fallback:** first plain ``COPY`` inside that slice (see
    :func:`skeleton_insert_line_before_first_build_copy_fallback`).
    """
    bounds = skeleton_copy_scan_slice(lines, s0, s1)
    if bounds is not None:
        scan_lo, scan_hi = bounds
        anchor = last_mount_anchor_line_after_for_skeleton(lines, scan_lo, scan_hi)
        if anchor is not None:
            return anchor
    return skeleton_insert_line_before_first_build_copy_fallback(lines, s0, s1)


def add_find_links_to_install(install_block: str) -> str:
    if re.search(r"--find-links\s+(\./wheels|/build/wheels)", install_block):
        return install_block
    return re.sub(
        r"(\bpip\s+install\b)",
        r"\1 --no-cache-dir --no-index --find-links /build/wheels",
        install_block,
        count=1,
    )


def ensure_wheel_blocks(
    lines: list[str],
    stage_start: int,
    stage_end: int,
    *,
    wheel_keep_inner: str | None = None,
) -> list[str]:
    stage_text = "\n".join(lines[stage_start:stage_end])
    if has_complete_wheel_flow(stage_text):
        return lines

    out: list[str] = []
    i = 0
    while i < len(lines):
        if i < stage_start or i >= stage_end:
            out.append(lines[i])
            i += 1
            continue

        line = lines[i]
        mc = REQUIREMENTS_COPY.match(line)
        if not mc:
            out.append(line)
            i += 1
            continue

        dst = mc.group("dst").strip().strip('"').strip("'")

        j = i + 1
        install_start: int | None = None
        while j < stage_end:
            cur = lines[j]
            if re.match(r"^\s*FROM\s", cur, re.IGNORECASE):
                break
            if re.match(r"^\s*RUN\s", cur, re.IGNORECASE):
                merged, _s, after = merge_run_block(lines, j, stage_end)
                if re.search(r"\bpip\b.*\binstall\b", merged) and (
                    re.search(r"-r\s+" + re.escape(dst), merged)
                    or re.search(r"-r\s+" + re.escape(Path(dst).name), merged)
                ):
                    if not re.search(r"--find-links\s+(\./wheels|/build/wheels)", merged):
                        install_start = j
                        break
                j = after
                continue
            j += 1

        if install_start is None:
            out.append(line)
            i += 1
            continue

        merged, run_start, run_after = merge_run_block(lines, install_start, stage_end)
        pip_cmd = extract_pip_command(merged) or "pip"
        keep_literal = wheel_keep_inner or "LUCID_WHEELS_$(date +%s)"
        wheel_lines = [
            "",
            MARK_WHEEL_BEGIN,
            f"# requirements: {dst}",
            "RUN --mount=type=cache,target=/root/.cache/pip \\",
            "    mkdir -p /build/wheels && \\",
            f'    printf "{keep_literal}" > /build/wheels/.keep && \\',
            "    touch /build/wheels/.keep && \\",
            f"    {pip_cmd} install --upgrade pip setuptools wheel",
            "",
        ]
        out.extend(wheel_lines)
        out.append(line)
        for k in range(i + 1, run_start):
            out.append(lines[k])
        wheel_lines = [
            "RUN --mount=type=cache,target=/root/.cache/pip \\",
            "    mkdir -p /build/wheels && \\",
            '    echo "building wheels from source" && \\',
            f"    {pip_cmd} wheel --no-cache-dir --wheel-dir /build/wheels -r {dst} && \\",
            '    echo "wheel build complete" && \\',
            '    echo "total wheels built: $(ls -1 /build/wheels/ | wc -l)"',
            MARK_WHEEL_END,
            "",
        ]
        out.extend(wheel_lines)
        modified = add_find_links_to_install(merged)
        if "\n" in modified:
            out.extend(modified.split("\n"))
        else:
            out.append(modified)
        i = run_after
        continue

    return out


def inject_skeleton(
    content: str,
    dirs: list[str],
    *,
    insert_at: int | None = None,
) -> str:
    while True:
        t = strip_marked_block(content, MARK_SKELETON_BEGIN, MARK_SKELETON_END)
        if t == content:
            break
        content = t
    content = strip_orphan_skeleton_without_begin_marker(content)
    lines = content.splitlines(keepends=True)
    if not lines:
        lines = ["\n"]

    plain = [ln.rstrip("\r\n") for ln in lines]
    s0, s1 = stage1_range(plain)
    resolved_insert = insert_at
    if resolved_insert is None:
        resolved_insert = skeleton_insert_line_stage1(plain, s0, s1)
    if resolved_insert is None:
        # Cannot insert a replacement; return stripped content (marked + orphan skeleton removed),
        # not before_strip — otherwise orphan END-only blocks would reappear unchanged.
        return "\n".join(plain) + ("\n" if content.endswith("\n") else "")

    block = build_skeleton_run_block(dirs)
    new_plain = plain[:resolved_insert] + block.splitlines() + plain[resolved_insert:]
    return "\n".join(new_plain) + ("\n" if content.endswith("\n") else "")


def process_file(
    path: Path,
    listing_path: Path,
    apply_wheels: bool,
    dry_run: bool,
    inject_runtime_copy: bool = False,
    *,
    post_sync_build_app_copy: bool = False,
    repo_root: Path | None = None,
) -> bool:
    """
    Strip prior LUCID blocks, optionally inject pip wheels then skeleton (dirs from stage-1 plain
    COPY/ADD in the builder slice). If ``inject_runtime_copy``, append ``LUCID_RUNTIME_COPY_FROM_BUILD``
    after the last LABEL/ENV in the final stage. If ``post_sync_build_app_copy``, normalize last-stage
    ``COPY --from=`` paths on the resulting text (in-memory, so dry-run is accurate).
    """
    original = path.read_text(encoding="utf-8")

    text = original
    while True:
        t = strip_marked_block(text, MARK_SKELETON_BEGIN, MARK_SKELETON_END)
        if t == text:
            break
        text = t
    text = strip_orphan_skeleton_without_begin_marker(text)
    text = strip_marked_block(text, MARK_WHEEL_BEGIN, MARK_WHEEL_END)

    plain = [ln.rstrip("\r\n") for ln in text.splitlines(keepends=True)]
    if not plain:
        plain = [""]
    s0, s1 = stage1_range(plain)
    plain, _layout_copy_edits = rewrite_stage1_layout_copy_paths_in_stage(plain, s0, s1)
    text = "\n".join(plain)
    if original.endswith("\n") and text != "" and not text.endswith("\n"):
        text += "\n"

    dirs = skeleton_dirs_for_dockerfile(text, listing_path, repo_root=repo_root)

    s0, s1 = stage1_range(plain)
    skeleton_insert_at: int | None = None
    if apply_wheels:
        keep_inner = wheel_keep_marker_inner_for_dockerfile(path)
        plain = ensure_wheel_blocks(
            plain, s0, s1, wheel_keep_inner=keep_inner
        )
        skeleton_insert_at = line_index_after_last_wheel_block_end_in_stage(plain, s0, s1)
        if skeleton_insert_at is None:
            skeleton_insert_at = line_index_after_last_pip_wheel_run_in_stage(plain, s0, s1)

    staged = "\n".join(plain)
    if original.endswith("\n") and staged != "" and not staged.endswith("\n"):
        staged += "\n"

    text = inject_skeleton(staged, dirs, insert_at=skeleton_insert_at)

    if inject_runtime_copy:
        # Use current staged content so runtime COPY dirs match builder COPY/skeleton after wheel strip.
        dirs_rt = dirs_for_runtime_copy_block(text, listing_path, repo_root=repo_root)
        text = inject_runtime_copy_from_build_block(
            text, dirs_rt, extract_builder_stage_name(text)
        )

    if post_sync_build_app_copy:
        text, _n_sync = sync_build_app_copy_paths_in_text(text)

    if text != original:
        if not dry_run:
            path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def process_strip_file(path: Path, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    text = strip_all_injections(original)
    if text != original:
        if not dry_run:
            path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def process_strip_build_scaffold(path: Path, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    text = strip_build_scaffold_runs(original)
    if text != original:
        if not dry_run:
            path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def discover_dockerfiles(containers_root: Path) -> list[Path]:
    """
    ``Dockerfile``, ``Dockerfile.*``, and ``dockerfile.*`` (lowercase names are missed by
    ``rglob('Dockerfile*')`` alone on case-sensitive filesystems).
    """
    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in ("Dockerfile*", "dockerfile*"):
        for p in containers_root.rglob(pattern):
            if p.is_dir():
                continue
            key = p.resolve()
            if key in seen:
                continue
            name = p.name
            if name == "Dockerfile" or name.startswith("Dockerfile.") or name.startswith("dockerfile."):
                seen.add(key)
                out.append(p)
    return sorted(out)


def discover_dockerfiles_under_roots(roots: list[Path]) -> list[Path]:
    """Merge ``discover_dockerfiles`` for each root; dedupe by resolved path; stable sort."""
    seen: set[Path] = set()
    out: list[Path] = []
    for containers_root in roots:
        if not containers_root.is_dir():
            continue
        for p in discover_dockerfiles(containers_root):
            key = p.resolve()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def dedupe_scan_roots(paths: list[Path]) -> list[Path]:
    """Preserve order; drop duplicate resolved paths."""
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        try:
            key = p.resolve()
        except OSError:
            out.append(p)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def main() -> int:
    root = repo_root_from_here()
    default_listing = root / "x-files-listing.txt"
    default_container_roots: tuple[Path, ...] = (
        Path("infrastructure/containers"),
        Path("infrastructure/docker"),
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strip-build-scaffold",
        "--strip-build-node-scaffold",
        action="store_true",
        dest="strip_build_scaffold",
        help=(
            "Remove redundant RUN scaffolds: mkdir -p under /build/ or ./ plus optional "
            "printf/touch/chown only (no pip/apt/--mount). Optional preceding # ... scaffold ... "
            "comment is removed too. Does not remove LUCID_X_FILES_SKELETON or for d in … loops."
        ),
    )
    ap.add_argument(
        "--strip",
        action="store_true",
        help="Remove LUCID_X_FILES_SKELETON_*, LUCID_PIP_WHEELS_*, and LUCID_RUNTIME_COPY_FROM_BUILD_* blocks (local revert; use --apply to write)",
    )
    ap.add_argument(
        "--listing",
        type=Path,
        default=default_listing,
        help=(
            "Path to x-files-listing.txt (required for skeleton / runtime COPY inject; "
            "default: <repo>/x-files-listing.txt). Relative paths are from the repository root."
        ),
    )
    ap.add_argument(
        "--containers-root",
        action="append",
        dest="containers_roots",
        type=Path,
        metavar="DIR",
        help=(
            "Extra root directory to scan (repeatable). By default this is **merged** with "
            "infrastructure/containers and infrastructure/docker, so images under "
            "infrastructure/containers/database/ are always included unless you pass "
            "--scan-roots-only. Relative paths are from the repository root."
        ),
    )
    ap.add_argument(
        "--scan-roots-only",
        action="store_true",
        help=(
            "Use only --containers-root paths (do not merge the default trees). "
            "Requires at least one --containers-root."
        ),
    )
    ap.add_argument(
        "--run-full-with-sync",
        action="store_true",
        help=(
            "Full pipeline: pip wheel / --find-links (unless --no-wheels), directory skeleton from "
            "builder stage-1 plain COPY/ADD between WORKDIR /build and WORKDIR /app, "
            "LUCID_RUNTIME_COPY_FROM_BUILD after the last LABEL/ENV in the final FROM (same as "
            "--with-runtime-copy-from-build), then last-FROM COPY --from= path normalization "
            "(same as --with-sync-build-app-copy, after inject). Implies runtime COPY inject; use "
            "--apply to write."
        ),
    )
    ap.add_argument(
        "--only",
        type=Path,
        default=None,
        help=(
            "Process a single Dockerfile. Relative paths are resolved from the repository root, "
            "not the shell cwd. Omit to process every Dockerfile* / dockerfile* under --containers-root."
        ),
    )
    ap.add_argument("--apply", action="store_true", help="Write files (default is dry-run)")
    ap.add_argument("--no-wheels", action="store_true", help="Skip pip wheel / --find-links injection")
    ap.add_argument(
        "--sync-build-app-copy",
        action="store_true",
        help=(
            "Does not run last-FROM COPY --from= sync (use --with-sync-build-app-copy). Default "
            "inject already builds skeleton from plain COPY/ADD only, after WORKDIR /build through "
            "builder stage (excludes ./wheels, never COPY --from=)."
        ),
    )
    ap.add_argument(
        "--sync-build-app-copy-only",
        action="store_true",
        help=(
            "Only rewrite COPY --from= in the last FROM (runtime) image: /build/… and ./… src → "
            "matching /app/… dst; strip # COPY hints. Does not build skeleton (skeleton uses builder "
            "WORKDIR /build plain COPY only). Exits after this pass; no x-files-listing required."
        ),
    )
    ap.add_argument(
        "--with-sync-build-app-copy",
        action="store_true",
        help=(
            "Before inject: last-FROM COPY --from= path normalization (same as "
            "--sync-build-app-copy-only). Skeleton dir sources are still builder plain COPY/ADD in the "
            "WORKDIR /build … WORKDIR /app slice only. Inject order with default wheels: "
            "LUCID_PIP_WHEELS_* first, then LUCID_X_FILES_SKELETON_* after # LUCID_PIP_WHEELS_END."
        ),
    )
    ap.add_argument(
        "--inject-runtime-copy-from-build",
        action="store_true",
        help=(
            "Only insert/replace # LUCID_RUNTIME_COPY_FROM_BUILD_* block: "
            "COPY --from=<first AS name> --chown=65532:65532 /build/<dir>/ /app/<dir>/ per pruned dir "
            "(dirs from x-files-listing.txt, same as LUCID_X_FILES_SKELETON). "
            "Inserts after last ENV (or last LABEL if no ENV) in the last runtime stage."
        ),
    )
    ap.add_argument(
        "--with-runtime-copy-from-build",
        "--with-runtimme-copy-from-build",
        action="store_true",
        help=(
            "After skeleton/wheel inject, also insert/replace the LUCID_RUNTIME_COPY_FROM_BUILD block. "
            "(Alias --with-runtimme-copy-from-build accepts a common typo.)"
        ),
    )
    ap.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print one line per Dockerfile (unchanged or updated).",
    )
    args = ap.parse_args()

    if args.only is not None:
        one = resolve_path_from_repo(args.only, root)
        if not one.is_file():
            print(f"error: --only is not a file: {one}", file=sys.stderr)
            return 1
        dockerfiles = [one]
        roots_display = str(one.relative_to(root)) if one.is_relative_to(root) else str(one)
    else:
        default_resolved = [resolve_path_from_repo(p, root) for p in default_container_roots]
        if args.scan_roots_only:
            if not args.containers_roots:
                print(
                    "error: --scan-roots-only requires at least one --containers-root",
                    file=sys.stderr,
                )
                return 1
            scan_roots = [resolve_path_from_repo(p, root) for p in args.containers_roots]
        elif args.containers_roots is None:
            scan_roots = default_resolved
        else:
            user_resolved = [resolve_path_from_repo(p, root) for p in args.containers_roots]
            scan_roots = dedupe_scan_roots(default_resolved + user_resolved)
        for r in scan_roots:
            if not r.is_dir():
                print(f"warning: not a directory (skipped): {r}", file=sys.stderr)
        dockerfiles = discover_dockerfiles_under_roots([r for r in scan_roots if r.is_dir()])
        roots_display = ", ".join(
            str(r.relative_to(root)) if r.is_relative_to(root) else str(r) for r in scan_roots
        )
    print(
        f"# inject_dockerfile_x_files_skeleton: {len(dockerfiles)} Dockerfile(s), "
        f"roots={roots_display}",
    )
    dry_run = not args.apply

    if args.inject_runtime_copy_from_build:
        listing_resolved = resolve_path_from_repo(args.listing, root)
        if not listing_resolved.is_file():
            print(f"error: x-files listing not found: {listing_resolved}", file=sys.stderr)
            return 1
        changed = 0
        for df in dockerfiles:
            rel = df.relative_to(root) if df.is_relative_to(root) else df
            if process_inject_runtime_copy_from_build(
                df, listing_resolved, dry_run, repo_root=root
            ):
                print(f"{'[dry-run] would inject' if dry_run else 'injected'} runtime COPY from build: {rel}")
                changed += 1
            elif args.verbose:
                print(f"unchanged (runtime COPY already matches): {rel}")
        print(
            f"done: {changed} file(s) {'would change' if dry_run else 'changed'}, {len(dockerfiles)} scanned"
        )
        if changed == 0:
            print(
                f"OK: {len(dockerfiles)} Dockerfile(s) checked; LUCID_RUNTIME_COPY_FROM_BUILD already "
                "matches x-files-listing.txt (or no distroless stage with WORKDIR /app). Nothing to write."
            )
        elif dry_run:
            print("Note: add --apply to write.", file=sys.stderr)
        return 0

    if args.sync_build_app_copy_only:
        changed_files = 0
        line_edits = 0
        for df in dockerfiles:
            did, n = process_sync_build_app_copy(df, dry_run)
            if did:
                rel = df.relative_to(root) if df.is_relative_to(root) else df
                print(
                    f"{'[dry-run] would sync' if dry_run else 'synced'} "
                    f"{n} COPY line(s) in {rel}"
                )
                changed_files += 1
                line_edits += n
        print(
            f"done (last-FROM COPY sync only): {changed_files} file(s) "
            f"{'would change' if dry_run else 'changed'}, "
            f"{line_edits} COPY line(s), {len(dockerfiles)} scanned"
        )
        if changed_files == 0:
            print(
                "No drift in last FROM: every COPY --from=<first AS> /build/... already has matching "
                "/app/<tail> (or is skipped). This pass does not build LUCID_X_FILES_SKELETON.",
                file=sys.stderr,
            )
        elif dry_run:
            print("Note: add --apply to write.", file=sys.stderr)
        return 0

    if args.strip_build_scaffold:
        changed = 0
        for df in dockerfiles:
            if process_strip_build_scaffold(df, dry_run):
                rel = df.relative_to(root) if df.is_relative_to(root) else df
                print(
                    f"{'[dry-run] would strip build mkdir scaffold' if dry_run else 'stripped build mkdir scaffold'}: {rel}"
                )
                changed += 1
        print(
            f"done: {changed} file(s) {'would strip' if dry_run else 'stripped'} (build scaffold), {len(dockerfiles)} scanned"
        )
        if changed == 0:
            print(
                "No matching redundant mkdir scaffold RUN blocks found (see --strip-build-scaffold help).",
                file=sys.stderr,
            )
        elif dry_run:
            print("Note: add --apply to write.", file=sys.stderr)
        return 0

    if args.strip:
        changed = 0
        for df in dockerfiles:
            if process_strip_file(df, dry_run):
                rel = df.relative_to(root) if df.is_relative_to(root) else df
                print(f"{'[dry-run] would strip' if dry_run else 'stripped'}: {rel}")
                changed += 1
        print(f"done: {changed} file(s) {'would strip' if dry_run else 'stripped'}, {len(dockerfiles)} scanned")
        if changed == 0:
            print(
                "No changes: no lines # LUCID_X_FILES_SKELETON_BEGIN … END, "
                "# LUCID_PIP_WHEELS_BEGIN … END, or # LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN … END found "
                "(or already removed). Revert only deletes those marked blocks — not other RUN lines.",
                file=sys.stderr,
            )
        elif dry_run:
            print("Note: add --apply to write the stripped files to disk.", file=sys.stderr)
        return 0

    listing_resolved = resolve_path_from_repo(args.listing, root)
    if not listing_resolved.is_file():
        print(f"error: x-files listing not found: {listing_resolved}", file=sys.stderr)
        return 1

    apply_wheels = not args.no_wheels

    if args.sync_build_app_copy and not args.with_sync_build_app_copy:
        print(
            "warning: --sync-build-app-copy does not run last-FROM COPY --from= sync; "
            "use --with-sync-build-app-copy if you need that before inject.",
            file=sys.stderr,
        )
    run_sync_before_inject = args.with_sync_build_app_copy and not args.run_full_with_sync
    if args.with_sync_build_app_copy and args.run_full_with_sync:
        print(
            "# note: --run-full-with-sync already runs last-FROM COPY --from= sync after inject; "
            "skipping pre-inject --with-sync-build-app-copy pass.",
            file=sys.stderr,
        )
    if run_sync_before_inject:
        sync_changed = 0
        sync_lines = 0
        for df in dockerfiles:
            did, n = process_sync_build_app_copy(df, dry_run)
            if did:
                rel = df.relative_to(root) if df.is_relative_to(root) else df
                print(
                    f"{'[dry-run] would sync' if dry_run else 'synced'} "
                    f"{n} last-FROM COPY --from= line(s) in {rel}"
                )
                sync_changed += 1
                sync_lines += n
        if sync_changed or sync_lines:
            print(
                f"# pre-inject last-FROM COPY sync: {sync_changed} file(s), {sync_lines} line edit(s); "
                f"continuing to skeleton/wheel inject (builder plain COPY only)"
            )
        elif args.verbose:
            print(
                "# pre-inject: no last-FROM COPY --from= path changes; continuing to skeleton inject"
            )

    inject_runtime = bool(args.with_runtime_copy_from_build or args.run_full_with_sync)
    post_sync = bool(args.run_full_with_sync)

    changed = 0
    for df in dockerfiles:
        rel = df.relative_to(root) if df.is_relative_to(root) else df
        if process_file(
            df,
            listing_resolved,
            apply_wheels,
            dry_run,
            inject_runtime_copy=inject_runtime,
            post_sync_build_app_copy=post_sync,
        ):
            print(f"{'[dry-run] would update' if dry_run else 'updated'}: {rel}")
            changed += 1
        elif args.verbose:
            print(f"unchanged: {rel}")

    print(f"done: {changed} file(s) {'would change' if dry_run else 'changed'}, {len(dockerfiles)} scanned")
    if changed == 0:
        if args.run_full_with_sync:
            print(
                f"OK: {len(dockerfiles)} Dockerfile(s) checked — full-with-sync (wheels, skeleton, "
                "runtime COPY block after LABEL/ENV, last-FROM COPY sync) already matches "
                "(nothing to write)."
            )
        elif args.with_runtime_copy_from_build:
            print(
                f"OK: {len(dockerfiles)} Dockerfile(s) checked - skeleton, pip wheels, and "
                "LUCID_RUNTIME_COPY_FROM_BUILD already match x-files-listing.txt (nothing to write)."
            )
        else:
            wh = "skeleton and pip wheels" if apply_wheels else "skeleton (pip wheels skipped: --no-wheels)"
            print(
                f"OK: {len(dockerfiles)} Dockerfile(s) checked - {wh} already match on disk (nothing to write). "
                "Add --with-runtime-copy-from-build to also sync LUCID_RUNTIME_COPY_FROM_BUILD blocks."
            )
        print(
            "# Tip: distroless apt/FHS library COPY lines: "
            "python infrastructure/containers/lib_search_and_inject.py --inject-dockerfile --apply"
        )
    elif dry_run:
        print("Note: add --apply to write.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
File (full path): infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py

Scan a multi-stage Dockerfile's **final** ``FROM`` stage for ``COPY --from=…`` lines whose
destination is under ``/app/…``. Ignore sources under ``/build/…`` (application skeleton copies).

From each remaining **source** path (FHS paths copied from the builder into distroless), derive
directory prefixes on the **builder** image (stopping at the first glob segment in the path) and
emit a ``RUN set -eux`` scaffold: ``mkdir -p …`` plus a ``for d in …`` loop that writes
``LUCID_LIB_SKELETON_<epoch>`` to ``$d/.keep`` and touches the marker — suitable for
stage-1 (builder) so library/runtime paths exist before population.

Usage (repo root)::

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    infrastructure/containers/admin/dockerfile.admin-overlord

  # same as above: single target prints the full block; directories print one summary line per file

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    --paths-only infrastructure/containers/electron_gui/Dockerfile.admin

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    --roots /usr,/var,/etc,/bin,/lib,/dev,/root \\
    path/to/Dockerfile

Directory (strict ``Dockerfile`` / ``Dockerfile.*`` / ``dockerfile.*`` only; no ``.bak`` / ``__pycache__``)::

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    infrastructure/containers

Several trees in one run (paths resolved from repo root when relative)::

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    infrastructure/containers/gui infrastructure/containers/electron_gui

Write generated blocks into each file (replace existing ``LUCID_LIB_SKELETON_*`` markers if present;
otherwise insert **after the first builder-stage ``RUN`` that runs ``apt-get install``** — i.e. after
packages are installed and before a typical ``apt-get remove … rustc`` / rustup step;
fall back to ``# LUCID_X_FILES_SKELETON_END``, then ``WORKDIR /build``)::

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    --apply infrastructure/containers

Preview apply without saving::

  python infrastructure/containers/generate_lib_skeleton_from_runtime_copy.py \\
    --apply --dry-run infrastructure/containers

If a file still has ``LUCID_LIB_SKELETON_*`` in an old position, delete that marked block once, then run
``--apply`` again so it inserts after the ``apt-get install`` RUN.
"""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path, PurePosixPath

from dockerfile_alignment import (
    discover_lucid_dockerfiles_under,
    discover_repo_root,
    read_dockerfile_text,
)

# Match lib_search_and_inject.NODE_BASE_IMAGE_FHS_PATHS — keep in sync for ``FROM node:…`` builders.
_NODE_BASE_IMAGE_LIB_SKELETON_EXTRAS: tuple[str, ...] = (
    "/usr/local/bin/",
    "/usr/local/lib/",
)


def _first_from_line(text: str) -> str | None:
    for line in text.splitlines():
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            return line
    return None


def _builder_uses_node_base_image(text: str) -> bool:
    fl = _first_from_line(text)
    if not fl:
        return False
    low = fl.lower()
    return bool(
        re.search(r"\bnode\s*:", low)
        or re.search(r"\bnodejs\s*:", low)
        or "/nodejs" in low
    )


def split_build_stages(lines: list[str]) -> list[tuple[int, int]]:
    """``FROM`` stage boundaries: ``(start_line_index, end_exclusive)``."""
    starts: list[int] = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            starts.append(i)
    if not starts:
        return [(0, len(lines))]
    out: list[tuple[int, int]] = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        out.append((s, e))
    return out


def merge_run_block(lines: list[str], start: int, end: int) -> tuple[str, int]:
    """One physical ``RUN`` instruction (``\\`` line continuations)."""
    parts: list[str] = []
    j = start
    while j < end:
        parts.append(lines[j])
        if lines[j].rstrip().endswith("\\") and j + 1 < end:
            j += 1
            continue
        return "\n".join(parts), j + 1
    return "\n".join(parts), min(start + 1, end)


def merge_copy_block(lines: list[str], start: int, end: int) -> tuple[str, int]:
    """One physical ``COPY`` instruction (with ``\\`` continuations)."""
    parts: list[str] = []
    j = start
    while j < end:
        parts.append(lines[j])
        if lines[j].rstrip().endswith("\\") and j + 1 < end:
            j += 1
            continue
        return "\n".join(parts), j + 1
    return "\n".join(parts), min(start + 1, end)


def iter_copy_spans(lines: list[str], range_start: int, range_end: int) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    i = range_start
    while i < range_end:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if not re.match(r"^\s*COPY\s", raw, re.IGNORECASE):
            i += 1
            continue
        merged, after = merge_copy_block(lines, i, range_end)
        out.append((i, after, merged))
        i = after
    return out


def normalized_one_line(merged: str) -> str:
    s = merged.strip()
    s = re.sub(r"\\\s*\n\s*", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def parse_copy_from_sources_and_dest(merged: str) -> tuple[str | None, list[str], str | None]:
    """
    Return ``(from_stage, source_paths, dest)`` for a ``COPY`` line.
    ``from_stage`` is None if there is no ``--from=``.
    """
    one = normalized_one_line(merged)
    try:
        parts = shlex.split(one, posix=True)
    except ValueError:
        return None, [], None
    if not parts or parts[0].upper() != "COPY":
        return None, [], None
    stage: str | None = None
    i = 1
    while i < len(parts) and parts[i].startswith("--"):
        if parts[i].startswith("--from="):
            stage = parts[i].split("=", 1)[1].strip()
        i += 1
    rest = parts[i:]
    if len(rest) < 2:
        return stage, [], None
    dest = rest[-1]
    sources = rest[:-1]
    return stage, sources, dest


def _segment_has_glob(seg: str) -> bool:
    return any(c in seg for c in "*?[")


# COPY sources without trailing ``/`` may still be directories (e.g. ``.../site-packages``).
# Single-file copies use a basename that looks like a file (extension or common binary name).
_DIR_LEAF_NAMES: frozenset[str] = frozenset(
    {
        "bin",
        "include",
        "lib",
        "lib64",
        "libexec",
        "local",
        "man",
        "onion",
        "tor",
        "tunnel",
        "run",
        "lucid",
        "lucid_admin",
        "lucid_vm",
        "lucid_node",
        "lucid_blockchain",
        "lucid_governance",
        "lucid_payment",
        "lucid_session",
        "lucid_user",
        "lucid_server",
        "lucid_portal",
        "lucid_voting",
        "lucid_dev",	
        "lucid_rdp",
        "lucid_wallet",
        "sbin",
        "rc",
        "rc.d",
        "etc",
        "sbin",
        "share",
        "ssl",
        "certs",
        "dist-packages",
        "site-packages",
        "aarch64-linux-gnu",
        "x86_64-linux-gnu",
        "i386-linux-gnu",
    }
)

_RE_PYTHON_VER_DIR = re.compile(r"^python\d+\.\d+$")


def _source_path_for_prefix_walk(src: str) -> str:
    """
    Return the path whose prefixes we should mkdir (directory tree on builder).

    - Trailing ``/`` → directory; use as-is.
    - Glob in path → handled later in ``fhs_dir_prefixes_from_source`` (pass through).
    - Otherwise: if last segment looks like a **file**, use ``dirname``; else directory path as-is.
    """
    s = src.strip()
    if not s.startswith("/"):
        return s
    parts = [p for p in s.split("/") if p]
    if not parts:
        return s
    if _segment_has_glob(parts[-1]) or any(_segment_has_glob(p) for p in parts):
        return s
    if s.endswith("/"):
        return s.rstrip("/") or "/"
    last = parts[-1]
    # Common binary copy patterns should scaffold parent dirs, not file leafs.
    if len(parts) >= 2 and parts[-2] in {"bin", "sbin"}:
        return str(PurePosixPath(s).parent)
    if last in _DIR_LEAF_NAMES or _RE_PYTHON_VER_DIR.match(last):
        return s
    if "." in last:
        # e.g. .crt, .so, .so.1, ld-linux-aarch64.so.1
        if last.endswith(".crt") or last.endswith(".pem") or last.endswith(".key"):
            return str(PurePosixPath(s).parent)
        if ".so." in last or last.endswith(".so") or re.search(r"\.so\.\d+$", last):
            return str(PurePosixPath(s).parent)
        if re.search(
            r"\.(cnf|conf|txt|py|json|yaml|yml|sh|bash|deb|rpm|1|2|3|4|5|6|7|8|9|0)$", last
        ):
            return str(PurePosixPath(s).parent)
    # No extension: treat as file (e.g. /usr/bin/tini, /bin/bash) → parent only.
    return str(PurePosixPath(s).parent)


def fhs_dir_prefixes_from_source(src: str) -> list[str]:
    """
    Absolute path prefixes to create on the builder for this ``COPY`` source.

    Stops at the first path segment containing a glob metacharacter (Docker treats ``*`` as one
    segment). Every non-glob prefix is included (e.g. ``/usr/lib/*/lib.so*`` → ``/usr``, ``/usr/lib``).

    File vs directory (no trailing ``/``) uses :func:`_source_path_for_prefix_walk` so
    ``site-packages`` and ``python3.11`` paths keep the full directory chain; ``.crt`` / ``.so``
    sources scaffold parents only.
    """
    s = _source_path_for_prefix_walk(src)
    if not s.startswith("/"):
        return []
    parts = [p for p in s.split("/") if p]
    acc: list[str] = []
    out: list[str] = []
    for part in parts:
        if _segment_has_glob(part):
            break
        acc.append(part)
        out.append("/" + "/".join(acc))
    return out


def path_allowed(path: str, roots: frozenset[str]) -> bool:
    p = str(PurePosixPath(path))
    for r in roots:
        if p == r or p.startswith(r + "/"):
            return True
    return False


def _skip_bad_lib_skeleton_dir(path: str) -> bool:
    """
    Skip dirs that must never get ``mkdir`` + ``.keep`` in the builder.

    Final-stage placeholders like ``COPY … /dev/null/ /app/dev/null/`` infer ``/dev/null``, which
    would mask the real null device if created as a directory on the builder.
    """
    p = str(PurePosixPath(path))
    return p == "/dev/null" or p.endswith("/dev/null")


def collapse_redundant_path_prefixes(paths: list[str]) -> list[str]:
    """
    Drop broad ancestor roots when more specific descendants exist.

    Example: ``/usr``, ``/usr/lib``, ``/etc``, ``/etc/ssl`` → ``/usr/lib``, ``/etc/ssl``.
    """
    uniq = {str(PurePosixPath(p)) for p in paths}
    ordered = sorted(uniq, key=lambda x: (-x.count("/"), -len(x), x))
    kept: list[str] = []
    for p in ordered:
        # If a more specific path already exists, keep the specific one.
        if any(k.startswith(p + "/") for k in kept):
            continue
        kept.append(p)
    return sorted(kept, key=lambda x: (x.count("/"), x))


def collect_builder_scaffold_abs_dirs(lines: list[str], bs: int, be: int) -> set[str]:
    """
    Collect absolute directory paths already created or targeted in the builder stage before we
    emit ``LUCID_LIB_SKELETON`` (``mkdir -p …``, shell redirects to ``*.keep`` under FHS).
    """
    out: set[str] = set()
    i = bs + 1
    while i < be:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if not re.match(r"^\s*RUN\s", raw, re.IGNORECASE):
            i += 1
            continue
        merged, after = merge_run_block(lines, i, be)
        i = after
        flat = normalized_one_line(merged)
        for m in re.finditer(r"mkdir\s+(?:-p\s+)+", flat, re.IGNORECASE):
            tail = flat[m.end() :]
            boundary = len(tail)
            for sep in ("&&", "||", ";", "|"):
                pos = tail.find(sep)
                if pos != -1:
                    boundary = min(boundary, pos)
            chunk = tail[:boundary].strip()
            if not chunk:
                continue
            try:
                tokens = shlex.split(chunk, posix=True)
            except ValueError:
                continue
            for t in tokens:
                if t.startswith("/") and not t.startswith("/build"):
                    out.add(str(PurePosixPath(t)))
        for m in re.finditer(r">\s*(/\S+)", flat):
            path = m.group(1).rstrip("'\"")
            if path.startswith("/build"):
                continue
            try:
                out.add(str(PurePosixPath(path).parent))
            except ValueError:
                continue
    return out


def subtract_paths_covered_by_builder_scaffold(
    paths: list[str], existing: set[str], fhs_roots: frozenset[str]
) -> list[str]:
    """Remove dirs already scaffolded in the builder (exact path or under an existing prefix)."""
    out: list[str] = []
    for p in paths:
        pn = str(PurePosixPath(p))
        if not path_allowed(pn, fhs_roots):
            out.append(pn)
            continue
        skip = False
        for e in existing:
            if pn == e or pn.startswith(e + "/"):
                skip = True
                break
        if not skip:
            out.append(pn)
    return collapse_redundant_path_prefixes(out)


def collect_skeleton_paths_from_dockerfile(
    text: str,
    *,
    fhs_roots: frozenset[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """
    Returns ``(sorted_unique_paths, debug_rows)`` where each path is an absolute FHS directory on
    the builder image.
    """
    lines = text.splitlines(keepends=False)
    stages = split_build_stages(lines)
    if len(stages) < 2:
        return [], [{"note": "fewer than two FROM stages; nothing to scan"}]
    s0, s1 = stages[-1]
    spans = iter_copy_spans(lines, s0 + 1, s1)
    collected: set[str] = set()
    must_keep: set[str] = set()
    debug: list[dict[str, str]] = []
    for _start, _end, merged in spans:
        stage, sources, dest = parse_copy_from_sources_and_dest(merged)
        if stage is None or not sources or not dest:
            continue
        if not dest.startswith("/app"):
            continue
        for src in sources:
            if src.startswith("/build/") or src == "/build":
                debug.append({"skipped_build": src, "dest": dest})
                continue
            # Preserve the strongest non-glob parent for glob-driven library copies,
            # e.g. /usr/lib/*/libssl.so* => keep /usr/lib explicitly.
            src_for_walk = _source_path_for_prefix_walk(src)
            src_parts = [p for p in src_for_walk.split("/") if p]
            acc: list[str] = []
            for part in src_parts:
                if _segment_has_glob(part):
                    break
                acc.append(part)
            if acc:
                candidate = "/" + "/".join(acc)
                if path_allowed(candidate, fhs_roots) and not _skip_bad_lib_skeleton_dir(candidate):
                    must_keep.add(candidate)
            for prefix in fhs_dir_prefixes_from_source(src):
                if _skip_bad_lib_skeleton_dir(prefix):
                    debug.append({"skipped_dev_null": prefix, "src": src})
                    continue
                if path_allowed(prefix, fhs_roots):
                    collected.add(prefix)
                else:
                    debug.append({"skipped_root": prefix, "src": src})
    if _builder_uses_node_base_image(text):
        for extra in _NODE_BASE_IMAGE_LIB_SKELETON_EXTRAS:
            pn = str(PurePosixPath(extra))
            if path_allowed(pn, fhs_roots) and not _skip_bad_lib_skeleton_dir(pn):
                collected.add(pn)
    sorted_paths = sorted(collected, key=lambda p: (p.count("/"), p))
    sorted_paths = collapse_redundant_path_prefixes(sorted_paths)
    sorted_paths = sorted(set(sorted_paths) | must_keep, key=lambda p: (p.count("/"), p))
    # Keep all section-19 derived roots from final-stage COPY --from; do not
    # remove paths just because builder-stage scaffolding exists elsewhere.
    return sorted_paths, debug


def emit_run_block(paths: list[str]) -> str:
    """Dockerfile ``RUN`` fragment with LUCID_LIB_SKELETON markers."""
    paths = [p for p in paths if not _skip_bad_lib_skeleton_dir(p)]
    if not paths:
        return (
            "# LUCID_LIB_SKELETON_BEGIN\n"
            "# (no non-/build/ FHS COPY --from paths under /app/ found; no directories to create.)\n"
            "# LUCID_LIB_SKELETON_END\n"
        )
    # Shell-escape single quotes in paths for POSIX sh
    def sq(p: str) -> str:
        return "'" + p.replace("'", "'\"'\"'") + "'"

    mkdir_line = " \\\n    ".join(sq(p) for p in paths)
    for_line = " \\\n    ".join(sq(p) for p in paths)
    return f"""# LUCID_LIB_SKELETON_BEGIN
# Generated: FHS dirs for builder (from final-stage COPY --from, excluding /build/ sources;
# ancestor dirs collapsed; see collect_skeleton_paths_from_dockerfile).
RUN set -eux; \\
  mkdir -p \\
    {mkdir_line}; \\
  for d in \\
    {for_line}; \\
  do \\
    printf 'LUCID_LIB_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \\
    touch "$d/.keep"; \\
  done
# LUCID_LIB_SKELETON_END
"""


DEFAULT_FHS_ROOTS: frozenset[str] = frozenset(
    {
        "/bin",
        "/dev",
        "/etc",
        "/lib",
        "/lib64",
        "/root",
        "/usr",
        "/var",
    }
)

MARK_LIB_BEGIN = "# LUCID_LIB_SKELETON_BEGIN"
MARK_LIB_END = "# LUCID_LIB_SKELETON_END"
MARK_X_FILES_END = "# LUCID_X_FILES_SKELETON_END"


def parse_fhs_roots(s: str) -> frozenset[str]:
    return frozenset(
        str(PurePosixPath(x.strip()))
        for x in s.split(",")
        if x.strip()
    )


def find_insert_after_first_apt_get_install_run(lines: list[str], bs: int, be: int) -> int | None:
    """
    Line index **after** the first ``RUN`` in the builder that invokes ``apt-get install`` (end of
    that instruction). Insert new lines at this index so the block sits before ``apt-get remove``
    / rustup-style RUNs.
    """
    i = bs + 1
    while i < be:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if not re.match(r"^\s*RUN\s", raw, re.IGNORECASE):
            i += 1
            continue
        merged, after = merge_run_block(lines, i, be)
        flat = normalized_one_line(merged)
        if re.search(r"(?:apt-get|apt)\s+install\b", flat, re.IGNORECASE):
            return after
        i = after
    return None


def replace_or_insert_lib_skeleton(
    lines: list[str],
    new_block_lines: list[str],
) -> tuple[list[str], str]:
    """
    Return ``(new_lines, action)`` where ``action`` is ``replaced``,
    ``inserted_after_apt_get_install``, ``inserted_after_x_files``, ``inserted_after_workdir_build``,
    or ``skipped``.
    """
    stages = split_build_stages(lines)
    if len(stages) < 2:
        return lines, "skipped"

    # 1) Replace existing marked block (whole file).
    for i, line in enumerate(lines):
        if line.strip() != MARK_LIB_BEGIN:
            continue
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == MARK_LIB_END:
                merged = lines[:i] + new_block_lines + lines[j + 1 :]
                return merged, "replaced"
        break

    bs, be = stages[-2]
    chunk = [""] + new_block_lines + [""]

    # 2) After first apt-get install RUN (before rustc removal / rustup).
    ins_apt = find_insert_after_first_apt_get_install_run(lines, bs, be)
    if ins_apt is not None:
        return lines[:ins_apt] + chunk + lines[ins_apt:], "inserted_after_apt_get_install"

    # 3) After LUCID_X_FILES_SKELETON_END in builder.
    for idx in range(bs + 1, be):
        if lines[idx].strip() == MARK_X_FILES_END:
            ins = idx + 1
            return lines[:ins] + chunk + lines[ins:], "inserted_after_x_files"

    # 4) After WORKDIR /build in builder.
    for idx in range(bs + 1, be):
        if re.match(r"^\s*WORKDIR\s+/build\s*$", lines[idx], re.IGNORECASE):
            ins = idx + 1
            return lines[:ins] + chunk + lines[ins:], "inserted_after_workdir_build"

    return lines, "skipped"


def process_one_dockerfile(
    path: Path,
    roots: frozenset[str],
    *,
    paths_only: bool,
    debug: bool,
    apply: bool,
    dry_run: bool,
    emit_block: bool,
) -> tuple[int, str]:
    """
    Returns ``(exit_code, summary_line)``. ``exit_code`` 0 normally, 1 on read/write error.
    """
    try:
        text = read_dockerfile_text(path)
    except OSError as e:
        return 1, f"{path}: read error: {e}"

    paths, dbg = collect_skeleton_paths_from_dockerfile(text, fhs_roots=roots)
    if debug:
        for row in dbg:
            if "note" in row:
                print(f"# {path}: {row['note']}", flush=True)
            else:
                print(f"# {path}: debug {row}", flush=True)

    if paths_only:
        for p in paths:
            print(p)
        return 0, f"{path}: {len(paths)} paths"

    block = emit_run_block(paths)
    if not apply:
        if emit_block:
            print(f"##### {path} #####", flush=True)
            print(block, end="", flush=True)
        suffix = "" if (emit_block or paths_only) else " (use --verbose to print block)"
        return 0, f"{path}: generated ({len(paths)} dirs){suffix}"

    lines = text.splitlines(keepends=False)
    new_block_lines = block.splitlines(keepends=False)
    new_lines, action = replace_or_insert_lib_skeleton(lines, new_block_lines)
    if action == "skipped":
        return (
            0,
            f"{path}: skipped (no markers; no apt-get install RUN; no {MARK_X_FILES_END}; no WORKDIR /build in builder)",
        )

    new_text = "\n".join(new_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    if dry_run:
        return 0, f"{path}: dry-run would {action} ({len(paths)} dirs)"

    try:
        path.write_text(new_text, encoding="utf-8")
    except OSError as e:
        return 1, f"{path}: write error: {e}"
    return 0, f"{path}: {action} ({len(paths)} dirs)"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Emit builder-stage LUCID_LIB_SKELETON RUN from final-stage FHS COPY lines."
    )
    ap.add_argument(
        "targets",
        nargs="+",
        type=Path,
        metavar="PATH",
        help=(
            "One or more Dockerfiles and/or directories. Each directory is scanned recursively "
            "(same rules as dockerfile_alignment.discover_lucid_dockerfiles_under). "
            "Duplicate paths are skipped."
        ),
    )
    ap.add_argument(
        "--roots",
        default=",".join(sorted(DEFAULT_FHS_ROOTS)),
        help="Comma-separated absolute path prefixes to include (default: standard FHS under /app sources).",
    )
    ap.add_argument(
        "--paths-only",
        action="store_true",
        help="Print sorted directory paths only (one per line).",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Print stderr lines for skipped COPY sources (build/ or disallowed roots).",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write LUCID_LIB_SKELETON block into each Dockerfile (see module docstring for splice rules).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="With --apply, show what would happen without writing files.",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="When scanning multiple Dockerfiles without --apply, print each generated block (default: one summary line per file).",
    )
    args = ap.parse_args()
    repo_root = discover_repo_root(Path(__file__))

    def _resolve_cli_path(raw: Path) -> Path:
        p = raw.expanduser()
        if p.is_absolute():
            return p.resolve()
        cand = (repo_root / p).resolve()
        return cand if cand.exists() else p.resolve()

    files_acc: list[Path] = []
    seen_resolved: set[Path] = set()
    for raw_target in args.targets:
        target = _resolve_cli_path(raw_target)
        if not target.exists():
            print(f"error: not found: {target}", flush=True)
            return 1
        if target.is_file():
            batch = [target]
        else:
            batch = discover_lucid_dockerfiles_under(target)
            if not batch:
                print(f"error: no Dockerfiles under {target}", flush=True)
                return 1
        for f in batch:
            try:
                k = f.resolve(strict=False)
            except OSError:
                k = f
            if k in seen_resolved:
                continue
            seen_resolved.add(k)
            files_acc.append(f)
    files = files_acc

    roots = parse_fhs_roots(args.roots)

    if args.apply and args.paths_only:
        print("error: --apply and --paths-only are incompatible", flush=True)
        return 1

    emit_block = len(files) == 1 or args.verbose

    worst = 0
    for f in files:
        if len(files) > 1 and args.paths_only:
            print(f"=== {f} ===", flush=True)
        code, summary = process_one_dockerfile(
            f,
            roots,
            paths_only=args.paths_only,
            debug=args.debug,
            apply=args.apply,
            dry_run=args.dry_run,
            emit_block=emit_block,
        )
        if code != 0:
            worst = 1
        print(summary, flush=True)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())

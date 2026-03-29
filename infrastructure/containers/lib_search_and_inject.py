#!/usr/bin/env python3
"""
Search ``infrastructure/containers/**/Dockerfile*`` and ``infrastructure/docker/**/Dockerfile*`` for ``RUN … apt-get install`` blocks (same shape as
``infrastructure/containers/blockchain/Dockerfile.chain-to-pay`` lines **65–86**: cache mounts + package list)
and for **other** RUN lines that create FHS paths (e.g. ``printf … > /var/run/.keep``, ``mkdir -p /usr/local/bin``),
then print **recommended directories** on the builder image to ``COPY`` into a distroless runtime under
``/app/…`` (FHS paths such as ``/usr/bin/``, ``/var/run/``, ``/usr/local/lib/…`` — **not** ``/build/`` or ``./`` skeleton trees).

By default nothing is written to disk. With ``--inject-dockerfile --apply``, splices the marked
apt->FHS ``COPY`` block **into** each multi-stage Dockerfile **after** the **last** ``ENV`` in the
runtime stage (or after the last ``LABEL`` if there is no ``ENV``), e.g. after ``Dockerfile.consensus-engine``-style
LABEL+ENV — never before that block, even when earlier ``COPY`` lines appear in the stage.

Clear command (repo root) — scan all container Dockerfiles in parallel (see ``--jobs``) and show recommendations + example ``COPY`` lines::

  python infrastructure/containers/lib_search_and_inject.py --recommend

Same for one file::

  python infrastructure/containers/lib_search_and_inject.py --recommend --only infrastructure/containers/blockchain/Dockerfile.chain-to-pay

Inject the apt->FHS ``COPY`` block directly into Dockerfiles::

  python infrastructure/containers/lib_search_and_inject.py --recommend --inject-dockerfile --apply

Remove stale ``# COPY …`` hint lines in the **final** ``FROM`` stage (orphans from older tool output), without re-injecting::

  python infrastructure/containers/lib_search_and_inject.py --cleanup-commented-copy --apply

Remove duplicate ``COPY --from=<prior stage> … /app/…`` lines in the final ``FROM`` stage (same normalized
instruction kept once: ``/build/…``→``/app/…`` skeleton copies and FHS paths under ``/app/``)::

  python infrastructure/containers/lib_search_and_inject.py --dedupe-build-app-copy --apply

``--inject-dockerfile`` always runs that cleanup on the runtime stage before splicing the recommend block.

Inserted block markers (inside the Dockerfile). Wildcard sources use a directory dest (e.g. ``/app/usr/lib/``)::

  # LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN
  # Generated: apt -> FHS paths only (not ./ or /build/ skeleton; lib_search_and_inject.py).
  COPY --from=<stage> --chown=<uid:gid> /usr/lib/*/libssl.so* /app/usr/lib/
  COPY --from=<stage> --chown=<uid:gid> /usr/bin/ /app/usr/bin/
  # LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END

Penultimate-``FROM`` (stage -2) ``COPY`` extraction: ``collect_stage_minus2_copy_from_all_dockerfiles``,
``extract_stage_minus2_copy_instructions``. Duplicate ``COPY --from=…`` lines into ``/app/…`` are removed only in the
**final** ``FROM`` stage (runtime / distroless image), with any ``--from=`` stage name: ``remove_duplicate_stage_minus2_build_app_copy_instructions``,
``dedupe_stage_minus2_build_app_copy_all_dockerfiles``, ``inspect_dedupe_build_app_copy``.

Full path to script:
  infrastructure/containers/lib_search_and_inject.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from typing import Iterable

# Stage -2 = penultimate ``FROM`` stage (second-to-last multi-stage slice). See
# :func:`extract_stage_minus2_copy_instructions`.

# Parallel to inject’s LUCID_RUNTIME_COPY_FROM_BUILD_* but FHS-only (no /build/<rel>/).
MARK_APT_RUNTIME_COPY_BEGIN = "# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN"
MARK_APT_RUNTIME_COPY_END = "# LUCID_RUNTIME_COPY_FROM_BUILDER_APT_END"

# Reference Dockerfile for the apt+mount RUN pattern this tool models.
APT_RUN_REFERENCE = (
    "infrastructure/containers/blockchain/Dockerfile.chain-to-pay lines 65-86 "
    "(RUN --mount=...cache... apt-get update && apt-get install ...)"
)

RUN_HELP_BANNER = f"""\
================================================================================
lib_search_and_inject.py - recommended FHS directories for distroless COPY
================================================================================
  Reads:  each Dockerfile under --containers-root (default: infrastructure/containers and infrastructure/docker)
  Models: apt-get install package lists in RUN blocks, like {APT_RUN_REFERENCE}
          plus non-apt RUN lines (mkdir, printf >, touch, chown, chmod) that touch absolute FHS paths.
  Output: merged builder paths (e.g. /usr/bin/, /var/run/, /usr/local/bin/) -> COPY under /app/...
  Write:   --inject-dockerfile --apply splices after the last ENV (or last LABEL) in the runtime stage.
================================================================================
"""

# Packages that only supply compilers/headers/static build tools — not copied for runtime as-is;
# see PACKAGE_RUNTIME_ALIASES for runtime lib equivalents (e.g. libssl-dev → libssl3).
BUILD_ONLY_PACKAGES: frozenset[str] = frozenset(
    {
        "build-essential",
        "gcc",
        "g++",
        "libc6-dev",
        "libc-dev",
        "linux-libc-dev",
        "pkg-config",
        "python3-dev",
        "libffi-dev",
        "libssl-dev",
        "rustc",
        "cargo",
    }
)

# If a -dev or build package is installed, these runtime packages are typical substitutes for COPY.
PACKAGE_RUNTIME_ALIASES: dict[str, tuple[str, ...]] = {
    "libssl-dev": ("libssl3", "openssl"),
    "libffi-dev": ("libffi8",),
    "python3-dev": ("python3.11", "libpython3.11"),
    "curl": ("libcurl4",),
}

# Minimal runtime support paths typically required when copying from a Debian builder into /app/...
# Paths are absolute on the builder stage. Extend per service (e.g. tor) as needed.
PACKAGE_RUNTIME_SUPPORT: dict[str, tuple[str, ...]] = {
    "tini": ("/usr/bin/tini",),
    # Example: Tor is not in chain-to-pay; listed so COPY hints match common service layouts.
    "tor": ("/usr/bin/tor", "/etc/tor/torrc", "/var/lib/tor/"),
    "ca-certificates": (
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/ssl/certs/",  # full store if something loads arbitrary CAs
    ),
    "curl": (
        "/usr/bin/curl",
        "/etc/ssl/openssl.cnf",
    ),
    # Runtime libs often pulled in as dependencies of curl/python; listed for explicit copies.
    "libcurl4": ("/usr/lib/*/libcurl.so*",),  # glob resolved at emit time for documentation
    "libssl3": ("/usr/lib/*/libssl.so*", "/usr/lib/*/ossl-modules/"),
    "libcrypto3": ("/usr/lib/*/libcrypto.so*",),
    "libffi8": ("/usr/lib/*/libffi.so*",),
    # python3-minimal / python3.11 on Debian: interpreters and stdlib (distroless often replaces this).
    "python3": (
        "/usr/bin/python3",
        "/usr/lib/python3.11/",
    ),
    "python3-minimal": ("/usr/bin/python3",),
    "python3.11": (
        "/usr/bin/python3.11",
        "/usr/lib/python3.11/",
    ),
    "python3-distutils": ("/usr/lib/python3.11/distutils/",),
    # Generic fall-through for other python3.* if present
    "python3-pip": ("/usr/lib/python3/dist-packages/",),
    "python3-setuptools": ("/usr/lib/python3/dist-packages/",),
    "python3-wheel": ("/usr/lib/python3/dist-packages/",),
    "openssl": ("/usr/bin/openssl", "/etc/ssl/openssl.cnf"),
    "libpython3.11": ("/usr/lib/python3.11/",),
}

# Optional dirs created later in the same Dockerfile (e.g. chain-to-pay touches /var/run).
POST_INSTALL_HINT_PATHS: tuple[str, ...] = (
    "/var/run/",
    "/var/lib/",
)

# Absolute path prefixes never copied from builder for distroless (caches, build context, apt state).
RUN_SCAFFOLD_EXCLUDE_PREFIXES: tuple[str, ...] = (
    "/build/",
    "/root/.cache",
    "/tmp/",
    "/var/tmp/",
    "/var/cache/apt",
    "/var/lib/apt",
)


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def resolve_path_from_repo(path: Path, repo_root: Path) -> Path:
    """
    Resolve CLI paths relative to the **repository root**, not the process cwd.

    Avoids scanning or editing a single directory when the shell is cd'd into e.g.
    ``infrastructure/containers/database`` and ``--containers-root infrastructure/containers``
    was intended.
    """
    p = path.expanduser()
    if p.is_absolute():
        return p.resolve()
    return (repo_root / p).resolve()


def discover_dockerfiles(containers_roots: list[Path]) -> list[Path]:
    """
    Collect Dockerfile* and dockerfile* under multiple containers_roots.
    Merges results and dedupes.
    """
    seen: set[Path] = set()
    out: list[Path] = []
    for containers_root in containers_roots:
        if not containers_root.is_dir():
            continue
        for pattern in ("Dockerfile*", "dockerfile*"):
            for p in containers_root.rglob(pattern):
                if p.is_file() and not p.name.startswith("."):
                    key = p.resolve()
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def split_build_stages_lines(lines: list[str]) -> list[tuple[int, int]]:
    """
    ``FROM`` stage boundaries as ``(start_line_index, end_line_index_exclusive)``.

    If the file has no ``FROM``, the whole file is treated as a single stage ``(0, len(lines))``.
    """
    from_idx: list[int] = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            from_idx.append(i)
    if not from_idx:
        return [(0, len(lines))]
    stages: list[tuple[int, int]] = []
    for k, start in enumerate(from_idx):
        end = from_idx[k + 1] if k + 1 < len(from_idx) else len(lines)
        stages.append((start, end))
    return stages


def from_instruction_as_name(from_line: str) -> str | None:
    """``AS <name>`` from a ``FROM`` line, or None."""
    m = re.search(r"\bAS\s+(\S+)", from_line, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip().strip("\"'`")


RE_RUN_MOUNT_TARGET = re.compile(r"--mount=[^\n\\]+?target=([^\s,\\]+)", re.IGNORECASE)
RE_USER_LINE = re.compile(r"^\s*USER\s+(?P<u>\S+)", re.IGNORECASE)


def extract_builder_stage_name(content: str) -> str:
    """First ``FROM … AS <name>`` in the Dockerfile (same as inject); defaults to ``builder``."""
    m = re.search(r"^\s*FROM\s+.+\bAS\s+(\S+)", content, re.MULTILINE | re.IGNORECASE)
    return m.group(1) if m else "builder"


def last_user_instruction(dockerfile_text: str) -> str | None:
    """Last ``USER`` value in the file (typical final runtime user for ``--chown``)."""
    last: str | None = None
    for line in dockerfile_text.splitlines():
        m = RE_USER_LINE.match(line)
        if m:
            last = m.group("u")
    return last


def extract_mount_targets_from_run(run_block: str) -> list[str]:
    """``--mount=…,target=/path`` targets (e.g. apt cache mounts on lines 65–66)."""
    out: list[str] = []
    for m in RE_RUN_MOUNT_TARGET.finditer(run_block):
        t = m.group(1).strip()
        if t and t not in out:
            out.append(t)
    return out


def iter_run_blocks(text: str) -> Iterable[str]:
    """Yield RUN instruction bodies (line-continued with \\)."""
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.lstrip()
        if stripped.upper().startswith("RUN"):
            chunk = [raw]
            i += 1
            while i < n and chunk[-1].rstrip().endswith("\\"):
                chunk.append(lines[i])
                i += 1
            yield "\n".join(chunk)
            continue
        i += 1


def extract_apt_packages_from_run(run_block: str) -> list[str]:
    """First ``apt-get install`` / ``apt install`` segment only; package tokens after flags."""
    if not re.search(r"\bapt(?:-get)?\s+install\b", run_block, re.IGNORECASE):
        return []
    # Unwrap Dockerfile line continuations
    one = re.sub(r"\\\s*\n\s*", " ", run_block)
    # Restrict to the shell pipeline part that contains apt install (first &&-separated command)
    # Often: RUN rm... && apt-get update && apt-get install ...
    parts = re.split(r"\s+&&\s+", one)
    segment = ""
    for p in parts:
        if re.search(r"\bapt(?:-get)?\s+install\b", p, re.IGNORECASE):
            segment = p
            break
    if not segment:
        return []
    m = re.search(r"\bapt(?:-get)?\s+install\b(?P<rest>.*)$", segment, re.IGNORECASE)
    if not m:
        return []
    rest = m.group("rest")
    # Stop at ';' starting a new statement in same RUN (rare)
    rest = rest.split(";")[0]
    try:
        tokens = shlex.split(rest)
    except ValueError:
        tokens = rest.split()
    pkgs: list[str] = []
    for t in tokens:
        if not t or t.startswith("#"):
            break
        if t.startswith("-"):
            continue
        pkgs.append(t)
    return pkgs


def apt_install_runs_detail(text: str) -> list[dict[str, object]]:
    """Each RUN that runs ``apt-get install`` / ``apt install``, with mounts + packages."""
    detail: list[dict[str, object]] = []
    for run in iter_run_blocks(text):
        pkgs = extract_apt_packages_from_run(run)
        if not pkgs:
            continue
        mounts = extract_mount_targets_from_run(run)
        detail.append(
            {
                "mount_targets": mounts,
                "apt_packages": pkgs,
            }
        )
    return detail


def _scaffold_path_excluded_raw(p: str) -> bool:
    """Drop caches, ``/build``, and apt dirs; keep e.g. ``/var/lib`` but not ``/var/lib/apt``."""
    pl = p.rstrip("/")
    for ex in RUN_SCAFFOLD_EXCLUDE_PREFIXES:
        if pl == ex.rstrip("/") or pl.startswith(ex):
            return True
    return False


def _scaffold_segment_looks_like_file(seg: str) -> bool:
    """
    Distinguish file paths (``…/.keep``, ``…/foo.txt``) from directory paths (``/var/run``, ``python3.11``).
    ``chown`` often lists dirs without a trailing ``/``; taking ``PurePosixPath.parent`` of ``/var/run`` would
    wrongly yield ``/var/``.
    """
    if seg in (".", "..", ""):
        return False
    if seg.startswith("."):
        return True
    if "." not in seg:
        return False
    if re.match(r"^python\d+\.\d+$", seg):
        return False
    if seg == "site-packages":
        return False
    return True


def _scaffold_raw_looks_like_file_path(p: str) -> bool:
    p = p.rstrip("/")
    if not p:
        return False
    seg = p.split("/")[-1]
    return _scaffold_segment_looks_like_file(seg)


def _normalize_scaffold_to_copy_dir(raw_path: str) -> str | None:
    """Turn a touched path into a ``COPY`` source directory (trailing ``/``), or None."""
    t = raw_path.strip()
    if not t.startswith("/") or t.startswith("/build/") or t.startswith("./"):
        return None
    if "*" in t:
        return None
    if _scaffold_path_excluded_raw(t):
        return None
    if t.endswith("/"):
        root = t
    elif _scaffold_raw_looks_like_file_path(t):
        root = path_to_copy_root(t)
        if not root:
            return None
    else:
        root = t.rstrip("/") + "/"
    if _scaffold_path_excluded_raw(root):
        return None
    return root


def extract_scaffold_fhs_paths_from_run(run_block: str) -> list[str]:
    """
    Paths on the builder image created or touched by ``mkdir``, ``>``, ``touch``, ``chown``, ``chmod``
    in a **single** RUN block (e.g. ``printf … > /var/run/.keep``, ``mkdir -p /usr/local/bin``).

    Skips RUN lines that include ``apt-get install`` / ``apt install`` so ``rm -rf /var/lib/apt/…``
    and cache mounts are not turned into runtime COPY sources.
    """
    one = re.sub(r"\\\s*\n\s*", " ", run_block)
    if re.search(r"\bapt(?:-get)?\s+install\b", one, re.IGNORECASE):
        return []

    raw_candidates: list[str] = []

    for m in re.finditer(r"\bmkdir\s+(?:-p\s+)+([^\n;]+?)(?=\s*(?:&&|;)\s*|\s*$)", one, re.IGNORECASE):
        chunk = m.group(1).strip()
        for tok in chunk.split():
            if tok.startswith("/"):
                raw_candidates.append(tok)

    for m in re.finditer(r">\s*(/[^\s&|;\\]+)", one):
        raw_candidates.append(m.group(1))

    for m in re.finditer(r"\btouch\s+(/[^\s&|;\\]+)", one, re.IGNORECASE):
        raw_candidates.append(m.group(1))

    for m in re.finditer(
        r"\bchown\s+(?:-R\s+)?[0-9]+:[0-9]+\s+(.+?)(?=\s*(?:&&|;)\s*|\s*chmod\b|\s*$)",
        one,
        re.IGNORECASE,
    ):
        chunk = m.group(1).strip()
        for tok in chunk.split():
            if tok.startswith("/"):
                raw_candidates.append(tok)

    for m in re.finditer(r"\bchmod\s+\d+\s+(.+?)(?=\s*(?:&&|;)\s*|\s*$)", one, re.IGNORECASE):
        chunk = m.group(1).strip()
        for tok in chunk.split():
            if tok.startswith("/"):
                raw_candidates.append(tok)

    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_candidates:
        norm = _normalize_scaffold_to_copy_dir(raw)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def collect_scaffold_fhs_paths_from_text(text: str) -> list[str]:
    """All scaffold-derived directory roots from non-apt RUN blocks, order-preserving, deduped."""
    merged: list[str] = []
    seen: set[str] = set()
    for run in iter_run_blocks(text):
        for p in extract_scaffold_fhs_paths_from_run(run):
            if p not in seen:
                seen.add(p)
                merged.append(p)
    return merged


def path_to_copy_root(p: str) -> str | None:
    """Directory used as COPY source root for a file or dir path (no globs)."""
    if "*" in p or not p.startswith("/"):
        return None
    if p.endswith("/"):
        return p
    parent = PurePosixPath(p).parent
    if str(parent) == "/" or str(parent) == ".":
        return "/"
    return str(parent) + "/"


def merge_copy_roots(support_paths: Iterable[str]) -> list[str]:
    """Collapse paths into minimal ``/a/b/`` prefixes so one COPY covers nested dirs."""
    pp_dirs: list[PurePosixPath] = []
    for p in support_paths:
        r = path_to_copy_root(p)
        if not r:
            continue
        pp = PurePosixPath(r.rstrip("/"))
        if str(pp) == "/":
            pp_dirs.append(PurePosixPath("/"))
        else:
            pp_dirs.append(pp)
    uniq: list[PurePosixPath] = []
    for p in pp_dirs:
        if p not in uniq:
            uniq.append(p)
    result: list[PurePosixPath] = []
    for p in sorted(uniq, key=lambda x: (len(x.parts), str(x))):
        if any(p != q and p.is_relative_to(q) for q in uniq if q != p):
            continue
        result.append(p)
    out: list[str] = []
    for p in sorted(result, key=str):
        if str(p) == "/":
            out.append("/")
        else:
            out.append(str(p) + "/")
    return out


def expanded_packages_for_mapping(packages: Iterable[str]) -> list[str]:
    """Include alias runtime packages when a -dev/build package appears."""
    out: list[str] = []
    seen: set[str] = set()
    for pkg in packages:
        if pkg not in seen:
            seen.add(pkg)
            out.append(pkg)
        for alias in PACKAGE_RUNTIME_ALIASES.get(pkg, ()):
            if alias not in seen:
                seen.add(alias)
                out.append(alias)
    return out


def normalized_support_paths(packages: Iterable[str]) -> tuple[str, ...]:
    """Merge package paths; drop build-only; apply aliases; dedupe while preserving order."""
    expanded = expanded_packages_for_mapping(packages)
    seen: set[str] = set()
    ordered: list[str] = []
    for pkg in expanded:
        if pkg in BUILD_ONLY_PACKAGES:
            continue
        for path in PACKAGE_RUNTIME_SUPPORT.get(pkg, ()):
            if path not in seen:
                seen.add(path)
                ordered.append(path)
    return tuple(ordered)


def app_dest_for_src(src: str, app_prefix: str) -> str:
    """Map /usr/bin/tini -> /app/usr/bin/tini; /usr/bin/ -> /app/usr/bin/"""
    p = src.rstrip("/") or src
    if p.startswith("/"):
        return f"{app_prefix.rstrip('/')}{src}" if src.endswith("/") else f"{app_prefix.rstrip('/')}{src}"
    return f"{app_prefix.rstrip('/')}/{src}"


def app_dest_dir_for_glob_src(src: str, app_prefix: str) -> str:
    """
    Directory destination for ``COPY`` when the source contains wildcards (Docker requires dest to
    be a directory ending with ``/``).
    """
    idx = src.find("*")
    if idx < 0:
        d = app_dest_for_src(src, app_prefix)
        return d if d.endswith("/") else d + "/"
    prefix = src[:idx]
    slash = prefix.rfind("/")
    dir_abs = "/" if slash <= 0 else prefix[: slash + 1]
    return app_dest_for_src(dir_abs, app_prefix)


def emit_copy_lines(
    stage: str,
    paths: Iterable[str],
    app_prefix: str,
    chown: str | None,
    *,
    glob_sources: Iterable[str] | None = None,
) -> list[str]:
    lines: list[str] = []
    ch = f" --chown={chown}" if chown else ""
    seen_glob: set[str] = set()
    for src in glob_sources or ():
        if "*" not in src or src in seen_glob:
            continue
        seen_glob.add(src)
        dst = app_dest_dir_for_glob_src(src, app_prefix)
        if not dst.endswith("/"):
            dst = dst + "/"
        lines.append(f"COPY --from={stage}{ch} {src} {dst}")
    for src in paths:
        if "*" in src:
            continue
        dst = app_dest_for_src(src, app_prefix)
        lines.append(f"COPY --from={stage}{ch} {src} {dst}")
    return lines


def effective_chown(runtime_user: str | None, override: str | None) -> str:
    if override is not None:
        return override
    if runtime_user:
        return runtime_user
    return "65532:65532"


def build_apt_fhs_runtime_copy_block_lines(
    merged_roots: list[str],
    runtime_support_paths: list[str],
    builder_stage: str,
    chown: str,
    app_prefix: str,
    detailed: bool,
) -> list[str]:
    """
    Same shape as ``build_runtime_copy_block_lines`` in inject, but sources are FHS paths on the
    builder image (not ``/build/<rel>/`` from the repo skeleton).
    """
    paths_emit: list[str] = list(runtime_support_paths) if detailed else list(merged_roots)
    lines: list[str] = [
        MARK_APT_RUNTIME_COPY_BEGIN,
        "# Generated: apt + RUN scaffold (mkdir/printf/touch/chown) -> FHS (not ./ or /build/; lib_search_and_inject.py).",
    ]
    seen_glob: set[str] = set()
    for p in runtime_support_paths:
        if "*" not in p or p in seen_glob:
            continue
        seen_glob.add(p)
        dst = app_dest_dir_for_glob_src(p, app_prefix)
        if not dst.endswith("/"):
            dst = dst + "/"
        lines.append(f"COPY --from={builder_stage} --chown={chown} {p} {dst}")
    for src in paths_emit:
        if "*" in src:
            continue
        dst = app_dest_for_src(src, app_prefix)
        lines.append(f"COPY --from={builder_stage} --chown={chown} {src} {dst}")
    lines.append(MARK_APT_RUNTIME_COPY_END)
    lines.append("")
    return lines


# Lines like ``# COPY --from=builder ...`` (older recommend output); strip in final stage only.
RE_COMMENTED_COPY_LINE = re.compile(r"^\s*#\s*COPY\b", re.IGNORECASE)


def strip_commented_copy_lines_in_last_stage(plain: list[str]) -> tuple[list[str], int]:
    """
    Drop ``# COPY …`` lines in the last ``FROM`` stage (final image). Leaves builder stages and
    non-commented ``COPY`` untouched. Returns ``(new_lines, removed_count)``.
    """
    from_idx = [i for i, line in enumerate(plain) if re.match(r"^\s*FROM\s", line, re.IGNORECASE)]
    if not from_idx:
        return plain, 0
    stage_start = from_idx[-1]
    removed = 0
    out: list[str] = []
    out.extend(plain[:stage_start])
    for line in plain[stage_start:]:
        if RE_COMMENTED_COPY_LINE.match(line):
            removed += 1
            continue
        out.append(line)
    return out, removed


def cleanup_commented_copy_in_content(content: str) -> tuple[str, int]:
    """Split, strip ``# COPY`` lines in the final stage, rejoin (preserve trailing newline if present)."""
    plain = content.splitlines(keepends=False)
    new_plain, n = strip_commented_copy_lines_in_last_stage(plain)
    out = "\n".join(new_plain)
    if content.endswith("\n"):
        out += "\n"
    return out, n


def normalize_glued_lucid_marker_lines(text: str) -> str:
    """
    Split two ``# LUCID_...`` comments on one physical line (missing newline between them).
    Otherwise ``strip_marked_block`` never matches ``end`` (e.g. ``...APT_END# LUCID_...BUILD_BEGIN``).
    """
    return re.sub(r"(#\s*LUCID[^\n#]+)\s*(#\s*LUCID)", r"\1\n\2", text)


def strip_marked_block(text: str, begin: str, end: str) -> str:
    """Remove begin/end sections (same line-based logic as inject_dockerfile_x_files_skeleton)."""
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


def skip_instruction_with_continuations(plain: list[str], i: int, end: int) -> int:
    """Advance past Dockerfile instruction lines ending with ``\\`` line continuations."""
    j = i
    while j < end:
        line = plain[j].rstrip("\n\r")
        if not line.rstrip().endswith("\\"):
            return j + 1
        j += 1
    return end


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


def _merge_copy_heredoc(lines: list[str], start: int, end: int) -> tuple[str, int, int]:
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


def _merge_copy_instruction_block(lines: list[str], start: int, end: int) -> tuple[str, int]:
    """One Dockerfile ``COPY`` (heredoc or ``\\`` continuations). Returns ``(text, line_after)``."""
    first = lines[start]
    if re.match(r"^\s*COPY\s", first, re.IGNORECASE) and re.search(
        r"COPY\s*<<", first, re.IGNORECASE
    ):
        merged, _, after = _merge_copy_heredoc(lines, start, end)
        return merged, after
    after = skip_instruction_with_continuations(lines, start, end)
    return "\n".join(lines[start:after]), after


def iter_copy_instructions_in_lines_range(
    lines: list[str], range_start: int, range_end: int
) -> list[tuple[int, str]]:
    """Each ``COPY`` in ``[range_start, range_end)``: ``(start_line_index_0based, merged_text)``."""
    out: list[tuple[int, str]] = []
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
        merged, after = _merge_copy_instruction_block(lines, i, range_end)
        out.append((i, merged))
        i = after
    return out


def iter_copy_instruction_spans_in_lines_range(
    lines: list[str], range_start: int, range_end: int
) -> list[tuple[int, int, str]]:
    """
    Each ``COPY`` in ``[range_start, range_end)``:
    ``(start_line_index_0based, end_line_index_exclusive, merged_text)``.
    """
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
        merged, after = _merge_copy_instruction_block(lines, i, range_end)
        out.append((i, after, merged))
        i = after
    return out


def normalized_copy_instruction_key(merged: str) -> str:
    """Stable key for comparing Dockerfile ``COPY`` blocks (unwrap ``\\`` continuations, collapse spaces)."""
    s = merged.strip()
    s = re.sub(r"\\\s*\n\s*", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _build_app_copy_dedupe_final_stage_range(stages: list[tuple[int, int]]) -> tuple[int, int] | None:
    """
    Line range ``(start, end_exclusive)`` for the **final** ``FROM`` stage.

    Skeleton ``COPY --from=<prior stage> --chown=… /build/… /app/…`` lines always live in the last
    stage in Lucid Dockerfiles (distroless/runtime), including multi-stage graphs where the first
    ``FROM … AS`` is not the copy source (e.g. ``strapper`` → ``bundle-prep`` → final).
    """
    if len(stages) < 2:
        return None
    return stages[-1]


def is_final_stage_copy_from_into_app(merged: str) -> bool:
    """
    True for ``COPY --from=<any stage> …`` whose normalized text mentions ``/app/…`` (runtime layout).

    Covers skeleton ``/build/…`` → ``/app/…`` lines and repeated FHS ``COPY`` blocks (e.g. ``/usr/lib/…``
    → ``/app/usr/lib/``) that previously failed dedupe because they lack ``/build/`` in the source path.
    """
    one = normalized_copy_instruction_key(merged)
    if not re.match(r"^COPY\s", one, re.IGNORECASE):
        return False
    if not re.search(r"--from=\S+", one, re.IGNORECASE):
        return False
    if "/app/" not in one:
        return False
    return True


def inspect_dedupe_build_app_copy(content: str) -> dict[str, object]:
    """
    Describe where :func:`remove_duplicate_stage_minus2_build_app_copy_instructions` will scan and
    which duplicate ``COPY --from=…`` into ``/app/`` lines it would drop (for CLI dry-run reporting).
    """
    lines = content.splitlines(keepends=False)
    stages = split_build_stages_lines(lines)
    n_stages = len(stages)
    if n_stages < 2:
        return {
            "ok": False,
            "reason": f"need at least 2 FROM stages (found {n_stages})",
            "total_stages": n_stages,
        }
    bounds = _build_app_copy_dedupe_final_stage_range(stages)
    if bounds is None:
        return {"ok": False, "reason": "internal: no final stage range", "total_stages": n_stages}
    s0, s1 = bounds
    spans = iter_copy_instruction_spans_in_lines_range(lines, s0 + 1, s1)
    seen_keys: dict[str, int] = {}
    skeleton_count = 0
    duplicate_count = 0
    duplicate_details: list[dict[str, object]] = []
    for start, end, merged in spans:
        if not is_final_stage_copy_from_into_app(merged):
            continue
        skeleton_count += 1
        k = normalized_copy_instruction_key(merged)
        if k in seen_keys:
            duplicate_count += 1
            first_ln = seen_keys[k]
            preview = lines[start].strip() if start < len(lines) else merged.strip()
            if len(preview) > 140:
                preview = preview[:137] + "..."
            duplicate_details.append(
                {
                    "start_line_1based": start + 1,
                    "preview": preview,
                    "keeps_first_at_line_1based": first_ln,
                }
            )
        else:
            seen_keys[k] = start + 1
    last_line_1based = s1 if s1 > 0 else len(lines)
    return {
        "ok": True,
        "total_stages": n_stages,
        "final_stage_index_1based": n_stages,
        "final_from_line_1based": s0 + 1,
        "final_from_text": lines[s0].strip(),
        "stage_body_first_line_1based": s0 + 2,
        "stage_body_last_line_1based": last_line_1based,
        "dedupe_candidate_copy_instructions": skeleton_count,
        "duplicate_instructions": duplicate_count,
        "duplicate_details": duplicate_details,
    }


def remove_duplicate_stage_minus2_build_app_copy_instructions(content: str) -> tuple[str, int]:
    """
    In the **final** ``FROM`` stage (runtime image), drop duplicate ``COPY --from=…`` instructions
    that target ``/app/…`` (normalized instruction text matches). First occurrence is kept; later
    identical instructions (after continuation/whitespace normalization) are removed.

    Returns ``(new_content, duplicate_copy_instructions_removed)``. Unchanged if fewer than two
    stages or no duplicates.
    """
    lines = content.splitlines(keepends=False)
    stages = split_build_stages_lines(lines)
    bounds = _build_app_copy_dedupe_final_stage_range(stages)
    if bounds is None:
        return content, 0
    s0, s1 = bounds
    spans = iter_copy_instruction_spans_in_lines_range(lines, s0 + 1, s1)
    seen_keys: set[str] = set()
    remove_line_indices: set[int] = set()
    removed_instructions = 0
    for start, end, merged in spans:
        if not is_final_stage_copy_from_into_app(merged):
            continue
        key = normalized_copy_instruction_key(merged)
        if key in seen_keys:
            removed_instructions += 1
            for li in range(start, end):
                remove_line_indices.add(li)
        else:
            seen_keys.add(key)
    if not remove_line_indices:
        return content, 0
    new_lines = [ln for i, ln in enumerate(lines) if i not in remove_line_indices]
    out = "\n".join(new_lines)
    if content.endswith("\n"):
        out += "\n"
    return out, removed_instructions


def dedupe_stage_minus2_build_app_copy_all_dockerfiles(
    containers_root: Path,
    *,
    repo_root: Path | None = None,
    apply: bool = False,
) -> list[dict[str, object]]:
    """
    Run :func:`remove_duplicate_stage_minus2_build_app_copy_instructions` on every
    ``Dockerfile`` / ``Dockerfile.*`` under ``containers_root`` (recursive, same discovery as
    :func:`discover_dockerfiles`). With ``apply=True``, write files that changed.

    Each result dict includes ``file`` (repo-relative when possible), ``path``, ``removed_duplicates``,
    ``written`` (bool), and optional ``error``.
    """
    rr = repo_root or repo_root_from_here()
    results: list[dict[str, object]] = []
    for path in discover_dockerfiles([containers_root]):
        try:
            rel_file = str(path.resolve().relative_to(rr))
        except ValueError:
            rel_file = str(path)
        row: dict[str, object] = {
            "file": rel_file,
            "path": str(path.resolve()),
            "removed_duplicates": 0,
            "written": False,
            "error": None,
        }
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            row["error"] = str(e)
            results.append(row)
            continue
        new_text, n = remove_duplicate_stage_minus2_build_app_copy_instructions(text)
        row["removed_duplicates"] = n
        if n == 0:
            results.append(row)
            continue
        if apply:
            try:
                path.write_text(new_text, encoding="utf-8", newline="\n")
                row["written"] = True
            except OSError as e:
                row["error"] = str(e)
        results.append(row)
    return results


def extract_stage_minus2_copy_instructions(text: str) -> dict[str, object]:
    """
    Parse Dockerfile text and return every ``COPY`` instruction in **stage -2** (the penultimate
    ``FROM`` stage — the build stage immediately before the final image stage).

    Keys:

    - ``stage_count``: number of ``FROM`` stages (or 1 if no ``FROM``).
    - ``stage_minus2``: dict with ``from_line_1based``, ``as_name``, ``from_text``, or ``None`` if
      fewer than two stages.
    - ``copy_instructions``: list of ``{"start_line_1based": int, "text": str}``.
    - ``reason``: empty when ok; otherwise a short skip message.
    """
    lines = text.splitlines(keepends=False)
    stages = split_build_stages_lines(lines)
    n = len(stages)
    if n < 2:
        return {
            "stage_count": n,
            "stage_minus2": None,
            "copy_instructions": [],
            "reason": "need at least 2 FROM stages for stage -2 (penultimate)",
        }
    s0, s1 = stages[-2]
    from_line = lines[s0]
    copies = iter_copy_instructions_in_lines_range(lines, s0 + 1, s1)
    return {
        "stage_count": n,
        "stage_minus2": {
            "from_line_1based": s0 + 1,
            "as_name": from_instruction_as_name(from_line),
            "from_text": from_line.strip(),
        },
        "copy_instructions": [
            {"start_line_1based": li + 1, "text": block} for li, block in copies
        ],
        "reason": "",
    }


def collect_stage_minus2_copy_from_all_dockerfiles(
    containers_root: Path,
    *,
    repo_root: Path | None = None,
) -> list[dict[str, object]]:
    """
    Read every ``Dockerfile`` / ``Dockerfile.*`` under ``containers_root`` (recursive) and attach
    :func:`extract_stage_minus2_copy_instructions` for each file.

    ``repo_root`` is used only for ``file`` (repo-relative path); defaults to
    :func:`repo_root_from_here`.
    """
    rr = repo_root or repo_root_from_here()
    results: list[dict[str, object]] = []
    for path in discover_dockerfiles([containers_root]):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            results.append(
                {
                    "file": str(path),
                    "path": str(path.resolve()),
                    "error": str(e),
                }
            )
            continue
        detail = extract_stage_minus2_copy_instructions(text)
        try:
            rel_file = str(path.resolve().relative_to(rr))
        except ValueError:
            rel_file = str(path)
        row: dict[str, object] = {
            "file": rel_file,
            "path": str(path.resolve()),
            **detail,
        }
        results.append(row)
    return results


def find_insert_after_workdir_arg_label_env_runtime(plain: list[str]) -> int | None:
    """
    Line index to insert **after** the **last** ``ENV`` in the last runtime stage, or after the last
    ``LABEL`` if there is no ``ENV``, so the apt->FHS block never sits **before** LABEL/ENV (e.g.
    ``Dockerfile.consensus-engine`` LABEL+ENV around lines 183-206).

    If the stage has no LABEL/ENV at all, falls back to after ``WORKDIR /app`` plus any leading ``ARG``
    run (before the first non-ARG instruction).
    """
    from_idx: list[int] = []
    for i, line in enumerate(plain):
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            from_idx.append(i)
    if len(from_idx) < 2:
        return None
    k = len(from_idx) - 1
    stage_start = from_idx[k]
    stage_end = len(plain)
    workdir_idx: int | None = None
    for i in range(stage_start, stage_end):
        if re.match(r"^\s*WORKDIR\s+/app(\s|$)", plain[i], re.IGNORECASE):
            workdir_idx = i
            break
    if workdir_idx is None:
        return None

    last_env_end: int | None = None
    last_label_end: int | None = None
    i = stage_start
    while i < stage_end:
        raw = plain[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if re.match(r"^\s*ENV\s", raw, re.IGNORECASE):
            last_env_end = skip_instruction_with_continuations(plain, i, stage_end)
            i = last_env_end
            continue
        if re.match(r"^\s*LABEL\s", raw, re.IGNORECASE):
            last_label_end = skip_instruction_with_continuations(plain, i, stage_end)
            i = last_label_end
            continue
        i += 1

    if last_env_end is not None:
        return last_env_end
    if last_label_end is not None:
        return last_label_end

    i = workdir_idx + 1
    insert_after = workdir_idx + 1
    while i < stage_end:
        raw = plain[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if re.match(r"^\s*ARG\s", raw, re.IGNORECASE):
            insert_after = skip_instruction_with_continuations(plain, i, stage_end)
            i = insert_after
            continue
        break
    return insert_after


def inject_apt_fhs_block_content(
    content: str,
    r: dict,
    app_prefix: str,
    chown_override: str | None,
    detailed: bool,
) -> tuple[str | None, str]:
    """
    Strip any prior ``LUCID_RUNTIME_COPY_FROM_BUILDER_APT_*`` block, insert a fresh one **after**
    the **last** ``ENV`` in the runtime stage (or after the last ``LABEL`` if no ``ENV``), so the
    block is never placed before LABEL/ENV even when ``COPY`` appears earlier in the stage.
    Returns (new_text, skip_reason); new_text None if skipped.
    """
    merged = list(r["merged_copy_roots"])
    support = list(r["runtime_support_paths"])
    if not merged and not any("*" in p for p in support):
        return None, "empty apt/scaffold to FHS mapping"
    stage = str(r.get("first_as") or "builder")
    chown = effective_chown(r.get("runtime_user"), chown_override)
    block_lines = build_apt_fhs_runtime_copy_block_lines(
        merged, support, stage, chown, app_prefix, detailed
    )
    text = strip_marked_block(content, MARK_APT_RUNTIME_COPY_BEGIN, MARK_APT_RUNTIME_COPY_END)
    plain = text.splitlines(keepends=False)
    plain, _ = strip_commented_copy_lines_in_last_stage(plain)
    insert_at = find_insert_after_workdir_arg_label_env_runtime(plain)
    if insert_at is None:
        return None, "need 2+ FROM stages, WORKDIR /app in runtime stage, and a valid insert point"
    new_plain = plain[:insert_at] + block_lines + plain[insert_at:]
    out = "\n".join(new_plain)
    if text.endswith("\n"):
        out += "\n"
    if out == content:
        return None, "already up to date (block unchanged)"
    return out, ""


def result_has_apt_fhs_mapping(r: dict) -> bool:
    """True if scan produced paths that could become an injected COPY block."""
    return bool(r.get("merged_copy_roots")) or any("*" in p for p in r.get("runtime_support_paths", ()))


def scan_file(path: Path, repo_root: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    as_name = extract_builder_stage_name(text)
    runtime_user = last_user_instruction(text)
    apt_runs = apt_install_runs_detail(text)
    mount_union: list[str] = []
    for block in apt_runs:
        mounts = block.get("mount_targets", [])
        if not isinstance(mounts, list):
            continue
        for t in mounts:
            if isinstance(t, str) and t not in mount_union:
                mount_union.append(t)
    all_pkgs: list[str] = []
    for run in iter_run_blocks(text):
        all_pkgs.extend(extract_apt_packages_from_run(run))
    # dedupe pkgs order-preserving
    seen_p: set[str] = set()
    uniq_pkgs: list[str] = []
    for p in all_pkgs:
        if p not in seen_p:
            seen_p.add(p)
            uniq_pkgs.append(p)
    expanded = expanded_packages_for_mapping(uniq_pkgs)
    support = normalized_support_paths(uniq_pkgs)
    run_scaffold_paths = collect_scaffold_fhs_paths_from_text(text)
    seen_support: set[str] = set()
    combined_support: list[str] = []
    for p in support:
        if p not in seen_support:
            seen_support.add(p)
            combined_support.append(p)
    for p in run_scaffold_paths:
        if p not in seen_support:
            seen_support.add(p)
            combined_support.append(p)
    merged_roots = merge_copy_roots(combined_support)
    build_only_hit = [p for p in uniq_pkgs if p in BUILD_ONLY_PACKAGES]
    unknown = [
        p
        for p in expanded
        if p not in BUILD_ONLY_PACKAGES and p not in PACKAGE_RUNTIME_SUPPORT
    ]
    try:
        rel_file = str(path.relative_to(repo_root))
    except ValueError:
        rel_file = str(path)
    return {
        "file": rel_file,
        "path": str(path),
        "first_as": as_name,
        "runtime_user": runtime_user,
        "apt_install_runs": apt_runs,
        "apt_cache_mount_targets": mount_union,
        "apt_packages": uniq_pkgs,
        "build_only_packages": build_only_hit,
        "run_scaffold_fhs_paths": run_scaffold_paths,
        "runtime_support_paths": combined_support,
        "merged_copy_roots": merged_roots,
        "unknown_packages_no_map": unknown,
        "expanded_packages_for_mapping": expanded,
        "post_install_fhs_hints": list(POST_INSTALL_HINT_PATHS),
    }


def resolve_job_workers(jobs: int, num_tasks: int) -> int:
    """Thread pool size: ``--jobs 0`` = auto (I/O-bound scan/write)."""
    if num_tasks < 1:
        return 1
    if jobs > 0:
        return max(1, min(jobs, num_tasks))
    cpu = os.cpu_count() or 4
    return max(1, min(num_tasks, min(32, cpu * 4)))


def _scan_one_safe(df: Path, repo_root: Path) -> tuple[dict | None, str | None]:
    try:
        return scan_file(df, repo_root), None
    except OSError as e:
        return None, f"error: {df}: {e}"


def apply_actions_to_dockerfile(r: dict, args: argparse.Namespace) -> dict[str, object]:
    """
    Inject apt->FHS block, cleanup ``# COPY`` lines, and/or dedupe duplicate ``COPY --from=…`` into ``/app/…``.
    Returns flags and per-file counters (no printing — main aggregates and reports).
    """
    df = Path(r["path"])
    out: dict[str, object] = {
        "injected_this": False,
        "cleanup_this": False,
        "cleanup_removed": 0,
        "dedupe_this": False,
        "dedupe_removed": 0,
        "inject_skip_reason": "",
        "inject_would": False,
        "docker_written": 0,
        "docker_skipped": 0,
        "docker_dry": 0,
        "read_error": None,
        "write_error": None,
    }
    if args.inject_dockerfile:
        try:
            raw_df = df.read_text(encoding="utf-8")
        except OSError as e:
            out["docker_skipped"] = 1
            out["inject_skip_reason"] = f"read error: {e}"
            out["read_error"] = f"read {df}: {e}"
        else:
            new_c, inj_reason = inject_apt_fhs_block_content(
                raw_df, r, args.app_prefix, args.chown, args.emit_copy_detailed
            )
            if new_c is None:
                out["docker_skipped"] = 1
                out["inject_skip_reason"] = inj_reason
            elif args.apply:
                try:
                    df.write_text(new_c, encoding="utf-8", newline="\n")
                    out["docker_written"] = 1
                    out["injected_this"] = True
                except OSError as e:
                    out["docker_skipped"] = 1
                    out["inject_skip_reason"] = f"write error: {e}"
                    out["write_error"] = f"write {df}: {e}"
            else:
                out["docker_dry"] = 1
                out["inject_would"] = True
    elif args.cleanup_commented_copy:
        try:
            raw_df = df.read_text(encoding="utf-8")
        except OSError as e:
            out["docker_skipped"] = 1
            out["inject_skip_reason"] = f"read error: {e}"
            out["read_error"] = f"read {df}: {e}"
        else:
            new_c, cleanup_removed = cleanup_commented_copy_in_content(raw_df)
            out["cleanup_removed"] = cleanup_removed
            if new_c == raw_df:
                out["docker_skipped"] = 1
                out["inject_skip_reason"] = "no # COPY lines to remove in final stage"
            elif args.apply:
                try:
                    df.write_text(new_c, encoding="utf-8", newline="\n")
                    out["docker_written"] = 1
                    out["cleanup_this"] = True
                except OSError as e:
                    out["docker_skipped"] = 1
                    out["inject_skip_reason"] = f"write error: {e}"
                    out["write_error"] = f"write {df}: {e}"
            else:
                out["docker_dry"] = 1
                out["inject_would"] = True
    elif args.dedupe_build_app_copy:
        try:
            raw_df = df.read_text(encoding="utf-8")
        except OSError as e:
            out["docker_skipped"] = 1
            out["inject_skip_reason"] = f"read error: {e}"
            out["read_error"] = f"read {df}: {e}"
        else:
            out["dedupe_inspect"] = inspect_dedupe_build_app_copy(raw_df)
            new_c, n_dup = remove_duplicate_stage_minus2_build_app_copy_instructions(raw_df)
            out["dedupe_removed"] = n_dup
            if n_dup == 0:
                out["docker_skipped"] = 1
                out["inject_skip_reason"] = "no duplicate build->app COPY lines in final FROM stage"
            elif args.apply:
                try:
                    df.write_text(new_c, encoding="utf-8", newline="\n")
                    out["docker_written"] = 1
                    out["dedupe_this"] = True
                except OSError as e:
                    out["docker_skipped"] = 1
                    out["inject_skip_reason"] = f"write error: {e}"
                    out["write_error"] = f"write {df}: {e}"
            else:
                out["docker_dry"] = 1
                out["inject_would"] = True
    return out


def main() -> int:
    root = repo_root_from_here()
    default_scan_roots = [
        root / "infrastructure" / "containers",
        root / "infrastructure" / "docker",
    ]

    ap = argparse.ArgumentParser(
        description=(
            "Scan Dockerfiles for apt-get install RUN blocks; recommend FHS COPY paths for distroless. "
            "Optional: --inject-dockerfile --apply splices the marked block into each Dockerfile."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (repo root):
  python infrastructure/containers/lib_search_and_inject.py --recommend
  python infrastructure/containers/lib_search_and_inject.py --recommend -j 16
  python infrastructure/containers/lib_search_and_inject.py --recommend --inject-dockerfile --apply
  python infrastructure/containers/lib_search_and_inject.py --inject-dockerfile --apply --only infrastructure/containers/blockchain/Dockerfile.chain-to-pay
  python infrastructure/containers/lib_search_and_inject.py --cleanup-commented-copy --apply
  python infrastructure/containers/lib_search_and_inject.py --dedupe-build-app-copy --apply

  --inject-dockerfile without --apply is dry-run. --apply persists with --inject-dockerfile, --cleanup-commented-copy, or --dedupe-build-app-copy.
""",
    )
    ap.add_argument(
        "--containers-root",
        action="append",
        type=Path,
        dest="containers_roots",
        metavar="DIR",
        help=(
            "Scan tree (repeatable; default: infrastructure/containers and infrastructure/docker). "
            "Relative paths are resolved from the repository root, not the shell cwd."
        ),
    )
    ap.add_argument(
        "--only",
        type=Path,
        default=None,
        help=(
            "Process a single Dockerfile path (like inject). Relative paths are from the repository root. "
            "Default is all Dockerfiles under the default scan roots (or paths from --containers-root)."
        ),
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Write Dockerfiles when used with --inject-dockerfile, --cleanup-commented-copy, or "
            "--dedupe-build-app-copy. No effect without one of those flags."
        ),
    )
    ap.add_argument(
        "--inject-dockerfile",
        action="store_true",
        help=(
            "Splice # LUCID_RUNTIME_COPY_FROM_BUILDER_APT_BEGIN … END after the last ENV (or last LABEL) "
            "in the runtime stage. Strips # COPY … lines in the final stage first, then inserts the "
            "same COPY lines as --recommend. Requires --apply to write; "
            "otherwise dry-run."
        ),
    )
    ap.add_argument(
        "--cleanup-commented-copy",
        action="store_true",
        help=(
            "Remove # COPY … lines in the final FROM stage (stale hints). With --inject-dockerfile, "
            "this runs automatically before splice. With --apply and without --inject-dockerfile, "
            "only performs this cleanup."
        ),
    )
    ap.add_argument(
        "--dedupe-build-app-copy",
        action="store_true",
        help=(
            "Remove duplicate COPY --from=<prior stage> … /app/… instructions in the final FROM stage "
            "(normalized match; includes FHS copies without /build/ in the source path). "
            "Dry-run without --recommend prints scope per file (stage line, counts). "
            "With --apply, write each changed Dockerfile."
        ),
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    ap.add_argument("--json", action="store_true", help="Print one JSON array for all files.")
    ap.add_argument(
        "--recommend",
        action="store_true",
        help=(
            "Recommended entrypoint: print banner + suggested COPY lines for apt install RUNs "
            "(same pattern as Dockerfile.chain-to-pay:65-86). Implies --emit-copy."
        ),
    )
    ap.add_argument(
        "--emit-copy",
        action="store_true",
        help="Print merged or per-path COPY lines in the report (included automatically with --recommend).",
    )
    ap.add_argument(
        "--emit-copy-detailed",
        action="store_true",
        help="Per-path COPY lines (not merged); use with --emit-copy.",
    )
    ap.add_argument("--app-prefix", default="/app", help="Destination root (default /app).")
    ap.add_argument(
        "--chown",
        default=None,
        metavar="UID:GID",
        help="Override --chown on generated COPY lines. Default: last USER in Dockerfile, else 65532:65532.",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="With --apply: only print paths of Dockerfiles that were modified (no full per-file report).",
    )
    ap.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Parallel worker threads for scanning and inject/cleanup/dedupe (default: 0 = auto, "
            "min(32, cpu*4), capped by file count)."
        ),
    )
    args = ap.parse_args()
    if args.write:
        args.apply = True
    if args.recommend:
        args.emit_copy = True

    if args.apply and not args.inject_dockerfile and not args.cleanup_commented_copy and not args.dedupe_build_app_copy:
        print(
            "warning: --apply does nothing without --inject-dockerfile, --cleanup-commented-copy, or --dedupe-build-app-copy.",
            file=sys.stderr,
        )

    if args.containers_roots:
        containers_roots = [resolve_path_from_repo(p, root) for p in args.containers_roots]
    else:
        containers_roots = list(default_scan_roots)

    if args.only is not None:
        one = resolve_path_from_repo(args.only, root)
        if not one.is_file():
            print(f"error: --only is not a file: {one}", file=sys.stderr)
            return 1
        dockerfiles = [one]
    else:
        if not any(r.is_dir() for r in containers_roots):
            print(
                "error: no scan root directory exists: "
                + ", ".join(str(r) for r in containers_roots),
                file=sys.stderr,
            )
            return 1
        dockerfiles = discover_dockerfiles(containers_roots)

    workers = resolve_job_workers(args.jobs, len(dockerfiles))
    results: list[dict] = []
    if dockerfiles:
        pool = max(1, min(workers, len(dockerfiles)))
        with ThreadPoolExecutor(max_workers=pool) as ex:
            scan_pairs = list(ex.map(lambda df: _scan_one_safe(df, root), dockerfiles))
        for r, err in scan_pairs:
            if err:
                print(err, file=sys.stderr)
            elif r is not None:
                results.append(r)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    quiet_apply = args.quiet and args.apply and (
        args.inject_dockerfile
        or args.cleanup_commented_copy
        or args.dedupe_build_app_copy
    )
    if args.recommend and not quiet_apply:
        print(RUN_HELP_BANNER)

    docker_written = 0
    docker_skipped = 0
    docker_dry = 0

    action_metas: list[dict[str, object]] = []
    if results and (args.inject_dockerfile or args.cleanup_commented_copy or args.dedupe_build_app_copy):
        pool_apply = max(1, min(workers, len(results)))
        with ThreadPoolExecutor(max_workers=pool_apply) as ex:
            action_metas = list(ex.map(lambda rr: apply_actions_to_dockerfile(rr, args), results))

    for idx, r in enumerate(results):
        df = Path(r["path"])
        chown_s = effective_chown(r.get("runtime_user"), args.chown)
        detailed = args.emit_copy_detailed

        injected_this = False
        cleanup_this = False
        cleanup_removed = 0
        dedupe_this = False
        dedupe_removed = 0
        inject_skip_reason = ""
        inject_would = False
        if action_metas:
            meta = action_metas[idx]
            injected_this = bool(meta["injected_this"])
            cleanup_this = bool(meta["cleanup_this"])
            cleanup_removed = int(meta["cleanup_removed"])
            dedupe_this = bool(meta.get("dedupe_this", False))
            dedupe_removed = int(meta.get("dedupe_removed", 0))
            inject_skip_reason = str(meta["inject_skip_reason"])
            inject_would = bool(meta["inject_would"])
            docker_written += int(meta["docker_written"])
            docker_skipped += int(meta["docker_skipped"])
            docker_dry += int(meta["docker_dry"])
            if meta.get("read_error"):
                print(f"error: {meta['read_error']}", file=sys.stderr)
            if meta.get("write_error"):
                print(f"error: {meta['write_error']}", file=sys.stderr)

        if quiet_apply:
            if injected_this or cleanup_this or dedupe_this:
                print(str(df))
            continue

        dedupe_focus_only = args.dedupe_build_app_copy and not args.recommend
        if dedupe_focus_only:
            print(f"=== {r['path']} ===")
            if action_metas:
                meta = action_metas[idx]
                if meta.get("read_error"):
                    print(f"  error: {meta['read_error']}")
                else:
                    insp_obj = meta.get("dedupe_inspect")
                    if isinstance(insp_obj, dict):
                        if not insp_obj.get("ok"):
                            print(
                                f"  [dedupe-build-app-copy] {insp_obj.get('reason', 'cannot analyze')}"
                            )
                        else:
                            print(
                                f"  Final FROM stage #{insp_obj['final_stage_index_1based']} of "
                                f"{insp_obj['total_stages']} "
                                f"(comment \"Stage 2\" in 2-stage files = this stage; FROM at line "
                                f"{insp_obj['final_from_line_1based']})"
                            )
                            print(f"    {insp_obj['final_from_text']}")
                            print(
                                f"  COPY scan: lines {insp_obj['stage_body_first_line_1based']}-"
                                f"{insp_obj['stage_body_last_line_1based']} - "
                                "pattern COPY --from=<stage> ... paths including /app/..."
                            )
                            print(
                                f"  Matching COPY --from into /app: {insp_obj['dedupe_candidate_copy_instructions']}"
                            )
                            print(
                                f"  Duplicate instructions (remove with --apply): "
                                f"{insp_obj['duplicate_instructions']}"
                            )
                            details = insp_obj.get("duplicate_details") or []
                            for d in details[:15]:
                                print(
                                    f"    - line {d['start_line_1based']} duplicates line "
                                    f"{d['keeps_first_at_line_1based']}: {d['preview']}"
                                )
                            if len(details) > 15:
                                print(f"    ... {len(details) - 15} more")
                if not meta.get("read_error"):
                    if dedupe_this:
                        print(
                            f"  [dedupe-build-app-copy] wrote: removed {dedupe_removed} duplicate instruction(s)"
                        )
                    elif inject_would and not args.apply:
                        print("  [dedupe-build-app-copy] dry-run: add --apply to write")
                    elif inject_skip_reason:
                        print(f"  [dedupe-build-app-copy] skipped: {inject_skip_reason}")
            print()
            continue

        print(f"=== {r['path']} ===")
        print(f"  first AS: {r['first_as']!r}")
        print(f"  runtime USER (last in file): {r['runtime_user']!r}")
        if r.get("apt_cache_mount_targets"):
            print(f"  apt RUN mount targets (cache): {', '.join(r['apt_cache_mount_targets'])}")
        if r["apt_packages"]:
            print(f"  apt packages (all RUNs): {', '.join(r['apt_packages'])}")
        else:
            print("  apt packages: (none detected)")
        if r["build_only_packages"]:
            print(f"  build-only (skipped for runtime paths): {', '.join(r['build_only_packages'])}")
        if r["unknown_packages_no_map"]:
            print(f"  unknown (add to PACKAGE_RUNTIME_SUPPORT): {', '.join(r['unknown_packages_no_map'])}")
        if r.get("run_scaffold_fhs_paths"):
            print(
                "  RUN scaffold dirs (mkdir / printf> / touch / chown / chmod, excluding apt install RUNs): "
                + ", ".join(r["run_scaffold_fhs_paths"])
            )
        print("  recommended merged roots on builder -> COPY into /app/... (apt packages + RUN scaffold):")
        print(f"    reference pattern: {APT_RUN_REFERENCE}")
        for pp in r["merged_copy_roots"]:
            print(f"    {pp}")
        print("  curated path list before merge (per mapped package):")
        for pp in r["runtime_support_paths"]:
            print(f"    {pp}")
        print("  FHS hints (often needed if Dockerfile touches /var or PID files):")
        for pp in r["post_install_fhs_hints"]:
            print(f"    {pp}")
        show_copy = args.emit_copy or args.apply or args.inject_dockerfile or args.dedupe_build_app_copy
        if show_copy and r["first_as"]:
            paths_emit = (
                r["runtime_support_paths"]
                if detailed
                else r["merged_copy_roots"]
            )
            if paths_emit or any("*" in x for x in r["runtime_support_paths"]):
                label = "suggested COPY (per-path)" if detailed else "suggested COPY (merged dirs)"
                print(f"  {label} --from={r['first_as']} --chown={chown_s!r}:")
                for line in emit_copy_lines(
                    r["first_as"],
                    paths_emit,
                    args.app_prefix,
                    chown_s,
                    glob_sources=r["runtime_support_paths"],
                ):
                    print(f"    {line}")
            elif not r["runtime_support_paths"]:
                print("  (no mapped runtime paths to COPY)")
        if args.dedupe_build_app_copy and action_metas:
            di = action_metas[idx].get("dedupe_inspect")
            if isinstance(di, dict) and di.get("ok"):
                print(
                    f"  [dedupe-build-app-copy] scope: final stage {di['final_stage_index_1based']}/"
                    f"{di['total_stages']} (FROM line {di['final_from_line_1based']}); "
                    f"COPY --from into /app matched: {di['dedupe_candidate_copy_instructions']}; "
                    f"duplicates: {di['duplicate_instructions']}"
                )
        if args.inject_dockerfile:
            if injected_this:
                print(
                    "  [inject-dockerfile] updated Dockerfile (apt/scaffold->FHS COPY block after last ENV or LABEL)"
                )
            elif inject_skip_reason:
                print(f"  [inject-dockerfile] skipped: {inject_skip_reason}")
            elif inject_would and not args.apply:
                print("  [inject-dockerfile] dry-run: would inject (add --apply to write)")
        elif args.cleanup_commented_copy:
            if cleanup_this:
                print(
                    f"  [cleanup-commented-copy] removed {cleanup_removed} line(s) (# COPY in final stage)"
                )
            elif inject_skip_reason:
                print(f"  [cleanup-commented-copy] skipped: {inject_skip_reason}")
            elif inject_would and not args.apply:
                print(
                    "  [cleanup-commented-copy] dry-run: would remove # COPY lines (add --apply to write)"
                )
        elif args.dedupe_build_app_copy:
            if dedupe_this:
                print(
                    f"  [dedupe-build-app-copy] removed {dedupe_removed} duplicate COPY instruction(s) "
                    "(final FROM stage)"
                )
            elif inject_skip_reason:
                print(f"  [dedupe-build-app-copy] skipped: {inject_skip_reason}")
            elif inject_would and not args.apply:
                print(
                    "  [dedupe-build-app-copy] dry-run: would remove duplicate COPY lines (add --apply to write)"
                )
        print()

    if args.apply and args.inject_dockerfile:
        print(
            f"# Apply summary: Dockerfiles injected: {docker_written}, skipped: {docker_skipped}."
        )
    elif args.apply and args.cleanup_commented_copy and not args.inject_dockerfile:
        print(
            f"# Apply summary: Dockerfiles cleaned (# COPY removed): {docker_written}, skipped: {docker_skipped}."
        )
    elif (
        args.apply
        and args.dedupe_build_app_copy
        and not args.inject_dockerfile
        and not args.cleanup_commented_copy
    ):
        print(
            f"# Apply summary: Dockerfiles deduped (build->app COPY): {docker_written}, skipped: {docker_skipped}."
        )
    elif args.inject_dockerfile and docker_dry:
        print(
            f"# Dry-run: {docker_dry} Dockerfile(s) would get apt->FHS block; {docker_skipped} skipped. "
            "Add --apply to write."
        )
    elif args.cleanup_commented_copy and docker_dry and not args.inject_dockerfile:
        print(
            f"# Dry-run: {docker_dry} Dockerfile(s) would have # COPY lines removed; {docker_skipped} skipped. "
            "Add --apply to write."
        )
    elif args.dedupe_build_app_copy and docker_dry and not args.inject_dockerfile:
        print(
            f"# Dry-run: {docker_dry} Dockerfile(s) would have duplicate build->app COPY removed; "
            f"{docker_skipped} skipped. Add --apply to write."
        )
    elif not args.quiet and not args.inject_dockerfile and not args.cleanup_commented_copy and not args.dedupe_build_app_copy:
        n = sum(1 for rr in results if result_has_apt_fhs_mapping(rr))
        print(
            f"# Dry-run: {n} Dockerfile(s) have apt->FHS mapping. "
            "Inject with: --inject-dockerfile --apply. Tip: --recommend for banner + COPY lines."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

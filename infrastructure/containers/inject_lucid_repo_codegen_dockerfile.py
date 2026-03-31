"""
File: /app/configs/inject_lucid_repo_codegen_dockerfile.py
x-lucid-file-path: /app/configs/inject_lucid_repo_codegen_dockerfile.py
x-lucid-file-directory: /app/configs
x-lucid-file-type: python

Insert or refresh a builder-stage ``RUN`` that executes ``lucid_docker_build_codegen.sh``.

That shell script runs, in order:

- ``_normalise_lucid_shell_headers.sh``
- ``_normalise_lucid_yaml_headers.py``
- ``_normalise_lucid_headers.py`` (Python docstrings)
- ``_normalise_lucid_headers.py --x-files-listing``
- ``_gen_host_config.py`` (needs repo-root ``ports.txt``)
- ``infrastructure/containers/_gen_x_lucid_cluster_calibration.py``

**Dockerfiles must copy a repo-root layout into the builder ``WORKDIR``** (often ``/build``) so
those paths exist; partial service-only contexts will fail unless you add the missing trees or
omit this block.

Markers (same style as ``LUCID_X_FILES_SKELETON_*``):

- ``# LUCID_REPO_CODEGEN_INSERT`` — single line replaced by the full marked block (opt-in per file).
- ``# LUCID_REPO_CODEGEN_BEGIN`` … ``# LUCID_REPO_CODEGEN_END`` — block replaced on re-run.

Default: **dry-run** (no writes). Use ``--apply`` to save.

Strip generated blocks::

    python infrastructure/containers/inject_lucid_repo_codegen_dockerfile.py --strip --apply

Bulk insert **after the first** ``WORKDIR /build`` (use only when you know the stage has a full repo copy)::

    python infrastructure/containers/inject_lucid_repo_codegen_dockerfile.py --after-workdir-build --apply

Scan roots (always both): ``infrastructure/containers/``, ``infrastructure/docker/``.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARK_BEGIN = "# LUCID_REPO_CODEGEN_BEGIN"
MARK_END = "# LUCID_REPO_CODEGEN_END"
MARK_INSERT = "# LUCID_REPO_CODEGEN_INSERT"

# Dockerfile fragment: backslash-continued RUN for readability.
CODEGEN_BLOCK_LINES = (
    f"{MARK_BEGIN}",
    "# Lucid repo codegen: normalises headers; regenerates x-files-listing.txt, host-config.yml,",
    "# and infrastructure/containers/services/x_lucid_cluster_calibration/*.yml.",
    "# Requires repo root at WORKDIR (e.g. /build): _normalise_lucid_headers.py, ports.txt, full trees for scanners.",
    "RUN python3 -m pip install --no-cache-dir pyyaml \\",
    "    && bash infrastructure/containers/lucid_docker_build_codegen.sh",
    f"{MARK_END}",
)

CODEGEN_BLOCK = "\n".join(CODEGEN_BLOCK_LINES) + "\n"

_RE_WORKDIR_BUILD = re.compile(r"^\s*WORKDIR\s+/build(?:\s+#.*)?\s*$")


def _line_body(ln: str) -> str:
    return ln.rstrip("\r\n")


DEFAULT_SCAN_ROOTS = (
    "infrastructure/containers",
    "infrastructure/docker",
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def iter_dockerfiles(roots: tuple[str, ...]) -> list[Path]:
    root = repo_root_from_script()
    out: list[Path] = []
    for rel in roots:
        base = (root / rel).resolve()
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            name = p.name
            if name == "Dockerfile" or name.startswith("Dockerfile.") or name.startswith("dockerfile."):
                out.append(p)
    return out


def find_block_span(lines: list[str]) -> tuple[int, int] | None:
    i = None
    for idx, ln in enumerate(lines):
        if _line_body(ln) == MARK_BEGIN:
            i = idx
            break
    if i is None:
        return None
    for k in range(i + 1, len(lines)):
        if _line_body(lines[k]) == MARK_END:
            return i, k
    return None


def find_insert_line_index(lines: list[str]) -> int | None:
    for idx, ln in enumerate(lines):
        if _line_body(ln).strip() == MARK_INSERT:
            return idx
    return None


def find_first_workdir_build(lines: list[str]) -> int | None:
    for idx, ln in enumerate(lines):
        if _RE_WORKDIR_BUILD.match(_line_body(ln)):
            return idx
    return None


def strip_block(text: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    span = find_block_span(lines)
    if span is None:
        return text, False
    i, j = span
    new_lines = lines[:i] + lines[j + 1 :]
    return "".join(new_lines), True


def splice_block(
    text: str,
    *,
    after_workdir_build: bool,
) -> tuple[str, str]:
    """
    Returns (new_text, action) where action is:
    'replaced-block' | 'replaced-insert' | 'inserted-after-workdir' | 'unchanged-no-anchor'.
    """
    lines = text.splitlines(keepends=True)
    span = find_block_span(lines)
    if span is not None:
        i, j = span
        new_lines = lines[:i] + [CODEGEN_BLOCK] + lines[j + 1 :]
        return "".join(new_lines), "replaced-block"

    ins = find_insert_line_index(lines)
    if ins is not None:
        new_lines = lines[:ins] + [CODEGEN_BLOCK] + lines[ins + 1 :]
        return "".join(new_lines), "replaced-insert"

    if after_workdir_build:
        w = find_first_workdir_build(lines)
        if w is not None:
            new_lines = lines[: w + 1] + ["\n", CODEGEN_BLOCK] + lines[w + 1 :]
            return "".join(new_lines), "inserted-after-workdir"

    return text, "unchanged-no-anchor"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Inject LUCID_REPO_CODEGEN Docker RUN (lucid_docker_build_codegen.sh)."
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default is dry-run).",
    )
    ap.add_argument(
        "--strip",
        action="store_true",
        help="Remove LUCID_REPO_CODEGEN_BEGIN/END blocks only.",
    )
    ap.add_argument(
        "--after-workdir-build",
        action="store_true",
        help="Insert block after first WORKDIR /build when no marker exists (risky for partial COPY contexts).",
    )
    ap.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="PATH",
        help="Restrict to this Dockerfile path (repo-relative); repeat allowed.",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Log per-file skips (no marker / no block to strip).",
    )
    args = ap.parse_args()

    root = repo_root_from_script()
    if args.only:
        paths = []
        for o in args.only:
            p = (root / o).resolve()
            if not p.is_file():
                print(f"skip (not a file): {o}", file=sys.stderr)
                continue
            paths.append(p)
    else:
        paths = iter_dockerfiles(DEFAULT_SCAN_ROOTS)

    changed = 0
    scanned = 0
    for path in paths:
        scanned += 1
        rel = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"read error {rel}: {e}", file=sys.stderr)
            continue

        if args.strip:
            new_text, did = strip_block(text)
            action = "stripped" if did else "unchanged"
        else:
            new_text, action = splice_block(
                text,
                after_workdir_build=args.after_workdir_build,
            )

        if new_text != text:
            changed += 1
            print(f"{action}: {rel}")
            if args.apply:
                path.write_text(new_text, encoding="utf-8", newline="\n")
        elif args.verbose:
            if args.strip and action == "unchanged":
                print(f"unchanged (no block): {rel}")
            elif not args.strip and action == "unchanged-no-anchor":
                print(
                    f"skip (no {MARK_INSERT} / block; use --after-workdir-build?): {rel}",
                    file=sys.stderr,
                )

    print(f"Scanned {scanned} Dockerfile(s); {changed} modified.", file=sys.stderr)
    if not args.apply and changed:
        print("Dry-run: re-run with --apply to write.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

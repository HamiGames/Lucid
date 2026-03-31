"""
Inject Lucid metadata comments at the top of ``*.yml`` / ``*.yaml`` files:

    # File: /app/<tree>/...
    # x-lucid-file-path: /app/<tree>/...
    # x-lucid-file-directory: /app/<tree>/...
    # x-lucid-file-type: YAML

Path mapping uses ``map_repo_rel_to_app_paths`` then ``ROOTS`` via ``resolve_lucid_app_path``
in ``_normalise_lucid_headers.py``. Aliases include ``infrastructure/containers/`` →
``/app/configs/``, ``infrastructure/containers/services/`` → ``/app/service_configs/``,
``infrastructure/kubernetes/`` → ``/app/service_configs/kubernetes/``,
``infrastructure/service_mesh/`` → ``/app/service_mesh/``, repo ``service_mesh/`` →
``/app/old-service_mesh/``. Unmapped paths use the longest ``ROOTS`` match or
``/app/<repo-relative-path>``.

Run from repo root::

    .venv\\Scripts\\python.exe _normalise_lucid_yaml_headers.py

``--dry-run`` prints paths that would change. Regenerate ``x-files-listing.txt`` with::

    .venv\\Scripts\\python.exe _normalise_lucid_headers.py --x-files-listing
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _normalise_lucid_headers import (
    DEFAULT_BRANCH_LISTING,
    REPO,
    iter_repo_yaml_files,
    load_listing_path_overrides,
    resolve_lucid_app_path,
)

RE_LUCID_YAML_COMMENT_LINE = re.compile(
    r"^\s*#\s*(?:File:|x-lucid-file-path:|x-lucid-file-directory:|x-lucid-file-type:)\s*"
)


def strip_leading_lucid_yaml_comments(content: str) -> str:
    """Remove leading blank lines and consecutive ``# File:`` / ``# x-lucid-*`` lines."""
    lines = content.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        if RE_LUCID_YAML_COMMENT_LINE.match(line):
            i += 1
            continue
        break
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return "\n".join(lines[i:])


def build_yaml_header_block(app_path: str, app_directory: str) -> str:
    return (
        f"# File: {app_path}\n"
        f"# x-lucid-file-path: {app_path}\n"
        f"# x-lucid-file-directory: {app_directory}\n"
        "# x-lucid-file-type: YAML\n"
    )


def process_yaml_file(
    path: Path,
    repo: Path,
    dry_run: bool,
    overrides: dict[str, str] | None = None,
) -> bool:
    app_path, app_dir = resolve_lucid_app_path(path, repo, overrides=overrides)
    bom = ""
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        bom = "\ufeff"
        raw = raw[1:]
    s = raw.replace("\r\n", "\n")
    body = strip_leading_lucid_yaml_comments(s)
    header = build_yaml_header_block(app_path, app_dir)
    new_full = bom + header + ("\n" if body else "") + body
    if new_full.replace("\r\n", "\n") == bom + s.replace("\r\n", "\n"):
        return False
    if dry_run:
        print(f"would update: {path.relative_to(repo)}")
        return True
    path.write_text(new_full, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> None:
    import argparse

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Add Lucid # x-lucid-* headers to YAML files (same ROOTS as Python normaliser).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print paths that would change; do not write files.",
    )
    parser.add_argument(
        "--x-files-listing-source",
        type=Path,
        default=DEFAULT_BRANCH_LISTING,
        help=(
            "Source listing used to override x-lucid-file-path values when present "
            "(default: ./x-files-listing-branches.txt)."
        ),
    )
    ns = parser.parse_args(argv)

    repo = REPO.resolve()
    source_listing = ns.x_files_listing_source
    if not source_listing.is_absolute():
        source_listing = (repo / source_listing).resolve()
    overrides = load_listing_path_overrides(source_listing)
    n = 0
    for p in iter_repo_yaml_files(repo):
        if process_yaml_file(p, repo, ns.dry_run, overrides=overrides):
            n += 1
    mode = "Would update" if ns.dry_run else "Updated"
    print(f"{mode} {n} YAML file(s)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Path: scripts/gui_auth_realignment/fix_services_dir_lucid_paths.py
# Repo: Lucid/scripts/gui_auth_realignment/fix_services_dir_lucid_paths.py
#
# Normalizes Lucid headers and bundle paths under infrastructure/containers/services/**/*.yml|yaml
# per container-runtime-layout.yml: /app/service_configs/<relpath-from-services/>.
# Optionally rewrites broken infrastructure/containers/services/<file> refs when the file lives
# in a subdirectory and basename is unique in the tree.

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

SERVICES_PREFIX = "infrastructure/containers/services/"
RE_BUNDLE_REPO = re.compile(r"^(\s*bundle_repo_path:\s*)(.+?)\s*$", re.MULTILINE)
RE_BUNDLE_CONT = re.compile(r"^(\s*bundle_container_path:\s*)(.+?)\s*$", re.MULTILINE)
# Quoted service-bundle refs (alignment lists)
RE_SERVICES_REF_DQ = re.compile(
    r'^(?P<indent>\s*-\s*)"(?P<path>infrastructure/containers/services/[^"]+)"\s*$'
)
RE_SERVICES_REF_SQ = re.compile(
    r"^(?P<indent>\s*-\s*)'(?P<path>infrastructure/containers/services/[^']+)'\s*$"
)


def _container_paths(rel_from_services: str) -> Tuple[str, str]:
    rel_from_services = rel_from_services.replace("\\", "/")
    p = Path(rel_from_services)
    parent = p.parent.as_posix()
    if parent == ".":
        return f"/app/service_configs/{p.name}", "/app/service_configs"
    return (
        f"/app/service_configs/{rel_from_services}",
        f"/app/service_configs/{parent}",
    )


def _build_basename_index(services_root: Path) -> Dict[str, List[str]]:
    m: Dict[str, List[str]] = defaultdict(list)
    for p in sorted(services_root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".yml", ".yaml"):
            continue
        rel = p.relative_to(services_root).as_posix()
        m[p.name].append(rel)
    return dict(m)


def _replace_header_block(content: str, rel_from_services: str) -> str:
    container_file, container_dir = _container_paths(rel_from_services)
    new_block = (
        f"# File: {container_file}\n"
        f"# x-lucid-file-path: {container_file}\n"
        f"# x-lucid-file-directory: {container_dir}\n"
        f"# x-lucid-file-type: YAML\n"
    )
    # Strip leading BOM
    if content.startswith("\ufeff"):
        content = content[1:]

    # Match consecutive header lines from start (optional # File, then x-lucid-*)
    m = re.match(
        r"(?:^# File:.*\n)?"
        r"(?:^# x-lucid-file-path:.*\n)"
        r"(?:^# x-lucid-file-directory:.*\n)"
        r"(?:^# x-lucid-file-type:.*\n)",
        content,
        re.MULTILINE,
    )
    if m:
        return new_block + content[m.end() :]

    # Only partial header
    m2 = re.match(
        r"^# x-lucid-file-path:.*\n(?:^# x-lucid-file-directory:.*\n)(?:^# x-lucid-file-type:.*\n)",
        content,
        re.MULTILINE,
    )
    if m2:
        # Prepend # File if missing
        return new_block + content[m2.end() :]

    return new_block + content


def _fix_bundle_paths(content: str, rel_from_services: str) -> str:
    repo_bundle = f"{SERVICES_PREFIX}{rel_from_services}"
    container_file, _ = _container_paths(rel_from_services)

    def sub_repo(m: re.Match[str]) -> str:
        return f"{m.group(1)}{repo_bundle}"

    def sub_cont(m: re.Match[str]) -> str:
        return f"{m.group(1)}{container_file}"

    content = RE_BUNDLE_REPO.sub(sub_repo, content)
    content = RE_BUNDLE_CONT.sub(sub_cont, content)
    return content


def _fix_services_refs_line(
    line: str,
    repo: Path,
    basename_index: Dict[str, List[str]],
) -> str:
    mm = RE_SERVICES_REF_DQ.match(line)
    if mm:
        pth = mm.group("path")
        full = repo / pth.replace("/", os.sep)
        if full.is_file():
            return line
        base = Path(pth).name
        cand = basename_index.get(base, [])
        if len(cand) != 1:
            return line
        new_p = f"{SERVICES_PREFIX}{cand[0]}"
        return f'{mm.group("indent")}"{new_p}"'
    mm = RE_SERVICES_REF_SQ.match(line)
    if mm:
        pth = mm.group("path")
        full = repo / pth.replace("/", os.sep)
        if full.is_file():
            return line
        base = Path(pth).name
        cand = basename_index.get(base, [])
        if len(cand) != 1:
            return line
        new_p = f"{SERVICES_PREFIX}{cand[0]}"
        return f"{mm.group('indent')}'{new_p}'"
    return line


def process_content(
    raw: str,
    rel_from_services: str,
    repo: Path,
    basename_index: Dict[str, List[str]],
    fix_refs: bool,
) -> Tuple[str, int]:
    n = 0
    prev = raw
    raw = _replace_header_block(raw, rel_from_services)
    if raw != prev:
        n += 1
    prev = raw
    raw = _fix_bundle_paths(raw, rel_from_services)
    if raw != prev:
        n += 1

    if fix_refs:
        lines = raw.splitlines(keepends=True)
        out: List[str] = []
        for line in lines:
            if line.endswith("\r\n"):
                core, eol = line[:-2], "\r\n"
            elif line.endswith("\n"):
                core, eol = line[:-1], "\n"
            else:
                core, eol = line, ""
            nl = _fix_services_refs_line(core, repo, basename_index)
            if nl != core:
                n += 1
            out.append(nl + eol)
        raw = "".join(out)

    return raw, n


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Fix x-lucid-file-path headers and bundle paths under "
            "infrastructure/containers/services (mirror /app/service_configs/<relpath>)."
        ),
        epilog=(
            "If you see '0 files would change', every scanned file already matches the layout "
            "(not skipped — there is nothing left to fix). Use -v to print 'ok:' per file. "
            "Dry-run never writes; pass --apply only when updates are listed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print one line per file: 'ok:' (already aligned) or 'update:' (needs fix).",
    )
    ap.add_argument(
        "--no-fix-refs",
        action="store_true",
        help="Do not rewrite broken infrastructure/containers/services/* list entries",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: print summary only)",
    )
    args = ap.parse_args()

    repo = (args.repo_root or Path(__file__).resolve().parent.parent.parent).resolve()
    services = repo / "infrastructure" / "containers" / "services"
    if not services.is_dir():
        print(f"error: missing {services}", file=sys.stderr)
        return 2

    basename_index = _build_basename_index(services)
    changed_files = 0
    total_edits = 0

    paths = sorted(
        p
        for p in services.rglob("*")
        if p.is_file() and p.suffix.lower() in (".yml", ".yaml")
    )
    for path in paths:
        rel_svc = path.relative_to(services).as_posix()
        old_text = path.read_text(encoding="utf-8", errors="replace")
        new_text, edits = process_content(
            old_text,
            rel_svc,
            repo,
            basename_index,
            fix_refs=not args.no_fix_refs,
        )
        rel = path.relative_to(repo).as_posix()
        if new_text != old_text:
            changed_files += 1
            total_edits += edits
            print(f"update: {rel} ({edits} change(s))")
            if args.apply:
                path.write_text(new_text, encoding="utf-8", newline="\n")
        elif args.verbose:
            print(f"ok: {rel}")

    verb = "applied" if args.apply else "dry-run (no writes; use --apply to save)"
    if changed_files == 0:
        print(
            f"--- done: 0 of {len(paths)} file(s) need changes ({verb}). "
            f"Already aligned with /app/service_configs/<relpath-from-services/>; not skipped. "
            f"Use -v to list each file as ok:. ---"
        )
    else:
        print(
            f"--- done: {changed_files} file(s) out of {len(paths)} scanned, "
            f"~{total_edits} operations ({verb}) ---"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

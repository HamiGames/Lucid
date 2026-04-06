#!/usr/bin/env python3
# Path: scripts/repair_dockerfile_from_risk_report.py
# File (repo): Lucid/scripts/repair_dockerfile_from_risk_report.py
#
# Applies fixes for error/warn findings listed in configs/alignment-mats/dockerfile-risk-report.json
# (produced by dockerfile_build_risk_scan.py). Only real Dockerfiles are modified (names matching
# Dockerfile* but not *.bak*, *.tmp, etc. — same rules as the scanner).
#
# Fixable codes:
#   COPY_MISSING, COPY_CONTEXT_ESCAPE, ADD_MISSING, ADD_CONTEXT_ESCAPE — rewrite sources
#     relative to context_dir using repo layout (strip repo-prefixed paths, relpath, basename).
#   COPY_GLOB, ADD_GLOB — replace with the single matching file in context when unambiguous.
#   ARG_NO_DEFAULT — append = or =<sensible default> for standalone ARG lines.
#   FROM_ARG — insert ARG <name>=<default> immediately before FROM when substitution is used.
#
# Skipped (not safely auto-fixable): RUN_MOUNT, RUN_NETWORK, COPY_FROM_*, ADD_URL, WORKDIR_*, etc.
#
# When COPY would require ../ (invalid in Docker), use --copy-context-parent so paths are
# rewritten relative to the Dockerfile directory's parent (e.g. 02_network_security for
# 02_network_security/tor/Dockerfile.*); you must set docker build context to that parent.

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dockerfile_build_risk_scan import (  # noqa: E402
    dockerfile_basename_is_scan_target,
    parse_copy_add_sources_dest,
    tokenize_instruction_args,
)

# Finding codes we attempt to repair (error + warn only).
FIX_CODES: Set[str] = {
    "COPY_MISSING",
    "COPY_CONTEXT_ESCAPE",
    "ADD_MISSING",
    "ADD_CONTEXT_ESCAPE",
    "COPY_GLOB",
    "ADD_GLOB",
    "ARG_NO_DEFAULT",
    "FROM_ARG",
}

# dockerfile_build_risk_scan.BUILDKIT_DEFAULT_ARGS — duplicate to avoid private import
BUILDKIT_DEFAULT_ARGS = frozenset(
    {
        "buildplatform",
        "targetplatform",
        "buildos",
        "targetos",
        "buildarch",
        "targetarch",
        "buildvariant",
        "targetvariant",
    }
)

# Defaults for FROM ${VAR} when inserting ARG before FROM
FROM_ARG_DEFAULTS: Dict[str, str] = {
    "nginx_tag": "stable-alpine",
    "node_version": "20-alpine",
    "python_version": "3.12-slim",
    "alpine_version": "3.19",
    "debian_version": "bookworm-slim",
    "ubuntu_version": "22.04",
    "go_version": "1.22-alpine",
    "rust_version": "1-bookworm",
    "java_version": "17-jdk-slim",
    "php_version": "8.2-cli",
    "ruby_version": "3.2-slim",
    "registry": "docker.io",
    "base_image": "debian:12-slim",
}


def _default_for_arg_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith("_port"):
        return "8080"
    if "python" in lower:
        return "3.12-slim"
    if "node" in lower:
        return "20-alpine"
    if "nginx" in lower:
        return "stable-alpine"
    if "go" in lower and "version" in lower:
        return "1.22-alpine"
    if lower in FROM_ARG_DEFAULTS:
        return FROM_ARG_DEFAULTS[lower]
    return "latest"


def effective_copy_base(
    repo_root: Path, context_dir: str, copy_context_parent: bool
) -> Path:
    """Directory used to resolve COPY/ADD sources (normally = build context)."""
    ctx = (repo_root / context_dir.replace("\\", "/")).resolve()
    if not copy_context_parent:
        return ctx
    rr = repo_root.resolve()
    try:
        ctx.relative_to(rr)
    except ValueError:
        return ctx
    parent = ctx.parent
    if parent == rr or ctx == rr:
        return ctx
    try:
        parent.relative_to(rr)
    except ValueError:
        return ctx
    return parent.resolve()


def rewrite_copy_add_source(
    src: str,
    context_dir: str,
    repo_root: Path,
    base_ctx: Path,
) -> Optional[str]:
    """
    Return a new source path relative to build context, or None if no safe rewrite.
    """
    norm = src.replace("\\", "/")
    if not norm or norm.startswith("http://") or norm.startswith("https://"):
        return None
    if "$" in norm or "${" in norm:
        return None

    ctx = base_ctx.resolve()

    def exists_rel(rel: str) -> bool:
        p = ctx / rel.replace("\\", "/")
        return p.exists()

    if exists_rel(norm):
        return None

    # Repo-absolute path string (e.g. 02_network_security/tor/torrc)
    cand = (repo_root / norm).resolve()
    try:
        if cand.exists():
            rel = Path(os.path.relpath(str(cand), str(ctx))).as_posix()
            if rel.startswith("../"):
                # Docker COPY/ADD sources must stay inside the build context; ".." is invalid.
                return None
            probe = (ctx / rel).resolve()
            if probe.exists():
                return rel
    except (ValueError, OSError):
        pass

    ctx_posix = context_dir.replace("\\", "/").rstrip("/")
    if ctx_posix and norm.startswith(ctx_posix + "/"):
        tail = norm[len(ctx_posix) + 1 :]
        if tail and exists_rel(tail):
            return tail

    # Wrong "absolute" container path: duplicate from file in context by basename
    if norm.startswith("/") and not norm.startswith("//"):
        base = norm.rstrip("/").split("/")[-1]
        if base and exists_rel(base):
            return base
        if base:
            hits = list(ctx.glob(f"**/{base}"))
            files = [h for h in hits if h.is_file()]
            if len(files) == 1:
                return files[0].relative_to(ctx).as_posix()

    return None


def expand_glob_source(pattern: str, repo_root: Path, base_ctx: Path) -> Optional[str]:
    if "*" not in pattern and "?" not in pattern and "[" not in pattern:
        return None
    ctx = base_ctx.resolve()
    matches = sorted(ctx.glob(pattern))
    files = [m for m in matches if m.is_file()]
    if len(files) != 1:
        return None
    return files[0].relative_to(ctx).as_posix()


def rebuild_copy_add_line(
    line: str,
    context_dir: str,
    repo_root: Path,
    base_ctx: Path,
    codes: Set[str],
) -> Optional[str]:
    """If line is COPY/ADD (no --from), rewrite source tokens. Returns new line or None."""
    stripped = line.lstrip()
    upper = stripped.upper()
    if upper.startswith("COPY "):
        instr = "COPY"
    elif upper.startswith("ADD "):
        instr = "ADD"
    else:
        return None

    rest = stripped[len(instr) :].lstrip()
    tokens = tokenize_instruction_args(rest)
    _, _, has_from = parse_copy_add_sources_dest(instr.upper(), tokens)
    if has_from:
        return None

    filtered_flags: List[str] = []
    filtered_rest: List[str] = []
    for t in tokens:
        if t.startswith("--"):
            filtered_flags.append(t)
        else:
            filtered_rest.append(t)
    if len(filtered_rest) < 2:
        return None

    dest = filtered_rest[-1]
    sources = filtered_rest[:-1]
    new_sources: List[str] = []
    changed = False

    for src in sources:
        new_s: Optional[str] = None
        if "GLOB" in "".join(codes) or any(
            c in ("COPY_GLOB", "ADD_GLOB") for c in codes
        ):
            new_s = expand_glob_source(src, repo_root, base_ctx)
        if new_s is None and any(
            c
            in (
                "COPY_MISSING",
                "COPY_CONTEXT_ESCAPE",
                "ADD_MISSING",
                "ADD_CONTEXT_ESCAPE",
            )
            for c in codes
        ):
            new_s = rewrite_copy_add_source(src, context_dir, repo_root, base_ctx)
        if new_s is None:
            new_s = rewrite_copy_add_source(src, context_dir, repo_root, base_ctx)
        if new_s is not None and new_s != src:
            new_sources.append(new_s)
            changed = True
        else:
            new_sources.append(src)

    if not changed:
        return None

    indent = line[: len(line) - len(stripped)]
    parts = [instr] + filtered_flags + new_sources + [dest]
    return indent + " ".join(parts) + "\n"


def fix_arg_no_default_line(line: str) -> Optional[str]:
    raw = line.rstrip("\n")
    m = re.match(r"^(\s*ARG\s+)([A-Za-z_][A-Za-z0-9_]*)\s*(\s#.*)?$", raw)
    if not m:
        return None
    name = m.group(2)
    if name.lower() in BUILDKIT_DEFAULT_ARGS:
        return None
    suffix = m.group(3) or ""
    if "=" in raw.split("#", 1)[0]:
        return None
    default = _default_for_arg_name(name)
    if name.isupper() and name in ("BUILD_DATE", "VCS_REF", "SOURCE_DATE_EPOCH"):
        default = ""
    return f"{m.group(1)}{name}={default}{suffix}\n"


def extract_from_substitution_vars(from_line: str) -> List[str]:
    out: List[str] = []
    for m in re.finditer(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", from_line):
        out.append(m.group(1))
    for m in re.finditer(r"\$([A-Za-z_][A-Za-z0-9_]*)\b", from_line):
        v = m.group(1)
        if v not in out:
            out.append(v)
    return out


def has_arg_declared_above(lines: List[str], idx: int, var: str) -> bool:
    """True if ARG var (with or without default) appears on any line above idx."""
    pat = re.compile(rf"^\s*ARG\s+{re.escape(var)}\b")
    for j in range(idx):
        if pat.match(lines[j]):
            return True
    return False


def build_from_arg_insertions(
    lines: List[str], line_numbers: Set[int]
) -> List[Tuple[int, str]]:
    """Returns list of (insert_before_index_0based, line_text) sorted descending by index."""
    inserts: List[Tuple[int, str]] = []
    for i, line in enumerate(lines):
        if (i + 1) not in line_numbers:
            continue
        stripped = line.lstrip()
        if not stripped.upper().startswith("FROM "):
            continue
        vars_ = extract_from_substitution_vars(stripped)
        seen_v: Set[str] = set()
        for var in vars_:
            if var in seen_v:
                continue
            seen_v.add(var)
            if has_arg_declared_above(lines, i, var):
                continue
            default = _default_for_arg_name(var)
            inserts.append((i, f"ARG {var}={default}\n"))
    return inserts


def collect_lines_to_fix(
    report_entry: dict,
) -> Dict[int, Set[str]]:
    """Map 1-based line number -> set of finding codes for that Dockerfile."""
    by_line: Dict[int, Set[str]] = defaultdict(set)
    for f in report_entry.get("findings", []):
        if f.get("severity") == "info":
            continue
        code = f.get("code", "")
        if code not in FIX_CODES:
            continue
        line = f.get("line")
        if isinstance(line, int) and line > 0:
            by_line[line].add(code)
    return by_line


def apply_repairs_to_file(
    dockerfile: Path,
    context_dir: str,
    repo_root: Path,
    line_codes: Dict[int, Set[str]],
    dry_run: bool,
    copy_context_parent: bool,
) -> Tuple[int, List[str]]:
    """
    Returns (change_count, log lines).
    """
    log: List[str] = []
    if not line_codes:
        return 0, log

    text = dockerfile.read_text(encoding="utf-8", errors="replace")
    orig_lines = text.splitlines(keepends=True)
    if not orig_lines:
        return 0, log

    plain = [ln.rstrip("\n") for ln in orig_lines]
    from_lines = {ln for ln, codes in line_codes.items() if "FROM_ARG" in codes}
    inserts = build_from_arg_insertions(plain, from_lines)
    inserts.sort(key=lambda x: x[0], reverse=True)

    working = list(orig_lines)
    insert_count = 0
    for insert_at, new_line in inserts:
        working.insert(insert_at, new_line)
        insert_count += 1
        log.append(f"  + insert before L{insert_at + 1}: {new_line.strip()}")

    sorted_ins = sorted(inserts, key=lambda x: x[0])
    offset_for: Dict[int, int] = {}
    for orig_ln in line_codes:
        offset_for[orig_ln] = sum(1 for ins_at, _ in sorted_ins if ins_at < orig_ln)

    base_ctx = effective_copy_base(repo_root, context_dir, copy_context_parent)

    change_count = insert_count
    for orig_ln in sorted(line_codes.keys(), reverse=True):
        codes = line_codes[orig_ln]
        new_idx = orig_ln - 1 + offset_for.get(orig_ln, 0)
        if new_idx < 0 or new_idx >= len(working):
            log.append(f"  ! skip L{orig_ln}: index out of range after inserts")
            continue
        line = working[new_idx]
        stripped = line.lstrip()
        upper = stripped.upper()

        if "ARG_NO_DEFAULT" in codes:
            fixed = fix_arg_no_default_line(line)
            if fixed and fixed != line:
                working[new_idx] = fixed
                change_count += 1
                log.append(f"  ~ L{orig_ln} ARG: {line.strip()} -> {fixed.strip()}")
                line = working[new_idx]
                stripped = line.lstrip()
                upper = stripped.upper()

        if any(
            c in codes
            for c in (
                "COPY_MISSING",
                "COPY_CONTEXT_ESCAPE",
                "ADD_MISSING",
                "ADD_CONTEXT_ESCAPE",
                "COPY_GLOB",
                "ADD_GLOB",
            )
        ):
            if upper.startswith("COPY ") or upper.startswith("ADD "):
                new_line = rebuild_copy_add_line(
                    line, context_dir, repo_root, base_ctx, codes
                )
                if new_line and new_line != line:
                    working[new_idx] = new_line
                    change_count += 1
                    log.append(f"  ~ L{orig_ln} COPY/ADD:")
                    log.append(f"      was: {line.rstrip()[:160]}")
                    log.append(f"      now: {new_line.rstrip()[:160]}")

    if change_count and dry_run:
        log.append("  (dry-run: no write)")
    elif change_count and not dry_run:
        dockerfile.write_text("".join(working), encoding="utf-8", newline="\n")

    return change_count, log


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Repair Dockerfiles using dockerfile-risk-report.json findings."
    )
    ap.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Path to dockerfile-risk-report.json",
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default is dry-run)",
    )
    ap.add_argument(
        "--path-prefix",
        action="append",
        default=[],
        help="Only process reports whose path starts with this prefix (repeatable)",
    )
    ap.add_argument(
        "--copy-context-parent",
        action="store_true",
        help=(
            "Resolve COPY/ADD paths against the parent of the Dockerfile directory "
            "(avoids illegal ../ sources; requires matching docker build context)."
        ),
    )
    args = ap.parse_args()

    repo_root = (args.root or _SCRIPTS.parent).resolve()
    report_path = (
        args.report
        or repo_root / "configs" / "alignment-mats" / "dockerfile-risk-report.json"
    ).resolve()

    if not report_path.is_file():
        print(f"error: report not found: {report_path}", file=sys.stderr)
        return 2

    data = json.loads(report_path.read_text(encoding="utf-8"))
    summary_root = data.get("summary", {}).get("root")
    if summary_root:
        sr = Path(str(summary_root))
        if sr.is_dir():
            repo_root = sr.resolve()

    dry_run = not args.apply
    prefixes = tuple(p.replace("\\", "/").rstrip("/") for p in (args.path_prefix or []))

    total_changes = 0
    files_touched = 0

    for rep in data.get("reports", []):
        rel = str(rep.get("path", "")).replace("\\", "/")
        if not rel or not dockerfile_basename_is_scan_target(Path(rel).name):
            continue
        if prefixes and not any(
            rel == p or rel.startswith(p + "/") for p in prefixes
        ):
            continue

        line_codes = collect_lines_to_fix(rep)
        if not line_codes:
            continue

        df_path = (repo_root / rel.replace("/", os.sep)).resolve()
        if not df_path.is_file():
            print(f"skip missing file: {rel}", file=sys.stderr)
            continue

        ctx = str(rep.get("context_dir", str(df_path.parent.relative_to(repo_root))))
        ctx = ctx.replace("\\", "/")

        ch, log = apply_repairs_to_file(
            df_path,
            ctx,
            repo_root,
            line_codes,
            dry_run,
            args.copy_context_parent,
        )
        if ch:
            files_touched += 1
            total_changes += ch
            mode = "DRY-RUN" if dry_run else "APPLY"
            print(f"\n[{mode}] {rel}")
            for row in log:
                print(row)

    print(
        f"\n--- done: {files_touched} files, {total_changes} edits"
        f"{' (dry-run)' if dry_run else ''} ---"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

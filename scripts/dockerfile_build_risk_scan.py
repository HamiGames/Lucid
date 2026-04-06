#!/usr/bin/env python3
# Path: scripts/dockerfile_build_risk_scan.py
# File (repo): Lucid/scripts/dockerfile_build_risk_scan.py
#
# Static "smoke" scan: flags Dockerfile regions likely to break `docker build`
# when context is the Dockerfile's directory (same as: docker build -f <file> <dir-of-file>).
# Does not pull images or run builds.

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass
class Finding:
    line: int
    severity: str  # "error" | "warn" | "info"
    code: str
    message: str
    instruction: str = ""


@dataclass
class FileReport:
    path: str
    context_dir: str
    findings: List[Finding] = field(default_factory=list)


EXCLUDE_DIR_PARTS = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
    }
)

# Docker BuildKit predefines these; omitting a default is normal.
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

# RUN lines that usually need network or external repos at build time
RUN_NETWORK_PATTERNS = (
    r"\bapt-get\b",
    r"\bapt\b",
    r"\bapk\b",
    r"\byum\b",
    r"\bdnf\b",
    r"\bmicrodnf\b",
    r"\bzypper\b",
    r"\bpacman\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bpip3?\b",
    r"\bpnpm\b",
    r"\byarn\b",
    r"\bnpm\b",
    r"\bgo\s+get\b",
    r"\bgo\s+install\b",
    r"\bcargo\b",
    r"\bgit\s+clone\b",
    r"\bgit\s+fetch\b",
)

HEREDOC_PATTERN = re.compile(r"<<[-]?\s*([A-Za-z0-9_]+)\s*$")


def dockerfile_basename_is_scan_target(filename: str) -> bool:
    """
    True for real Dockerfiles: Dockerfile, Dockerfile.foo.
    False for editor/backup names that still match Dockerfile* (e.g. Dockerfile.tunnels.bak.2026…Z).
    """
    n = filename.lower()
    if n.endswith("~"):
        return False
    if ".bak." in n or n.endswith(".bak"):
        return False
    if n.endswith((".swp", ".tmp", ".orig", ".rej")):
        return False
    return n == "dockerfile" or n.startswith("dockerfile.")


def iter_dockerfiles(root: Path, include_legacy: bool) -> Iterable[Path]:
    for p in sorted(root.rglob("Dockerfile*")):
        if not p.is_file():
            continue
        if not dockerfile_basename_is_scan_target(p.name):
            continue
        parts_lower = {x.lower() for x in p.parts}
        if parts_lower & EXCLUDE_DIR_PARTS:
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if not include_legacy and (
            rel.startswith("legacy_files/") or rel.startswith("legacy_files\\")
        ):
            continue
        yield p


def physical_lines(text: str) -> List[Tuple[int, str]]:
    """Merge backslash-continued lines; return (physical_line_no, content) per logical line."""
    raw_lines = text.splitlines()
    out: List[Tuple[int, str]] = []
    buf: List[str] = []
    start_phys = 1
    for i, line in enumerate(raw_lines, start=1):
        if buf:
            buf.append(line.lstrip())
        else:
            start_phys = i
            buf = [line]
        stripped = line.rstrip()
        if stripped.endswith("\\") and not stripped.endswith("\\\\"):
            buf[-1] = buf[-1].rstrip()[:-1].rstrip()
            continue
        logical = "".join(buf)
        buf = []
        out.append((start_phys, logical))
    if buf:
        out.append((start_phys, "".join(buf)))
    return out


def strip_docker_comment(line: str) -> str:
    """Remove end-of-line # comment (rough heuristic; ignores quotes)."""
    if "#" not in line:
        return line
    out: List[str] = []
    i = 0
    in_s = False
    in_d = False
    while i < len(line):
        c = line[i]
        if c == "'" and not in_d:
            in_s = not in_s
            out.append(c)
        elif c == '"' and not in_s:
            in_d = not in_d
            out.append(c)
        elif c == "#" and not in_s and not in_d:
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).rstrip()


def tokenize_instruction_args(rest: str) -> List[str]:
    """Split Dockerfile instruction arguments on whitespace; respect single/double quotes."""
    rest = rest.strip()
    if not rest:
        return []
    tokens: List[str] = []
    i = 0
    n = len(rest)
    while i < n:
        while i < n and rest[i].isspace():
            i += 1
        if i >= n:
            break
        if rest[i] in "'\"":
            q = rest[i]
            i += 1
            start = i
            while i < n and rest[i] != q:
                if rest[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                i += 1
            tokens.append(rest[start:i])
            if i < n and rest[i] == q:
                i += 1
        else:
            start = i
            while i < n and not rest[i].isspace():
                i += 1
            tokens.append(rest[start:i])
    return tokens


def parse_copy_add_sources_dest(
    instr_upper: str, tokens: Sequence[str]
) -> Tuple[List[str], Optional[str], bool]:
    """
    Returns (sources, dest, has_from).
    For ADD/COPY after flags removed from tokens.
    """
    has_from = any(t.startswith("--from=") for t in tokens)
    filtered: List[str] = []
    for t in tokens:
        if t.startswith("--"):
            continue
        filtered.append(t)
    if len(filtered) < 2:
        return [], None, has_from
    dest = filtered[-1]
    sources = filtered[:-1]
    return sources, dest, has_from


def path_escapes_context(context: Path, rel_src: str) -> bool:
    try:
        resolved = (context / rel_src).resolve()
        resolved.relative_to(context.resolve())
        return False
    except ValueError:
        return True
    except (OSError, RuntimeError):
        return True


def scan_file(dockerfile: Path, repo_root: Path) -> FileReport:
    context = dockerfile.parent
    rel_path = dockerfile.relative_to(repo_root)
    report = FileReport(
        path=str(rel_path).replace("\\", "/"),
        context_dir=str(context.relative_to(repo_root)).replace("\\", "/"),
    )

    try:
        text = dockerfile.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        report.findings.append(
            Finding(1, "error", "READ_FAIL", f"cannot read file: {e}", "")
        )
        return report

    stages: List[str] = []
    stage_index = 0

    def add(line_no: int, sev: str, code: str, msg: str, instr: str = "") -> None:
        report.findings.append(Finding(line_no, sev, code, msg, instr))

    logical = physical_lines(text)
    in_heredoc: Optional[str] = None

    for phys_line, raw in logical:
        line = strip_docker_comment(raw).strip()
        if not line:
            continue

        if in_heredoc:
            if line == in_heredoc:
                in_heredoc = None
            continue

        upper_line = line.upper()
        if not (
            upper_line.startswith("FROM ")
            or upper_line.startswith("COPY ")
            or upper_line.startswith("ADD ")
            or upper_line.startswith("RUN ")
            or upper_line.startswith("WORKDIR ")
            or upper_line.startswith("ARG ")
            or upper_line.startswith("ENV ")
        ):
            m_heredoc = HEREDOC_PATTERN.search(line)
            if m_heredoc and upper_line.startswith("RUN "):
                in_heredoc = m_heredoc.group(1)
                add(
                    phys_line,
                    "info",
                    "HEREDOC_RUN",
                    "RUN uses heredoc; requires BuildKit / Docker syntax=docker/dockerfile:1",
                    line[:120],
                )
            continue

        if upper_line.startswith("FROM "):
            rest = line[5:].lstrip()
            if not rest:
                add(phys_line, "error", "FROM_EMPTY", "FROM has no image reference", line)
                continue
            toks = tokenize_instruction_args(rest)
            if not toks:
                add(phys_line, "error", "FROM_EMPTY", "FROM has no image reference", line)
                continue
            # FROM [--platform=...] image [AS name]
            img_tok = None
            for i, t in enumerate(toks):
                if t.startswith("--"):
                    continue
                img_tok = i
                break
            if img_tok is None:
                add(phys_line, "error", "FROM_EMPTY", "FROM has no image reference", line)
                continue
            image_ref = toks[img_tok]
            if "$" in image_ref or "${" in image_ref:
                add(
                    phys_line,
                    "warn",
                    "FROM_ARG",
                    "FROM uses substitution; build fails if ARG unset at build time",
                    line[:160],
                )
            for i in range(img_tok + 1, len(toks) - 1):
                if toks[i].upper() == "AS" and i + 1 < len(toks):
                    stages.append(toks[i + 1].lower())
                    break
            stage_index += 1
            continue

        if upper_line.startswith("WORKDIR "):
            rest = line[8:].strip()
            if "$" in rest:
                add(
                    phys_line,
                    "info",
                    "WORKDIR_VAR",
                    "WORKDIR uses variables; ensure parent dirs exist in prior layers",
                    line[:120],
                )
            continue

        if upper_line.startswith("ARG "):
            rest = line[4:].strip()
            if rest and "=" not in rest and not rest.startswith("--"):
                first = rest.split()[0]
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", first):
                    if first.lower() not in BUILDKIT_DEFAULT_ARGS:
                        add(
                            phys_line,
                            "warn",
                            "ARG_NO_DEFAULT",
                            f"ARG {first} has no default; FROM ${{{first}}} or COPY may fail if not passed",
                            line[:120],
                        )
            continue

        if upper_line.startswith("ENV "):
            body = line[4:].strip()
            if body and "=" not in body:
                add(
                    phys_line,
                    "warn",
                    "ENV_SHAPE",
                    "ENV without key=value form can confuse legacy parsers",
                    line[:120],
                )
            continue

        if upper_line.startswith("RUN "):
            body = line[4:]
            if "--mount=" in body:
                add(
                    phys_line,
                    "warn",
                    "RUN_MOUNT",
                    "RUN --mount= may require BuildKit and valid cache/bind sources",
                    line[:160],
                )
            for pat in RUN_NETWORK_PATTERNS:
                if re.search(pat, body, re.IGNORECASE):
                    add(
                        phys_line,
                        "info",
                        "RUN_NETWORK",
                        "RUN likely needs network/registry access at build time",
                        line[:160],
                    )
                    break
            continue

        if upper_line.startswith("COPY ") or upper_line.startswith("ADD "):
            instr = "COPY" if upper_line.startswith("COPY ") else "ADD"
            raw_tokens = tokenize_instruction_args(line[len(instr) :])
            sources, dest, has_from = parse_copy_add_sources_dest(instr.upper(), raw_tokens)
            if has_from:
                from_tok = next((t for t in raw_tokens if t.startswith("--from=")), "")
                ref = from_tok.split("=", 1)[-1].strip().strip('"').strip("'")
                if ref.isdigit():
                    idx = int(ref)
                    if idx < 0 or idx >= stage_index:
                        add(
                            phys_line,
                            "error",
                            "COPY_FROM_INDEX",
                            f"{instr} --from={ref} references stage index out of range (0..{stage_index - 1})",
                            line[:160],
                        )
                elif any(ch in ref for ch in (":", "/", "@")):
                    # Typical image refs: alpine:3, ghcr.io/foo/bar:tag, image@sha256:...
                    add(
                        phys_line,
                        "info",
                        "COPY_FROM_IMAGE",
                        f"{instr} --from uses an image ref; build fails if registry/auth/pull fails",
                        line[:160],
                    )
                elif ref.lower() not in stages:
                    add(
                        phys_line,
                        "warn",
                        "COPY_FROM_UNKNOWN",
                        f"{instr} --from={ref!r} is not a prior AS name in this file (may be valid image short name)",
                        line[:160],
                    )
                continue

            if not sources:
                add(phys_line, "warn", f"{instr}_EMPTY", f"{instr} missing sources", line[:120])
                continue

            for src in sources:
                if src.startswith("http://") or src.startswith("https://"):
                    add(
                        phys_line,
                        "info",
                        "ADD_URL",
                        "ADD from URL needs network at build time",
                        line[:160],
                    )
                    continue
                if any(ch in src for ch in "*?["):
                    add(
                        phys_line,
                        "warn",
                        f"{instr}_GLOB",
                        f"{instr} source {src!r} uses glob; cannot verify paths statically",
                        line[:160],
                    )
                    continue
                if "$" in src or "${" in src:
                    add(
                        phys_line,
                        "warn",
                        f"{instr}_VAR_SRC",
                        f"{instr} source uses variable expansion; cannot verify path exists in context",
                        line[:160],
                    )
                    continue
                if src.startswith("/") and instr == "ADD":
                    pass
                norm = src.replace("\\", "/")
                if norm.startswith("../") or "/../" in norm:
                    add(
                        phys_line,
                        "error",
                        f"{instr}_CONTEXT_ESCAPE",
                        f"{instr} source {src!r} uses `..` and is invalid or escapes build context",
                        line[:160],
                    )
                    continue
                full = context / src
                if path_escapes_context(context, src):
                    add(
                        phys_line,
                        "error",
                        f"{instr}_CONTEXT_ESCAPE",
                        f"{instr} source {src!r} resolves outside build context directory",
                        line[:160],
                    )
                    continue
                if not full.exists():
                    add(
                        phys_line,
                        "error",
                        f"{instr}_MISSING",
                        f"{instr} source not found relative to context {report.context_dir!r}: {src}",
                        line[:160],
                    )
                elif full.is_file():
                    pass
                elif full.is_dir():
                    pass
                else:
                    add(
                        phys_line,
                        "warn",
                        f"{instr}_PATH",
                        f"{instr} source exists but is not a regular file or directory: {src}",
                        line[:160],
                    )

            if dest and ("$" in dest or "${" in dest):
                add(
                    phys_line,
                    "warn",
                    f"{instr}_VAR_DEST",
                    f"{instr} destination uses variables; ensure parent path exists",
                    line[:160],
                )
            continue

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan Dockerfiles for static build risks (context paths, stages, heredocs, network RUN). "
            "Assumes build context is the directory containing each Dockerfile."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--include-legacy",
        action="store_true",
        help="Include legacy_files/** Dockerfiles",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write full report as JSON to this path",
    )
    parser.add_argument(
        "--fail-on",
        choices=("error", "warn", "info"),
        default="error",
        help="Exit non-zero if any finding is at or above this severity (default: error)",
    )
    args = parser.parse_args()
    fail_on = args.fail_on

    root = (args.root or Path(__file__).resolve().parent.parent).resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    order = {"info": 0, "warn": 1, "error": 2}
    threshold = order.get(fail_on, 2)

    reports: List[FileReport] = []
    for df in iter_dockerfiles(root, include_legacy=args.include_legacy):
        reports.append(scan_file(df, root))

    err_count = warn_count = info_count = 0
    for rep in reports:
        for f in rep.findings:
            if order[f.severity] >= order["error"]:
                err_count += 1
            elif order[f.severity] >= order["warn"]:
                warn_count += 1
            else:
                info_count += 1

    lines_out: List[str] = []
    for rep in reports:
        if not rep.findings:
            continue
        lines_out.append(f"\n== {rep.path} (context: {rep.context_dir or '.'}) ==")
        for f in sorted(rep.findings, key=lambda x: (x.line, x.severity)):
            lines_out.append(
                f"  L{f.line:4d} [{f.severity.upper():5s}] {f.code}: {f.message}"
            )

    if lines_out:
        print("\n".join(lines_out).strip())
    else:
        print("No findings (or no Dockerfiles scanned).")

    summary = {
        "root": str(root),
        "files_scanned": len(reports),
        "files_with_findings": sum(1 for r in reports if r.findings),
        "findings_error": err_count,
        "findings_warn": warn_count,
        "findings_info": info_count,
    }
    print(
        f"\n--- summary: {summary['files_scanned']} files, "
        f"{summary['files_with_findings']} with findings | "
        f"errors={err_count} warns={warn_count} info={info_count} ---"
    )

    if args.json_out:
        payload = {
            "summary": summary,
            "reports": [
                {
                    "path": r.path,
                    "context_dir": r.context_dir,
                    "findings": [
                        {
                            "line": f.line,
                            "severity": f.severity,
                            "code": f.code,
                            "message": f.message,
                            "instruction": f.instruction,
                        }
                        for f in r.findings
                    ],
                }
                for r in reports
            ],
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")

    worst = 0
    for rep in reports:
        for f in rep.findings:
            if order[f.severity] >= threshold:
                worst = max(worst, order[f.severity])
    return 1 if worst >= threshold else 0


if __name__ == "__main__":
    sys.exit(main())

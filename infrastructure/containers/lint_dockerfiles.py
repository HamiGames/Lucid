#!/usr/bin/env python3
"""
File: infrastructure/containers/lint_dockerfiles.py

Lint Dockerfiles against Lucid host registry (host-config.yml), x-files.json manifest, and
Dockerfile syntax rules.

**Writes:** This tool does not modify Dockerfiles unless you pass ``--fix``. ``--fix`` only applies
a small set of safe typo replacements (e.g. ``pyhton`` → ``python``). It does not rewrite LABELs,
COPY paths, or heredocs — those warnings are report-only.

Uses:
  - infrastructure/containers/host-config.yml — expected labels and ports per source_dockerfile
  - x-files.json — section_to_canonical paths to validate build-context COPY sources and
    directory relevance (prefix overlap with copied repo paths)
  - Path relevance — flags suspicious absolute paths in ``COPY --from=`` sources and ``WORKDIR``
    (e.g. ``/export-tor/bin``, ``/t/bin`` typos, root ``/dynamic/``)

Usage (repository root):
  python infrastructure/containers/lint_dockerfiles.py
  python infrastructure/containers/lint_dockerfiles.py --fix
  python infrastructure/containers/lint_dockerfiles.py --only infrastructure/containers/gui/Dockerfile.gui
  python infrastructure/containers/lint_dockerfiles.py --json

Requires: PyYAML (pip install pyyaml)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2) from e


DOCKERFILE_NAMES = ("Dockerfile", "dockerfile")
VALID_INSTRUCTIONS = frozenset(
    {
        "FROM",
        "RUN",
        "CMD",
        "LABEL",
        "EXPOSE",
        "ENV",
        "ADD",
        "COPY",
        "ENTRYPOINT",
        "VOLUME",
        "USER",
        "WORKDIR",
        "ARG",
        "ONBUILD",
        "STOPSIGNAL",
        "HEALTHCHECK",
        "SHELL",
    }
)

# Safe automatic replacements (word-boundary typos common in apt package lists).
FIX_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpyhton(\d)"), r"python\1"),
    (re.compile(r"\bpyhton\b"), "python"),
)

# First path segment (lowercase) that must not appear as a COPY --from= / WORKDIR root in Lucid images.
_PATH_FORBIDDEN_ROOTS = frozenset({"export-tor"})


def normalize_repo_rel(path_like: str) -> str:
    return path_like.replace("\\", "/").strip().lstrip("./")


def casefold_path_key(p: str) -> str:
    return normalize_repo_rel(p).casefold()


def merge_dockerfile_physical_lines(text: str) -> list[str]:
    """Merge backslash-continued lines into single logical lines."""
    raw_lines = text.splitlines()
    out: list[str] = []
    buf: list[str] = []
    for line in raw_lines:
        if buf:
            buf.append(line)
            if line.rstrip().endswith("\\"):
                continue
            merged = "\n".join(buf)
            buf = []
            out.append(merged)
            continue
        if line.rstrip().endswith("\\") and not line.strip().startswith("#"):
            buf.append(line)
        else:
            out.append(line)
    if buf:
        out.append("\n".join(buf))
    return out


_HEREDOC_DELIM = re.compile(r"""<<-?\s*(?:'([^']*)'|"([^"]*)"|([a-zA-Z_][\w-]*))""")


def extract_heredoc_delimiter(line: str) -> str | None:
    if "<<" not in line:
        return None
    m = _HEREDOC_DELIM.search(line)
    if not m:
        return None
    return m.group(1) or m.group(2) or m.group(3)


def iter_skip_heredoc_bodies(raw_lines: list[str]) -> list[tuple[int, str]]:
    """Return (1-based line number, text) per line, omitting COPY/RUN heredoc bodies (BuildKit)."""
    out: list[tuple[int, str]] = []
    i = 0
    n = len(raw_lines)
    while i < n:
        line = raw_lines[i]
        lineno = i + 1
        s = strip_comment(line).strip()
        if s and not s.startswith("#"):
            sup = s.upper()
            if (sup.startswith("COPY ") or sup.startswith("RUN ")) and "<<" in s:
                delim = extract_heredoc_delimiter(s)
                out.append((lineno, line))
                i += 1
                if delim is None:
                    continue
                while i < n:
                    cl = raw_lines[i].rstrip("\r\n")
                    if cl.strip() == delim or cl.lstrip("\t").rstrip() == delim:
                        i += 1
                        break
                    i += 1
                continue
        out.append((lineno, line))
        i += 1
    return out


def merge_continuations_tagged(tagged: list[tuple[int, str]]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    buf_ln: int | None = None
    buf_parts: list[str] = []
    for ln, line in tagged:
        if buf_ln is not None:
            buf_parts.append(line)
            if line.rstrip().endswith("\\") and not line.strip().startswith("#"):
                continue
            merged = "\n".join(buf_parts)
            out.append((buf_ln, merged))
            buf_ln = None
            buf_parts = []
            continue
        if line.rstrip().endswith("\\") and not line.strip().startswith("#"):
            buf_ln = ln
            buf_parts.append(line)
        else:
            out.append((ln, line))
    if buf_ln is not None:
        out.append((buf_ln, "\n".join(buf_parts)))
    return out


def build_scannable_logical_lines(text: str) -> list[tuple[int, str]]:
    """Physical lines with heredoc bodies removed, then ``\\`` continuations merged."""
    raw = text.splitlines()
    tagged = iter_skip_heredoc_bodies(raw)
    return merge_continuations_tagged(tagged)


_LABEL_FRAGMENT = re.compile(r"^\s*[a-z0-9_.]+\.[a-z0-9_.]+\s*=")


def looks_like_label_key_value_line(s: str) -> bool:
    """True if line looks like ``com.foo.bar=\"...\"`` but is missing leading ``LABEL``."""
    return bool(_LABEL_FRAGMENT.match(s.strip()))


def strip_comment(line: str) -> str:
    in_sq = False
    in_dq = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == "'" and not in_dq:
            in_sq = not in_sq
        elif c == '"' and not in_sq:
            in_dq = not in_dq
        elif c == "#" and not in_sq and not in_dq:
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def _tokenize_copy_add_paths(logical_line: str) -> list[str]:
    """Strip COPY/ADD and flags; return path tokens (last is destination)."""
    s = strip_comment(logical_line).strip()
    if s.upper().startswith("COPY "):
        rest = s[5:].strip()
    elif s.upper().startswith("ADD "):
        rest = s[4:].strip()
    else:
        return []
    tokens: list[str] = []
    i = 0
    parts = rest.split()
    while i < len(parts):
        t = parts[i]
        if t.startswith("--"):
            if "=" not in t and i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                i += 2
                continue
            i += 1
            continue
        tokens.append(t)
        i += 1
    return tokens


def parse_copy_add_sources(logical_line: str) -> list[str]:
    """
    Extract build-context source paths from COPY/ADD (not COPY --from=...).
    Returns repo-relative first segments for validation.
    """
    s = strip_comment(logical_line).strip()
    upper = s.upper()
    if not (upper.startswith("COPY ") or upper.startswith("ADD ")):
        return []
    rest = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else ""
    if "<<" in rest:
        return []
    if "--from=" in rest.lower():
        return []

    tokens = _tokenize_copy_add_paths(logical_line)
    if len(tokens) < 2:
        return []
    sources = tokens[:-1]
    out: list[str] = []
    for src in sources:
        if src.startswith("/"):
            continue
        norm = normalize_repo_rel(src.rstrip("/"))
        if norm and not norm.startswith(".."):
            out.append(norm)
    return out


def extract_copy_from_absolute_sources(logical_line: str) -> list[str]:
    """Absolute source paths in COPY/ADD --from=... (image stage), excluding heredocs."""
    s = strip_comment(logical_line).strip()
    if "<<" in s:
        return []
    if "--from=" not in s.lower():
        return []
    tokens = _tokenize_copy_add_paths(logical_line)
    if len(tokens) < 2:
        return []
    return [x for x in tokens[:-1] if x.startswith("/")]


def path_relevance_message(abs_path: str) -> str | None:
    """
    If ``abs_path`` is a suspicious absolute path for Lucid distroless/builder COPY sources
    or WORKDIR, return a short reason; else None.
    """
    raw = abs_path.strip().strip("`\"'")
    p = raw.split("#", 1)[0].strip().rstrip("/")
    if not p.startswith("/"):
        return None
    parts = [x for x in p.split("/") if x]
    if not parts:
        return None
    root = parts[0].lower()
    if root in _PATH_FORBIDDEN_ROOTS:
        return (
            f"path {abs_path!r} is not a Lucid-relevant root (/{root}/); "
            "use FHS paths (/usr, /bin, /etc), /build/, /app/, or /export/... staging - not /export-tor/..."
        )
    if root == "dynamic":
        return (
            f"path {abs_path!r} starts with /dynamic/ - verify this directory exists on the source "
            "stage; it is not a standard FHS or Lucid layout root"
        )
    if len(root) == 1 and root.isalpha() and len(parts) >= 2 and parts[1] in (
        "bin",
        "lib",
        "lib64",
        "sbin",
    ):
        return (
            f"path {abs_path!r} looks like a mistyped root (single-letter /{root}/); "
            "often a truncated name such as export-tor or a missing /usr prefix"
        )
    return None


def extract_workdir_absolute(logical_line: str) -> str | None:
    s = strip_comment(logical_line).strip()
    m = re.match(r"^WORKDIR\s+(\S+)", s, re.I)
    if not m:
        return None
    val = m.group(1).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    if val.startswith("/"):
        return val
    return None


def lint_path_relevance(
    rel_path: str,
    tagged_logical: list[tuple[int, str]],
    report: LintReport,
) -> None:
    """Warn on irrelevant or likely-wrong absolute paths (COPY --from= sources, WORKDIR)."""
    for lineno, line in tagged_logical:
        for src in extract_copy_from_absolute_sources(line):
            msg = path_relevance_message(src)
            if msg:
                report.add(
                    rel_path,
                    lineno,
                    "warning",
                    "PATH_RELEVANCE",
                    msg,
                )
        wd = extract_workdir_absolute(line)
        if wd:
            msg = path_relevance_message(wd)
            if msg:
                report.add(
                    rel_path,
                    lineno,
                    "warning",
                    "PATH_RELEVANCE_WORKDIR",
                    f"WORKDIR {wd!r}: {msg}",
                )


def extract_label_kv_from_block(text: str) -> dict[str, str]:
    """Parse KEY=\"value\" pairs from a LABEL instruction body."""
    out: dict[str, str] = {}
    for m in re.finditer(r'([a-zA-Z0-9_.]+)\s*=\s*"([^"]*)"', text):
        out[m.group(1)] = m.group(2)
    return out


def collect_labels_from_dockerfile(text: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in merge_dockerfile_physical_lines(text):
        sl = strip_comment(line).strip()
        if not sl.upper().startswith("LABEL "):
            continue
        body = sl[6:].strip()
        labels.update(extract_label_kv_from_block(body))
    return labels


def load_host_config(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    services = raw.get("services") or {}
    by_dockerfile: dict[str, dict[str, Any]] = {}
    for _k, svc in services.items():
        if not isinstance(svc, dict):
            continue
        src = svc.get("source_dockerfile")
        if isinstance(src, str) and src.strip():
            by_dockerfile[casefold_path_key(src)] = svc
    return raw, by_dockerfile


def load_x_files(path: Path) -> tuple[set[str], dict[str, str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    stm = data.get("section_to_canonical") or {}
    if not isinstance(stm, dict):
        stm = {}
    sections: set[str] = set()
    canonical_by_section: dict[str, str] = {}
    top_level_dirs: set[str] = set()
    for sec, can in stm.items():
        if not isinstance(sec, str):
            continue
        sec_n = normalize_repo_rel(sec)
        sections.add(sec_n)
        if isinstance(can, str):
            canonical_by_section[sec_n] = can
        first = sec_n.split("/", 1)[0]
        if first:
            top_level_dirs.add(first)
    return sections, canonical_by_section, top_level_dirs


def discover_dockerfiles(roots: Iterable[Path], repo_root: Path) -> list[Path]:
    found: set[Path] = set()
    skip_name_substrings = (".layout.bak", " copy.", " copy ")
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("Dockerfile*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if not (name == "dockerfile" or name.startswith("dockerfile.")):
                continue
            rel = p.relative_to(repo_root).as_posix()
            if any(s in rel for s in skip_name_substrings):
                continue
            if "__pycache__" in rel:
                continue
            found.add(p)
    return sorted(found)


@dataclass
class LintFinding:
    path: str
    line: int | None
    severity: str  # error | warning | info
    code: str
    message: str


@dataclass
class LintReport:
    findings: list[LintFinding] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)

    def add(
        self,
        path: str,
        line: int | None,
        severity: str,
        code: str,
        message: str,
    ) -> None:
        self.findings.append(LintFinding(path, line, severity, code, message))


def instruction_name(logical_line: str) -> str | None:
    s = strip_comment(logical_line).strip()
    if not s or s.startswith("#"):
        return None
    return s.split(None, 1)[0].upper()


def _from_body_has_base_image(body: str) -> bool:
    """True if FROM line has an image ref (not 'FROM AS name' only)."""
    parts = body.split()
    i = 0
    while i < len(parts) and parts[i].startswith("--"):
        i += 1
    if i >= len(parts):
        return False
    return parts[i].upper() != "AS"


def lint_syntax_logical_lines(
    rel_path: str,
    tagged_logical: list[tuple[int, str]],
    report: LintReport,
) -> None:
    seen_from = False
    for lineno, line in tagged_logical:
        s = strip_comment(line).strip()
        if not s or s.startswith("#"):
            continue
        inst = instruction_name(line)
        if inst is None:
            continue
        if inst not in VALID_INSTRUCTIONS:
            if looks_like_label_key_value_line(s):
                report.add(
                    rel_path,
                    lineno,
                    "warning",
                    "LABEL_CONTINUATION_BREAK",
                    "line looks like LABEL key=value but has no LABEL keyword — previous LABEL line "
                    "may be missing a trailing backslash (\\)",
                )
            else:
                report.add(
                    rel_path,
                    lineno,
                    "warning",
                    "UNKNOWN_INSTRUCTION",
                    f"unknown instruction {inst!r}",
                )
            continue
        if inst == "FROM":
            rest = s[4:].strip() if len(s) >= 4 and s[:4].upper() == "FROM" else ""
            if not rest.strip():
                report.add(rel_path, lineno, "error", "FROM_EMPTY", "FROM has no base image")
            elif not _from_body_has_base_image(rest):
                report.add(
                    rel_path,
                    lineno,
                    "error",
                    "FROM_EMPTY",
                    "FROM has no base image before AS",
                )
            seen_from = True
        if inst in {"RUN", "CMD", "ENTRYPOINT"} and seen_from:
            payload = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else ""
            if not payload.strip():
                report.add(rel_path, lineno, "error", f"{inst}_EMPTY", f"{inst} has empty payload")
        if not seen_from and inst != "ARG":
            report.add(
                rel_path,
                lineno,
                "warning",
                "BEFORE_FIRST_FROM",
                f"{inst} appears before first FROM (only ARG is valid before FROM besides comments)",
            )


def path_exists_in_manifest_or_disk(
    repo_root: Path,
    rel: str,
    x_sections: set[str],
) -> tuple[bool, str]:
    """
    True if rel matches x-files section, is a prefix of a section, or exists on disk under repo_root.
    """
    rel = normalize_repo_rel(rel)
    if rel in x_sections:
        return True, "x-files exact"
    for sep in ("/",):
        if rel.endswith(sep):
            base = rel.rstrip("/")
        else:
            base = rel
        for sec in x_sections:
            if sec == base or sec.startswith(base + "/"):
                return True, "x-files prefix"
    p = repo_root / rel
    if p.is_file():
        return True, "disk file"
    if p.is_dir():
        return True, "disk dir"
    return False, "missing"


def lint_copy_sources(
    rel_path: str,
    tagged_logical: list[tuple[int, str]],
    repo_root: Path,
    x_sections: set[str],
    report: LintReport,
) -> set[str]:
    """Return set of top-level directory names seen in COPY sources (for relevance)."""
    tops: set[str] = set()
    for lineno, line in tagged_logical:
        s = strip_comment(line).strip()
        if not s.upper().startswith("COPY ") and not s.upper().startswith("ADD "):
            continue
        for src in parse_copy_add_sources(line):
            if any(ch in src for ch in "*?[]"):
                continue
            first = src.split("/", 1)[0]
            if first:
                tops.add(first)
            ok, why = path_exists_in_manifest_or_disk(repo_root, src, x_sections)
            if not ok:
                report.add(
                    rel_path,
                    lineno,
                    "warning",
                    "COPY_SOURCE_UNKNOWN",
                    f"COPY/ADD source {src!r} not in x-files.json and not found on disk ({why})",
                )
    return tops


def lint_host_config_labels(
    rel_path: str,
    full_text: str,
    svc: dict[str, Any] | None,
    report: LintReport,
) -> None:
    if not svc:
        report.add(
            rel_path,
            None,
            "info",
            "HOST_CONFIG_UNREGISTERED",
            "no source_dockerfile entry in host-config.yml — skipping label/port alignment",
        )
        return
    expected_labels = svc.get("labels") or {}
    if not isinstance(expected_labels, dict):
        return
    got = collect_labels_from_dockerfile(full_text)
    for k, v in expected_labels.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        gv = got.get(k)
        if gv is None:
            report.add(
                rel_path,
                None,
                "warning",
                "LABEL_MISSING",
                f"expected LABEL {k}={v!r} from host-config.yml — not found in Dockerfile",
            )
        elif gv != v:
            report.add(
                rel_path,
                None,
                "warning",
                "LABEL_MISMATCH",
                f"LABEL {k}: got {gv!r}, host-config expects {v!r}",
            )
    port = svc.get("port")
    if isinstance(port, int) and port > 0:
        exp_expose = str(port)
        ge = got.get("com.lucid.expose")
        if ge is not None and ge != exp_expose:
            report.add(
                rel_path,
                None,
                "warning",
                "EXPOSE_LABEL_VS_HOST_CONFIG",
                f"com.lucid.expose is {ge!r} but host-config port is {port}",
            )


def relevance_report(
    rel_path: str,
    copy_top_levels: set[str],
    x_sections: set[str],
    repo_root: Path,
    report: LintReport,
) -> None:
    """Summarize overlap between COPY top-level dirs and x-files sections (image relevance)."""
    if not copy_top_levels:
        return
    matched: defaultdict[str, list[str]] = defaultdict(list)
    for tl in sorted(copy_top_levels):
        for sec in x_sections:
            if sec == tl or sec.startswith(tl + "/"):
                matched[tl].append(sec)
    for tl, secs in matched.items():
        n = len(secs)
        sample = ", ".join(secs[:3])
        more = f" (+{n - 3} more)" if n > 3 else ""
        report.add(
            rel_path,
            None,
            "info",
            "X_FILES_RELEVANCE",
            f"COPY prefix {tl!r} matches {n} x-files section(s): {sample}{more}",
        )
    orphan_tls = copy_top_levels - set(matched.keys())
    for tl in sorted(orphan_tls):
        if (repo_root / tl).is_file():
            continue
        if (repo_root / tl).is_dir():
            report.add(
                rel_path,
                None,
                "warning",
                "COPY_PREFIX_NO_X_FILES",
                f"COPY prefix {tl!r} is a directory on disk but has no matching path prefix in x-files.json",
            )
            continue
        report.add(
            rel_path,
            None,
            "warning",
            "COPY_PREFIX_NO_X_FILES",
            f"top-level COPY prefix {tl!r} has no matching path prefix in x-files.json",
        )


def apply_fixes(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines(keepends=True)
    changes: list[str] = []
    out_lines: list[str] = []
    for line in lines:
        new_line = line
        for pat, repl in FIX_PATTERNS:
            new_line = pat.sub(repl, new_line)
        if new_line != line:
            changes.append(f"typo fix: {line.strip()[:80]!r} -> {new_line.strip()[:80]!r}")
        out_lines.append(new_line)
    return "".join(out_lines), changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint Lucid Dockerfiles (host-config + x-files + syntax).")
    ap.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of infrastructure/containers).",
    )
    ap.add_argument(
        "--host-config",
        type=Path,
        default=None,
        help="Path to host-config.yml (default: <root>/infrastructure/containers/host-config.yml).",
    )
    ap.add_argument(
        "--x-files",
        type=Path,
        default=None,
        help="Path to x-files.json (default: <root>/x-files.json).",
    )
    ap.add_argument(
        "--scan-root",
        action="append",
        dest="scan_roots",
        default=None,
        help="Extra directory to scan (repeatable). Default: infrastructure/containers, infrastructure/docker.",
    )
    ap.add_argument("--only", type=str, default=None, help="Single Dockerfile path relative to repo root.")
    ap.add_argument(
        "--fix",
        action="store_true",
        help="Apply only safe typo repairs (e.g. pyhton→python); does not fix LABEL/COPY/heredocs.",
    )
    ap.add_argument("--json", action="store_true", help="Print findings as JSON.")
    ap.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit 1 if any warning or error (default: exit 1 only on errors).",
    )
    ap.add_argument(
        "--no-path-relevance",
        action="store_true",
        help="Skip PATH_RELEVANCE checks (COPY --from= / WORKDIR absolute paths).",
    )
    args = ap.parse_args()

    here = Path(__file__).resolve()
    default_root = here.parents[2]
    repo_root = (args.root or default_root).resolve()
    host_config = args.host_config or (repo_root / "infrastructure/containers/host-config.yml")
    x_files_path = args.x_files or (repo_root / "x-files.json")

    if not host_config.is_file():
        print(f"error: host-config not found: {host_config}", file=sys.stderr)
        return 2
    if not x_files_path.is_file():
        print(f"error: x-files.json not found: {x_files_path}", file=sys.stderr)
        return 2

    _, by_df = load_host_config(host_config)
    x_sections, _canon, _tops = load_x_files(x_files_path)

    scan_roots = args.scan_roots
    if not scan_roots:
        scan_roots = [
            repo_root / "infrastructure/containers",
            repo_root / "infrastructure/docker",
        ]

    if args.only:
        only = Path(args.only)
        if only.is_absolute():
            files = [only.resolve()]
        else:
            files = [(repo_root / only).resolve()]
        for f in files:
            if not f.is_file():
                print(f"error: file not found: {f}", file=sys.stderr)
                return 2
    else:
        files = discover_dockerfiles(scan_roots, repo_root)

    report = LintReport()
    error_count = 0
    warning_count = 0

    for fp in files:
        rel = fp.relative_to(repo_root).as_posix()
        text = fp.read_text(encoding="utf-8", errors="replace")
        if args.fix:
            new_text, fixes = apply_fixes(text)
            if new_text != text:
                fp.write_text(new_text, encoding="utf-8", newline="\n")
                report.fixes_applied.extend(f"{rel}: {x}" for x in fixes)
            text = new_text

        tagged_logical = build_scannable_logical_lines(text)
        lint_syntax_logical_lines(rel, tagged_logical, report)
        copy_tls = lint_copy_sources(rel, tagged_logical, repo_root, x_sections, report)

        svc = by_df.get(casefold_path_key(rel))
        lint_host_config_labels(rel, text, svc, report)
        relevance_report(rel, copy_tls, x_sections, repo_root, report)
        if not args.no_path_relevance:
            lint_path_relevance(rel, tagged_logical, report)

    for f in report.findings:
        if f.severity == "error":
            error_count += 1
        elif f.severity == "warning":
            warning_count += 1

    if args.json:
        out = {
            "findings": [
                {
                    "path": f.path,
                    "line": f.line,
                    "severity": f.severity,
                    "code": f.code,
                    "message": f.message,
                }
                for f in report.findings
            ],
            "fixes_applied": report.fixes_applied,
            "summary": {
                "errors": error_count,
                "warnings": warning_count,
                "files_scanned": len(files),
            },
        }
        print(json.dumps(out, indent=2))
    else:
        for f in report.findings:
            loc = f"{f.path}:{f.line}" if f.line else f.path
            print(f"{f.severity.upper()} [{f.code}] {loc}: {f.message}")
        for fx in report.fixes_applied:
            print(f"FIX: {fx}")
        print(
            f"--- summary: {len(files)} file(s), {error_count} error(s), {warning_count} warning(s) ---",
            file=sys.stderr,
        )

    if error_count:
        return 1
    if args.fail_on_warning and warning_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

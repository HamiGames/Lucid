"""
File: /app/<tree>/...
x-lucid-file-path: /app/<tree>/...
x-lucid-file-directory: /app/<tree>
x-lucid-file-type: python

Normalise module docstrings to:

Run from repo root:  .venv\\Scripts\\python.exe _normalise_lucid_headers.py
Optional: one or more ROOT directory names, e.g.  .venv\\Scripts\\python.exe _normalise_lucid_headers.py gui_tor_manager

Write ``x-files-listing.txt`` (all ``*.py`` under the repo, ``File:`` + ``x-lucid-file-path:``
extracted; plus ``*.sh`` under ``scripts/``, ``tests/``, ``ops/``; plus all ``*.yml`` /
``*.yaml``)::

    .venv\\Scripts\\python.exe _normalise_lucid_headers.py --x-files-listing

Add more trees: append (REPO / "dirname", "/app/dirname") to ROOTS below
(e.g. ``(REPO / "scripts", "/app/scripts")``). Selected paths under ``infrastructure/``
and repo-root ``service_mesh/`` map to runtime ``/app/...`` layouts (see
``map_repo_rel_to_app_paths``).

``--x-files-listing`` also emits every ``*.sh`` under ``scripts/``, ``tests/``, and ``ops/``
(see ``SH_FILE_ROOTS``), with ``x-lucid-file-type: shell`` when not set in-file, and
every ``*.yml`` / ``*.yaml`` (``#`` comment headers; use ``_normalise_lucid_yaml_headers.py``).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
DEFAULT_BRANCH_LISTING = REPO / "x-files-listing-branches.txt"

# (directory under Lucid repo root, /app prefix for container paths)
ROOTS: list[tuple[Path, str]] = [
    (REPO / "blockchain", "/app/blockchain"),
    (REPO / "common", "/app/common"),
    (REPO / "auth", "/app/auth"),
    (REPO / "admin", "/app/admin"),
    (REPO / "03_api_gateway", "/app/03_api_gateway"),
    (REPO / "02_network_security", "/app/02_network_security"),
    (REPO / "RDP", "/app/RDP"),
    (REPO / "api", "/app/api"),
    (REPO / "app", "/app/app"),
    (REPO / "database", "/app/database"),
    (REPO / "node", "/app/node"),
    (REPO / "sessions", "/app/sessions"),
    (REPO / "gui_hardware_manager", "/app/gui_hardware_manager"),
    (REPO / "gui_tor_manager", "/app/gui_tor_manager"),
    (REPO / "gui_docker_manager", "/app/gui_docker_manager"),
    (REPO / "payment_systems", "/app/payment_systems"),
    (REPO / "server", "/app/server"),
    (REPO / "apps", "/app/apps"),
    (REPO / "user", "/app/user"),
    (REPO / "user_content", "/app/user_content"),
    (REPO / "tools", "/app/tools"),
    (REPO / "storage", "/app/storage"),
    (REPO / "vm", "/app/vm"),
    (REPO / "wallet", "/app/wallet"),
    (REPO / "electron_gui", "/app/electron_gui"),
    (REPO / "infrastructure", "/app/infrastructure"),
    (REPO / "service_mesh", "/app/old-service_mesh"),
    (REPO / "scripts", "/app/scripts"),
    (REPO / "tests", "/app/tests"),
    (REPO / "ops", "/app/ops"),
]

# (host subtree, /app prefix) — shell listing only; use # File: / # x-lucid-* in .sh sources
SH_FILE_ROOTS: list[tuple[Path, str]] = [
    (REPO / "scripts", "/app/scripts"),
    (REPO / "tests", "/app/tests"),
    (REPO / "ops", "/app/ops"),
]

RE_SHELL_FILE = re.compile(r"^\s*#\s*File:\s*(.+?)\s*$")
RE_SHELL_XPATH = re.compile(r"^\s*#\s*x-lucid-file-path:\s*(.+?)\s*$")
RE_SHELL_XDIR = re.compile(r"^\s*#\s*x-lucid-file-directory:\s*(.+?)\s*$")
RE_SHELL_XTYPE = re.compile(r"^\s*#\s*x-lucid-file-type:\s*(.+?)\s*$")

STRAY_STAR = re.compile(
    r"^\s*required:\s*x-lucid-file-path:\s*/app/\*\s*"
    r"\n\s*x-lucid-file-type:\s*python\s*$",
    re.MULTILINE,
)

RE_FILE_HEADER = re.compile(r"^\s*File:\s*(.+?)\s*$", re.MULTILINE)
RE_X_LUCID_PATH = re.compile(r"^\s*x-lucid-file-path:\s*(.+?)\s*$", re.MULTILINE)
RE_X_LUCID_DIR = re.compile(r"^\s*x-lucid-file-directory:\s*(.+?)\s*$", re.MULTILINE)
RE_X_LUCID_TYPE = re.compile(r"^\s*x-lucid-file-type:\s*(.+?)\s*$", re.MULTILINE)
RE_SECTION_FILE = re.compile(r"^\s*#\s*---\s+(.+?)\s+---\s*$")
RE_LISTING_XPATH = re.compile(r"^\s*#?\s*x-lucid-file-path:\s*(.+?)\s*$")

# Skip heavy or non-source trees when scanning the whole repo for headers.
SKIP_PATH_PARTS = frozenset(
    {
        ".venv",
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".eggs",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
    }
)


def _norm_app_join(prefix: str, suffix: str) -> str:
    """Single-slash /app path from prefix and relative suffix."""
    p = prefix.rstrip("/")
    s = suffix.lstrip("/")
    if not s:
        return p
    return f"{p}/{s}".replace("//", "/")


def map_repo_rel_to_app_paths(rel_posix: str) -> tuple[str, str] | None:
    """
    If repo-relative path matches a known runtime layout, return
    ``(full /app/... path, parent directory for x-lucid-file-directory)``.

    Order matters: more specific repo prefixes first (``containers/services`` before
    ``containers``).

    - ``infrastructure/containers/services/...`` → ``/app/service_configs/...``
    - ``infrastructure/containers/...`` → ``/app/configs/...``
    - ``infrastructure/kubernetes/...`` → ``/app/service_configs/kubernetes/...``
    - ``infrastructure/service_mesh/...`` → ``/app/service_mesh/...``
    - ``service_mesh/...`` (repo root tree) → ``/app/old-service_mesh/...``
    """
    rules: list[tuple[str, str]] = [
        ("infrastructure/containers/services", "/app/service_configs"),
        ("infrastructure/containers", "/app/configs"),
        ("infrastructure/kubernetes", "/app/service_configs/kubernetes"),
        ("infrastructure/service_mesh", "/app/service_mesh"),
        ("service_mesh", "/app/old-service_mesh"),
    ]
    for prefix, app_base in rules:
        if rel_posix == prefix:
            app_path = app_base
            return app_path, str(Path(app_path).parent.as_posix())
        pfx = prefix + "/"
        if rel_posix.startswith(pfx):
            rest = rel_posix[len(pfx) :]
            app_path = _norm_app_join(app_base, rest)
            return app_path, str(Path(app_path).parent.as_posix())
    return None


def legacy_header_strip_prefixes(rel_posix: str) -> list[str]:
    """Old /app paths to strip from suffix docstrings after repo→app remapping."""
    if rel_posix.startswith("infrastructure/containers/services/") or rel_posix == "infrastructure/containers/services":
        return ["/app/infrastructure/containers/services"]
    if rel_posix.startswith("infrastructure/containers/") or rel_posix == "infrastructure/containers":
        return ["/app/infrastructure/containers"]
    if rel_posix.startswith("infrastructure/kubernetes/") or rel_posix == "infrastructure/kubernetes":
        return ["/app/infrastructure/kubernetes"]
    if rel_posix.startswith("infrastructure/service_mesh/") or rel_posix == "infrastructure/service_mesh":
        return ["/app/infrastructure/service_mesh"]
    if rel_posix.startswith("service_mesh/") or rel_posix == "service_mesh":
        return ["/app/service_mesh", "/app/old-service_mesh", "/app/old_service_mesh"]
    return []


def canonical_app_path(path: Path, repo: Path) -> tuple[str, str]:
    """
    Return ``(full /app/... path, x-lucid-file-directory)`` for header output.

    Applies container/runtime path aliases first, then longest ``ROOTS`` match,
    else ``/app/<repo-relative>``. Aliased trees use the file's parent directory;
    unmapped ``ROOTS`` matches use the mount prefix (existing convention).
    """
    resolved = path.resolve()
    repo_r = repo.resolve()
    rel = resolved.relative_to(repo_r).as_posix()
    mapped = map_repo_rel_to_app_paths(rel)
    if mapped is not None:
        return mapped
    best: tuple[int, str, Path] | None = None
    for base, prefix in ROOTS:
        br = base.resolve()
        try:
            resolved.relative_to(br)
        except ValueError:
            continue
        score = len(br.parts)
        if best is None or score > best[0]:
            best = (score, prefix, br)
    if best is None:
        app_path = f"/app/{rel}"
        doc_directory = str(Path(app_path).parent.as_posix())
    else:
        _, prefix, br = best
        sub = resolved.relative_to(br).as_posix()
        app_path = _norm_app_join(prefix, sub)
        doc_directory = prefix
    return app_path, doc_directory


def load_listing_path_overrides(listing_path: Path) -> dict[str, str]:
    """
    Parse x-files-listing-style sections into ``{repo-relative: x-lucid-file-path}``.

    Uses the first ``x-lucid-file-path`` found in each ``# --- <repo path> ---`` section.
    """
    if not listing_path.is_file():
        return {}
    out: dict[str, str] = {}
    current_rel: str | None = None
    try:
        raw = listing_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    for line in raw.replace("\r\n", "\n").split("\n"):
        ms = RE_SECTION_FILE.match(line)
        if ms:
            current_rel = ms.group(1).strip().replace("\\", "/")
            continue
        if current_rel is None or current_rel in out:
            continue
        mx = RE_LISTING_XPATH.match(line)
        if not mx:
            continue
        candidate = mx.group(1).strip()
        if candidate.startswith("/app/") or candidate == "/app":
            out[current_rel] = candidate
    return out


def resolve_lucid_app_path_with_overrides(
    path: Path,
    repo: Path,
    overrides: dict[str, str] | None = None,
) -> tuple[str, str]:
    """
    Resolve path to runtime app path, preferring listing override when available.
    """
    rel = path.resolve().relative_to(repo.resolve()).as_posix()
    if overrides:
        ov = overrides.get(rel)
        if ov and ov.startswith("/app"):
            return ov, str(Path(ov).parent.as_posix())
    return canonical_app_path(path, repo)


def _should_skip_py_path(path: Path, repo: Path) -> bool:
    try:
        rel = path.relative_to(repo)
    except ValueError:
        return True
    return any(part in SKIP_PATH_PARTS for part in rel.parts)


def iter_repo_py_files(repo: Path | None = None) -> list[Path]:
    root = repo or REPO
    out: list[Path] = []
    for p in root.rglob("*.py"):
        if _should_skip_py_path(p, root):
            continue
        out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def iter_repo_sh_files(repo: Path | None = None) -> list[tuple[Path, str]]:
    """(path, canonical /app/... path) for each *.sh under SH_FILE_ROOTS."""
    root = (repo or REPO).resolve()
    out: list[tuple[Path, str]] = []
    for base, prefix in SH_FILE_ROOTS:
        if not base.is_dir():
            continue
        for p in base.rglob("*.sh"):
            if _should_skip_py_path(p, root):
                continue
            rel = p.relative_to(base).as_posix()
            out.append((p, f"{prefix}/{rel}"))
    return sorted(out, key=lambda x: str(x[0]).lower())


def resolve_lucid_app_path(
    path: Path,
    repo: Path,
    overrides: dict[str, str] | None = None,
) -> tuple[str, str]:
    """
    Return ``(full /app/... path, parent directory of that path)`` for YAML/shell
    listing defaults. Same path rules as ``canonical_app_path``.
    """
    app_path, _ = resolve_lucid_app_path_with_overrides(path, repo, overrides)
    parent = str(Path(app_path).parent.as_posix())
    return app_path, parent


def iter_repo_yaml_files(repo: Path | None = None) -> list[Path]:
    """All ``*.yml`` / ``*.yaml`` under the repo (excluding skip trees)."""
    root = (repo or REPO).resolve()
    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in ("*.yml", "*.yaml"):
        for p in root.rglob(pattern):
            if _should_skip_py_path(p, root):
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def extract_lucid_metadata_shell(content: str) -> tuple[str, str, str, str]:
    """First # File: / # x-lucid-* lines in the first chunk of a shell file."""
    fv = pv = dv = tv = ""
    n = 0
    for line in content.replace("\r\n", "\n").split("\n"):
        n += 1
        if n > 120:
            break
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("#!"):
            if fv or pv:
                break
            continue
        mf = RE_SHELL_FILE.match(line)
        mx = RE_SHELL_XPATH.match(line)
        md = RE_SHELL_XDIR.match(line)
        mt = RE_SHELL_XTYPE.match(line)
        if mf:
            fv = mf.group(1).strip()
        if mx:
            pv = mx.group(1).strip()
        if md:
            dv = md.group(1).strip()
        if mt:
            tv = mt.group(1).strip()
    return fv, pv, dv, tv


def extract_file_and_x_lucid_path(content: str) -> tuple[str, str]:
    """First ``File:`` and first ``x-lucid-file-path:`` line in the file (anywhere)."""
    fv, pv, _, _ = extract_lucid_metadata(content)
    return fv, pv


def extract_lucid_metadata(content: str) -> tuple[str, str, str, str]:
    """First ``File:``, path, directory, and file-type lines (anywhere in file)."""
    m_file = RE_FILE_HEADER.search(content)
    m_path = RE_X_LUCID_PATH.search(content)
    m_dir = RE_X_LUCID_DIR.search(content)
    m_type = RE_X_LUCID_TYPE.search(content)
    file_val = m_file.group(1).strip() if m_file else ""
    path_val = m_path.group(1).strip() if m_path else ""
    dir_val = m_dir.group(1).strip() if m_dir else ""
    type_val = m_type.group(1).strip() if m_type else ""
    return file_val, path_val, dir_val, type_val


def format_listing_block(
    file_val: str,
    path_val: str,
    dir_val: str = "",
    type_val: str = "",
) -> str:
    block = (
        '"""\n'
        f"File: {file_val}\n"
        f"x-lucid-file-path: {path_val}\n"
    )
    if dir_val.strip():
        block += f"x-lucid-file-directory: {dir_val}\n"
    if type_val.strip():
        block += f"x-lucid-file-type: {type_val}\n"
    block += '"""\n'
    return block


def write_x_files_listing(
    repo: Path | None = None,
    output: Path | None = None,
    overrides: dict[str, str] | None = None,
) -> Path:
    """
    Scan all ``*.py`` files under the repo, ``*.sh`` under ``scripts/``, ``tests/``,
    ``ops/``, and ``*.yml`` / ``*.yaml`` (whole repo); write ``x-files-listing.txt``
    with one triple-quoted block per file.
    """
    root = (repo or REPO).resolve()
    out_path = output or (root / "x-files-listing.txt")
    lines: list[str] = []
    header = (
        "# Auto-generated by _normalise_lucid_headers.py --x-files-listing\n"
        f"# Repo: {root}\n"
        "# One block per .py file (whole repo), .sh under scripts/, tests/, ops/, and\n"
        "# .yml/.yaml (whole repo). Values from each file or inferred (shell/YAML).\n"
        "#\n"
        "# Host registry (repo: infrastructure/containers/host-config.yml). @ = that repo path.\n"
        "# /app/host/@infrastructure/containers/host-config.yml  and  /app/configs/@infrastructure/containers/host-config.yml\n"
        "# are equivalent to /app/configs/host-config.yml (same file; canonical runtime path).\n\n"
    )
    lines.append(header)

    for py_path in iter_repo_py_files(root):
        try:
            raw = py_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        raw = raw.replace("\r\n", "\n")
        fv, pv, dv, tv = extract_lucid_metadata(raw)
        if not pv.strip():
            pv, _d = resolve_lucid_app_path_with_overrides(py_path, root, overrides)
            if not fv.strip():
                fv = pv
            if not dv.strip():
                dv = _d
        rel = py_path.relative_to(root).as_posix()
        lines.append(f"# --- {rel} ---\n")
        lines.append(format_listing_block(fv, pv, dv, tv))
        lines.append("\n")

    for sh_path, canonical in iter_repo_sh_files(root):
        try:
            raw = sh_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        raw = raw.replace("\r\n", "\n")
        fv, pv, dv, tv = extract_lucid_metadata_shell(raw)
        if not fv.strip():
            fv = canonical
        if not pv.strip():
            pv = canonical
        if not dv.strip():
            dv = str(Path(canonical).parent.as_posix())
        if not tv.strip():
            tv = "shell"
        rel = sh_path.relative_to(root).as_posix()
        lines.append(f"# --- {rel} ---\n")
        lines.append(format_listing_block(fv, pv, dv, tv))
        lines.append("\n")

    for yaml_path in iter_repo_yaml_files(root):
        try:
            raw = yaml_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        raw = raw.replace("\r\n", "\n")
        fv, pv, dv, tv = extract_lucid_metadata_shell(raw)
        canonical, can_dir = resolve_lucid_app_path(yaml_path, root, overrides)
        if not fv.strip():
            fv = canonical
        if not pv.strip():
            pv = canonical
        if not dv.strip():
            dv = can_dir
        if not tv.strip():
            tv = "YAML"
        rel = yaml_path.relative_to(root).as_posix()
        lines.append(f"# --- {rel} ---\n")
        lines.append(format_listing_block(fv, pv, dv, tv))
        lines.append("\n")

    out_path.write_text("".join(lines), encoding="utf-8", newline="\n")
    return out_path


def find_first_triple_quoted(s: str):
    start = s.find('"""')
    if start == -1:
        return None
    j = start + 3
    while True:
        end = s.find('"""', j)
        if end == -1:
            return None
        if end > 0 and s[end - 1] == "\\":
            j = end + 3
            continue
        return (start, end + 3)


def pos_after_leading_comments(s: str) -> int:
    pos = 0
    while pos < len(s):
        nl = s.find("\n", pos)
        if nl == -1:
            line = s[pos:]
            next_pos = len(s)
        else:
            line = s[pos:nl]
            next_pos = nl + 1
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            pos = next_pos
            continue
        break
    return pos


def find_module_docstring_span(s: str) -> tuple[int, int] | None:
    pos = pos_after_leading_comments(s)
    rest = s[pos:]
    if not rest.lstrip().startswith('"""'):
        return None
    indent = len(rest) - len(rest.lstrip())
    abs_start = pos + indent
    sub = s[abs_start:]
    span = find_first_triple_quoted(sub)
    if span is None:
        return None
    return (abs_start, abs_start + span[1])


def strip_lucid_lines_from_inner(inner: str) -> str:
    lines = []
    for line in inner.split("\n"):
        s = line.strip()
        if re.match(r"^File:\s*", s, re.I):
            continue
        if re.match(r"^x-lucid-file-path:\s*", s):
            continue
        if re.match(r"^x-lucid-file-directory:\s*", s):
            continue
        if re.match(r"^x-lucid-file-type:\s*", s):
            continue
        if re.match(r"^required:\s*x-lucid-file-path:\s*", s):
            continue
        if re.match(r"^file:\s*", s, re.I):
            continue
        lines.append(line)
    out = "\n".join(lines)
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.strip()


def build_docstring(app_path: str, description: str, app_directory: str) -> str:
    meta = (
        '"""\n'
        f"File: {app_path}\n"
        f"x-lucid-file-path: {app_path}\n"
        f"x-lucid-file-directory: {app_directory}\n"
        "x-lucid-file-type: python"
    )
    if description.strip():
        return meta + "\n\n" + description.strip() + '\n"""'
    return meta + '\n"""'


def _strip_suffix_metadata_for_prefix(s: str, app_root_prefix: str) -> str:
    esc = re.escape(app_root_prefix)
    patterns = [
        re.compile(
            rf"^\s*File:\s*{esc}/[^\s]+\s*\n\s*x-lucid-file-path:\s*{esc}/[^\s]+\s*\n\s*x-lucid-file-directory:\s*{esc}\s*\n\s*x-lucid-file-type:\s*python\s*$",
            re.MULTILINE,
        ),
        re.compile(
            rf"^\s*File:\s*{esc}/[^\s]+\s*\n\s*x-lucid-file-path:\s*{esc}/[^\s]+\s*\n\s*x-lucid-file-type:\s*python\s*$",
            re.MULTILINE,
        ),
        re.compile(
            rf"^\s*required:\s*x-lucid-file-path:\s*{esc}/[^\s]+\s*\n\s*x-lucid-file-type:\s*python\s*$",
            re.MULTILINE,
        ),
        re.compile(
            rf"^\s*x-lucid-file-path:\s*{esc}/[^\s]+\s*\n\s*x-lucid-file-type:\s*python\s*$",
            re.MULTILINE,
        ),
    ]
    prev = None
    while prev != s:
        prev = s
        for p in patterns:
            s = p.sub("", s)
    return s


def strip_suffix_metadata(
    s: str,
    app_root_prefix: str,
    extra_prefixes: list[str] | None = None,
) -> str:
    """Remove duplicate trailing Lucid header blocks; try legacy /app paths too."""
    out = s
    for pref in [app_root_prefix, *(extra_prefixes or [])]:
        out = _strip_suffix_metadata_for_prefix(out, pref)
    return out


def process_file(path: Path, repo: Path, overrides: dict[str, str] | None = None) -> bool:
    rel_repo = path.resolve().relative_to(repo.resolve()).as_posix()
    app_path, doc_directory = resolve_lucid_app_path_with_overrides(path, repo, overrides)
    legacy_prefixes = legacy_header_strip_prefixes(rel_repo)

    raw = path.read_text(encoding="utf-8")
    bom = ""
    if raw.startswith("\ufeff"):
        bom = "\ufeff"
        raw = raw[1:]
    s = raw.replace("\r\n", "\n")

    shebang = ""
    rest = s
    if s.startswith("#!"):
        nl = s.find("\n")
        if nl != -1:
            shebang = s[: nl + 1]
            rest = s[nl + 1:]

    mod_span = find_module_docstring_span(rest)
    if mod_span:
        inner = rest[mod_span[0] + 3 : mod_span[1] - 3]
        desc = strip_lucid_lines_from_inner(inner)
        new_doc = build_docstring(app_path, desc, doc_directory)
        suffix = rest[mod_span[1] :]
        rest = (
            rest[: mod_span[0]]
            + new_doc
            + strip_suffix_metadata(suffix, doc_directory, legacy_prefixes)
        )
    else:
        insert_at = pos_after_leading_comments(rest)
        new_doc = build_docstring(app_path, "", doc_directory)
        suffix = rest[insert_at:]
        rest = (
            rest[:insert_at]
            + new_doc
            + "\n\n"
            + strip_suffix_metadata(suffix, doc_directory, legacy_prefixes)
        )

    rest2 = STRAY_STAR.sub("", rest)
    new_full = bom + shebang + rest2
    if new_full == bom + s:
        return False
    path.write_text(new_full, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> None:
    import argparse
    import sys

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Normalise Lucid module docstrings or emit x-files-listing.txt.",
    )
    parser.add_argument(
        "--x-files-listing",
        action="store_true",
        help="Scan *.py, *.sh (scripts/, tests/, ops/), *.yml/*.yaml; write x-files-listing.txt.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for --x-files-listing (default: ./x-files-listing.txt).",
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
    parser.add_argument(
        "roots",
        nargs="*",
        help="Optional ROOT directory names (see ROOTS), e.g. gui_tor_manager",
    )
    ns, unknown = parser.parse_known_args(argv)
    if unknown:
        print("Unknown arguments:", " ".join(unknown), file=sys.stderr)
        sys.exit(2)

    source_listing = ns.x_files_listing_source
    if not source_listing.is_absolute():
        source_listing = (REPO / source_listing).resolve()
    overrides = load_listing_path_overrides(source_listing)

    if ns.x_files_listing:
        out = write_x_files_listing(repo=REPO, output=ns.output, overrides=overrides)
        npy = len(iter_repo_py_files(REPO))
        nsh = len(iter_repo_sh_files(REPO))
        nyml = len(iter_repo_yaml_files(REPO))
        print(f"Wrote {out} ({npy} .py + {nsh} .sh + {nyml} .yml/.yaml scanned)")
        return

    roots_to_use: list[tuple[Path, str]] = ROOTS
    if ns.roots:
        wanted = set(ns.roots)
        roots_to_use = [(p, pref) for p, pref in ROOTS if p.name in wanted]
        found = {p.name for p, _ in roots_to_use}
        missing = wanted - found
        if missing:
            print("Unknown directory names (not in ROOTS):", ", ".join(sorted(missing)))
    n = 0
    skipped: list[str] = []
    for root_dir, _ in roots_to_use:
        if not root_dir.is_dir():
            skipped.append(str(root_dir))
            continue
        for p in sorted(root_dir.rglob("*.py")):
            if process_file(p, REPO, overrides=overrides):
                n += 1
    print(f"Updated {n} files")
    if skipped:
        print("Missing (skipped):", ", ".join(skipped))


if __name__ == "__main__":
    main()

"""
Normalise module docstrings to:

    File: /app/<tree>/...
    x-lucid-file-path: /app/<tree>/...
    x-lucid-file-directory: /app/<tree>
    x-lucid-file-type: python

Run from repo root:  .venv\\Scripts\\python.exe _normalise_lucid_headers.py
Optional: one or more ROOT directory names, e.g.  .venv\\Scripts\\python.exe _normalise_lucid_headers.py gui_tor_manager

Write ``x-files-listing.txt`` (all ``*.py`` under the repo, ``File:`` + ``x-lucid-file-path:`` extracted)::

    .venv\\Scripts\\python.exe _normalise_lucid_headers.py --x-files-listing

Add more trees: append (REPO / "dirname", "/app/dirname") to ROOTS below
(e.g. ``(REPO / "infrastructure" / "service_mesh", "/app/service_mesh")``).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent

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
    (REPO / "infrastructure" / "service_mesh", "/app/service_mesh"),
]

STRAY_STAR = re.compile(
    r"^\s*required:\s*x-lucid-file-path:\s*/app/\*\s*"
    r"\n\s*x-lucid-file-type:\s*python\s*$",
    re.MULTILINE,
)

RE_FILE_HEADER = re.compile(r"^\s*File:\s*(.+?)\s*$", re.MULTILINE)
RE_X_LUCID_PATH = re.compile(r"^\s*x-lucid-file-path:\s*(.+?)\s*$", re.MULTILINE)
RE_X_LUCID_DIR = re.compile(r"^\s*x-lucid-file-directory:\s*(.+?)\s*$", re.MULTILINE)
RE_X_LUCID_TYPE = re.compile(r"^\s*x-lucid-file-type:\s*(.+?)\s*$", re.MULTILINE)

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
) -> Path:
    """
    Scan all ``*.py`` files under the repo and write ``x-files-listing.txt`` with one
    triple-quoted block per file (``File:`` / ``x-lucid-file-path:`` / optional
    ``x-lucid-file-directory`` / ``x-lucid-file-type`` as found, possibly empty).
    """
    root = (repo or REPO).resolve()
    out_path = output or (root / "x-files-listing.txt")
    lines: list[str] = []
    header = (
        "# Auto-generated by _normalise_lucid_headers.py --x-files-listing\n"
        f"# Repo: {root}\n"
        "# One block per .py file; values are the first matching line in each file.\n"
        "#\n"
        "# Host registry (repo: infrastructure/containers/host-config.yml). @ = that repo path.\n"
        "# /app/host/@infrastructure/containers/host-config.yml  and  /app/configs/@infrastructure/containers/host-config.yml\n"
        "# are equivalent to /app/service_configs/host-config.yml (same file; canonical runtime path).\n\n"
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
        rel = py_path.relative_to(root).as_posix()
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


def strip_suffix_metadata(s: str, app_root_prefix: str) -> str:
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


def process_file(path: Path, app_root_prefix: str, root_dir: Path) -> bool:
    rel = path.relative_to(root_dir)
    app_path = app_root_prefix + "/" + rel.as_posix()

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
        new_doc = build_docstring(app_path, desc, app_root_prefix)
        suffix = rest[mod_span[1] :]
        rest = rest[: mod_span[0]] + new_doc + strip_suffix_metadata(suffix, app_root_prefix)
    else:
        insert_at = pos_after_leading_comments(rest)
        new_doc = build_docstring(app_path, "", app_root_prefix)
        suffix = rest[insert_at:]
        rest = rest[:insert_at] + new_doc + "\n\n" + strip_suffix_metadata(suffix, app_root_prefix)

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
        help="Scan all *.py under the repo and write x-files-listing.txt (no normalisation).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for --x-files-listing (default: ./x-files-listing.txt).",
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

    if ns.x_files_listing:
        out = write_x_files_listing(repo=REPO, output=ns.output)
        print(f"Wrote {out} ({len(iter_repo_py_files(REPO))} .py files scanned)")
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
    for root_dir, prefix in roots_to_use:
        if not root_dir.is_dir():
            skipped.append(str(root_dir))
            continue
        for p in sorted(root_dir.rglob("*.py")):
            if process_file(p, prefix, root_dir):
                n += 1
    print(f"Updated {n} files")
    if skipped:
        print("Missing (skipped):", ", ".join(skipped))


if __name__ == "__main__":
    main()

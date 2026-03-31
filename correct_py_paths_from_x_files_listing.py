"""
Correct paths and service hostnames in Lucid ``*.py`` files.

Repository path: ``correct_py_paths_from_x_files_listing.py`` (run from repository root).

Uses ``x-files-listing.txt`` as the **only** source for which ``/app/...`` file paths and
directory prefixes are accepted. Documented ``/app/...`` paths in the listing header comments
are included in that allowlist. Invalid quoted literals are replaced only when the replacement
is a path that appears in that allowlist: exact repo-relative match after ``/app/``, or a
unique suffix match among listed paths; basename-only disambiguation applies to ``*.py`` only
(so runtime paths like ``/app/service_configs/*.yml`` are not guessed from filename alone).

``service_name`` / Docker DNS hostnames are aligned with
``infrastructure/containers/host-config.yml`` (tags and labels → canonical ``service_name``).
``infrastructure/containers/services/container-runtime-layout.yml`` is loaded for policy
metadata (e.g. ``lucid_services_config_root``); runtime layout defers DNS names to the same
host registry.

Run from repo root (default is dry-run; do not pass ``--dry-run`` with ``--apply``)::

    python correct_py_paths_from_x_files_listing.py
    python correct_py_paths_from_x_files_listing.py --dry-run
    python correct_py_paths_from_x_files_listing.py --apply
    python correct_py_paths_from_x_files_listing.py --apply --no-headers

``--no-headers`` skips rewriting module docstrings (only quoted ``/app/...`` literals, HTTP
hosts, and ``SERVICE_NAME`` assignments are updated).

Requires PyYAML for host-config parsing (``pip install pyyaml``).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import _normalise_lucid_headers as _nlh

REPO = Path(__file__).resolve().parent

LISTING_NAME = "x-files-listing.txt"
HOST_CONFIG = REPO / "infrastructure" / "containers" / "host-config.yml"
CONFIG_LISTINGS = REPO / "infrastructure" / "containers" / "config-listings.json"
RUNTIME_LAYOUT = (
    REPO / "infrastructure" / "containers" / "services" / "container-runtime-layout.yml"
)

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

REL_HEADER = re.compile(r"^# --- (.+) ---\s*$")
RE_FILE_LINE = re.compile(r"^\s*File:\s*(.*?)\s*$")
RE_XPATH_LINE = re.compile(r"^\s*x-lucid-file-path:\s*(.*?)\s*$")
RE_XDIR_LINE = re.compile(r"^\s*x-lucid-file-directory:\s*(.*?)\s*$")
RE_XTYPE_LINE = re.compile(r"^\s*x-lucid-file-type:\s*(.*?)\s*$")
# /app/... inside listing comment lines (header documentation)
RE_COMMENT_APP_PATH = re.compile(r"(/app/[A-Za-z0-9_./@-]+)")
# Quoted /app/... string literals in Python source
RE_APP_STRING = re.compile(r"(['\"])(/app/[^'\"\\]+)\1")
# http(s)://hostname:port
RE_HTTP_HOST = re.compile(
    r"(https?://)([a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9])(:\d+)([^\s'\"]*)"
)


def _should_skip_py_path(path: Path, repo: Path) -> bool:
    try:
        rel = path.relative_to(repo)
    except ValueError:
        return True
    return any(part in SKIP_PATH_PARTS for part in rel.parts)


def iter_repo_py_files(repo: Path) -> list[Path]:
    out: list[Path] = []
    for p in repo.rglob("*.py"):
        if _should_skip_py_path(p, repo):
            continue
        out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def parse_listing_header_comment_paths(text: str, max_lines: int = 24) -> set[str]:
    paths: set[str] = set()
    for i, line in enumerate(text.splitlines()):
        if i >= max_lines:
            break
        if not line.lstrip().startswith("#"):
            continue
        for m in RE_COMMENT_APP_PATH.finditer(line):
            p = m.group(1).rstrip(").,;")
            if "/@" in p:
                p = p.split("/@")[0]
            paths.add(p)
    return paths


def parse_x_files_listing(
    listing_path: Path,
) -> tuple[dict[str, str], set[str], set[str]]:
    """
    Returns:
        rel_posix -> canonical /app/... path (non-empty blocks only)
        valid_paths: every /app file path from File: / x-lucid-file-path + header comments
        valid_dirs: every directory prefix of each valid file path
    """
    raw = listing_path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    raw = raw.replace("\r\n", "\n")

    rel_to_canonical: dict[str, str] = {}
    valid_paths: set[str] = set(parse_listing_header_comment_paths(raw))

    lines = raw.split("\n")
    i = 0
    current_rel = ""
    while i < len(lines):
        m = REL_HEADER.match(lines[i])
        if m:
            current_rel = m.group(1).strip().replace("\\", "/")
            i += 1
            chunk: list[str] = []
            while i < len(lines) and not REL_HEADER.match(lines[i]):
                chunk.append(lines[i])
                i += 1
            block = "\n".join(chunk)
            fv = pv = dv = tv = ""
            for bl in block.splitlines():
                mf = RE_FILE_LINE.match(bl)
                mx = RE_XPATH_LINE.match(bl)
                md = RE_XDIR_LINE.match(bl)
                mt = RE_XTYPE_LINE.match(bl)
                if mf:
                    fv = mf.group(1).strip()
                if mx:
                    pv = mx.group(1).strip()
                if md:
                    dv = md.group(1).strip()
                if mt:
                    tv = mt.group(1).strip()
            canonical = pv or fv
            if canonical:
                rel_to_canonical[current_rel] = canonical
                valid_paths.add(canonical)
            if fv:
                valid_paths.add(fv)
            if pv:
                valid_paths.add(pv)
            continue
        i += 1

    valid_dirs: set[str] = set()
    for p in valid_paths:
        if not p.startswith("/app/"):
            continue
        parts = p.strip("/").split("/")
        for n in range(1, len(parts)):
            valid_dirs.add("/" + "/".join(parts[:n]))

    return rel_to_canonical, valid_paths, valid_dirs


def listing_blocks_as_dicts(listing_path: Path) -> list[dict[str, str | None]]:
    """
    One record per ``# --- section ---`` block in x-files-listing.txt (for JSON export / tooling).
    """
    raw = listing_path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    raw = raw.replace("\r\n", "\n")
    lines = raw.split("\n")
    out: list[dict[str, str | None]] = []
    i = 0
    while i < len(lines):
        m = REL_HEADER.match(lines[i])
        if m:
            section = m.group(1).strip().replace("\\", "/")
            i += 1
            chunk: list[str] = []
            while i < len(lines) and not REL_HEADER.match(lines[i]):
                chunk.append(lines[i])
                i += 1
            block = "\n".join(chunk)
            fv = pv = dv = tv = ""
            for bl in block.splitlines():
                mf = RE_FILE_LINE.match(bl)
                mx = RE_XPATH_LINE.match(bl)
                md = RE_XDIR_LINE.match(bl)
                mt = RE_XTYPE_LINE.match(bl)
                if mf:
                    fv = mf.group(1).strip()
                if mx:
                    pv = mx.group(1).strip()
                if md:
                    dv = md.group(1).strip()
                if mt:
                    tv = mt.group(1).strip()
            canonical = pv or fv or ""
            out.append(
                {
                    "section": section,
                    "file": fv or None,
                    "x_lucid_file_path": pv or None,
                    "x_lucid_file_directory": dv or None,
                    "x_lucid_file_type": tv or None,
                    "canonical_path": canonical or None,
                }
            )
            continue
        i += 1
    return out


def _is_valid_app_path(
    path: str, valid_paths: set[str], valid_dirs: set[str]
) -> bool:
    p = path.rstrip("/")
    if p in valid_paths:
        return True
    if p in valid_dirs:
        return True
    if any(f.startswith(p + "/") for f in valid_paths):
        return True
    return False


def _resolve_app_path_literal(
    path: str,
    rel_to_canonical: dict[str, str],
    valid_paths: set[str],
) -> str | None:
    if path in valid_paths:
        return None
    if not path.startswith("/app/"):
        return None
    rel = path[len("/app/") :].lstrip("/")
    if rel in rel_to_canonical:
        c = rel_to_canonical[rel]
        if c != path:
            return c
        return None
    # Fuzzy matching only for Python modules: avoids remapping e.g. /app/service_configs/*.yml
    # (runtime layout) to a repo-mirror path that happens to appear in the listing.
    if not path.endswith(".py"):
        return None
    suffix = "/" + rel if rel else ""
    candidates = [f for f in valid_paths if f.endswith(suffix) or f == path]
    if len(candidates) == 1:
        return candidates[0]
    base = rel.split("/")[-1] if rel else ""
    if base:
        by_base = [f for f in valid_paths if f.endswith("/" + base)]
        if len(by_base) == 1:
            return by_base[0]
    return None


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "PyYAML is required to parse host-config / runtime layout. "
            "Install with: pip install pyyaml"
        ) from e
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_service_alias_map(host_config_path: Path) -> tuple[dict[str, str], set[str]]:
    """
    Map lowercase alias -> canonical service_name from host-config.yml.
    Aliases: service_name, each tag, com.lucid.service label.
    """
    data = load_yaml(host_config_path)
    services = data.get("services") or {}
    alias_to_canonical: dict[str, str] = {}
    canonicals: set[str] = set()

    for _key, block in services.items():
        if not isinstance(block, dict):
            continue
        sn = block.get("service_name")
        if not sn or not isinstance(sn, str):
            continue
        canonical = sn.strip()
        canonicals.add(canonical)
        c_low = canonical.lower()
        alias_to_canonical[c_low] = canonical
        tags = block.get("tags") or []
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str) and t.strip():
                    alias_to_canonical.setdefault(t.strip().lower(), canonical)
        labels = block.get("labels") or {}
        if isinstance(labels, dict):
            cs = labels.get("com.lucid.service")
            if isinstance(cs, str) and cs.strip():
                alias_to_canonical.setdefault(cs.strip().lower(), canonical)

    return alias_to_canonical, canonicals


def _port_from_service_block(block: dict) -> int | None:
    """Best-effort canonical service port from host-config service block."""
    for key in ("port", "service_port", "container_port", "expose"):
        v = block.get(key)
        if isinstance(v, int) and v > 0:
            return v
        if isinstance(v, str) and v.isdigit():
            p = int(v)
            if p > 0:
                return p
    labels = block.get("labels") or {}
    if isinstance(labels, dict):
        ev = labels.get("com.lucid.expose")
        if isinstance(ev, int) and ev > 0:
            return ev
        if isinstance(ev, str) and ev.isdigit():
            p = int(ev)
            if p > 0:
                return p
    return None


def build_service_authority_from_host_config(
    host_config_path: Path,
) -> tuple[dict[str, str], dict[str, int]]:
    """
    Build alias->canonical and canonical->port maps from host-config.yml.
    """
    data = load_yaml(host_config_path)
    services = data.get("services") or {}
    alias_to_canonical: dict[str, str] = {}
    canonical_to_port: dict[str, int] = {}

    for _key, block in services.items():
        if not isinstance(block, dict):
            continue
        sn = block.get("service_name")
        if not isinstance(sn, str) or not sn.strip():
            continue
        canonical = sn.strip()
        alias_to_canonical[canonical.lower()] = canonical
        p = _port_from_service_block(block)
        if p is not None:
            canonical_to_port[canonical] = p

        tags = block.get("tags") or []
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str) and t.strip():
                    alias_to_canonical.setdefault(t.strip().lower(), canonical)
        labels = block.get("labels") or {}
        if isinstance(labels, dict):
            cs = labels.get("com.lucid.service")
            if isinstance(cs, str) and cs.strip():
                alias_to_canonical.setdefault(cs.strip().lower(), canonical)
    return alias_to_canonical, canonical_to_port


def build_service_authority_from_config_listings(
    config_listings_path: Path,
) -> tuple[dict[str, str], dict[str, int]]:
    """
    Build alias->canonical and canonical->port maps from config-listings.json.
    """
    import json

    data = json.loads(config_listings_path.read_text(encoding="utf-8"))
    services = data.get("services") or {}
    alias_to_canonical: dict[str, str] = {}
    canonical_to_port: dict[str, int] = {}
    for _stable_id, block in services.items():
        if not isinstance(block, dict):
            continue
        sn = block.get("service_name")
        if not isinstance(sn, str) or not sn.strip():
            continue
        canonical = sn.strip()
        alias_to_canonical[canonical.lower()] = canonical
        port = block.get("port")
        if isinstance(port, int) and port > 0:
            canonical_to_port[canonical] = port
        elif isinstance(port, str) and port.isdigit():
            p = int(port)
            if p > 0:
                canonical_to_port[canonical] = p
        tags = block.get("tags_from_ports_txt") or []
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str) and t.strip():
                    alias_to_canonical.setdefault(t.strip().lower(), canonical)
        labels = block.get("host_config_labels") or {}
        if isinstance(labels, dict):
            cs = labels.get("com.lucid.service")
            if isinstance(cs, str) and cs.strip():
                alias_to_canonical.setdefault(cs.strip().lower(), canonical)
    return alias_to_canonical, canonical_to_port


def load_runtime_layout_roots(layout_path: Path) -> dict[str, str]:
    """Structured fields from container-runtime-layout.yml (policy / paths, not path allowlist)."""
    if not layout_path.is_file():
        return {}
    data = load_yaml(layout_path)
    out: dict[str, str] = {}
    root = data.get("lucid_services_config_root")
    if isinstance(root, str):
        out["lucid_services_config_root"] = root
    return out


def fix_lucid_header_block(
    content: str,
    rel_posix: str,
    rel_to_canonical: dict[str, str],
) -> tuple[str, bool]:
    """
    Sync Lucid header lines to the canonical ``/app/...`` path from ``x-files-listing.txt``,
    preserving the rest of the module docstring (same approach as ``_normalise_lucid_headers``).
    """
    canonical = rel_to_canonical.get(rel_posix)
    if not canonical:
        return content, False
    app_directory = str(Path(canonical).parent.as_posix())
    if app_directory == ".":
        app_directory = "/app"

    shebang = ""
    rest = content
    if content.startswith("#!"):
        nl = content.find("\n")
        if nl != -1:
            shebang = content[: nl + 1]
            rest = content[nl + 1 :]

    mod_span = _nlh.find_module_docstring_span(rest)
    if mod_span:
        inner = rest[mod_span[0] + 3 : mod_span[1] - 3]
        desc = _nlh.strip_lucid_lines_from_inner(inner)
        new_doc = _nlh.build_docstring(canonical, desc, app_directory)
        suffix = _nlh.strip_suffix_metadata(rest[mod_span[1] :], "/app")
        new_rest = rest[: mod_span[0]] + new_doc + suffix
    else:
        insert_at = _nlh.pos_after_leading_comments(rest)
        new_doc = _nlh.build_docstring(canonical, "", app_directory)
        suffix = _nlh.strip_suffix_metadata(rest[insert_at:], "/app")
        new_rest = rest[:insert_at] + new_doc + "\n\n" + suffix

    new_full = shebang + new_rest
    if new_full == content:
        return content, False
    return new_full, True


def replace_app_string_literals(
    content: str,
    rel_to_canonical: dict[str, str],
    valid_paths: set[str],
    valid_dirs: set[str],
) -> tuple[str, list[tuple[str, str]]]:
    changes: list[tuple[str, str]] = []

    def repl(m: re.Match[str]) -> str:
        q, p = m.group(1), m.group(2)
        if _is_valid_app_path(p, valid_paths, valid_dirs):
            return m.group(0)
        new_p = _resolve_app_path_literal(p, rel_to_canonical, valid_paths)
        if new_p and new_p != p:
            changes.append((p, new_p))
            return f"{q}{new_p}{q}"
        return m.group(0)

    new_content = RE_APP_STRING.sub(repl, content)
    return new_content, changes


def replace_http_hosts(
    content: str,
    alias_to_canonical: dict[str, str],
    canonical_to_port: dict[str, int] | None = None,
    enforce_authority_port: bool = False,
) -> tuple[str, list[tuple[str, str]]]:
    changes: list[tuple[str, str]] = []

    def repl(m: re.Match[str]) -> str:
        scheme, host, port, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        low = host.lower()
        canon = alias_to_canonical.get(low, host)
        out_port = port
        if enforce_authority_port and canonical_to_port:
            p = canonical_to_port.get(canon)
            if p is not None:
                out_port = f":{p}"
        if canon == host and out_port == port:
            return m.group(0)
        changes.append((f"{scheme}{host}{port}", f"{scheme}{canon}{out_port}"))
        return f"{scheme}{canon}{out_port}{tail}"

    new_content = RE_HTTP_HOST.sub(repl, content)
    return new_content, changes


def replace_service_name_assignments(
    content: str, alias_to_canonical: dict[str, str]
) -> tuple[str, list[tuple[str, str]]]:
    """
    SERVICE_NAME = "..." / : str = "..." style defaults that match a known alias.
    """
    changes: list[tuple[str, str]] = []
    # Match quoted string after SERVICE_NAME optional type and =
    pat = re.compile(
        r'(\bSERVICE_NAME\b\s*(?::\s*str\s*)?=\s*)(["\'])([^"\']+)(\2)',
        re.MULTILINE,
    )

    def repl(m: re.Match[str]) -> str:
        prefix, q, val, q2 = m.group(1), m.group(2), m.group(3), m.group(4)
        low = val.lower()
        if low not in alias_to_canonical:
            return m.group(0)
        canon = alias_to_canonical[low]
        if canon == val:
            return m.group(0)
        changes.append((val, canon))
        return f"{prefix}{q}{canon}{q2}"

    return pat.sub(repl, content), changes


def process_file(
    py_path: Path,
    repo: Path,
    rel_to_canonical: dict[str, str],
    valid_paths: set[str],
    valid_dirs: set[str],
    alias_to_canonical: dict[str, str],
    canonical_to_port: dict[str, int],
    apply: bool,
    fix_headers: bool = True,
    enforce_authority_port: bool = False,
) -> dict[str, object]:
    rel = py_path.relative_to(repo).as_posix()
    raw = py_path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    raw = raw.replace("\r\n", "\n")

    report: dict[str, object] = {
        "path": rel,
        "header": False,
        "paths": [],
        "http": [],
        "service_name": [],
        "modified": False,
    }

    new = raw
    if fix_headers:
        new, he
#!/usr/bin/env python3
"""Shared Dockerfile metadata alignment helpers for Lucid."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DockerfileAlignmentCriteria:
    source_dockerfile: str
    service_name: str
    com_lucid_service_id: str
    onion_lucid_service_id: str
    org_lucid_service_id: str


def normalize_repo_rel(path_like: str) -> str:
    return path_like.replace("\\", "/").strip().lstrip("./")


def load_alignment_criteria(config_path: Path) -> dict[str, DockerfileAlignmentCriteria]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    services = raw.get("services", {})
    out: dict[str, DockerfileAlignmentCriteria] = {}
    for service in services.values():
        if not isinstance(service, dict):
            continue
        src = service.get("source_dockerfile")
        name = service.get("service_name")
        ids = service.get("service_ids")
        if not isinstance(src, str) or not isinstance(name, str) or not isinstance(ids, dict):
            continue
        com_id = ids.get("com_lucid_service_id")
        onion_id = ids.get("onion_lucid_service_id")
        org_id = ids.get("org_lucid_service_id")
        if not isinstance(com_id, str) or not isinstance(onion_id, str) or not isinstance(org_id, str):
            continue
        rel = normalize_repo_rel(src)
        out[rel] = DockerfileAlignmentCriteria(
            source_dockerfile=rel,
            service_name=name,
            com_lucid_service_id=com_id,
            onion_lucid_service_id=onion_id,
            org_lucid_service_id=org_id,
        )
    return out


def _replace_or_append_label_block(label_block: str, key: str, value: str) -> str:
    escaped = re.escape(key)
    pat = re.compile(rf'({escaped}\s*=\s*")([^"]*)(")')
    if pat.search(label_block):
        return pat.sub(rf'\1{value}\3', label_block)
    suffix = " \\\n"
    if label_block.rstrip().endswith("\\"):
        return f'{label_block.rstrip()}\n      {key}="{value}"{suffix}'
    return f'{label_block.rstrip()} \\\n      {key}="{value}"{suffix}'


def align_dockerfile_text(
    dockerfile_text: str, criteria: DockerfileAlignmentCriteria
) -> tuple[str, bool]:
    # Update the last LABEL block in the file (runtime stage metadata).
    matches = list(re.finditer(r"(?ms)^\s*LABEL\s+.*?(?=^\s*[A-Z][A-Z0-9_]*\b|\Z)", dockerfile_text))
    if not matches:
        return dockerfile_text, False
    m = matches[-1]
    block = m.group(0)
    updated = block
    updated = _replace_or_append_label_block(updated, "com.lucid.service", criteria.service_name)
    updated = _replace_or_append_label_block(
        updated, "com.lucid.service_id", criteria.com_lucid_service_id
    )
    updated = _replace_or_append_label_block(
        updated, "onion.lucid.service_id", criteria.onion_lucid_service_id
    )
    updated = _replace_or_append_label_block(
        updated, "org.lucid.service_id", criteria.org_lucid_service_id
    )
    if updated == block:
        return dockerfile_text, False
    return dockerfile_text[: m.start()] + updated + dockerfile_text[m.end() :], True


def validate_alignment(dockerfile_text: str, criteria: DockerfileAlignmentCriteria) -> list[str]:
    problems: list[str] = []
    checks = {
        "com.lucid.service": criteria.service_name,
        "com.lucid.service_id": criteria.com_lucid_service_id,
        "onion.lucid.service_id": criteria.onion_lucid_service_id,
        "org.lucid.service_id": criteria.org_lucid_service_id,
    }
    for key, expected in checks.items():
        if f'{key}="{expected}"' not in dockerfile_text:
            problems.append(f"{key} mismatch or missing")
    return problems


def discover_repo_root(script_file: Path) -> Path:
    """
    Locate the Lucid repo root from any script path under the tree.

    ``parent.parent.parent`` only works when the tool lives in
    ``<root>/infrastructure/containers/``. Copies (e.g. under ``/app/configs/``) or alternate checkouts
    need a walk: first directory containing ``infrastructure/containers`` plus a root marker
    (``Dockerfile-layout.txt`` or ``x-files-listing.txt``), else the path above ``infrastructure/containers``.
    """
    sf = script_file.resolve()
    start = sf.parent
    for p in [start, *start.parents]:
        ic = p / "infrastructure" / "containers"
        if not ic.is_dir():
            continue
        if (p / "Dockerfile-layout.txt").is_file() or (p / "x-files-listing.txt").is_file():
            return p
    parts = sf.parts
    try:
        idx = parts.index("containers")
        if idx >= 1 and parts[idx - 1] == "infrastructure":
            return Path(*parts[: idx - 1])
    except ValueError:
        pass
    legacy = sf.parent.parent.parent
    if (legacy / "infrastructure" / "containers").is_dir():
        return legacy
    return legacy


_LUCID_DOCKERFILE_NAME_RE = re.compile(r"^[Dd]ockerfile(?:\..+)?$")


def dockerfile_name_looks_like_backup_or_temp(name: str) -> bool:
    """Skip editor/backup artifacts that still match ``Dockerfile*`` globs (``rglob``)."""
    n = name.lower()
    if n.endswith("~"):
        return True
    for marker in (".bak", ".orig", ".tmp", ".temp", ".swp", ".layout.bak"):
        if marker in n:
            return True
    return False


def is_processable_lucid_dockerfile(path: Path) -> bool:
    """
    True for a regular file the Lucid tooling should edit: ``Dockerfile`` or ``Dockerfile.<tag>`` /
    ``dockerfile.<tag>``, not ``__pycache__``, dotfiles, or common backup names.
    """
    if not path.is_file():
        return False
    if path.name.startswith("."):
        return False
    if "__pycache__" in path.parts:
        return False
    if dockerfile_name_looks_like_backup_or_temp(path.name):
        return False
    return bool(_LUCID_DOCKERFILE_NAME_RE.fullmatch(path.name))


def discover_lucid_dockerfiles_under(root: Path) -> list[Path]:
    """
    All ``Dockerfile`` / ``Dockerfile.*`` / ``dockerfile.*`` under ``root`` (recursive).

    Uses two ``rglob`` patterns so lowercase ``dockerfile`` names are found on case-sensitive
    filesystems. Dedupes by ``resolve()``; skips backup/temp filenames and ``__pycache__``.
    """
    out: list[Path] = []
    seen: set[Path] = set()
    try:
        walk_root = root.resolve(strict=False)
    except OSError:
        walk_root = root
    if not walk_root.is_dir():
        return out
    for pattern in ("Dockerfile*", "dockerfile*"):
        for p in walk_root.rglob(pattern):
            if not is_processable_lucid_dockerfile(p):
                continue
            try:
                key = p.resolve(strict=False)
            except OSError:
                key = p
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def discover_lucid_dockerfiles_under_roots(roots: list[Path]) -> list[Path]:
    """Merge :func:`discover_lucid_dockerfiles_under` for each existing directory; dedupe; sort."""
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in discover_lucid_dockerfiles_under(root):
            try:
                key = p.resolve(strict=False)
            except OSError:
                key = p
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def read_dockerfile_text(path: Path) -> str:
    """Read Dockerfile bytes as UTF-8; invalid sequences do not abort the tool."""
    return path.read_text(encoding="utf-8", errors="replace")

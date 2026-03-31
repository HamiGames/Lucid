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

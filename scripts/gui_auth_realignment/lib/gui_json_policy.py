"""FORBIDDEN / REQUIRED key policy for Tier A GUI JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set


def load_policy(repo: Path) -> Dict[str, Any]:
    p = repo / "scripts" / "gui_auth_realignment" / "gui_json_policy.json"
    return json.loads(p.read_text(encoding="utf-8"))


def validate_manifest(doc: Dict[str, Any], policy: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    forbidden: Set[str] = set(policy.get("forbidden_keys") or [])
    for k in doc:
        ku = k.upper()
        for f in forbidden:
            if f.upper() in ku or ku == f.upper():
                issues.append(f"forbidden key pattern: {k}")
    required = list(policy.get("required_non_secret_fields") or [])
    for r in required:
        if r not in doc:
            issues.append(f"missing required field: {r}")
    return issues

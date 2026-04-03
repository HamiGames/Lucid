#!/usr/bin/env python3
"""T2: scan Tier A alignment drift → .cache/issues.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root, scripts_dir
from lib.mat import load_gui_mat, mat_services
from lib.gui_json_policy import load_policy, validate_manifest

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


def _compose_env_file_refs(repo: Path, rel_path: str) -> list:
    path = repo / rel_path
    if not path.is_file() or yaml is None:
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    services = (data or {}).get("services") or {}
    out = []
    mat_names = {r.get("compose_service") for r in mat_services(load_gui_mat(repo))}
    for name, block in services.items():
        if name not in mat_names:
            continue
        if not isinstance(block, dict):
            continue
        ef = block.get("env_file")
        if ef:
            out.append((name, ef))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    p.add_argument("--fail-on-issues", action="store_true")
    args = p.parse_args()
    repo = resolve_repo_root(args)
    base = scripts_dir(repo)
    cache = base / ".cache"
    cache.mkdir(parents=True, exist_ok=True)

    issues = []
    policy = load_policy(repo)
    targets = json.loads((base / "tier_a_json_targets.json").read_text(encoding="utf-8")).get("targets") or {}

    for row in mat_services(load_gui_mat(repo)):
        cs = row.get("compose_service")
        for rel in targets.get(cs, []):
            path = repo / rel
            if not path.is_file():
                issues.append({"rule_id": "ALLOWLIST_ONLY_JSON", "severity": "error", "path": str(path), "detail": "missing json manifest"})
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            for msg in validate_manifest(doc, policy):
                issues.append({"rule_id": "REQUIRED_JSON_FIELDS", "severity": "error", "path": str(path), "detail": msg})

    compose_rel = Path("configs") / "docker" / "docker-compose.gui-integration.yml"
    for name, ef in _compose_env_file_refs(repo, str(compose_rel)):
        issues.append(
            {
                "rule_id": "NO_DOTENV_MAT",
                "severity": "error",
                "path": str(repo / compose_rel),
                "detail": f"service {name} still declares env_file {ef}",
            }
        )

    (cache / "issues.json").write_text(json.dumps({"issues": issues}, indent=2), encoding="utf-8")
    if args.fail_on_issues and issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

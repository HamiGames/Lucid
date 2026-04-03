#!/usr/bin/env python3
"""T3: build proposed_alignment.json (compose edits + json confirmation)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root, scripts_dir


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    args = p.parse_args()
    repo = resolve_repo_root(args)
    base = scripts_dir(repo)
    cache = base / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    issues_path = cache / "issues.json"
    issues = []
    if issues_path.is_file():
        issues = json.loads(issues_path.read_text(encoding="utf-8")).get("issues") or []

    proposal = {
        "schema_version": 1,
        "generated_from": str(issues_path),
        "note": "Initial proposal: strip mat env_file from docker-compose.gui-integration.yml; JSON manifests in configs/gui-alignment",
        "compose_files": [
            {
                "path": "configs/docker/docker-compose.gui-integration.yml",
                "ops": [{"op": "strip_env_file_mat_services", "mat_source": "configs/alignment-mats/gui-services.json"}],
            }
        ],
        "json_files": [],
    }
    targets = json.loads((base / "tier_a_json_targets.json").read_text(encoding="utf-8")).get("targets") or {}
    for rel_list in targets.values():
        for rel in rel_list:
            fp = repo / rel
            if fp.is_file():
                proposal["json_files"].append({"path": rel, "full_body": json.loads(fp.read_text(encoding="utf-8"))})

    (cache / "proposed_alignment.json").write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return 0 if not issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

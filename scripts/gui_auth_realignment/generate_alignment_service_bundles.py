#!/usr/bin/env python3
"""
File: scripts/gui_auth_realignment/generate_alignment_service_bundles.py

Create missing infrastructure/containers/services/<compose_service>.yml bundle files using
data from configs/alignment-mats/<compose_service>_manifest.json (same compose_service key).

Run from repo root:
  python scripts/gui_auth_realignment/generate_alignment_service_bundles.py
  python scripts/gui_auth_realignment/generate_alignment_service_bundles.py --update-master-endpoint
  python scripts/gui_auth_realignment/generate_alignment_service_bundles.py --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parents[1]
MAT_DIR = REPO / "configs" / "alignment-mats"
SERVICES_DIR = REPO / "infrastructure" / "containers" / "services"
MASTER_ENDPOINT = SERVICES_DIR / "master-endpoint.yml"
PREFIX = "infrastructure/containers/services/"

LUCID_AUTH_CANONICAL = {
    "repo_path": "infrastructure/containers/services/auth-service.yml",
    "container_path": "/app/service_configs/auth-service.yml",
    "note": (
        "Full runtime configuration lives in auth-service.yml; this file satisfies "
        "the conventional compose_service path lucid-auth-service."
    ),
}


def render_bundle(compose_service: str, data: dict) -> str:
    needles = data.get("associated_needles") or []
    yml_refs = data.get("yml") or []
    json_refs = data.get("json") or []
    py_refs = data.get("py") or []

    lines: list[str] = []
    cs = compose_service
    lines.append(f"# File: /app/service_configs/{cs}.yml")
    lines.append(f"# x-lucid-file-path: /app/service_configs/{cs}.yml")
    lines.append("# x-lucid-file-directory: /app/service_configs")
    lines.append("# x-lucid-file-type: YAML")
    lines.append(
        "# Lucid alignment: host_registry=infrastructure/containers/host-config.yml "
        "(container /app/configs/host-config.yml); path_index=x-files.json section_to_canonical"
    )
    lines.append("#")
    lines.append(
        f"# compose_service={cs}; YAML/JSON/Python lists from alignment manifest "
        f"(list_service_files_by_name.py)."
    )
    lines.append("")
    lines.append("version: '1.0'")
    lines.append("description: >")
    lines.append(f"  Conventional service bundle index for {cs}. Refs below mirror the alignment")
    lines.append(
        "  manifest for this compose service. Cross-check infrastructure/containers/host-config.yml and x-files.json."
    )
    lines.append("")
    lines.append("x-lucid-calibration:")
    lines.append("  source_host_config: infrastructure/containers/host-config.yml")
    lines.append("  source_x_files: x-files.json")
    lines.append(f"  bundle_repo_path: infrastructure/containers/services/{cs}.yml")
    lines.append(f"  bundle_container_path: /app/service_configs/{cs}.yml")
    lines.append("  alignment_manifest_tool: scripts/gui_auth_realignment/list_service_files_by_name.py")
    lines.append("")
    lines.append(f'compose_service: "{cs}"')
    lines.append("associated_needles:")
    for n in needles:
        lines.append(f'  - "{n}"')
    if cs == "lucid-auth-service":
        lines.append("")
        lines.append("canonical_config_bundle:")
        lines.append(f'  repo_path: {LUCID_AUTH_CANONICAL["repo_path"]}')
        lines.append(f'  container_path: {LUCID_AUTH_CANONICAL["container_path"]}')
        lines.append(f'  note: "{LUCID_AUTH_CANONICAL["note"]}"')
    lines.append("")
    lines.append("manifest_alignment:")
    lines.append("  yml_refs:")
    for p in yml_refs:
        lines.append(f"    - {json.dumps(p)}")
    lines.append("  json_refs:")
    for p in json_refs:
        lines.append(f"    - {json.dumps(p)}")
    lines.append("  py_refs:")
    for p in py_refs:
        lines.append(f"    - {json.dumps(p)}")
    lines.append("")
    return "\n".join(lines)


def update_master_endpoint(candidate_relpaths: list[str]) -> int:
    text = MASTER_ENDPOINT.read_text(encoding="utf-8")
    existing = set(
        re.findall(r"path: (infrastructure/containers/services/[^\s]+\.yml)", text)
    )
    blocks: list[str] = []
    for rel in sorted(set(candidate_relpaths)):
        if rel in existing:
            continue
        bn = rel.split("/")[-1].replace(".yml", "")
        container_path = f"/app/service_configs/{bn}.yml"
        scope = f"{bn.replace('-', ' ')} bundle"
        blocks.append(
            f"  - path: {rel}\n"
            f"    container_path: {container_path}\n"
            f"    scope: {scope}"
        )
    if not blocks:
        return 0
    insert = "\n".join(blocks) + "\n"
    anchor = "common_http:\n"
    if anchor not in text:
        raise SystemExit(f"Anchor {anchor!r} not found in master-endpoint.yml")
    text = text.replace(anchor, insert + anchor, 1)
    MASTER_ENDPOINT.write_text(text, encoding="utf-8")
    return len(blocks)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate alignment service bundle YAML files.")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing bundle files from manifests",
    )
    ap.add_argument(
        "--update-master-endpoint",
        action="store_true",
        help="Append missing entries to meta.endpoint_source_files in master-endpoint.yml",
    )
    args = ap.parse_args()

    written_paths: list[str] = []
    for mf in sorted(MAT_DIR.glob("*_manifest.json")):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"skip unreadable {mf}: {exc}", file=sys.stderr)
            continue
        cs = data.get("compose_service")
        if not cs or not isinstance(cs, str):
            continue
        out_path = SERVICES_DIR / f"{cs}.yml"
        if out_path.is_file() and not args.force:
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_bundle(cs, data), encoding="utf-8")
        written_paths.append(f"{PREFIX}{cs}.yml")

    print(f"Wrote {len(written_paths)} bundle file(s)")
    for r in sorted(written_paths):
        print(f"  {r}")

    if args.update_master_endpoint:
        register: list[str] = []
        for mf in sorted(MAT_DIR.glob("*_manifest.json")):
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            cs = data.get("compose_service")
            if not cs or not isinstance(cs, str):
                continue
            rel = f"{PREFIX}{cs}.yml"
            if (SERVICES_DIR / f"{cs}.yml").is_file():
                register.append(rel)
        n = update_master_endpoint(register)
        print(f"master-endpoint.yml: inserted {n} endpoint_source_files block(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

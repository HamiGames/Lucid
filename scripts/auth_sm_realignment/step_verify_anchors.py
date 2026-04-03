#!/usr/bin/env python3
"""
File: c:\\Users\\surba\\Desktop\\personal\\THE_FUCKER\\lucid_2\\Lucid\\scripts\\auth_sm_realignment\\step_verify_anchors.py
Read-only: lucid_auth_service + lucid_server_manager ports vs host-config and ports.txt.
Exit: 0 ok, 2 anchor failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.anchors import load_host_config, ports_txt_has_port, service_port


def main() -> int:
    p = argparse.ArgumentParser(description="Verify host-config + ports.txt for auth and SM.")
    p.add_argument("--repo-root", type=Path, required=True)
    args = p.parse_args()
    repo = args.repo_root.resolve()

    try:
        hc = load_host_config(repo)
    except Exception as e:
        print(f"anchor error: host-config: {e}", file=sys.stderr)
        return 2

    auth_id = "lucid_auth_service"
    sm_id = "lucid_server_manager"
    ap = service_port(hc, auth_id)
    sp = service_port(hc, sm_id)
    if ap is None:
        print(f"anchor error: missing service {auth_id} port in host-config.yml", file=sys.stderr)
        return 2
    if sp is None:
        print(f"anchor error: missing service {sm_id} port in host-config.yml", file=sys.stderr)
        return 2
    if not ports_txt_has_port(repo, ap):
        print(f"anchor error: port {ap} ({auth_id}) not found in ports.txt", file=sys.stderr)
        return 2
    if not ports_txt_has_port(repo, sp):
        print(f"anchor error: port {sp} ({sm_id}) not found in ports.txt", file=sys.stderr)
        return 2

    print(f"anchors ok: {auth_id}={ap}, {sm_id}={sp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
File: c:\\Users\\surba\\Desktop\\personal\\THE_FUCKER\\lucid_2\\Lucid\\scripts\\auth_sm_realignment\\step_codegen_contracts.py
Emit JSON contract stubs under scripts/auth_sm_realignment/.cache/ (local only; do not edit .gitignore).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CONTRACTS = {
    "ClientMetadataPackage": {
        "description": "Tier A client metadata forwarded to auth (non-secret): machine_id, location, etc.",
        "example": {"machine_id": "string", "location": "string|unknown"},
    },
    "sm_preauth_issue_response": {
        "pre_auth_token": "string",
        "expires_in": 600,
    },
    "sm_verify_preauth_request": {
        "pre_auth_token": "string",
        "intent": "login|register",
        "user_id": "optional for login binding",
    },
    "sm_verify_preauth_response": {"ok": True, "claims": {"binding": "opaque"}},
    "sm_registry_users_request": {
        "user_id": "string",
        "registration_key": "string",
        "pre_auth_token": "optional",
    },
    "sm_registry_users_response": {"ok": True},
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    cache = args.repo_root.resolve() / "scripts" / "auth_sm_realignment" / ".cache"
    if args.dry_run:
        print("dry-run: would write", cache / "contracts.json")
        return 0
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / "contracts.json"
    out.write_text(json.dumps(CONTRACTS, indent=2), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

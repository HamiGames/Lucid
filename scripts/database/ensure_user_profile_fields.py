#!/usr/bin/env python3
# Path: scripts/database/ensure_user_profile_fields.py
"""
File: /app/scripts/database/ensure_user_profile_fields.py
x-lucid-file-path: /app/scripts/database/ensure_user_profile_fields.py
x-lucid-file-directory: /app/scripts/database
x-lucid-file-type: python

Ensure MongoDB `users` documents have Lucid contact-profile / env-scope fields.

Aligns with: common/contact_profile_env.py, database/models/user.py, common/profile_secrets_registry.yml

Does not store passwords. Sets:
  - contact_profile_key (null until you set e.g. admin / node_operator)
  - profile.metadata.contact_profile_key
  - profile.lucid_env.node_operational_config_path
  - profile.lucid_env.variable_groups (booleans by subsystem)

Usage:
  export MONGODB_URL='mongodb://lucid:PASS@localhost:27017/lucid?authSource=admin'
  python scripts/database/ensure_user_profile_fields.py

  # Or pass URI:
  python scripts/database/ensure_user_profile_fields.py --uri 'mongodb://...'
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Repo root: scripts/database/ensure_user_profile_fields.py -> parents[2]
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

DEFAULT_LUCID_ENV: Dict[str, Any] = {
    "node_operational_config_path": "/app/config/operational-config.json",
    "variable_groups": {
        "mongodb": True,
        "redis": True,
        "elasticsearch": True,
        "tor": True,
        "tron": False,
        "blockchain": False,
        "payment": False,
        "rdp": False,
        "session": False,
        "api_gateway": True,
        "signing": False,
    },
}


def _deep_merge_missing(existing: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    base = dict(existing) if isinstance(existing, dict) else {}
    for k, dv in defaults.items():
        if k not in base:
            base[k] = dv
        elif isinstance(dv, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge_missing(base[k], dv)
    return base


def ensure_fields(db: Any, collection_name: str = "users") -> int:
    coll = db[collection_name]
    count = 0
    for doc in coll.find({}):
        profile: Dict[str, Any] = dict(doc.get("profile") or {})
        meta: Dict[str, Any] = dict(profile.get("metadata") or {})
        if "contact_profile_key" not in meta:
            meta["contact_profile_key"] = None
        profile["metadata"] = meta
        profile["lucid_env"] = _deep_merge_missing(
            dict(profile.get("lucid_env") or {}),
            DEFAULT_LUCID_ENV,
        )

        update: Dict[str, Any] = {"profile": profile}
        if "contact_profile_key" not in doc:
            update["contact_profile_key"] = None

        coll.update_one({"_id": doc["_id"]}, {"$set": update})
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure user profile fields for Lucid env overlays.")
    parser.add_argument(
        "--uri",
        default=os.environ.get("MONGODB_URL", "").strip()
        or os.environ.get("MONGODB_URI", "").strip(),
        help="MongoDB URI (default: MONGODB_URL or MONGODB_URI)",
    )
    parser.add_argument("--db", default="lucid", help="Database name (default: lucid)")
    parser.add_argument("--collection", default="users", help="Collection name (default: users)")
    args = parser.parse_args()

    if not args.uri:
        print(
            "Set MONGODB_URL or pass --uri. "
            "Alternatively run: mongosh lucid < scripts/database/ensure_user_profile_fields.js",
            file=sys.stderr,
        )
        return 1

    try:
        from pymongo import MongoClient  # type: ignore
    except ImportError:
        print("Install pymongo: pip install pymongo", file=sys.stderr)
        return 1

    client = MongoClient(args.uri, serverSelectionTimeoutMS=10_000)
    db = client[args.db]
    n = ensure_fields(db, args.collection)
    print(f"Processed documents: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

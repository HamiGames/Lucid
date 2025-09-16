# Path: tests/conftest.py
# Purpose: Make repo packages importable during pytest runs from project root.
# - Adds repo root for "blockchain"
# - Adds 03-api-gateway for "api.app.*"
# - Adds 03-api-gateway/api for "app.*"
# No pytest hooks are defined (avoids plugin validation errors).

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRA_PATHS = [
    ROOT,  # enables "blockchain"
    ROOT / "03-api-gateway",  # enables "api.app.*"
    ROOT / "03-api-gateway" / "api",  # enables "app.*"
]

for p in EXTRA_PATHS:
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

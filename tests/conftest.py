"""
Pytest configuration for Lucid RDP tests.

Ensures the repo root and key submodules are on sys.path,
and registers pytest plugins/marks for async tests.
"""

import sys
from pathlib import Path
import pytest


def _add_path(path: Path):
    abs_path = str(path.resolve())
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)


# 1. Repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
_add_path(REPO_ROOT)

# 2. Add API Gateway path (handle "03-api-gateway")
API_GATEWAY = REPO_ROOT / "03-api-gateway" / "api"
if API_GATEWAY.exists():
    _add_path(API_GATEWAY)

# 3. Add other top-level packages
for subdir in ["blockchain", "wallet", "governance", "client", "db", "utils"]:
    pkg = REPO_ROOT / subdir
    if pkg.exists():
        _add_path(pkg)


# --- Pytest Config Hooks ---

def pytest_configure(config):
    """
    Register custom marks so pytest doesn't warn about them.
    """
    config.addinivalue_line(
        "markers", "asyncio: mark test as async and run with pytest-asyncio"
    )

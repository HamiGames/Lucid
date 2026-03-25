"""
Distroless build verification: /app/node/* tree and openssl-api support files exist.
Invoked during image build (see Dockerfile.admin-system-gateway) then removed from the image.
"""
from __future__ import annotations

import os
import sys

# Mirrors scaffold created in the builder stage and copied to runtime /app/node
NODE_DIRS = [
    "/app/node/config",
    "/app/node/cache",
    "/app/node/data",
    "/app/node/logs",
    "/app/node/runtime",
    "/app/node/tmp",
]

SUPPORT_FILES = [
    "/app/node/config/openssl-api.yml",
    "/app/node/config/connections.json",
]

# Aligned with 03_api_gateway verify_runtime: wheels + var markers present
EXTRA_DIRS = [
    "/app/wheels",
    "/app/var/run",
    "/app/var/lib",
    "/app/etc/ssl/certs",
]


def main() -> None:
    for d in NODE_DIRS + EXTRA_DIRS:
        if not os.path.isdir(d):
            print(f"ERROR: directory missing: {d}", file=sys.stderr)
            sys.exit(1)
        if not os.listdir(d):
            print(f"ERROR: directory empty: {d}", file=sys.stderr)
            sys.exit(1)

    for f in SUPPORT_FILES:
        if not os.path.isfile(f):
            print(f"ERROR: file missing: {f}", file=sys.stderr)
            sys.exit(1)
        if os.path.getsize(f) < 4:
            print(f"ERROR: file too small: {f}", file=sys.stderr)
            sys.exit(1)

    sp = "/app/usr/local/lib/python3.11/site-packages"
    if not os.path.isdir(sp):
        print(f"ERROR: site-packages missing: {sp}", file=sys.stderr)
        sys.exit(1)

    try:
        import yaml  # noqa: F401
    except ImportError:
        print("ERROR: PyYAML not importable at runtime", file=sys.stderr)
        sys.exit(1)

    print("✅ admin-system-gateway runtime verified (/app/node/*, openssl-api, PyYAML)")


if __name__ == "__main__":
    main()

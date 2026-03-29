"""
File: /app/service_mesh/verify_runtime.py
x-lucid-file-path: /app/service_mesh/verify_runtime.py
x-lucid-file-directory: /app/service_mesh
x-lucid-file-type: python

Distroless runtime layout for Dockerfile.service-mesh-controller (host-config.yml registry in /app/configs).
"""
import os
import sys

# Paths that must exist and be non-empty after COPY --from=builder (service-mesh-controller image)
DIRS = [
    "/app/configs",
    "/app/service_mesh",
    "/app/usr/local/lib/python3.11/site-packages",
    "/app/wheels",
    "/app/api",
    "/app/common",
    "/app/core",
    "/app/utils",
]

ENTRYPOINT = "/app/service_mesh/entrypoint.py"


def main() -> None:
    for d in DIRS:
        if not os.path.isdir(d):
            print(f"ERROR: {d} missing", file=sys.stderr)
            sys.exit(1)
        if not os.listdir(d):
            print(f"ERROR: {d} empty", file=sys.stderr)
            sys.exit(1)
    if not os.path.isfile(ENTRYPOINT):
        print(f"ERROR: {ENTRYPOINT} missing", file=sys.stderr)
        sys.exit(1)
    hc = "/app/configs/host-config.yml"
    if not os.path.isfile(hc):
        print(f"ERROR: {hc} missing", file=sys.stderr)
        sys.exit(1)
    print("✅ service-mesh-controller runtime layout OK")


if __name__ == "__main__":
    main()

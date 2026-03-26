"""Distroless runtime layout: directories from 03_api_gateway/verify_runtime.py plus service-mesh paths."""
import os
import sys

dirs = [
    "/app/api/app",
    "/app/config",
    "/app/utils",
    "/app/api",
    "/app/usr",
    "/app/etc",
    "/app/var",
    "/app/tmp",
    "/app/wheels",
    "/app/services",
    "/app/database",
    "/app/models",
    "/app/endpoints",
    "/app/api/app/middleware",
    "/app/api/app/utils",
    "/app/api/app/schemas",
    "/app/api/app/models",
    "/app/api/app/services",
    "/app/api/app/db",
    "/app/api/app/db/models",
    "/app/api/app/routers",
    "/app/api/app/routes",
    "/app/controller",
    "/app/sidecar",
    "/app/discovery",
    "/app/communication",
    "/app/security",
    "/app/configs",
    "/app/configs/container",
    "/app/usr/local/lib/python3.11/site-packages",
    "/app/infrastructure/service_mesh",
]

for d in dirs:
    if not os.path.isdir(d):
        print(f"ERROR: {d} missing")
        sys.exit(1)
    if not os.listdir(d):
        print(f"ERROR: {d} empty")
        sys.exit(1)

if not os.path.isfile("/app/entrypoint.py"):
    print("ERROR: /app/entrypoint.py missing")
    sys.exit(1)

print("✅ service mesh + API gateway runtime layout OK")

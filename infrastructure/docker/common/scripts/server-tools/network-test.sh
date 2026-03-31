#!/bin/bash
# Path: infrastructure/docker/common/scripts/server-tools/network-test.sh
set -euo pipefail

echo "[network-test] reachability"

targets=(
    "tor-proxy:9050"
    "lucid_mongo:27017"
    "lucid_api_gateway:8080"
    "lucid_api:8081"
    "lucid_tunnel_tools:7000"
)

for svc in "${targets[@]}"; do
    host="${svc%%:*}"
    port="${svc##*:}"
    if nc -z "$host" "$port" 2>/dev/null; then
        echo "$svc: ok"
    else
        echo "$svc: fail"
    fi
done

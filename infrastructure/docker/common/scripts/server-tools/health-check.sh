#!/bin/bash
# Path: infrastructure/docker/common/scripts/server-tools/health-check.sh
set -euo pipefail

readonly CURL_MAX_TIME=5

echo "[health-check] Lucid server-tools"

if curl -fsS --max-time "$CURL_MAX_TIME" --socks5 tor-proxy:9050 http://check.torproject.org >/dev/null 2>&1; then
    echo "Tor proxy: ok"
else
    echo "Tor proxy: fail"
fi

if mongosh --quiet --eval "db.runCommand({ ping: 1 })" "${MONGO_URL:-mongodb://localhost:27017}" >/dev/null 2>&1; then
    echo "MongoDB: ok"
else
    echo "MongoDB: fail"
fi

if curl -fsS --max-time "$CURL_MAX_TIME" "http://lucid_api_gateway:8080/health" >/dev/null 2>&1; then
    echo "API gateway: ok"
else
    echo "API gateway: fail"
fi

if curl -fsS --max-time "$CURL_MAX_TIME" "http://lucid_api:8081/health" >/dev/null 2>&1; then
    echo "API server: ok"
else
    echo "API server: fail"
fi

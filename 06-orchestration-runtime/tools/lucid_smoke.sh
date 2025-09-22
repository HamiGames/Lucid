#!/usr/bin/env bash
# lucid_smoke.sh — build, up, health, and OpenAPI smoke tests for Lucid
# LUCID-STRICT: NO terminal closing (no exit/return), tests never force-quit.

set +e

# ── Repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$REPO_ROOT" ] && cd "$REPO_ROOT"

# ── Paths
C="06-orchestration-runtime/compose/lucid-dev.yaml"
ENV_FILE="06-orchestration-runtime/compose/.env"
HALT=""

echo "==> PRECHECK"
[ -f "$C" ]        && echo "OK: $C"        || { echo "HALT — NEED: missing $C"; HALT=1; }
[ -f "$ENV_FILE" ] && echo "OK: $ENV_FILE" || { echo "HALT — NEED: missing $ENV_FILE"; HALT=1; }

# Env keys referenced by compose
if [ -z "$HALT" ]; then
  VARS=$(grep -oE '\$\{([A-Z0-9_]+)(:-[^}]*)?\}' "$C" | sed -E 's/^\$\{([A-Z0-9_]+).*/\1/' | sort -u)
  [ -n "$VARS" ] && echo "ENV_VARS_IN_COMPOSE: $VARS" || echo "ENV_VARS_IN_COMPOSE: none"
  MISS=""
  for v in $VARS; do grep -qE "^[[:space:]]*$v=" "$ENV_FILE" || MISS="$MISS $v"; done
  [ -z "$MISS" ] || { echo "HALT — NEED: missing keys in $ENV_FILE:$MISS"; HALT=1; }
fi

# Detect profiles (if any)
PF=()
if [ -z "$HALT" ]; then
  while IFS= read -r p; do [ -n "$p" ] && PF+=("--profile" "$p"); done < <(awk '
    /profiles:[[:space:]]*$/ {p=1; next}
    p && /^[[:space:]]*-[[:space:]]*[A-Za-z0-9_.-]+/ { gsub(/^[[:space:]]*-[[:space:]]*/, "", $0); print $0 }
    p && !/^[[:space:]]*-/ {p=0}
  ' "$C" | sort -u)
  [ ${#PF[@]} -gt 0 ] && echo "PROFILES: ${PF[*]//--profile /}" || echo "PROFILES: none"
fi

echo "==> COMPOSE RENDER"
if [ -z "$HALT" ]; then
  if docker compose "${PF[@]}" --env-file "$ENV_FILE" -f "$C" config >/tmp/lucid_render.yaml 2>/dev/null; then
    echo "COMPOSE_CONFIG_OK"
    if grep -q '\${' /tmp/lucid_render.yaml 2>/dev/null; then
      echo "HALT — NEED: unresolved \${VAR} after render"
      HALT=1
    else
      echo "RENDER_OK"
    fi
  else
    echo "HALT — NEED: compose config error"
    HALT=1
  fi
fi

echo "==> BUILD"
if [ -z "$HALT" ]; then
  if docker compose "${PF[@]}" --env-file "$ENV_FILE" -f "$C" build; then
    echo "BUILD_OK"
  else
    echo "HALT — NEED: build failed"
    HALT=1
  fi
fi

echo "==> UP"
SRV=""
if [ -z "$HALT" ]; then
  SRV=$(docker compose "${PF[@]}" -f "$C" config --services | xargs)
  if [ -z "$SRV" ]; then
    echo "HALT — NEED: no services resolved (check profiles/services in $C)"
    HALT=1
  else
    if docker compose "${PF[@]}" --env-file "$ENV_FILE" -f "$C" up -d $SRV; then
      echo "UP_OK"
    else
      echo "HALT — NEED: up failed"
      HALT=1
    fi
  fi
fi

echo "==> HEALTH (soft wait up to 120s)"
if [ -z "$HALT" ]; then
  deadline=$((SECONDS+120))
  while :; do
    states=$(docker compose -f "$C" ps --format '{{.Name}} {{.State}}')
    bad=$(printf "%s\n" "$states" | awk '$2 ~ /unhealthy|exited|dead/ {print $0}')
    [ -z "$bad" ] && break
    [ $SECONDS -ge $deadline ] && { echo "HALT — NEED: unhealthy/exited -> $bad"; break; }
    sleep 3
  done
  echo "HEALTH_SNAPSHOT:"
  docker compose -f "$C" ps
fi

echo "==> RUNTIME OPENAPI TESTS"
if [ -z "$HALT" ]; then
  for svc in $(docker compose -f "$C" config --services); do
    cid=$(docker compose -f "$C" ps -q "$svc")
    [ -n "$cid" ] || { echo "$svc: not running"; continue; }
    ports=$(docker inspect "$cid" --format '{{range $p,$v := .NetworkSettings.Ports}}{{if $v}}{{(index $v 0).HostPort}} {{end}}{{end}}' | xargs -r echo)
    [ -n "$ports" ] || { echo "$svc: no published ports"; continue; }
    for p in $ports; do
      code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$p/openapi.json" || true)
      if [ "$code" = "200" ]; then
        ver=$(curl -s "http://127.0.0.1:$p/openapi.json" | grep -oE '"openapi"\s*:\s*"[^"]+"' | head -n1)
        echo "$svc:$p /openapi.json -> 200 ${ver}"
      else
        echo "$svc:$p /openapi.json -> $code"
      fi
      code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$p/docs" || true)
      echo "$svc:$p /docs -> $code"
    done
  done
fi

[ -z "$HALT" ] && echo "DONE: build ✓ up ✓ health ✓ openapi/docs tests ✓" || echo "STOPPED: see HALT messages above"

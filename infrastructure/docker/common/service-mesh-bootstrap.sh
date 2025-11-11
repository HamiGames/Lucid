#!/bin/bash
# -----------------------------------------------------------------------------
# Lucid Service Mesh bootstrap helper
# Ensures the pickme/lucid-service-mesh:latest-arm64 container runs with the
# same runtime profile used by docker-compose on the Pi
# -----------------------------------------------------------------------------

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
LOG_DIR="/opt/lucid/logs"
LOG_FILE="${LOG_DIR}/service-mesh-bootstrap.log"

CONTAINER_NAME="lucid-service-mesh"
IMAGE_NAME="pickme/lucid-service-mesh:latest-arm64"
NETWORK_NAME="${LUCID_PI_NETWORK:-lucid-pi-network}"
RESERVED_IP="${SERVICE_MESH_CONTROLLER_HOST:-172.20.0.19}"
VOLUME_NAME="lucid-service-mesh-cache"

ROOT_CONFIG="/mnt/myssd/Lucid/Lucid"
ENV_FILES=(
  "${ROOT_CONFIG}/configs/environment/.env.foundation"
  "${ROOT_CONFIG}/configs/environment/.env.core"
  "${ROOT_CONFIG}/configs/environment/.env.secrets"
)

HOST_PORT_8500="${SERVICE_MESH_PORT:-8500}"
PORT_FLAGS=(
  "-p" "${HOST_PORT_8500}:8500"
  "-p" "8501:8501"
  "-p" "8502:8502"
  "-p" "8600:8600/udp"
  "-p" "8088:8088"
)

VOLUME_FLAGS=(
  "-v" "${ROOT_CONFIG}/logs/service-mesh:/app/logs:rw"
  "-v" "${ROOT_CONFIG}/data/service-mesh/config:/app/config:rw"
  "-v" "${VOLUME_NAME}:/tmp/mesh"
)

RUNTIME_FLAGS=(
  "--detach"
  "--restart" "unless-stopped"
  "--name" "${CONTAINER_NAME}"
  "--hostname" "${CONTAINER_NAME}"
  "--user" "65532:65532"
  "--security-opt" "no-new-privileges:true"
  "--security-opt" "seccomp=unconfined"
  "--cap-drop" "ALL"
  "--cap-add" "NET_BIND_SERVICE"
  "--read-only"
  "--tmpfs" "/tmp:noexec,nosuid,size=100m"
)

ENV_VARS_DEFAULT=(
  "LUCID_ENV=${LUCID_ENV:-production}"
  "LUCID_PLATFORM=${LUCID_PLATFORM:-arm64}"
  "SERVICE_MESH_HOST=${SERVICE_MESH_HOST:-${CONTAINER_NAME}}"
  "SERVICE_MESH_PORT=${SERVICE_MESH_PORT:-8500}"
  "SERVICE_MESH_URL=${SERVICE_MESH_URL:-http://lucid-service-mesh:8500}"
  "MONGODB_URL=${MONGODB_URL:-mongodb://lucid:${MONGODB_PASSWORD:-changeme}@lucid-mongodb:27017/lucid?authSource=admin}"
  "REDIS_URL=${REDIS_URL:-redis://lucid-redis:6379/0}"
)

ensure_log_dir() {
  mkdir -p "${LOG_DIR}"
  touch "${LOG_FILE}"
}

log() {
  local level="$1"; shift
  local message="$*"
  printf '[%s] %s: %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "${level}" "${message}" | tee -a "${LOG_FILE}"
}

require_cli() {
  if ! command -v docker >/dev/null 2>&1; then
    log "ERROR" "docker CLI not found; install Docker before continuing"
    exit 1
  fi
}

load_env_files() {
  for env_file in "${ENV_FILES[@]}"; do
    if [[ -f "${env_file}" ]]; then
      set -o allexport
      # shellcheck disable=SC1090
      source "${env_file}"
      set +o allexport
      log "INFO" "Loaded environment file: ${env_file}"
    fi
  done
}

ensure_network() {
  if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
    log "INFO" "Creating network ${NETWORK_NAME}"
    docker network create \
      --driver bridge \
      --subnet "${LUCID_PI_SUBNET:-172.20.0.0/16}" \
      --gateway "${LUCID_PI_GATEWAY:-172.20.0.1}" \
      "${NETWORK_NAME}"
  fi
}

ensure_volume() {
  if ! docker volume inspect "${VOLUME_NAME}" >/dev/null 2>&1; then
    log "INFO" "Creating volume ${VOLUME_NAME}"
    docker volume create --name "${VOLUME_NAME}" >/dev/null
  fi
}

pull_image() {
  log "INFO" "Pulling ${IMAGE_NAME}"
  docker pull "${IMAGE_NAME}"
}

start_container() {
  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log "WARN" "Container ${CONTAINER_NAME} already exists; stopping/removing before start"
    docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    docker rm "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  ensure_network
  ensure_volume
  pull_image

  local env_flags=()
  for kv in "${ENV_VARS_DEFAULT[@]}"; do
    env_flags+=("-e" "${kv}")
  done

  log "INFO" "Launching ${CONTAINER_NAME} on network ${NETWORK_NAME} (IP ${RESERVED_IP})"
  docker run \
    "${RUNTIME_FLAGS[@]}" \
    --network "${NETWORK_NAME}" \
    --ip "${RESERVED_IP}" \
    "${env_flags[@]}" \
    "${VOLUME_FLAGS[@]}" \
    "${PORT_FLAGS[@]}" \
    "${IMAGE_NAME}"

  log "INFO" "Container ${CONTAINER_NAME} started"
  docker ps --filter "name=${CONTAINER_NAME}"
}

stop_container() {
  if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log "INFO" "Stopping ${CONTAINER_NAME}"
    docker stop "${CONTAINER_NAME}"
  else
    log "WARN" "${CONTAINER_NAME} not running"
  fi

  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log "INFO" "Removing ${CONTAINER_NAME}"
    docker rm "${CONTAINER_NAME}"
  fi
}

show_status() {
  if ! docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log "INFO" "${CONTAINER_NAME} is not created"
    exit 0
  fi

  local state
  state="$(docker ps --filter "name=${CONTAINER_NAME}" --format '{{.Status}}')"
  if [[ -z "${state}" ]]; then
    log "INFO" "${CONTAINER_NAME} is stopped"
  else
    log "INFO" "${CONTAINER_NAME} status: ${state}"
  fi
}

tail_logs() {
  if ! docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log "ERROR" "${CONTAINER_NAME} does not exist"
    exit 1
  fi
  docker logs -f "${CONTAINER_NAME}"
}

exec_container() {
  if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log "ERROR" "${CONTAINER_NAME} is not running"
    exit 1
  fi
  docker exec -it "${CONTAINER_NAME}" "${@}"
}

show_help() {
  cat <<'EOF'
Usage: service-mesh-bootstrap.sh <command> [args]

Commands:
  start           Pull image, ensure network/volume, start container
  stop            Stop and remove the container
  status          Show current container status
  logs            Follow container logs
  exec <cmd...>   Run a command inside the running container
  pull            Pull the latest image
  help            Show this help message

Environment overrides:
  LUCID_ENV, LUCID_PLATFORM, SERVICE_MESH_HOST, SERVICE_MESH_PORT,
  SERVICE_MESH_URL, MONGODB_URL, REDIS_URL, LUCID_PI_NETWORK,
  SERVICE_MESH_CONTROLLER_HOST, LUCID_PI_SUBNET, LUCID_PI_GATEWAY
EOF
}

main() {
  ensure_log_dir
  require_cli
  load_env_files

  case "${1:-help}" in
    start) shift; start_container "$@";;
    stop) shift; stop_container "$@";;
    status) shift; show_status "$@";;
    logs) shift; tail_logs "$@";;
    exec) shift; exec_container "$@";;
    pull) shift; pull_image "$@";;
    help|-h|--help|"") show_help;;
    *) log "ERROR" "Unknown command: $1"; show_help; exit 1;;
  esac
}

main "$@"
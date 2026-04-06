#!/usr/bin/env bash
# Path: scripts/docker-smoke-test.sh
# Lucid Dockerfile / compose static smoke checks (no Docker required by default).
# Optional: --test-build / --test-compose when a working Docker daemon is available.
#
# Terminal DIR: run from repository root (Lucid/), e.g.:
#   bash scripts/docker-smoke-test.sh
#   bash scripts/docker-smoke-test.sh -v

# No -e: errexit is brittle here (CI redirects, optional tools); failures are tracked explicitly.
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_verbose() {
  [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${CYAN}[VERBOSE]${NC} $*"
}

VERBOSE=false
TEST_BUILD=false
TEST_COMPOSE=false
# COPY path checks against repo root are noisy (generated assets, optional trees); opt in with --strict-copy
STRICT_COPY=false
# Fail on bare ARG TARGETPLATFORM after defaulted ARG (plain docker build risk); opt in with --strict-platform
STRICT_PLATFORM=false
PASSED_TESTS=()
FAILED_TESTS=()
SKIPPED_TESTS=()

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Prefer cwd when it looks like the repo; else parent of scripts/
resolve_lucid_root() {
  if [[ -f "${PWD}/README.md" ]] && [[ -d "${PWD}/infrastructure" ]]; then
    printf '%s' "$(cd "${PWD}" && pwd)"
    return 0
  fi
  if [[ -f "${SCRIPT_PATH}/../README.md" ]] && [[ -d "${SCRIPT_PATH}/../infrastructure" ]]; then
    cd "${SCRIPT_PATH}/.." && pwd
    return 0
  fi
  return 1
}

show_help() {
  cat << 'EOF'
Lucid Docker smoke checks (static by default; Docker optional)

USAGE:
  bash scripts/docker-smoke-test.sh [OPTIONS]

OPTIONS:
  -v, --verbose       Verbose output
  -x, --strict-copy     Verify COPY sources exist under repo root (strict; many false positives)
  -p, --strict-platform  Flag bare ARG TARGETPLATFORM after defaulted ARG (plain docker build)
  -b, --test-build    Run docker build per Dockerfile (requires working Docker)
  -c, --test-compose  Run docker compose up tests (requires Docker + compose)
  -h, --help          This help

DEFAULT (no Docker):
  - Discover Dockerfiles (excluding .git, node_modules, __pycache__, .venv)
  - Optional: COPY sources vs repository root (off unless --strict-copy)
  - Basic ENV / WORKDIR heuristics
  - Detect bare "ARG TARGETPLATFORM" before "FROM --platform=$TARGETPLATFORM" (empty platform bug)
  - Validate compose YAML syntax when docker compose is available; otherwise skip

EXAMPLES:
  bash scripts/docker-smoke-test.sh
  bash scripts/docker-smoke-test.sh -v
  bash scripts/docker-smoke-test.sh -b
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      -v|--verbose) VERBOSE=true; shift ;;
      -x|--strict-copy) STRICT_COPY=true; shift ;;
      -p|--strict-platform) STRICT_PLATFORM=true; shift ;;
      -b|--test-build) TEST_BUILD=true; shift ;;
      -c|--test-compose) TEST_COMPOSE=true; shift ;;
      -h|--help) show_help; exit 0 ;;
      *) log_error "Unknown option: $1"; show_help; exit 1 ;;
    esac
  done
}

_have_docker_daemon() {
  command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

_have_compose_cli() {
  if docker compose version >/dev/null 2>&1; then
    return 0
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

_compose_config_check() {
  local file="$1"
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$file" config >/dev/null 2>&1
    return $?
  fi
  docker-compose -f "$file" config >/dev/null 2>&1
}

check_prerequisites() {
  if ! LUCID_ROOT="$(resolve_lucid_root)"; then
    log_error "Not in Lucid repo root (expected README.md + infrastructure/). CWD=${PWD}"
    exit 1
  fi
  export LUCID_ROOT
  log_info "Repository root: ${LUCID_ROOT}"

  if [[ "$TEST_BUILD" == true ]] || [[ "$TEST_COMPOSE" == true ]]; then
    if ! command -v docker >/dev/null 2>&1; then
      log_error "Docker CLI not found (required for --test-build / --test-compose)"
      exit 1
    fi
    if ! _have_docker_daemon; then
      log_error "Docker daemon not reachable (start Docker or drop -b / -c)"
      exit 1
    fi
    log_success "Docker daemon is available"
  fi

  if [[ "$TEST_COMPOSE" == true ]]; then
    if ! _have_compose_cli; then
      log_error "docker compose / docker-compose not available"
      exit 1
    fi
  fi
}

find_dockerfiles() {
  DOCKERFILES=()
  local f
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    DOCKERFILES+=("$f")
  done < <(
    # Portable prune (GNU/BSD): directory names, not -path (avoids MSYS find errors)
    find "$LUCID_ROOT" \
      \( -name .git -o -name node_modules -o -name __pycache__ -o -name .venv \) -prune \
      -o -type f \( \( -name 'Dockerfile' -o -name 'Dockerfile.*' -o -name 'Dockerfile-*' \) \
        ! -name '*.txt' ! -name '*.md' \) -print \
      2>/dev/null | LC_ALL=C sort
  )
  if [[ ${#DOCKERFILES[@]} -eq 0 ]]; then
    log_error "No Dockerfiles found under ${LUCID_ROOT}"
    exit 1
  fi
  log_info "Found ${#DOCKERFILES[@]} Dockerfiles"
}

# Strip inline # comments (naive; good enough for smoke checks)
_strip_docker_comment() {
  local line="$1"
  # Remove ' # ...' when # is preceded by space or start (avoid # in URLs minimally)
  if [[ "$line" =~ [[:space:]]# ]]; then
    line="${line%%[[:space:]]#*}"
  fi
  printf '%s' "$line"
}

validate_copy_paths() {
  local dockerfile="$1"
  local line stripped errors=0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line//$'\r'/}"
    stripped="$(_strip_docker_comment "$line")"
    [[ "$stripped" =~ ^[[:space:]]*COPY ]] || continue
    [[ "$stripped" =~ --from= ]] && continue
    [[ "$stripped" =~ ^[[:space:]]*COPY[[:space:]]+\[ ]] && continue

    local rest="${stripped#*COPY}"
    rest="${rest#"${rest%%[![:space:]]*}"}"
    local args=()
    local _guard=0
    while [[ -n "$rest" ]]; do
      _guard=$((_guard + 1))
      if [[ "$_guard" -gt 500 ]]; then
        log_error "${dockerfile}: COPY parse stuck (line too complex); simplify or fix script"
        return 1
      fi
      if [[ "$rest" =~ ^--[a-zA-Z0-9-]+ ]]; then
        local flag="${rest%% *}"
        rest="${rest#"$flag"}"
        rest="${rest#"${rest%%[![:space:]]*}"}"
        if [[ "$flag" == --from=* ]]; then
          args=()
          break
        fi
        continue
      fi
      if [[ "$rest" =~ ^\"([^\"]+)\" ]]; then
        args+=("${BASH_REMATCH[1]}")
        rest="${rest#\"${BASH_REMATCH[1]}\"}"
      elif [[ "$rest" =~ ^\'([^\']+)\' ]]; then
        args+=("${BASH_REMATCH[1]}")
        rest="${rest#\'${BASH_REMATCH[1]}\'}"
      elif [[ "$rest" =~ ^([^[:space:]]+) ]]; then
        args+=("${BASH_REMATCH[1]}")
        rest="${rest#${BASH_REMATCH[1]}}"
      else
        break
      fi
      rest="${rest#"${rest%%[![:space:]]*}"}"
    done
    [[ ${#args[@]} -lt 2 ]] && continue

    local dest="${args[-1]}"
    unset 'args[-1]'
    local src
    for src in "${args[@]}"; do
      [[ "$src" =~ \$ ]] && continue
      [[ "$src" == /* ]] && continue
      local full="${LUCID_ROOT}/${src}"
      if [[ ! -e "$full" ]]; then
        log_error "${dockerfile}: COPY source missing (context=${LUCID_ROOT}): ${src}"
        errors=$((errors + 1))
      fi
    done
  done < "$dockerfile"

  [[ "$errors" -eq 0 ]]
}

# Fast single-pass awk (avoids bash read on multi-hundred-line Dockerfiles × 200+ files)
validate_env_and_workdir_awk() {
  local dockerfile="$1"
  awk '
  function strip_comment(s) {
    sub(/[[:space:]]#.*/, "", s)
    return s
  }
  {
    line = strip_comment($0)
    sub(/^[[:space:]]+/, "", line)
    if (line ~ /^ENV[[:space:]]/) {
      rest = line
      sub(/^ENV[[:space:]]+/, "", rest)
      eq = index(rest, "=")
      if (eq > 0) {
        val = substr(rest, eq + 1)
        sub(/^[[:space:]]+/, "", val)
        sub(/[[:space:]]+$/, "", val)
        if (val == "") {
          key = substr(rest, 1, eq - 1)
          sub(/[[:space:]]+$/, "", key)
          printf "%s:%d: ENV '\''%s'\'' empty value\n", FILENAME, NR, key
          err = 1
        }
      }
    }
    if (line ~ /^WORKDIR[[:space:]]/) {
      wd = line
      sub(/^WORKDIR[[:space:]]+/, "", wd)
      sub(/[[:space:]]+$/, "", wd)
      if (wd == "") {
        printf "%s:%d: WORKDIR empty\n", FILENAME, NR
        err = 1
      } else if (wd ~ /[[:space:]]/) {
        printf "%s:%d: WORKDIR contains spaces: %s\n", FILENAME, NR, wd
        err = 1
      }
    }
  }
  END { exit (err ? 1 : 0) }
  ' "$dockerfile"
}

# Fail when a stage preamble ends with bare ARG TARGETPLATFORM (no =) then FROM --platform=$TARGETPLATFORM
# Global preamble (before the *first* FROM): fail if the first FROM uses
# --platform=$TARGETPLATFORM but no ARG TARGETPLATFORM=<non-empty default> appears
# anywhere in that preamble. A trailing bare ARG TARGETPLATFORM after a defaulted
# ARG TARGETPLATFORM=… is a common Lucid pattern (BuildKit / compose supply the
# value); plain docker build can still break — use --strict-platform to flag that.
validate_targetplatform_from_preamble() {
  local dockerfile="$1"
  local strict="${STRICT_PLATFORM:-false}"
  awk -v strict="$strict" '
  /^#/ { next }
  /^[[:space:]]*$/ { next }
  /^ARG[[:space:]]+TARGETPLATFORM=/ {
    if (!seen_first_from) {
      last_global_tp_bare = 0
      v = $0
      sub(/^ARG[[:space:]]+TARGETPLATFORM=/, "", v)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
      if (v != "") global_tp_default_nonempty = 1
    }
    next
  }
  /^ARG[[:space:]]+TARGETPLATFORM([[:space:]]|$)/ {
    if (!seen_first_from) { last_global_tp_bare = 1 }
    next
  }
  /^FROM[[:space:]]/ {
    if (!seen_first_from) {
      seen_first_from = 1
      uses_tp = ($0 ~ /platform=\$TARGETPLATFORM/ || $0 ~ /platform=\$\{TARGETPLATFORM\}/)
      if (uses_tp) {
        if (!global_tp_default_nonempty && last_global_tp_bare) {
          printf "%s:%d: first FROM uses --platform=$TARGETPLATFORM but global preamble has only bare ARG TARGETPLATFORM (no default)\n", FILENAME, NR
          exit 1
        }
        if (strict == "true" && last_global_tp_bare && global_tp_default_nonempty) {
          printf "%s:%d: strict-platform: bare ARG TARGETPLATFORM after ARG TARGETPLATFORM=… can empty plain docker build\n", FILENAME, NR
          exit 1
        }
      }
    }
    next
  }
  { next }
  ' "$dockerfile"
}

validate_dockerfile_static() {
  local dockerfile="$1"
  local name="${dockerfile#"${LUCID_ROOT}/"}"
  local ok=true

  [[ "$VERBOSE" == true ]] && log_info "Static check: ${name}"

  if ! validate_targetplatform_from_preamble "$dockerfile"; then
    ok=false
  fi
  if [[ "$STRICT_COPY" == true ]]; then
    if ! validate_copy_paths "$dockerfile"; then
      ok=false
    fi
  fi
  if ! validate_env_and_workdir_awk "$dockerfile"; then
    ok=false
  fi

  if [[ "$ok" == true ]]; then
    [[ "$VERBOSE" == true ]] && log_success "OK ${name}"
    return 0
  fi
  log_error "FAIL ${name}"
  return 1
}

test_docker_build() {
  local dockerfile="$1"
  local tag="lucid-smoke-$(basename "$dockerfile" | tr '[:upper:]' '[:lower:]' | tr './' '--')"
  log_verbose "docker build -f ${dockerfile#"${LUCID_ROOT}/"} -t ${tag} ${LUCID_ROOT}"
  if docker build -f "$dockerfile" -t "$tag" "$LUCID_ROOT" >/dev/null 2>&1; then
    docker rmi "$tag" >/dev/null 2>&1 || true
    return 0
  fi
  return 1
}

validate_dockerfile_with_optional_build() {
  local dockerfile="$1"
  local name="${dockerfile#"${LUCID_ROOT}/"}"

  if ! validate_dockerfile_static "$dockerfile"; then
    FAILED_TESTS+=("$name")
    return 1
  fi

  PASSED_TESTS+=("$name")

  if [[ "$TEST_BUILD" == true ]]; then
    log_info "Docker build: ${name}"
    if test_docker_build "$dockerfile"; then
      [[ "$VERBOSE" == true ]] && log_success "Build OK ${name}"
    else
      log_error "Build FAIL ${name}"
      FAILED_TESTS+=("${name} (build)")
      local i filtered=()
      for i in "${!PASSED_TESTS[@]}"; do
        [[ "${PASSED_TESTS[$i]}" != "$name" ]] && filtered+=("${PASSED_TESTS[$i]}")
      done
      PASSED_TESTS=("${filtered[@]}")
      return 1
    fi
  fi
  return 0
}

test_compose_files() {
  local compose_files=(
    "infrastructure/docker/compose/docker-compose.yml"
    "infrastructure/docker/compose/docker-compose.dev.yml"
    ".devcontainer/docker-compose.dev.yml"
    "configs/container/database/docker-compose.database-system.yml"
  )
  local cf path

  for cf in "${compose_files[@]}"; do
    path="${LUCID_ROOT}/${cf}"
    if [[ ! -f "$path" ]]; then
      log_warn "Compose file missing (skip): ${cf}"
      SKIPPED_TESTS+=("${cf} (missing)")
      continue
    fi

    if _have_docker_daemon && _have_compose_cli; then
      log_info "Compose config: ${cf}"
      if _compose_config_check "$path"; then
        log_success "Compose syntax OK: ${cf}"
        PASSED_TESTS+=("${cf} (compose config)")
      else
        log_error "Compose config FAIL: ${cf}"
        FAILED_TESTS+=("${cf} (compose config)")
      fi
    else
      log_verbose "Skipping compose config (no Docker): ${cf}"
      SKIPPED_TESTS+=("${cf} (compose skipped, no docker)")
    fi

    if [[ "$TEST_COMPOSE" == true ]] && _have_docker_daemon && _have_compose_cli; then
      log_warn "Live compose up tests are destructive; not auto-running all services."
      log_warn "Use your stack-specific compose project to start services manually."
    fi
  done
}

generate_summary() {
  local failed=${#FAILED_TESTS[@]}
  local passed=${#PASSED_TESTS[@]}
  local skipped=${#SKIPPED_TESTS[@]}

  echo ""
  echo "=========================================="
  echo "    LUCID DOCKER SMOKE CHECK SUMMARY"
  echo "=========================================="
  echo "Passed:  ${passed}"
  echo "Failed:  ${failed}"
  echo "Skipped: ${skipped}"
  echo ""

  if [[ "$passed" -gt 0 ]]; then
    echo -e "${GREEN}PASSED:${NC} ${passed} Dockerfile(s)"
    if [[ "$VERBOSE" == true ]]; then
      printf '  %s\n' "${PASSED_TESTS[@]}"
      echo ""
    fi
  fi
  if [[ "$failed" -gt 0 ]]; then
    echo -e "${RED}FAILED:${NC}"
    printf '  %s\n' "${FAILED_TESTS[@]}"
    echo ""
  fi
  if [[ "$skipped" -gt 0 ]]; then
    echo -e "${YELLOW}SKIPPED:${NC}"
    printf '  %s\n' "${SKIPPED_TESTS[@]}"
    echo ""
  fi

  if [[ "$failed" -eq 0 ]]; then
    log_success "All executed checks passed."
    exit 0
  fi
  log_error "${failed} check(s) failed."
  exit 1
}

main() {
  log_info "Lucid docker-smoke-test (static default; Docker optional)"
  parse_args "$@"
  check_prerequisites
  find_dockerfiles
  log_info "Scanning ${#DOCKERFILES[@]} Dockerfiles (strict-copy=${STRICT_COPY}, strict-platform=${STRICT_PLATFORM})"

  local df
  for df in "${DOCKERFILES[@]}"; do
    validate_dockerfile_with_optional_build "$df" || true
  done

  test_compose_files
  if ! _have_docker_daemon; then
    log_info "Docker daemon not used: compose config checks skipped (expected for static CI)."
  fi
  generate_summary
}

main "$@"

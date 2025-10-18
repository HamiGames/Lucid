#!/bin/bash
# Path: scripts/docker-smoke-test.sh
# Comprehensive Dockerfile smoke test for Lucid project
# Validates COPY, ENV, WORKDIR paths and docker-compose spin-up

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${CYAN}[VERBOSE]${NC} $1"
    fi
}

# Configuration
VERBOSE=false
TEST_BUILD=false
TEST_COMPOSE=false
FAILED_TESTS=()
PASSED_TESTS=()
SKIPPED_TESTS=()

# Help function
show_help() {
    cat << EOF
Lucid Dockerfile Smoke Test

USAGE:
    ./scripts/docker-smoke-test.sh [OPTIONS]

OPTIONS:
    -v, --verbose           Enable verbose output
    -b, --test-build        Test Docker builds (requires Docker)
    -c, --test-compose      Test docker-compose spin-up (requires Docker)
    -h, --help              Show this help message

EXAMPLES:
    ./scripts/docker-smoke-test.sh
    ./scripts/docker-smoke-test.sh --verbose --test-build
    ./scripts/docker-smoke-test.sh --test-compose

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -b|--test-build)
                TEST_BUILD=true
                shift
                ;;
            -c|--test-compose)
                TEST_COMPOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if we're in the project root
    if [[ ! -f "README.md" ]] || [[ ! -d "infrastructure" ]]; then
        log_error "Please run this script from the Lucid project root directory"
        exit 1
    fi
    
    # Check Docker if build testing is enabled
    if [[ "$TEST_BUILD" == "true" ]] || [[ "$TEST_COMPOSE" == "true" ]]; then
        if ! command -v docker &> /dev/null; then
            log_error "Docker is required for build/compose testing but not installed"
            exit 1
        fi
        
        if ! docker info &> /dev/null; then
            log_error "Docker daemon is not running"
            exit 1
        fi
        
        log_success "Docker is available"
    fi
    
    # Check docker-compose if compose testing is enabled
    if [[ "$TEST_COMPOSE" == "true" ]]; then
        if ! command -v docker-compose &> /dev/null; then
            log_error "docker-compose is required for compose testing but not installed"
            exit 1
        fi
        
        log_success "docker-compose is available"
    fi
    
    log_success "Prerequisites check passed"
}

# Find all Dockerfiles
find_dockerfiles() {
    log_info "Finding all Dockerfiles..."
    
    # Find all Dockerfile* files
    mapfile -t DOCKERFILES < <(find . -name "Dockerfile*" -type f | sort)
    
    if [[ ${#DOCKERFILES[@]} -eq 0 ]]; then
        log_error "No Dockerfiles found"
        exit 1
    fi
    
    log_info "Found ${#DOCKERFILES[@]} Dockerfiles:"
    for dockerfile in "${DOCKERFILES[@]}"; do
        echo "  - $dockerfile"
    done
    
    log_success "Dockerfile discovery completed"
}

# Validate COPY paths in a Dockerfile
validate_copy_paths() {
    local dockerfile="$1"
    local errors=()
    
    log_verbose "Validating COPY paths in $dockerfile"
    
    # Extract COPY instructions
    while IFS= read -r line; do
        # Handle COPY with --chmod flags
        if [[ "$line" =~ ^COPY[[:space:]]+(--[^[:space:]]+[[:space:]]+)*([^[:space:]]+)[[:space:]]+([^[:space:]]+) ]]; then
            local source_path="${BASH_REMATCH[2]}"
            local dest_path="${BASH_REMATCH[3]}"
            
            # Skip if source is a build stage (contains --from)
            if [[ "$line" =~ --from= ]]; then
                continue
            fi
            
            # Skip if source contains variables
            if [[ "$source_path" =~ \$ ]]; then
                continue
            fi
            
            # Skip if source starts with -- (it's a flag, not a path)
            if [[ "$source_path" =~ ^-- ]]; then
                continue
            fi
            
            # Check if source path exists
            local dockerfile_dir=$(dirname "$dockerfile")
            local full_source_path="$dockerfile_dir/$source_path"
            
            # Handle relative paths from project root
            if [[ "$source_path" =~ ^\.\./ ]]; then
                full_source_path="$(dirname "$dockerfile_dir")/$source_path"
            elif [[ "$source_path" =~ ^\./ ]]; then
                full_source_path="$dockerfile_dir/$source_path"
            elif [[ ! "$source_path" =~ ^/ ]]; then
                full_source_path="$dockerfile_dir/$source_path"
            fi
            
            if [[ ! -e "$full_source_path" ]]; then
                errors+=("COPY source path does not exist: $source_path -> $full_source_path")
            fi
        fi
    done < "$dockerfile"
    
    if [[ ${#errors[@]} -gt 0 ]]; then
        for error in "${errors[@]}"; do
            log_error "$dockerfile: $error"
        done
        return 1
    fi
    
    return 0
}

# Validate ENV variables in a Dockerfile
validate_env_vars() {
    local dockerfile="$1"
    local errors=()
    
    log_verbose "Validating ENV variables in $dockerfile"
    
    # Extract ENV instructions
    while IFS= read -r line; do
        if [[ "$line" =~ ^ENV[[:space:]]+([^[:space:]]+)=(.+) ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            
            # Check for common issues
            if [[ -z "$var_value" ]]; then
                errors+=("ENV variable '$var_name' has empty value")
            fi
            
            # Check for unquoted values with spaces
            if [[ "$var_value" =~ [[:space:]] && ! "$var_value" =~ ^\".*\"$ && ! "$var_value" =~ ^\'.*\'$ ]]; then
                errors+=("ENV variable '$var_name' has unquoted value with spaces: $var_value")
            fi
        fi
    done < "$dockerfile"
    
    if [[ ${#errors[@]} -gt 0 ]]; then
        for error in "${errors[@]}"; do
            log_error "$dockerfile: $error"
        done
        return 1
    fi
    
    return 0
}

# Validate WORKDIR paths in a Dockerfile
validate_workdir_paths() {
    local dockerfile="$1"
    local errors=()
    
    log_verbose "Validating WORKDIR paths in $dockerfile"
    
    # Extract WORKDIR instructions
    while IFS= read -r line; do
        if [[ "$line" =~ ^WORKDIR[[:space:]]+(.+) ]]; then
            local workdir_path="${BASH_REMATCH[1]}"
            
            # Check for common issues
            if [[ -z "$workdir_path" ]]; then
                errors+=("WORKDIR has empty path")
            elif [[ "$workdir_path" =~ [[:space:]] ]]; then
                errors+=("WORKDIR path contains spaces: $workdir_path")
            elif [[ "$workdir_path" =~ \$ ]]; then
                # Variables in WORKDIR are generally OK, just warn
                log_verbose "WORKDIR uses variable: $workdir_path"
            fi
        fi
    done < "$dockerfile"
    
    if [[ ${#errors[@]} -gt 0 ]]; then
        for error in "${errors[@]}"; do
            log_error "$dockerfile: $error"
        done
        return 1
    fi
    
    return 0
}

# Test Docker build for a single Dockerfile
test_docker_build() {
    local dockerfile="$1"
    local build_context=$(dirname "$dockerfile")
    local image_name="lucid-test-$(basename "$dockerfile" | tr '[:upper:]' '[:lower:]' | tr '.' '-')"
    
    log_verbose "Testing Docker build for $dockerfile"
    
    # Build the image
    if docker build -f "$dockerfile" -t "$image_name" "$build_context" >/dev/null 2>&1; then
        log_verbose "Docker build successful for $dockerfile"
        
        # Clean up the test image
        docker rmi "$image_name" >/dev/null 2>&1 || true
        
        return 0
    else
        log_error "Docker build failed for $dockerfile"
        return 1
    fi
}

# Test docker-compose services
test_docker_compose() {
    local compose_file="$1"
    local service_name="$2"
    
    log_verbose "Testing docker-compose service: $service_name from $compose_file"
    
    # Start the service
    if docker-compose -f "$compose_file" up -d "$service_name" >/dev/null 2>&1; then
        # Wait a bit for the service to start
        sleep 5
        
        # Check if service is running
        if docker-compose -f "$compose_file" ps "$service_name" | grep -q "Up"; then
            log_verbose "Docker-compose service $service_name is running"
            
            # Stop the service
            docker-compose -f "$compose_file" down >/dev/null 2>&1 || true
            
            return 0
        else
            log_error "Docker-compose service $service_name failed to start properly"
            docker-compose -f "$compose_file" logs "$service_name" 2>/dev/null || true
            docker-compose -f "$compose_file" down >/dev/null 2>&1 || true
            return 1
        fi
    else
        log_error "Docker-compose failed to start service $service_name"
        docker-compose -f "$compose_file" down >/dev/null 2>&1 || true
        return 1
    fi
}

# Validate a single Dockerfile
validate_dockerfile() {
    local dockerfile="$1"
    local dockerfile_name=$(basename "$dockerfile")
    local errors=0
    
    log_info "Validating $dockerfile_name..."
    
    # Validate COPY paths
    if ! validate_copy_paths "$dockerfile"; then
        ((errors++))
    fi
    
    # Validate ENV variables
    if ! validate_env_vars "$dockerfile"; then
        ((errors++))
    fi
    
    # Validate WORKDIR paths
    if ! validate_workdir_paths "$dockerfile"; then
        ((errors++))
    fi
    
    # Test Docker build if enabled
    if [[ "$TEST_BUILD" == "true" ]]; then
        if ! test_docker_build "$dockerfile"; then
            ((errors++))
        fi
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "$dockerfile_name validation passed"
        PASSED_TESTS+=("$dockerfile_name")
        return 0
    else
        log_error "$dockerfile_name validation failed with $errors errors"
        FAILED_TESTS+=("$dockerfile_name")
        return 1
    fi
}

# Test docker-compose files
test_compose_files() {
    log_info "Testing docker-compose files..."
    
    local compose_files=(
        "infrastructure/docker/compose/docker-compose.yml"
        "infrastructure/docker/compose/docker-compose.dev.yml"
        ".devcontainer/docker-compose.dev.yml"
    )
    
    for compose_file in "${compose_files[@]}"; do
        if [[ -f "$compose_file" ]]; then
            log_info "Testing compose file: $compose_file"
            
            # Validate compose file syntax
            if docker-compose -f "$compose_file" config >/dev/null 2>&1; then
                log_success "Compose file syntax valid: $compose_file"
                
                # Test individual services if enabled
                if [[ "$TEST_COMPOSE" == "true" ]]; then
                    # Get list of services
                    local services
                    mapfile -t services < <(docker-compose -f "$compose_file" config --services 2>/dev/null || echo "")
                    
                    for service in "${services[@]}"; do
                        if [[ -n "$service" ]]; then
                            test_docker_compose "$compose_file" "$service"
                        fi
                    done
                fi
            else
                log_error "Compose file syntax invalid: $compose_file"
                FAILED_TESTS+=("$compose_file")
            fi
        else
            log_warn "Compose file not found: $compose_file"
            SKIPPED_TESTS+=("$compose_file")
        fi
    done
}

# Generate summary report
generate_summary() {
    log_info "Generating smoke test summary..."
    
    local total_tests=$((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]}))
    local passed_count=${#PASSED_TESTS[@]}
    local failed_count=${#FAILED_TESTS[@]}
    local skipped_count=${#SKIPPED_TESTS[@]}
    
    echo
    echo "=========================================="
    echo "    LUCID DOCKERFILE SMOKE TEST SUMMARY"
    echo "=========================================="
    echo "Total Tests: $total_tests"
    echo -e "Passed: ${GREEN}$passed_count${NC}"
    echo -e "Failed: ${RED}$failed_count${NC}"
    echo -e "Skipped: ${YELLOW}$skipped_count${NC}"
    echo
    
    if [[ $passed_count -gt 0 ]]; then
        echo -e "${GREEN}PASSED TESTS:${NC}"
        for test in "${PASSED_TESTS[@]}"; do
            echo "  ✓ $test"
        done
        echo
    fi
    
    if [[ $failed_count -gt 0 ]]; then
        echo -e "${RED}FAILED TESTS:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  ✗ $test"
        done
        echo
    fi
    
    if [[ $skipped_count -gt 0 ]]; then
        echo -e "${YELLOW}SKIPPED TESTS:${NC}"
        for test in "${SKIPPED_TESTS[@]}"; do
            echo "  - $test"
        done
        echo
    fi
    
    # Overall result
    if [[ $failed_count -eq 0 ]]; then
        log_success "All tests passed! 🎉"
        exit 0
    else
        log_error "$failed_count test(s) failed. Please fix the issues above."
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting Lucid Dockerfile Smoke Test"
    log_info "===================================="
    
    # Parse arguments
    parse_args "$@"
    
    # Check prerequisites
    check_prerequisites
    
    # Find all Dockerfiles
    find_dockerfiles
    
    # Validate each Dockerfile
    for dockerfile in "${DOCKERFILES[@]}"; do
        validate_dockerfile "$dockerfile"
    done
    
    # Test compose files
    test_compose_files
    
    # Generate summary
    generate_summary
}

# Run main function
main "$@"

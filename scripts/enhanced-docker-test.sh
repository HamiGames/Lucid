#!/bin/bash
set -euo pipefail

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $*"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }
log_warning() { echo -e "\033[0;33m[WARNING]\033[0m $*"; }

log_info "Starting Enhanced Docker Smoke Test"
log_info "======================================"

# Test configuration files exist
test_config_files() {
    local errors=()
    
    log_info "Testing configuration files..."
    
    # Check MongoDB config
    if [[ -f "infrastructure/docker/compose/mongodb/mongod.conf" ]]; then
        log_success "MongoDB config file exists"
    else
        errors+=("MongoDB config file missing: infrastructure/docker/compose/mongodb/mongod.conf")
    fi
    
    # Check other critical config files
    local config_files=(
        "infrastructure/docker/compose/nginx/nginx.conf"
        "infrastructure/docker/compose/redis/redis.conf"
        "infrastructure/docker/compose/nats/nats-server.conf"
        "infrastructure/docker/compose/vault/vault.hcl"
    )
    
    for config in "${config_files[@]}"; do
        if [[ -f "$config" ]]; then
            log_success "Config file exists: $config"
        else
            errors+=("Config file missing: $config")
        fi
    done
    
    if [ ${#errors[@]} -eq 0 ]; then
        log_success "All configuration files exist"
        return 0
    else
        for error in "${errors[@]}"; do
            log_error "$error"
        done
        return 1
    fi
}

# Test Dockerfile COPY paths
test_dockerfile_paths() {
    local dockerfiles=(
        "infrastructure/docker/admin/Dockerfile.admin-ui"
        "infrastructure/docker/blockchain/Dockerfile.blockchain-api"
        "infrastructure/docker/auth/Dockerfile.authentication"
        "infrastructure/docker/common/Dockerfile.common"
        "infrastructure/docker/databases/Dockerfile.mongodb"
        "src/api/Dockerfile"
    )
    
    local errors=()
    
    log_info "Testing Dockerfile COPY paths..."
    
    for dockerfile in "${dockerfiles[@]}"; do
        if [[ ! -f "$dockerfile" ]]; then
            errors+=("Dockerfile not found: $dockerfile")
            continue
        fi
        
        log_info "Checking $dockerfile"
        
        while IFS= read -r line; do
            if [[ "$line" =~ ^COPY[[:space:]]+(--[^[:space:]]+[[:space:]]+)*([^[:space:]]+)[[:space:]]+([^[:space:]]+) ]]; then
                local source_path="${BASH_REMATCH[2]}"
                
                # Skip build stage copies and variables
                if [[ "$line" =~ --from= ]] || [[ "$source_path" =~ \$ ]] || [[ "$source_path" =~ ^-- ]]; then
                    continue
                fi
                
                local dockerfile_dir=$(dirname "$dockerfile")
                local full_source_path="$dockerfile_dir/$source_path"
                
                if [[ ! -e "$full_source_path" ]]; then
                    errors+=("COPY source path does not exist: $source_path -> $full_source_path")
                else
                    echo "  ✓ $source_path"
                fi
            fi
        done < "$dockerfile"
    done
    
    if [ ${#errors[@]} -eq 0 ]; then
        log_success "All Dockerfile COPY paths are valid"
        return 0
    else
        for error in "${errors[@]}"; do
            log_error "$error"
        done
        return 1
    fi
}

# Test docker-compose syntax
test_compose_syntax() {
    local compose_files=(
        "infrastructure/docker/compose/docker-compose.yml"
        "infrastructure/docker/compose/docker-compose.dev.yml"
        ".devcontainer/docker-compose.dev.yml"
    )
    
    local errors=()
    
    log_info "Testing docker-compose syntax..."
    
    for compose_file in "${compose_files[@]}"; do
        if [[ ! -f "$compose_file" ]]; then
            errors+=("Compose file not found: $compose_file")
            continue
        fi
        
        if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
            log_success "Compose file syntax is valid: $compose_file"
        else
            errors+=("Compose file syntax is invalid: $compose_file")
        fi
    done
    
    if [ ${#errors[@]} -eq 0 ]; then
        log_success "All docker-compose files have valid syntax"
        return 0
    else
        for error in "${errors[@]}"; do
            log_error "$error"
        done
        return 1
    fi
}

# Test container startup (basic services only)
test_container_startup() {
    local services=("lucid-mongodb" "lucid-redis")
    local errors=()
    
    log_info "Testing basic container startup..."
    
    # Start services
    if ! docker-compose -f infrastructure/docker/compose/docker-compose.yml up -d "${services[@]}"; then
        errors+=("Failed to start basic services")
        return 1
    fi
    
    # Wait for services to start
    sleep 10
    
    # Check service status
    for service in "${services[@]}"; do
        local status=$(docker-compose -f infrastructure/docker/compose/docker-compose.yml ps -q "$service")
        if [[ -n "$status" ]]; then
            local container_status=$(docker inspect --format='{{.State.Status}}' "$status")
            if [[ "$container_status" == "running" ]]; then
                log_success "Service $service is running"
            else
                errors+=("Service $service is not running (status: $container_status)")
                # Show logs for debugging
                log_error "Logs for $service:"
                docker-compose -f infrastructure/docker/compose/docker-compose.yml logs --tail=10 "$service"
            fi
        else
            errors+=("Service $service container not found")
        fi
    done
    
    # Cleanup
    docker-compose -f infrastructure/docker/compose/docker-compose.yml down
    
    if [ ${#errors[@]} -eq 0 ]; then
        log_success "All basic services started successfully"
        return 0
    else
        for error in "${errors[@]}"; do
            log_error "$error"
        done
        return 1
    fi
}

# Main execution
overall_status=0

log_info "Phase 1: Configuration Files"
if ! test_config_files; then
    overall_status=1
fi
echo

log_info "Phase 2: Dockerfile COPY Paths"
if ! test_dockerfile_paths; then
    overall_status=1
fi
echo

log_info "Phase 3: Docker Compose Syntax"
if ! test_compose_syntax; then
    overall_status=1
fi
echo

log_info "Phase 4: Container Startup Test"
if ! test_container_startup; then
    overall_status=1
fi
echo

log_info "======================================"
if [ $overall_status -eq 0 ]; then
    log_success "All tests passed! Docker setup is ready."
else
    log_error "Some tests failed. Please check the logs above."
fi

exit $overall_status

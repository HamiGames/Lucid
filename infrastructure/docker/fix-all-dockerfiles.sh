#!/bin/bash
# Fix all Dockerfiles to include build-env.sh script execution and WSL2 support
# This script updates all Dockerfiles in the infrastructure/docker directory

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DRY_RUN=${DRY_RUN:-false}
VERBOSE=${VERBOSE:-false}

# Function to check if Dockerfile needs updates
needs_update() {
    local dockerfile="$1"
    local content
    content=$(cat "$dockerfile")
    
    # Check if it already has build-env.sh integration
    if echo "$content" | grep -q "build-env\.sh" && echo "$content" | grep -q "bash.*git"; then
        return 1  # No update needed
    fi
    return 0  # Update needed
}

# Function to update a single Dockerfile
update_dockerfile() {
    local dockerfile="$1"
    local service_dir
    local temp_file
    
    log_info "Processing: $dockerfile"
    
    # Determine service directory from path
    service_dir=$(dirname "$dockerfile" | sed 's|infrastructure/docker/||')
    
    # Create temporary file
    temp_file=$(mktemp)
    
    # Process the Dockerfile
    awk -v service_dir="$service_dir" '
    BEGIN { 
        in_builder = 0
        added_build_env = 0
        added_env_copy = 0
    }
    
    # Track if we are in builder stage
    /^FROM.*AS.*builder/ { in_builder = 1; print; next }
    /^FROM.*AS.*[^b]|^FROM gcr\.io/ { in_builder = 0; print; next }
    
    # Add bash and git to apt-get install commands in builder stage
    in_builder && /apt-get install.*-y/ && !/bash.*git/ {
        if (/--no-install-recommends/) {
            gsub(/\\$/, "\\\n        bash \\\n        git \\")
        } else {
            gsub(/\\$/, "\\\n    bash \\\n    git \\")
        }
        print
        next
    }
    
    # Add build-env.sh script execution after WORKDIR /app in builder stage
    in_builder && /^WORKDIR \/app/ && !added_build_env {
        print
        print ""
        print "# Copy build environment script"
        print "COPY infrastructure/docker/" service_dir "/build-env.sh /tmp/build-env.sh"
        print "RUN chmod +x /tmp/build-env.sh"
        print ""
        print "# Execute build environment script to generate .env files"
        print "RUN /tmp/build-env.sh"
        added_build_env = 1
        next
    }
    
    # Add .env file copy in final stage after copying application
    !in_builder && /COPY --from=.*\/app \/app/ && !added_env_copy {
        print
        print "# Copy generated environment files"
        print "COPY --from=builder /tmp/infrastructure/docker/" service_dir "/env/*.env /app/.env"
        added_env_copy = 1
        next
    }
    
    # Add platform specification to FROM commands if not present
    /^FROM [^-]/ && !/--platform=/ {
        gsub(/^FROM /, "FROM --platform=$TARGETPLATFORM ")
        print
        next
    }
    
    # Default: print the line
    { print }
    ' "$dockerfile" > "$temp_file"
    
    # Check if changes were made
    if ! diff -q "$dockerfile" "$temp_file" >/dev/null 2>&1; then
        if [ "$DRY_RUN" = "true" ]; then
            log_warning "Would update: $dockerfile"
        else
            mv "$temp_file" "$dockerfile"
            log_success "Updated: $dockerfile"
        fi
        rm -f "$temp_file"
        return 0
    else
        log_warning "No changes needed: $dockerfile"
        rm -f "$temp_file"
        return 1
    fi
}

# Main execution
log_info "Fixing Dockerfiles for build-env.sh integration and WSL2 support"
log_info "Working directory: $(pwd)"

if [ "$DRY_RUN" = "true" ]; then
    log_warning "DRY RUN MODE - No files will be modified"
fi

# Find all Dockerfiles
dockerfiles=($(find infrastructure/docker -name "Dockerfile*" -type f | grep -v "\.md$" | sort))

updated_count=0
total_count=${#dockerfiles[@]}

log_info "Found $total_count Dockerfiles to process"

for dockerfile in "${dockerfiles[@]}"; do
    if [ -f "$dockerfile" ]; then
        if needs_update "$dockerfile"; then
            if update_dockerfile "$dockerfile"; then
                ((updated_count++))
            fi
        else
            log_warning "Already up to date: $dockerfile"
        fi
    else
        log_error "File not found: $dockerfile"
    fi
done

log_info ""
log_info "Summary:"
log_info "  Total Dockerfiles: $total_count"
log_info "  Updated: $updated_count"
log_info "  No changes needed: $((total_count - updated_count))"

if [ "$DRY_RUN" = "true" ]; then
    log_warning ""
    log_warning "This was a dry run. Set DRY_RUN=false to apply changes."
else
    log_success ""
    log_success "All Dockerfiles have been updated!"
fi

log_info ""
log_info "Next steps:"
log_info "  1. Test building a few Dockerfiles to ensure they work"
log_info "  2. Verify that .env files are generated correctly"
log_info "  3. Test WSL2 compatibility if building from Windows"

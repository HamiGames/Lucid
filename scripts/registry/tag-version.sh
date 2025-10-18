#!/bin/bash

# Lucid Container Version Tagging Script
# Manages version tags for Lucid containers in GitHub Container Registry
# Usage: ./tag-version.sh [action] [service] [version]

set -euo pipefail

# Configuration
REGISTRY="ghcr.io"
REPOSITORY="hamigames/lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
ACTION=""
SERVICE_NAME=""
VERSION=""
SOURCE_TAG="latest"
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Lucid Container Version Tagging Script

USAGE:
    $0 [ACTION] [SERVICE] [VERSION] [OPTIONS]

ACTIONS:
    create          Create a new version tag from source tag
    delete          Delete a version tag
    list            List all tags for a service
    promote         Promote a version to latest
    rollback        Rollback latest to a previous version

ARGUMENTS:
    SERVICE         Name of the service
    VERSION         Version tag to create/delete (e.g., v1.0.0, 1.0.0)

OPTIONS:
    -s, --source SOURCE    Source tag to create from (default: latest)
    -d, --dry-run          Show what would be done without actually doing it
    -h, --help             Show this help message

EXAMPLES:
    $0 create api-gateway v1.0.0
    $0 create blockchain-core 1.0.0 -s main
    $0 delete session-management v0.9.0
    $0 list api-gateway
    $0 promote api-gateway v1.0.0
    $0 rollback api-gateway v0.9.0

SERVICES:
    Phase 1 (Foundation):
    - auth-service, storage-database, mongodb, redis, elasticsearch

    Phase 2 (Core Services):
    - api-gateway, blockchain-core, blockchain-engine, session-anchoring
    - block-manager, data-chain, service-mesh-controller

    Phase 3 (Application Services):
    - session-pipeline, session-recorder, session-processor, session-storage
    - session-api, rdp-server-manager, rdp-xrdp, rdp-controller, rdp-monitor
    - node-management

    Phase 4 (Support Services):
    - admin-interface, tron-client, tron-payout-router, tron-wallet-manager
    - tron-usdt-manager, tron-staking, tron-payment-gateway

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--source)
                SOURCE_TAG="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$ACTION" ]]; then
                    ACTION="$1"
                elif [[ -z "$SERVICE_NAME" ]]; then
                    SERVICE_NAME="$1"
                elif [[ -z "$VERSION" ]]; then
                    VERSION="$1"
                else
                    log_error "Too many arguments"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments based on action
    case "$ACTION" in
        create|delete|promote|rollback)
            if [[ -z "$SERVICE_NAME" || -z "$VERSION" ]]; then
                log_error "Service name and version are required for action: $ACTION"
                show_help
                exit 1
            fi
            ;;
        list)
            if [[ -z "$SERVICE_NAME" ]]; then
                log_error "Service name is required for action: $ACTION"
                show_help
                exit 1
            fi
            ;;
        "")
            log_error "Action is required"
            show_help
            exit 1
            ;;
        *)
            log_error "Unknown action: $ACTION"
            show_help
            exit 1
            ;;
    esac
}

# Validate service name
validate_service() {
    local service="$1"
    local valid_services=(
        # Phase 1
        "auth-service" "storage-database" "mongodb" "redis" "elasticsearch"
        # Phase 2
        "api-gateway" "blockchain-core" "blockchain-engine" "session-anchoring" 
        "block-manager" "data-chain" "service-mesh-controller"
        # Phase 3
        "session-pipeline" "session-recorder" "session-processor" "session-storage"
        "session-api" "rdp-server-manager" "rdp-xrdp" "rdp-controller" "rdp-monitor"
        "node-management"
        # Phase 4
        "admin-interface" "tron-client" "tron-payout-router" "tron-wallet-manager"
        "tron-usdt-manager" "tron-staking" "tron-payment-gateway"
    )

    for valid_service in "${valid_services[@]}"; do
        if [[ "$service" == "$valid_service" ]]; then
            return 0
        fi
    done

    log_error "Invalid service name: $service"
    log_info "Valid services: ${valid_services[*]}"
    return 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi

    # Check if Docker Buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        exit 1
    fi

    # Check if logged into GHCR
    if ! docker info | grep -q "ghcr.io"; then
        log_warning "Not logged into GHCR. Attempting to login..."
        if ! echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin; then
            log_error "Failed to login to GHCR. Please set GITHUB_TOKEN environment variable"
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Get image manifest
get_manifest() {
    local service="$1"
    local tag="$2"
    local image="$REGISTRY/$REPOSITORY/$service:$tag"

    docker manifest inspect "$image" 2>/dev/null || {
        log_error "Failed to get manifest for $image"
        return 1
    }
}

# Create version tag
create_tag() {
    local service="$1"
    local version="$2"
    local source_tag="$3"
    local dry_run="$4"

    local source_image="$REGISTRY/$REPOSITORY/$service:$source_tag"
    local target_image="$REGISTRY/$REPOSITORY/$service:$version"

    log_info "Creating tag $version for $service from $source_tag"

    # Check if source image exists
    if ! get_manifest "$service" "$source_tag" >/dev/null 2>&1; then
        log_error "Source image does not exist: $source_image"
        exit 1
    fi

    # Check if target tag already exists
    if get_manifest "$service" "$version" >/dev/null 2>&1; then
        log_warning "Tag $version already exists for $service"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Operation cancelled"
            exit 0
        fi
    fi

    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would create tag $target_image from $source_image"
        return 0
    fi

    # Create the tag by pulling and pushing
    log_info "Pulling source image: $source_image"
    if ! docker pull "$source_image"; then
        log_error "Failed to pull source image: $source_image"
        exit 1
    fi

    log_info "Tagging image: $source_image -> $target_image"
    if ! docker tag "$source_image" "$target_image"; then
        log_error "Failed to tag image"
        exit 1
    fi

    log_info "Pushing tagged image: $target_image"
    if ! docker push "$target_image"; then
        log_error "Failed to push tagged image: $target_image"
        exit 1
    fi

    log_success "Successfully created tag $version for $service"
}

# Delete version tag
delete_tag() {
    local service="$1"
    local version="$2"
    local dry_run="$3"

    local image="$REGISTRY/$REPOSITORY/$service:$version"

    log_info "Deleting tag $version for $service"

    # Check if tag exists
    if ! get_manifest "$service" "$version" >/dev/null 2>&1; then
        log_error "Tag does not exist: $image"
        exit 1
    fi

    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would delete tag $image"
        return 0
    fi

    # Note: GHCR doesn't support direct tag deletion via Docker CLI
    # This would need to be done via GitHub API or web interface
    log_warning "Direct tag deletion is not supported via Docker CLI"
    log_info "Please delete the tag manually via GitHub Container Registry web interface:"
    log_info "https://github.com/orgs/hamigames/packages/container/package/lucid%2F$service"
    log_info "Or use GitHub API to delete the tag"
}

# List tags for service
list_tags() {
    local service="$1"

    log_info "Listing tags for $service"

    # This would require GitHub API access to list all tags
    # For now, we'll show a message about manual checking
    log_info "To list all tags for $service, visit:"
    log_info "https://github.com/orgs/hamigames/packages/container/package/lucid%2F$service"
    
    # Try to get some basic info about the service
    local latest_image="$REGISTRY/$REPOSITORY/$service:latest"
    if get_manifest "$service" "latest" >/dev/null 2>&1; then
        log_success "Latest tag exists: $latest_image"
        
        # Show manifest info
        log_info "Latest image details:"
        get_manifest "$service" "latest" | jq -r '.manifests[] | "  - \(.platform.os)/\(.platform.architecture): \(.digest)"' 2>/dev/null || true
    else
        log_warning "No latest tag found for $service"
    fi
}

# Promote version to latest
promote_to_latest() {
    local service="$1"
    local version="$2"
    local dry_run="$3"

    log_info "Promoting $version to latest for $service"

    # Create latest tag from version
    create_tag "$service" "latest" "$version" "$dry_run"
}

# Rollback latest to previous version
rollback_latest() {
    local service="$1"
    local version="$2"
    local dry_run="$3"

    log_info "Rolling back latest to $version for $service"

    # Create latest tag from version
    create_tag "$service" "latest" "$version" "$dry_run"
}

# Main function
main() {
    log_info "Starting Lucid container version tagging process"
    log_info "Action: $ACTION"
    log_info "Service: $SERVICE_NAME"
    log_info "Version: $VERSION"
    log_info "Source tag: $SOURCE_TAG"
    log_info "Dry run: $DRY_RUN"

    # Parse arguments
    parse_args "$@"

    # Validate service
    validate_service "$SERVICE_NAME"

    # Check prerequisites
    check_prerequisites

    # Execute action
    case "$ACTION" in
        create)
            create_tag "$SERVICE_NAME" "$VERSION" "$SOURCE_TAG" "$DRY_RUN"
            ;;
        delete)
            delete_tag "$SERVICE_NAME" "$VERSION" "$DRY_RUN"
            ;;
        list)
            list_tags "$SERVICE_NAME"
            ;;
        promote)
            promote_to_latest "$SERVICE_NAME" "$VERSION" "$DRY_RUN"
            ;;
        rollback)
            rollback_latest "$SERVICE_NAME" "$VERSION" "$DRY_RUN"
            ;;
    esac

    log_success "Version tagging process completed successfully"
}

# Run main function with all arguments
main "$@"

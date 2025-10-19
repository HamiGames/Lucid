#!/bin/bash

# =============================================================================
# Lucid Deployment with Automatic Volume Setup
# Automatically creates volume mounts and deploys Docker Compose files
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PI_USER="${PI_USER:-pickme}"
PI_HOST="${PI_HOST:-192.168.0.75}"
PI_SSH_KEY_PATH="${PI_SSH_KEY_PATH:-~/.ssh/id_rsa}"
LUCID_ROOT="/mnt/myssd/Lucid"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Logging function
log_step() {
    local step="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" = "SUCCESS" ]; then
        echo -e "${GREEN}✅ [$step] $message${NC}"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠️  [$step] $message${NC}"
    else
        echo -e "${RED}❌ [$step] $message${NC}"
    fi
}

# Show help
show_help() {
    echo "Usage: $0 [OPTIONS] <COMPOSE_FILE>"
    echo ""
    echo "Deploy Lucid services to Pi with automatic volume setup"
    echo ""
    echo "Arguments:"
    echo "  COMPOSE_FILE    Docker Compose file to deploy (required)"
    echo ""
    echo "Options:"
    echo "  -h, --help      Show this help message"
    echo "  -u, --user      Pi username (default: pickme)"
    echo "  -H, --host      Pi hostname/IP (default: 192.168.0.75)"
    echo "  -k, --key       SSH key path (default: ~/.ssh/id_rsa)"
    echo "  -s, --skip-volumes  Skip volume setup (assume directories exist)"
    echo "  -d, --detach    Run containers in detached mode"
    echo "  -b, --build     Build images before deployment"
    echo ""
    echo "Environment Variables:"
    echo "  PI_USER         Pi username"
    echo "  PI_HOST         Pi hostname/IP"
    echo "  PI_SSH_KEY_PATH SSH key path"
    echo ""
    echo "Examples:"
    echo "  $0 configs/docker/docker-compose.foundation.yml"
    echo "  $0 -u pi -H 192.168.1.100 configs/docker/docker-compose.core.yml"
    echo "  $0 --build --detach configs/docker/docker-compose.all.yml"
    echo ""
    echo "Available Compose Files:"
    echo "  - configs/docker/docker-compose.foundation.yml (Phase 1)"
    echo "  - configs/docker/docker-compose.core.yml (Phase 2)"
    echo "  - configs/docker/docker-compose.application.yml (Phase 3)"
    echo "  - configs/docker/docker-compose.support.yml (Phase 4)"
    echo "  - configs/docker/docker-compose.all.yml (All phases)"
}

# Setup volumes on Pi
setup_volumes() {
    echo -e "${BLUE}=== Setting up Volume Mounts ===${NC}"
    
    if [ -f "$SCRIPT_DIR/setup-pi-volumes.sh" ]; then
        # Use the volume setup script
        "$SCRIPT_DIR/setup-pi-volumes.sh" -u "$PI_USER" -H "$PI_HOST" -k "$PI_SSH_KEY_PATH"
        
        if [ $? -eq 0 ]; then
            log_step "volume-setup" "SUCCESS" "Volume mounts created successfully"
        else
            log_step "volume-setup" "FAILURE" "Failed to create volume mounts"
            return 1
        fi
    else
        # Fallback: create directories directly
        echo "Volume setup script not found, creating directories directly..."
        
        ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
            sudo mkdir -p $LUCID_ROOT/data/{mongodb,redis,elasticsearch,auth,blockchain,consul,session-pipeline,node-management,admin-interface,tron-client,storage}
            sudo mkdir -p $LUCID_ROOT/logs/{auth,api-gateway,blockchain,consul,session-pipeline,node-management,admin-interface,tron-client,storage}
            sudo mkdir -p $LUCID_ROOT/backups
            sudo chown -R $PI_USER:$PI_USER $LUCID_ROOT
            sudo chmod -R 755 $LUCID_ROOT
        " >/dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            log_step "volume-setup" "SUCCESS" "Volume mounts created successfully (fallback)"
        else
            log_step "volume-setup" "FAILURE" "Failed to create volume mounts (fallback)"
            return 1
        fi
    fi
}

# Copy compose file to Pi
copy_compose_file() {
    local compose_file="$1"
    local compose_name=$(basename "$compose_file")
    
    echo -e "${BLUE}=== Copying Compose File to Pi ===${NC}"
    
    # Copy compose file to Pi
    scp -i "$PI_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$compose_file" "$PI_USER@$PI_HOST:$LUCID_ROOT/" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "compose-copy" "SUCCESS" "Compose file copied to Pi"
    else
        log_step "compose-copy" "FAILURE" "Failed to copy compose file to Pi"
        return 1
    fi
}

# Deploy services on Pi
deploy_services() {
    local compose_file="$1"
    local compose_name=$(basename "$compose_file")
    local deploy_args=""
    
    echo -e "${BLUE}=== Deploying Services ===${NC}"
    
    # Build deploy arguments
    if [ "$BUILD_IMAGES" = "true" ]; then
        deploy_args="$deploy_args --build"
    fi
    
    if [ "$DETACH_MODE" = "true" ]; then
        deploy_args="$deploy_args -d"
    fi
    
    # Deploy on Pi
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $LUCID_ROOT
        echo 'Deploying $compose_name...'
        docker-compose -f $compose_name up $deploy_args
    "
    
    if [ $? -eq 0 ]; then
        log_step "deployment" "SUCCESS" "Services deployed successfully"
    else
        log_step "deployment" "FAILURE" "Failed to deploy services"
        return 1
    fi
}

# Verify deployment
verify_deployment() {
    echo -e "${BLUE}=== Verifying Deployment ===${NC}"
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        echo 'Container Status:'
        docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'
        
        echo ''
        echo 'Volume Mounts:'
        docker inspect \$(docker ps -q) | jq -r '.[] | \"\\(.Name): \\(.Mounts[] | select(.Destination | contains(\"/app/\")) | .Destination)\"' 2>/dev/null || echo 'Volume inspection not available'
        
        echo ''
        echo 'Disk Usage:'
        df -h $LUCID_ROOT
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log_step "verification" "SUCCESS" "Deployment verified successfully"
    else
        log_step "verification" "WARNING" "Deployment verification had issues"
    fi
}

# Main function
main() {
    local compose_file="$1"
    
    # Validate compose file
    if [ ! -f "$compose_file" ]; then
        echo -e "${RED}Error: Compose file '$compose_file' not found${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}=== Lucid Deployment with Volume Setup ===${NC}"
    echo "Pi Host: $PI_USER@$PI_HOST"
    echo "SSH Key: $PI_SSH_KEY_PATH"
    echo "Compose File: $compose_file"
    echo "Lucid Root: $LUCID_ROOT"
    echo ""
    
    # Setup volumes (unless skipped)
    if [ "$SKIP_VOLUMES" = "false" ]; then
        setup_volumes || exit 1
    else
        log_step "volume-setup" "SKIPPED" "Volume setup skipped as requested"
    fi
    
    # Copy compose file
    copy_compose_file "$compose_file" || exit 1
    
    # Deploy services
    deploy_services "$compose_file" || exit 1
    
    # Verify deployment
    verify_deployment
    
    echo ""
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo "Services have been deployed successfully with volume mounts."
    echo ""
    echo "Access your services:"
    echo "- SSH to Pi: ssh -i $PI_SSH_KEY_PATH $PI_USER@$PI_HOST"
    echo "- View logs: docker logs <container_name>"
    echo "- Check status: docker ps"
}

# Default values
SKIP_VOLUMES="false"
DETACH_MODE="true"
BUILD_IMAGES="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--user)
            PI_USER="$2"
            shift 2
            ;;
        -H|--host)
            PI_HOST="$2"
            shift 2
            ;;
        -k|--key)
            PI_SSH_KEY_PATH="$2"
            shift 2
            ;;
        -s|--skip-volumes)
            SKIP_VOLUMES="true"
            shift
            ;;
        -d|--detach)
            DETACH_MODE="true"
            shift
            ;;
        -b|--build)
            BUILD_IMAGES="true"
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "${COMPOSE_FILE:-}" ]; then
                COMPOSE_FILE="$1"
            else
                echo "Error: Multiple compose files specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if compose file was provided
if [ -z "${COMPOSE_FILE:-}" ]; then
    echo -e "${RED}Error: Compose file is required${NC}"
    show_help
    exit 1
fi

# Run main function
main "$COMPOSE_FILE"

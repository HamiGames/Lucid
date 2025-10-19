#!/bin/bash

# =============================================================================
# Pi Volume Setup Script
# Creates all necessary volume mount directories on Raspberry Pi
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

# Test SSH connection
test_ssh_connection() {
    echo -e "${BLUE}=== Testing SSH Connection to Pi ===${NC}"
    
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_step "ssh-connection" "SUCCESS" "SSH connection to Pi established"
        return 0
    else
        log_step "ssh-connection" "FAILURE" "SSH connection to Pi failed"
        return 1
    fi
}

# Create directory structure
create_directory_structure() {
    echo -e "${BLUE}=== Creating Directory Structure ===${NC}"
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Create main Lucid directory structure
        sudo mkdir -p $LUCID_ROOT
        sudo mkdir -p $LUCID_ROOT/data
        sudo mkdir -p $LUCID_ROOT/logs
        sudo mkdir -p $LUCID_ROOT/config
        sudo mkdir -p $LUCID_ROOT/backups
        sudo mkdir -p $LUCID_ROOT/certs
        
        # Create data directories for all services
        sudo mkdir -p $LUCID_ROOT/data/{mongodb,mongodb-config,redis,elasticsearch,auth}
        sudo mkdir -p $LUCID_ROOT/data/{blockchain,blockchain-engine,anchoring,block-manager,data-chain,consul}
        sudo mkdir -p $LUCID_ROOT/data/{session-pipeline,session-recorder,session-processor,session-storage}
        sudo mkdir -p $LUCID_ROOT/data/{rdp-server-manager,rdp-xrdp,rdp-controller,rdp-monitor}
        sudo mkdir -p $LUCID_ROOT/data/{node-management,admin-interface}
        sudo mkdir -p $LUCID_ROOT/data/{tron-client,tron-payout-router,tron-wallet-manager,tron-usdt-manager,tron-staking,tron-payment-gateway}
        sudo mkdir -p $LUCID_ROOT/data/{storage,tor}
        
        # Create log directories for all services
        sudo mkdir -p $LUCID_ROOT/logs/{auth,api-gateway,blockchain,blockchain-engine,anchoring,block-manager,data-chain,consul}
        sudo mkdir -p $LUCID_ROOT/logs/{session-pipeline,session-recorder,session-processor,session-storage,session-api}
        sudo mkdir -p $LUCID_ROOT/logs/{rdp-server-manager,rdp-xrdp,rdp-controller,rdp-monitor}
        sudo mkdir -p $LUCID_ROOT/logs/{node-management,admin-interface}
        sudo mkdir -p $LUCID_ROOT/logs/{tron-client,tron-payout-router,tron-wallet-manager,tron-usdt-manager,tron-staking,tron-payment-gateway}
        sudo mkdir -p $LUCID_ROOT/logs/{storage,monitoring}
        
        # Create config directories
        sudo mkdir -p $LUCID_ROOT/config/{database,redis,elasticsearch,tor,monitoring}
        sudo mkdir -p $LUCID_ROOT/config/{blockchain,consul,session,rdp,node,admin,tron}
        
        # Set proper ownership and permissions
        sudo chown -R $PI_USER:$PI_USER $LUCID_ROOT
        sudo chmod -R 755 $LUCID_ROOT
        
        # Set specific permissions for sensitive directories
        sudo chmod 700 $LUCID_ROOT/data/mongodb
        sudo chmod 700 $LUCID_ROOT/data/mongodb-config
        sudo chmod 700 $LUCID_ROOT/certs
        
        # Ensure MongoDB can write to its directories
        sudo chmod 755 $LUCID_ROOT/data/mongodb
        sudo chmod 755 $LUCID_ROOT/data/mongodb-config
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "directory-creation" "SUCCESS" "Directory structure created successfully"
    else
        log_step "directory-creation" "FAILURE" "Failed to create directory structure"
        return 1
    fi
}

# Verify directory structure
verify_directory_structure() {
    echo -e "${BLUE}=== Verifying Directory Structure ===${NC}"
    
    local result=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Check main directories
        [ -d $LUCID_ROOT ] && echo '✅ Main directory exists' || echo '❌ Main directory missing'
        [ -d $LUCID_ROOT/data ] && echo '✅ Data directory exists' || echo '❌ Data directory missing'
        [ -d $LUCID_ROOT/logs ] && echo '✅ Logs directory exists' || echo '❌ Logs directory missing'
        [ -d $LUCID_ROOT/config ] && echo '✅ Config directory exists' || echo '❌ Config directory missing'
        [ -d $LUCID_ROOT/backups ] && echo '✅ Backups directory exists' || echo '❌ Backups directory missing'
        
        # Check critical service directories
        [ -d $LUCID_ROOT/data/mongodb ] && echo '✅ MongoDB data directory exists' || echo '❌ MongoDB data directory missing'
        [ -d $LUCID_ROOT/data/redis ] && echo '✅ Redis data directory exists' || echo '❌ Redis data directory missing'
        [ -d $LUCID_ROOT/data/elasticsearch ] && echo '✅ Elasticsearch data directory exists' || echo '❌ Elasticsearch data directory missing'
        [ -d $LUCID_ROOT/data/auth ] && echo '✅ Auth data directory exists' || echo '❌ Auth data directory missing'
        
        # Check permissions
        ls -ld $LUCID_ROOT | grep -q $PI_USER && echo '✅ Correct ownership' || echo '❌ Incorrect ownership'
    " 2>/dev/null)
    
    echo "$result"
    
    # Count successful checks
    local success_count=$(echo "$result" | grep -c '✅')
    local total_count=$(echo "$result" | grep -c -E '✅|❌')
    
    if [ "$success_count" -eq "$total_count" ]; then
        log_step "directory-verification" "SUCCESS" "All directories verified successfully"
        return 0
    else
        log_step "directory-verification" "WARNING" "Some directories may need attention ($success_count/$total_count passed)"
        return 1
    fi
}

# Show directory usage
show_directory_usage() {
    echo -e "${BLUE}=== Directory Usage Information ===${NC}"
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        echo 'Directory Structure:'
        tree $LUCID_ROOT -L 3 2>/dev/null || find $LUCID_ROOT -type d -maxdepth 3 | sort
        
        echo ''
        echo 'Disk Usage:'
        df -h $LUCID_ROOT 2>/dev/null || echo 'Could not get disk usage'
        
        echo ''
        echo 'Directory Sizes:'
        du -sh $LUCID_ROOT/* 2>/dev/null || echo 'Could not get directory sizes'
    " 2>/dev/null
}

# Main function
main() {
    echo -e "${BLUE}=== Lucid Pi Volume Setup ===${NC}"
    echo "Pi Host: $PI_USER@$PI_HOST"
    echo "SSH Key: $PI_SSH_KEY_PATH"
    echo "Lucid Root: $LUCID_ROOT"
    echo ""
    
    # Test SSH connection
    test_ssh_connection || exit 1
    
    # Create directory structure
    create_directory_structure || exit 1
    
    # Verify directory structure
    verify_directory_structure
    
    # Show usage information
    show_directory_usage
    
    echo ""
    echo -e "${GREEN}=== Volume Setup Complete ===${NC}"
    echo "All volume mount directories have been created on the Pi."
    echo "You can now deploy Docker Compose files with confidence."
    echo ""
    echo "Next steps:"
    echo "1. Deploy Phase 1: ./scripts/deployment/deploy-phase1-pi.sh"
    echo "2. Or deploy specific phase: docker-compose -f configs/docker/docker-compose.foundation.yml up -d"
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -u, --user     Pi username (default: pickme)"
    echo "  -H, --host     Pi hostname/IP (default: 192.168.0.75)"
    echo "  -k, --key      SSH key path (default: ~/.ssh/id_rsa)"
    echo ""
    echo "Environment Variables:"
    echo "  PI_USER        Pi username"
    echo "  PI_HOST        Pi hostname/IP"
    echo "  PI_SSH_KEY_PATH SSH key path"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 -u pi -H 192.168.1.100 -k ~/.ssh/pi_key"
    echo "  PI_USER=pi PI_HOST=192.168.1.100 $0"
}

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
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main

#!/bin/bash
# Lucid GUI QR Code Bootstrap Script
# Generates QR codes for all GUI services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
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

# Check if qrencode is installed
check_dependencies() {
    if ! command -v qrencode &> /dev/null; then
        log_error "qrencode is not installed. Installing..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y qrencode
        elif command -v yum &> /dev/null; then
            sudo yum install -y qrencode
        elif command -v brew &> /dev/null; then
            brew install qrencode
        else
            log_error "Cannot install qrencode. Please install manually."
            exit 1
        fi
    fi
}

# Generate QR codes for GUI services
generate_qr_codes() {
    log_info "Generating QR codes for Lucid GUI services..."
    
    # Check if Tor hidden service directories exist
    local user_onion=""
    local admin_onion=""
    local node_onion=""
    
    if [ -f "/var/lib/tor/lucid-user-gui/hostname" ]; then
        user_onion=$(cat /var/lib/tor/lucid-user-gui/hostname)
        log_success "User GUI .onion: $user_onion"
    else
        log_warning "User GUI .onion service not found"
    fi
    
    if [ -f "/var/lib/tor/lucid-admin-gui/hostname" ]; then
        admin_onion=$(cat /var/lib/tor/lucid-admin-gui/hostname)
        log_success "Admin GUI .onion: $admin_onion"
    else
        log_warning "Admin GUI .onion service not found"
    fi
    
    if [ -f "/var/lib/tor/lucid-node-gui/hostname" ]; then
        node_onion=$(cat /var/lib/tor/lucid-node-gui/hostname)
        log_success "Node GUI .onion: $node_onion"
    else
        log_warning "Node GUI .onion service not found"
    fi
    
    echo ""
    echo "=============================================="
    echo "          Lucid RDP GUI Access Codes"
    echo "=============================================="
    echo ""
    
    if [ -n "$user_onion" ]; then
        echo "📱 USER GUI (End Users)"
        echo "   URL: https://$user_onion"
        echo "   Purpose: Session management and control"
        echo ""
        qrencode -t ANSI256 "https://$user_onion" || qrencode -t UTF8 "https://$user_onion"
        echo ""
        echo "----------------------------------------------"
        echo ""
    fi
    
    if [ -n "$admin_onion" ]; then
        echo "⚙️  ADMIN GUI (Operators)"
        echo "   URL: https://$admin_onion"
        echo "   Purpose: Pi administration and provisioning"
        echo ""
        qrencode -t ANSI256 "https://$admin_onion" || qrencode -t UTF8 "https://$admin_onion"
        echo ""
        echo "----------------------------------------------"
        echo ""
    fi
    
    if [ -n "$node_onion" ]; then
        echo "🖥️  NODE GUI (Node Workers)"
        echo "   URL: https://$node_onion"
        echo "   Purpose: Node monitoring and PoOT management"
        echo ""
        qrencode -t ANSI256 "https://$node_onion" || qrencode -t UTF8 "https://$node_onion"
        echo ""
        echo "----------------------------------------------"
        echo ""
    fi
    
    echo "📋 Instructions:"
    echo "   1. Scan the appropriate QR code with your device"
    echo "   2. Open the .onion URL in Tor Browser"
    echo "   3. Authenticate to access the GUI"
    echo ""
    echo "🔒 Security Note:"
    echo "   All GUI access is via Tor .onion addresses only"
    echo "   No clearnet ingress is available"
    echo ""
    echo "=============================================="
}

# Save QR codes to files
save_qr_codes() {
    log_info "Saving QR codes to files..."
    
    local output_dir="/opt/lucid/qr-codes"
    mkdir -p "$output_dir"
    
    if [ -f "/var/lib/tor/lucid-user-gui/hostname" ]; then
        local user_onion=$(cat /var/lib/tor/lucid-user-gui/hostname)
        qrencode -o "$output_dir/user-gui.png" "https://$user_onion"
        echo "https://$user_onion" > "$output_dir/user-gui.txt"
        log_success "User GUI QR code saved to $output_dir/user-gui.png"
    fi
    
    if [ -f "/var/lib/tor/lucid-admin-gui/hostname" ]; then
        local admin_onion=$(cat /var/lib/tor/lucid-admin-gui/hostname)
        qrencode -o "$output_dir/admin-gui.png" "https://$admin_onion"
        echo "https://$admin_onion" > "$output_dir/admin-gui.txt"
        log_success "Admin GUI QR code saved to $output_dir/admin-gui.png"
    fi
    
    if [ -f "/var/lib/tor/lucid-node-gui/hostname" ]; then
        local node_onion=$(cat /var/lib/tor/lucid-node-gui/hostname)
        qrencode -o "$output_dir/node-gui.png" "https://$node_onion"
        echo "https://$node_onion" > "$output_dir/node-gui.txt"
        log_success "Node GUI QR code saved to $output_dir/node-gui.png"
    fi
}

# Check GUI service health
check_gui_health() {
    log_info "Checking GUI service health..."
    
    local services=("lucid-user-gui:3001" "lucid-admin-gui:3002" "lucid-node-gui:3003")
    local healthy_count=0
    
    for service in "${services[@]}"; do
        local name=$(echo "$service" | cut -d: -f1)
        local port=$(echo "$service" | cut -d: -f2)
        
        if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
            log_success "$name is healthy"
            ((healthy_count++))
        else
            log_warning "$name is not responding"
        fi
    done
    
    if [ $healthy_count -eq ${#services[@]} ]; then
        log_success "All GUI services are healthy"
    else
        log_warning "$healthy_count/${#services[@]} GUI services are healthy"
    fi
}

# Main function
main() {
    log_info "Starting Lucid GUI QR code generation..."
    
    check_dependencies
    check_gui_health
    generate_qr_codes
    save_qr_codes
    
    log_success "QR code generation completed"
}

# Handle command line arguments
case "${1:-}" in
    --save-only)
        check_dependencies
        save_qr_codes
        ;;
    --health-only)
        check_gui_health
        ;;
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --save-only    Save QR codes to files only"
        echo "  --health-only  Check GUI service health only"
        echo "  --help, -h     Show this help message"
        echo ""
        echo "Default: Display QR codes in terminal and save to files"
        ;;
    *)
        main
        ;;
esac

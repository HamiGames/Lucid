#!/bin/bash
# Path: build/scripts/generate-qr-bootstrap.sh
# Generate QR codes for GUI bootstrap access
# Follows SPEC-5 Web-Based GUI Architecture

set -euo pipefail

# Default values
OUTPUT_FORMAT="ansi256"  # ansi256, png, svg, eps
DISPLAY_ON_CONSOLE=true
SAVE_TO_FILE=false
OUTPUT_DIR="/tmp/lucid-qr"
VERBOSE=false
HELP=false

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

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Generate QR codes for Lucid RDP GUI bootstrap access.

OPTIONS:
    -f, --format FORMAT        QR code format: ansi256, png, svg, eps (default: ansi256)
    -d, --display              Display QR codes on console (default: true)
    -s, --save                 Save QR codes to files
    -o, --output-dir DIR       Output directory for saved files (default: /tmp/lucid-qr)
    -v, --verbose              Verbose output
    -h, --help                 Show this help message

EXAMPLES:
    # Display QR codes on console (default)
    $0

    # Save QR codes as PNG files
    $0 --format png --save --output-dir ./qr-codes

    # Save as SVG for web use
    $0 --format svg --save

    # Display on console and save as files
    $0 --display --save --format png

ENVIRONMENT VARIABLES:
    TOR_DATA_DIR               Directory containing .onion hostname files (default: /var/lib/tor)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            -d|--display)
                DISPLAY_ON_CONSOLE=true
                shift
                ;;
            -s|--save)
                SAVE_TO_FILE=true
                shift
                ;;
            -o|--output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                HELP=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if qrencode is installed
    if ! command -v qrencode >/dev/null 2>&1; then
        log_error "qrencode is not installed. Please install it with:"
        log_error "  Ubuntu/Debian: sudo apt-get install qrencode"
        log_error "  CentOS/RHEL: sudo yum install qrencode"
        log_error "  macOS: brew install qrencode"
        exit 1
    fi
    
    # Check if qrencode supports the requested format
    case "$OUTPUT_FORMAT" in
        ansi256|png|svg|eps)
            ;;
        *)
            log_error "Unsupported QR code format: $OUTPUT_FORMAT"
            log_error "Supported formats: ansi256, png, svg, eps"
            exit 1
            ;;
    esac
    
    # Check if Tor data directory exists
    local tor_data_dir="${TOR_DATA_DIR:-/var/lib/tor}"
    if [[ ! -d "$tor_data_dir" ]]; then
        log_warn "Tor data directory not found: $tor_data_dir"
        log_warn "Using default .onion URLs for demonstration"
    fi
    
    log_success "Prerequisites validated"
}

# Get .onion URLs
get_onion_urls() {
    local tor_data_dir="${TOR_DATA_DIR:-/var/lib/tor}"
    local user_onion=""
    local admin_onion=""
    local node_onion=""
    
    # Try to read actual .onion hostnames
    if [[ -f "$tor_data_dir/lucid-user-gui/hostname" ]]; then
        user_onion=$(cat "$tor_data_dir/lucid-user-gui/hostname")
    fi
    
    if [[ -f "$tor_data_dir/lucid-admin-gui/hostname" ]]; then
        admin_onion=$(cat "$tor_data_dir/lucid-admin-gui/hostname")
    fi
    
    if [[ -f "$tor_data_dir/lucid-node-gui/hostname" ]]; then
        node_onion=$(cat "$tor_data_dir/lucid-node-gui/hostname")
    fi
    
    # Use demo URLs if real ones aren't available
    if [[ -z "$user_onion" ]]; then
        user_onion="demo-user-gui.onion"
        log_warn "Using demo URL for User GUI: $user_onion"
    fi
    
    if [[ -z "$admin_onion" ]]; then
        admin_onion="demo-admin-gui.onion"
        log_warn "Using demo URL for Admin GUI: $admin_onion"
    fi
    
    if [[ -z "$node_onion" ]]; then
        node_onion="demo-node-gui.onion"
        log_warn "Using demo URL for Node GUI: $node_onion"
    fi
    
    # Export URLs for use in other functions
    export USER_ONION_URL="https://$user_onion"
    export ADMIN_ONION_URL="https://$admin_onion"
    export NODE_ONION_URL="https://$node_onion"
    
    log_verbose "User GUI URL: $USER_ONION_URL"
    log_verbose "Admin GUI URL: $ADMIN_ONION_URL"
    log_verbose "Node GUI URL: $NODE_ONION_URL"
}

# Generate QR code for a URL
generate_qr_code() {
    local url="$1"
    local service_name="$2"
    local output_format="$3"
    
    log_verbose "Generating QR code for $service_name: $url"
    
    case "$output_format" in
        ansi256)
            qrencode -t ANSI256 "$url"
            ;;
        png)
            local filename="$OUTPUT_DIR/${service_name}-gui-qr.png"
            qrencode -t PNG -o "$filename" "$url"
            echo "Saved: $filename"
            ;;
        svg)
            local filename="$OUTPUT_DIR/${service_name}-gui-qr.svg"
            qrencode -t SVG -o "$filename" "$url"
            echo "Saved: $filename"
            ;;
        eps)
            local filename="$OUTPUT_DIR/${service_name}-gui-qr.eps"
            qrencode -t EPS -o "$filename" "$url"
            echo "Saved: $filename"
            ;;
    esac
}

# Display QR codes on console
display_qr_codes() {
    if [[ "$DISPLAY_ON_CONSOLE" != "true" ]]; then
        return 0
    fi
    
    log_info "Generating QR codes for console display..."
    
    echo ""
    echo -e "${WHITE}=== Lucid RDP GUI Access ===${NC}"
    echo ""
    
    # User GUI
    echo -e "${CYAN}User GUI (End Users):${NC}"
    echo "$USER_ONION_URL"
    generate_qr_code "$USER_ONION_URL" "user" "ansi256"
    echo ""
    
    # Admin GUI
    echo -e "${CYAN}Admin GUI (Operators):${NC}"
    echo "$ADMIN_ONION_URL"
    generate_qr_code "$ADMIN_ONION_URL" "admin" "ansi256"
    echo ""
    
    # Node GUI
    echo -e "${CYAN}Node GUI (Node Workers):${NC}"
    echo "$NODE_ONION_URL"
    generate_qr_code "$NODE_ONION_URL" "node" "ansi256"
    echo ""
    
    echo -e "${GREEN}Scan any QR code above to access the corresponding GUI${NC}"
    echo ""
}

# Save QR codes to files
save_qr_codes() {
    if [[ "$SAVE_TO_FILE" != "true" ]]; then
        return 0
    fi
    
    log_info "Saving QR codes to files..."
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Generate QR codes for each service
    generate_qr_code "$USER_ONION_URL" "user" "$OUTPUT_FORMAT"
    generate_qr_code "$ADMIN_ONION_URL" "admin" "$OUTPUT_FORMAT"
    generate_qr_code "$NODE_ONION_URL" "node" "$OUTPUT_FORMAT"
    
    # Create HTML file for web display
    if [[ "$OUTPUT_FORMAT" == "png" || "$OUTPUT_FORMAT" == "svg" ]]; then
        local html_file="$OUTPUT_DIR/lucid-gui-access.html"
        cat > "$html_file" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid RDP GUI Access</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .gui-section {
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: #f9f9f9;
        }
        .gui-section h2 {
            color: #555;
            margin-top: 0;
        }
        .qr-code {
            text-align: center;
            margin: 20px 0;
        }
        .qr-code img {
            max-width: 200px;
            height: auto;
        }
        .url {
            font-family: monospace;
            background-color: #e9e9e9;
            padding: 10px;
            border-radius: 4px;
            word-break: break-all;
            margin: 10px 0;
        }
        .instructions {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #2196F3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Lucid RDP GUI Access</h1>
        
        <div class="instructions">
            <strong>Instructions:</strong> Scan the QR code with your mobile device or camera app to access the GUI directly. 
            Make sure you have Tor Browser installed on your device to access .onion URLs.
        </div>
        
        <div class="gui-section">
            <h2>User GUI (End Users)</h2>
            <div class="url">$USER_ONION_URL</div>
            <div class="qr-code">
EOF
        
        if [[ "$OUTPUT_FORMAT" == "png" ]]; then
            echo '                <img src="user-gui-qr.png" alt="User GUI QR Code">' >> "$html_file"
        elif [[ "$OUTPUT_FORMAT" == "svg" ]]; then
            echo '                <img src="user-gui-qr.svg" alt="User GUI QR Code">' >> "$html_file"
        fi
        
        cat >> "$html_file" << EOF
            </div>
            <p>Access your Lucid RDP sessions, manage policies, and view proofs.</p>
        </div>
        
        <div class="gui-section">
            <h2>Admin GUI (Operators)</h2>
            <div class="url">$ADMIN_ONION_URL</div>
            <div class="qr-code">
EOF
        
        if [[ "$OUTPUT_FORMAT" == "png" ]]; then
            echo '                <img src="admin-gui-qr.png" alt="Admin GUI QR Code">' >> "$html_file"
        elif [[ "$OUTPUT_FORMAT" == "svg" ]]; then
            echo '                <img src="admin-gui-qr.svg" alt="Admin GUI QR Code">' >> "$html_file"
        fi
        
        cat >> "$html_file" << EOF
            </div>
            <p>Manage Pi appliance, view manifests, handle payouts, and system diagnostics.</p>
        </div>
        
        <div class="gui-section">
            <h2>Node GUI (Node Workers)</h2>
            <div class="url">$NODE_ONION_URL</div>
            <div class="qr-code">
EOF
        
        if [[ "$OUTPUT_FORMAT" == "png" ]]; then
            echo '                <img src="node-gui-qr.png" alt="Node GUI QR Code">' >> "$html_file"
        elif [[ "$OUTPUT_FORMAT" == "svg" ]]; then
            echo '                <img src="node-gui-qr.svg" alt="Node GUI QR Code">' >> "$html_file"
        fi
        
        cat >> "$html_file" << EOF
            </div>
            <p>Monitor PoOT metrics, relay status, energy budgeting, and payout batches.</p>
        </div>
        
        <div class="instructions">
            <strong>Security Note:</strong> These .onion URLs provide secure, anonymous access to your Lucid RDP system. 
            Only share these URLs with authorized users.
        </div>
    </div>
</body>
</html>
EOF
        
        log_success "HTML file created: $html_file"
    fi
    
    # Create text file with URLs
    local text_file="$OUTPUT_DIR/lucid-gui-urls.txt"
    cat > "$text_file" << EOF
Lucid RDP GUI Access URLs
Generated: $(date)

User GUI (End Users):
$USER_ONION_URL

Admin GUI (Operators):
$ADMIN_ONION_URL

Node GUI (Node Workers):
$NODE_ONION_URL

Instructions:
1. Install Tor Browser on your device
2. Scan the QR code or manually enter the URL
3. Access the GUI through Tor Browser

Security Note:
These .onion URLs provide secure, anonymous access to your Lucid RDP system.
Only share these URLs with authorized users.
EOF
    
    log_success "Text file created: $text_file"
    log_success "QR codes saved to: $OUTPUT_DIR"
}

# Create systemd service for QR display
create_qr_display_service() {
    if [[ "$SAVE_TO_FILE" != "true" ]]; then
        return 0
    fi
    
    log_info "Creating systemd service for QR display..."
    
    # Create service file
    sudo tee /etc/systemd/system/lucid-qr-display.service > /dev/null << EOF
[Unit]
Description=Lucid RDP QR Code Display Service
After=tor.service
Requires=tor.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/lucid-qr-display.sh
RemainAfterExit=yes
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
EOF
    
    # Create QR display script
    sudo tee /usr/local/bin/lucid-qr-display.sh > /dev/null << 'EOF'
#!/bin/bash
set -euo pipefail

# Wait for Tor to be ready
until nc -z localhost 9050; do sleep 1; done

# Generate QR codes and display on console
/usr/local/bin/lucid-qr-generate.sh --display

# Also save to file for web access
/usr/local/bin/lucid-qr-generate.sh --save --format png --output-dir /var/www/html/qr
EOF
    
    sudo chmod +x /usr/local/bin/lucid-qr-display.sh
    sudo systemctl enable lucid-qr-display.service
    
    log_success "QR display service created and enabled"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Show help if requested
    if [[ "$HELP" == "true" ]]; then
        show_help
        exit 0
    fi
    
    log_info "Starting QR code generation..."
    log_info "Format: $OUTPUT_FORMAT"
    log_info "Display on console: $DISPLAY_ON_CONSOLE"
    log_info "Save to files: $SAVE_TO_FILE"
    if [[ "$SAVE_TO_FILE" == "true" ]]; then
        log_info "Output directory: $OUTPUT_DIR"
    fi
    log_info "Verbose: $VERBOSE"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Get .onion URLs
    get_onion_urls
    
    # Display QR codes on console
    display_qr_codes
    
    # Save QR codes to files
    save_qr_codes
    
    # Create systemd service if saving files
    if [[ "$SAVE_TO_FILE" == "true" ]]; then
        create_qr_display_service
    fi
    
    log_success "QR code generation completed!"
    
    if [[ "$SAVE_TO_FILE" == "true" ]]; then
        echo ""
        log_info "=== FILES CREATED ==="
        log_info "Output directory: $OUTPUT_DIR"
        if [[ "$OUTPUT_FORMAT" == "png" || "$OUTPUT_FORMAT" == "svg" ]]; then
            log_info "HTML file: $OUTPUT_DIR/lucid-gui-access.html"
        fi
        log_info "Text file: $OUTPUT_DIR/lucid-gui-urls.txt"
        log_info "Systemd service: lucid-qr-display.service"
    fi
}

# Run main function with all arguments
main "$@"

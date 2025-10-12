#!/bin/bash
# Lucid RDP - macOS Code Signing and Notarization Script
# =====================================================
#
# Signs and notarizes macOS applications using codesign and xcrun notarytool.
# Supports hardened runtime, entitlements, and Apple Developer ID certificates.
#
# Based on SPEC-2 requirements:
# - codesign --deep --options runtime for .app and .dmg
# - notarize with Apple Developer ID
# - staple notarization ticket
# - Verify signatures and notarization
#
# Usage:
#     ./sign_mac.sh -i "path/to/app.app" -c "Developer ID Application: Your Name"
#     ./sign_mac.sh -i "path/to/installer.dmg" -c "Developer ID Application: Your Name" --notarize
#
# Author: Lucid RDP Build System
# License: MIT

set -euo pipefail

# Default values
INPUT_PATH=""
CERTIFICATE_ID=""
ENTITLEMENTS_FILE=""
NOTARIZE=false
STAPLE=false
VERIFY_ONLY=false
OUTPUT_PATH=""
VERBOSE=false
HELP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print verbose output
verbose_print() {
    if [ "$VERBOSE" = true ]; then
        print_color "$GRAY" "VERBOSE: $1"
    fi
}

# Function to show help
show_help() {
    cat << EOF
Lucid RDP - macOS Code Signing and Notarization Script
====================================================

Signs and notarizes macOS applications using codesign and xcrun notarytool.

Usage: $0 [OPTIONS]

Options:
    -i, --input <path>           Path to file to sign (required)
    -c, --certificate <id>       Certificate ID for signing (required)
    -e, --entitlements <path>    Path to entitlements file
    -o, --output <path>          Output path for signed file
    --notarize                   Enable notarization
    --staple                     Staple notarization ticket
    --verify-only                Only verify existing signatures
    -v, --verbose                Enable verbose output
    -h, --help                   Show this help message

Environment Variables:
    MACOS_CERTIFICATE_ID         Default certificate ID
    MACOS_ENTITLEMENTS_FILE      Default entitlements file path
    MACOS_NOTARIZATION_USER      Apple ID for notarization
    MACOS_NOTARIZATION_PASSWORD  App-specific password for notarization
    MACOS_NOTARIZATION_TEAM_ID   Team ID for notarization

Examples:
    # Sign application bundle
    $0 -i "LucidUserGUI.app" -c "Developer ID Application: Your Name (ABC123DEF4)"
    
    # Sign and notarize DMG
    $0 -i "LucidUserGUI.dmg" -c "Developer ID Application: Your Name (ABC123DEF4)" --notarize --staple
    
    # Sign with entitlements
    $0 -i "LucidUserGUI.app" -c "Developer ID Application: Your Name (ABC123DEF4)" -e "entitlements.plist"
    
    # Verify signature only
    $0 -i "LucidUserGUI.app" --verify-only

Certificate Requirements:
    - Developer ID Application certificate for distribution outside App Store
    - Valid Apple Developer Program membership
    - Certificate installed in macOS Keychain

Notarization Requirements:
    - Apple ID with App Store Connect access
    - App-specific password for notarization
    - Team ID from Apple Developer account
EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_color "$CYAN" "Checking prerequisites..."
    
    # Check if running on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_color "$RED" "✗ This script must be run on macOS"
        exit 1
    fi
    
    # Check if codesign is available
    if ! command -v codesign &> /dev/null; then
        print_color "$RED" "✗ codesign command not found"
        exit 1
    fi
    
    # Check if xcrun is available
    if ! command -v xcrun &> /dev/null; then
        print_color "$RED" "✗ xcrun command not found"
        exit 1
    fi
    
    # Check if notarytool is available (for notarization)
    if [ "$NOTARIZE" = true ]; then
        if ! xcrun notarytool --help &> /dev/null; then
            print_color "$RED" "✗ xcrun notarytool not available (requires Xcode 13+)"
            exit 1
        fi
    fi
    
    verbose_print "✓ Prerequisites check passed"
}

# Function to validate input file
validate_input_file() {
    local input_path="$1"
    
    if [ ! -e "$input_path" ]; then
        print_color "$RED" "✗ Input file not found: $input_path"
        exit 1
    fi
    
    local extension="${input_path##*.}"
    case "$extension" in
        "app"|"dmg"|"pkg"|"framework"|"bundle"|"dylib")
            verbose_print "✓ Input file type supported: $extension"
            ;;
        *)
            print_color "$RED" "✗ Unsupported file type: $extension"
            exit 1
            ;;
    esac
}

# Function to validate certificate
validate_certificate() {
    local cert_id="$1"
    
    print_color "$YELLOW" "Validating certificate: $cert_id"
    
    # Check if certificate exists in keychain
    if ! security find-identity -v -p codesigning | grep -q "$cert_id"; then
        print_color "$RED" "✗ Certificate not found in keychain: $cert_id"
        print_color "$YELLOW" "Available certificates:"
        security find-identity -v -p codesigning | grep -v "0 valid identities found" || true
        exit 1
    fi
    
    # Get certificate details
    local cert_info=$(security find-certificate -c "$cert_id" -p | openssl x509 -text -noout 2>/dev/null || true)
    if [ -n "$cert_info" ]; then
        local expiry_date=$(echo "$cert_info" | openssl x509 -noout -enddate | cut -d= -f2)
        local subject=$(echo "$cert_info" | openssl x509 -noout -subject | sed 's/subject=//')
        
        print_color "$CYAN" "Certificate Information:"
        print_color "$GRAY" "  Subject: $subject"
        print_color "$GRAY" "  Expires: $expiry_date"
        
        # Check if certificate is expired
        local expiry_timestamp=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null || echo "0")
        local current_timestamp=$(date +%s)
        
        if [ "$expiry_timestamp" -lt "$current_timestamp" ]; then
            print_color "$RED" "✗ Certificate has expired"
            exit 1
        fi
    fi
    
    verbose_print "✓ Certificate validation passed"
}

# Function to create default entitlements
create_default_entitlements() {
    local entitlements_file="$1"
    
    if [ -f "$entitlements_file" ]; then
        verbose_print "Using existing entitlements file: $entitlements_file"
        return
    fi
    
    print_color "$YELLOW" "Creating default entitlements file: $entitlements_file"
    
    cat > "$entitlements_file" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Allow network connections -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- Allow file access -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    
    <!-- Disable library validation for bundled libraries -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    
    <!-- Disable hardened runtime for GUI applications that need it -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
EOF
    
    verbose_print "✓ Default entitlements file created"
}

# Function to sign file
sign_file() {
    local input_path="$1"
    local cert_id="$2"
    local entitlements_file="$3"
    
    print_color "$YELLOW" "Signing file: $input_path"
    
    local codesign_args=(
        "--sign" "$cert_id"
        "--force"
        "--verbose"
    )
    
    # Add entitlements if provided
    if [ -n "$entitlements_file" ] && [ -f "$entitlements_file" ]; then
        codesign_args+=("--entitlements" "$entitlements_file")
        verbose_print "Using entitlements: $entitlements_file"
    fi
    
    # Add hardened runtime for applications
    local extension="${input_path##*.}"
    if [ "$extension" = "app" ] || [ "$extension" = "framework" ] || [ "$extension" = "bundle" ]; then
        codesign_args+=("--options" "runtime")
        verbose_print "Using hardened runtime"
    fi
    
    # Add deep signing for app bundles
    if [ "$extension" = "app" ]; then
        codesign_args+=("--deep")
        verbose_print "Using deep signing for app bundle"
    fi
    
    codesign_args+=("$input_path")
    
    verbose_print "Running: codesign ${codesign_args[*]}"
    
    if codesign "${codesign_args[@]}"; then
        print_color "$GREEN" "✓ File signed successfully"
        return 0
    else
        print_color "$RED" "✗ Signing failed"
        return 1
    fi
}

# Function to verify signature
verify_signature() {
    local input_path="$1"
    
    print_color "$YELLOW" "Verifying signature: $input_path"
    
    # Basic signature verification
    if codesign --verify --verbose "$input_path"; then
        print_color "$GREEN" "✓ Signature verification successful"
    else
        print_color "$RED" "✗ Signature verification failed"
        return 1
    fi
    
    # Display signature information
    print_color "$CYAN" "Signature Information:"
    codesign --display --verbose=4 "$input_path" 2>/dev/null || true
    
    # Check for hardened runtime
    if codesign --verify --verbose=4 "$input_path" 2>&1 | grep -q "valid on disk"; then
        print_color "$GREEN" "✓ Signature is valid on disk"
    else
        print_color "$YELLOW" "⚠ Signature may have issues"
    fi
    
    return 0
}

# Function to notarize file
notarize_file() {
    local input_path="$1"
    
    # Check environment variables for notarization credentials
    local apple_id="${MACOS_NOTARIZATION_USER:-}"
    local password="${MACOS_NOTARIZATION_PASSWORD:-}"
    local team_id="${MACOS_NOTARIZATION_TEAM_ID:-}"
    
    if [ -z "$apple_id" ] || [ -z "$password" ]; then
        print_color "$RED" "✗ Notarization credentials not provided"
        print_color "$YELLOW" "Set environment variables:"
        print_color "$GRAY" "  MACOS_NOTARIZATION_USER - Apple ID"
        print_color "$GRAY" "  MACOS_NOTARIZATION_PASSWORD - App-specific password"
        print_color "$GRAY" "  MACOS_NOTARIZATION_TEAM_ID - Team ID (optional)"
        exit 1
    fi
    
    print_color "$YELLOW" "Submitting for notarization: $input_path"
    
    local notary_args=(
        "submit"
        "$input_path"
        "--apple-id" "$apple_id"
        "--password" "$password"
    )
    
    if [ -n "$team_id" ]; then
        notary_args+=("--team-id" "$team_id")
    fi
    
    verbose_print "Running: xcrun notarytool ${notary_args[*]}"
    
    # Submit for notarization
    local submission_id
    if submission_id=$(xcrun notarytool "${notary_args[@]}" 2>&1 | grep -o 'id: [a-f0-9-]*' | cut -d' ' -f2); then
        print_color "$GREEN" "✓ Notarization submitted successfully"
        print_color "$CYAN" "Submission ID: $submission_id"
    else
        print_color "$RED" "✗ Notarization submission failed"
        return 1
    fi
    
    # Wait for notarization to complete
    print_color "$YELLOW" "Waiting for notarization to complete..."
    
    local status_args=(
        "info" "$submission_id"
        "--apple-id" "$apple_id"
        "--password" "$password"
    )
    
    if [ -n "$team_id" ]; then
        status_args+=("--team-id" "$team_id")
    fi
    
    local max_attempts=60  # 30 minutes max
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local status_output
        if status_output=$(xcrun notarytool "${status_args[@]}" 2>&1); then
            if echo "$status_output" | grep -q "status: Accepted"; then
                print_color "$GREEN" "✓ Notarization accepted"
                return 0
            elif echo "$status_output" | grep -q "status: Invalid"; then
                print_color "$RED" "✗ Notarization rejected"
                echo "$status_output"
                return 1
            else
                print_color "$YELLOW" "Notarization in progress... (attempt $((attempt + 1))/$max_attempts)"
                sleep 30
                ((attempt++))
            fi
        else
            print_color "$RED" "✗ Error checking notarization status"
            return 1
        fi
    done
    
    print_color "$RED" "✗ Notarization timed out"
    return 1
}

# Function to staple notarization ticket
staple_notarization() {
    local input_path="$1"
    
    print_color "$YELLOW" "Stapling notarization ticket: $input_path"
    
    if xcrun stapler staple "$input_path"; then
        print_color "$GREEN" "✓ Notarization ticket stapled successfully"
        return 0
    else
        print_color "$RED" "✗ Failed to staple notarization ticket"
        return 1
    fi
}

# Function to verify notarization
verify_notarization() {
    local input_path="$1"
    
    print_color "$YELLOW" "Verifying notarization: $input_path"
    
    if xcrun stapler validate "$input_path"; then
        print_color "$GREEN" "✓ Notarization verification successful"
        return 0
    else
        print_color "$RED" "✗ Notarization verification failed"
        return 1
    fi
}

# Function to copy file if output path is specified
copy_signed_file() {
    local source_path="$1"
    local output_path="$2"
    
    print_color "$YELLOW" "Copying signed file to: $output_path"
    
    if cp -R "$source_path" "$output_path"; then
        print_color "$GREEN" "✓ Signed file copied successfully"
        return 0
    else
        print_color "$RED" "✗ Failed to copy signed file"
        return 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_PATH="$2"
            shift 2
            ;;
        -c|--certificate)
            CERTIFICATE_ID="$2"
            shift 2
            ;;
        -e|--entitlements)
            ENTITLEMENTS_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        --notarize)
            NOTARIZE=true
            shift
            ;;
        --staple)
            STAPLE=true
            shift
            ;;
        --verify-only)
            VERIFY_ONLY=true
            shift
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
            print_color "$RED" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$HELP" = true ]; then
    show_help
    exit 0
fi

# Main execution
main() {
    print_color "$CYAN" "Lucid RDP - macOS Code Signing and Notarization Script"
    print_color "$CYAN" "====================================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Validate input file
    if [ -z "$INPUT_PATH" ]; then
        print_color "$RED" "✗ Input path is required"
        show_help
        exit 1
    fi
    
    validate_input_file "$INPUT_PATH"
    
    # If only verification is requested
    if [ "$VERIFY_ONLY" = true ]; then
        print_color "$YELLOW" "Verification mode only"
        if verify_signature "$INPUT_PATH"; then
            if [ "$NOTARIZE" = true ]; then
                verify_notarization "$INPUT_PATH"
            fi
            exit 0
        else
            exit 1
        fi
    fi
    
    # Get default values from environment variables
    if [ -z "$CERTIFICATE_ID" ] && [ -n "${MACOS_CERTIFICATE_ID:-}" ]; then
        CERTIFICATE_ID="$MACOS_CERTIFICATE_ID"
        verbose_print "Using certificate ID from environment"
    fi
    
    if [ -z "$ENTITLEMENTS_FILE" ] && [ -n "${MACOS_ENTITLEMENTS_FILE:-}" ]; then
        ENTITLEMENTS_FILE="$MACOS_ENTITLEMENTS_FILE"
        verbose_print "Using entitlements file from environment"
    fi
    
    # Validate certificate
    if [ -z "$CERTIFICATE_ID" ]; then
        print_color "$RED" "✗ Certificate ID is required"
        show_help
        exit 1
    fi
    
    validate_certificate "$CERTIFICATE_ID"
    
    # Create default entitlements if needed
    local temp_entitlements=""
    if [ -z "$ENTITLEMENTS_FILE" ]; then
        temp_entitlements=$(mktemp -t entitlements.plist)
        create_default_entitlements "$temp_entitlements"
        ENTITLEMENTS_FILE="$temp_entitlements"
    fi
    
    # Sign the file
    if ! sign_file "$INPUT_PATH" "$CERTIFICATE_ID" "$ENTITLEMENTS_FILE"; then
        exit 1
    fi
    
    # Verify signature
    if ! verify_signature "$INPUT_PATH"; then
        exit 1
    fi
    
    # Notarize if requested
    if [ "$NOTARIZE" = true ]; then
        if ! notarize_file "$INPUT_PATH"; then
            exit 1
        fi
        
        # Staple if requested
        if [ "$STAPLE" = true ]; then
            if ! staple_notarization "$INPUT_PATH"; then
                exit 1
            fi
            
            # Verify notarization
            if ! verify_notarization "$INPUT_PATH"; then
                exit 1
            fi
        fi
    fi
    
    # Copy to output path if specified
    if [ -n "$OUTPUT_PATH" ]; then
        if ! copy_signed_file "$INPUT_PATH" "$OUTPUT_PATH"; then
            exit 1
        fi
    fi
    
    # Clean up temporary files
    if [ -n "$temp_entitlements" ] && [ -f "$temp_entitlements" ]; then
        rm -f "$temp_entitlements"
    fi
    
    print_color "$GREEN" "✓ Code signing completed successfully"
}

# Run main function
main

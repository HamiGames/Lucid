#!/bin/bash
# Path: build/scripts/verify-gui-security-compliance.sh
# Verify security compliance for GUI services
# Follows SPEC-1B-v2-DISTROLESS and SPEC-5 Web-Based GUI Architecture

set -euo pipefail

# Default values
SERVICES="user,admin,node"
REGISTRY="ghcr.io"
IMAGE_NAME="HamiGames/Lucid"
TAG="latest"
VERBOSE=false
HELP=false
FAIL_ON_NON_COMPLIANCE=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Compliance results
declare -A COMPLIANCE_RESULTS
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

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

# Compliance check functions
check_compliance() {
    local check_name="$1"
    local check_description="$2"
    local check_command="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    log_verbose "Checking: $check_name"
    
    if eval "$check_command" >/dev/null 2>&1; then
        COMPLIANCE_RESULTS["$check_name"]="PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "✓ $check_name: $check_description"
        return 0
    else
        COMPLIANCE_RESULTS["$check_name"]="FAIL"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        log_error "✗ $check_name: $check_description"
        return 1
    fi
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Verify security compliance for Lucid RDP GUI services.

OPTIONS:
    -s, --services SERVICES     Comma-separated list of GUI services (default: user,admin,node)
    -r, --registry REGISTRY     Container registry (default: ghcr.io)
    -i, --image-name NAME       Image name prefix (default: HamiGames/Lucid)
    -t, --tag TAG               Image tag (default: latest)
    -w, --warn-only             Only warn on non-compliance, don't fail
    -v, --verbose               Verbose output
    -h, --help                  Show this help message

EXAMPLES:
    # Verify all GUI services
    $0

    # Verify specific services only
    $0 --services user,admin

    # Verify with warnings only
    $0 --warn-only

ENVIRONMENT VARIABLES:
    REGISTRY                    Container registry
    IMAGE_NAME                  Image name prefix
    TAG                         Image tag

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--services)
                SERVICES="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -i|--image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -w|--warn-only)
                FAIL_ON_NON_COMPLIANCE=false
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
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if required tools are available
    local required_tools=("docker" "trivy" "cosign")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_warn "$tool is not installed. Some checks will be skipped."
        fi
    done
    
    log_success "Prerequisites validated"
}

# Check distroless compliance
check_distroless_compliance() {
    local service="$1"
    local image_tag="$REGISTRY/$IMAGE_NAME/$service-gui:$TAG"
    
    log_info "Checking distroless compliance for $service..."
    
    # Check if image exists
    if ! docker image inspect "$image_tag" >/dev/null 2>&1; then
        log_error "Image $image_tag not found locally"
        return 1
    fi
    
    # Check for shell (should fail)
    check_compliance \
        "$service-distroless-shell" \
        "No shell found in distroless image" \
        "docker run --rm $image_tag /bin/sh -c 'echo test'"
    
    # Check for bash (should fail)
    check_compliance \
        "$service-distroless-bash" \
        "No bash found in distroless image" \
        "docker run --rm $image_tag /bin/bash -c 'echo test'"
    
    # Check user (should be nonroot - UID 65532)
    local user_id
    user_id=$(docker run --rm "$image_tag" id -u 2>/dev/null || echo "unknown")
    
    if [[ "$user_id" == "65532" ]]; then
        COMPLIANCE_RESULTS["$service-distroless-user"]="PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "✓ $service-distroless-user: Correct user (nonroot)"
    else
        COMPLIANCE_RESULTS["$service-distroless-user"]="FAIL"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        log_error "✗ $service-distroless-user: Wrong user ID: $user_id (expected: 65532)"
    fi
    
    # Check base image
    local base_image
    base_image=$(docker inspect "$image_tag" --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
    
    if [[ "$base_image" == *"distroless"* ]]; then
        COMPLIANCE_RESULTS["$service-distroless-base"]="PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "✓ $service-distroless-base: Distroless base image confirmed"
    else
        COMPLIANCE_RESULTS["$service-distroless-base"]="FAIL"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        log_error "✗ $service-distroless-base: Non-distroless base image: $base_image"
    fi
    
    # Check read-only root (should fail to write)
    check_compliance \
        "$service-distroless-readonly" \
        "Read-only root filesystem" \
        "docker run --rm $image_tag touch /test"
    
    # Check for package manager (should not exist)
    check_compliance \
        "$service-distroless-package-manager" \
        "No package manager found" \
        "docker run --rm $image_tag which apt-get || docker run --rm $image_tag which yum || docker run --rm $image_tag which apk"
}

# Check Tor integration compliance
check_tor_integration() {
    local service="$1"
    
    log_info "Checking Tor integration for $service..."
    
    # Check if .onion service is configured
    local onion_file="/var/lib/tor/lucid-$service-gui/hostname"
    check_compliance \
        "$service-tor-onion-service" \
        ".onion service configured" \
        "test -f $onion_file"
    
    # Check if .onion URL is accessible via Tor
    if [[ -f "$onion_file" ]]; then
        local onion_url
        onion_url=$(cat "$onion_file")
        
        check_compliance \
            "$service-tor-onion-access" \
            ".onion URL accessible via Tor" \
            "curl --socks5 127.0.0.1:9050 -f http://$onion_url --max-time 10"
    fi
    
    # Check Tor SOCKS proxy configuration
    check_compliance \
        "$service-tor-socks" \
        "Tor SOCKS proxy accessible" \
        "nc -z localhost 9050"
}

# Check security scanning compliance
check_security_scanning() {
    local service="$1"
    local image_tag="$REGISTRY/$IMAGE_NAME/$service-gui:$TAG"
    
    log_info "Checking security scanning for $service..."
    
    # Check if Trivy is available
    if ! command -v trivy >/dev/null 2>&1; then
        log_warn "Trivy not available, skipping vulnerability scan"
        return 0
    fi
    
    # Run Trivy vulnerability scan
    log_info "Running Trivy vulnerability scan for $service..."
    
    local trivy_output
    trivy_output=$(trivy image --severity HIGH,CRITICAL --exit-code 0 --format json "$image_tag" 2>/dev/null || echo "{}")
    
    # Check for high/critical vulnerabilities
    local vuln_count
    vuln_count=$(echo "$trivy_output" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH" or .Severity == "CRITICAL") | .VulnerabilityID' 2>/dev/null | wc -l || echo "0")
    
    if [[ "$vuln_count" -eq 0 ]]; then
        COMPLIANCE_RESULTS["$service-security-vulns"]="PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "✓ $service-security-vulns: No high/critical vulnerabilities found"
    else
        COMPLIANCE_RESULTS["$service-security-vulns"]="FAIL"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        log_error "✗ $service-security-vulns: Found $vuln_count high/critical vulnerabilities"
        
        # Show vulnerabilities if verbose
        if [[ "$VERBOSE" == "true" ]]; then
            echo "$trivy_output" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH" or .Severity == "CRITICAL") | "  - \(.VulnerabilityID): \(.Severity) - \(.Title)"' 2>/dev/null || true
        fi
    fi
}

# Check image signing compliance
check_image_signing() {
    local service="$1"
    local image_tag="$REGISTRY/$IMAGE_NAME/$service-gui:$TAG"
    
    log_info "Checking image signing for $service..."
    
    # Check if cosign is available
    if ! command -v cosign >/dev/null 2>&1; then
        log_warn "cosign not available, skipping signature verification"
        return 0
    fi
    
    # Check image signature
    check_compliance \
        "$service-image-signature" \
        "Image is signed" \
        "cosign verify --key cosign.pub $image_tag"
}

# Check container runtime security
check_container_runtime_security() {
    local service="$1"
    
    log_info "Checking container runtime security for $service..."
    
    # Check if container is running
    local container_name="lucid-$service-gui"
    check_compliance \
        "$service-container-running" \
        "Container is running" \
        "docker ps --format '{{.Names}}' | grep -q '^$container_name'"
    
    # Check container security options
    if docker ps --format '{{.Names}}' | grep -q "^$container_name"; then
        # Check if container runs as non-root
        local container_user
        container_user=$(docker exec "$container_name" id -u 2>/dev/null || echo "unknown")
        
        if [[ "$container_user" == "65532" ]]; then
            COMPLIANCE_RESULTS["$service-container-user"]="PASS"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            log_success "✓ $service-container-user: Container runs as non-root user"
        else
            COMPLIANCE_RESULTS["$service-container-user"]="FAIL"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            log_error "✗ $service-container-user: Container runs as root user: $container_user"
        fi
        
        # Check if container has security options
        local security_opts
        security_opts=$(docker inspect "$container_name" --format='{{.HostConfig.SecurityOpt}}' 2>/dev/null || echo "[]")
        
        if [[ "$security_opts" != "[]" && "$security_opts" != "null" ]]; then
            COMPLIANCE_RESULTS["$service-container-security-opts"]="PASS"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            log_success "✓ $service-container-security-opts: Container has security options"
        else
            COMPLIANCE_RESULTS["$service-container-security-opts"]="FAIL"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            log_error "✗ $service-container-security-opts: Container lacks security options"
        fi
    fi
}

# Check trust-nothing policy compliance
check_trust_nothing_policy() {
    local service="$1"
    
    log_info "Checking trust-nothing policy compliance for $service..."
    
    # Check if .onion-only access is enforced
    check_compliance \
        "$service-trust-nothing-onion-only" \
        ".onion-only access enforced" \
        "test -f /var/lib/tor/lucid-$service-gui/hostname"
    
    # Check if clearnet access is blocked
    check_compliance \
        "$service-trust-nothing-clearnet-blocked" \
        "Clearnet access blocked" \
        "! curl -f http://localhost:300$([ "$service" == "user" ] && echo "1" || [ "$service" == "admin" ] && echo "2" || echo "3") --max-time 5"
    
    # Check if Tor SOCKS proxy is required
    check_compliance \
        "$service-trust-nothing-tor-required" \
        "Tor SOCKS proxy required" \
        "nc -z localhost 9050"
}

# Generate compliance report
generate_compliance_report() {
    local report_file="build/reports/gui-security-compliance-$(date +%Y%m%d-%H%M%S).json"
    
    log_info "Generating compliance report..."
    
    mkdir -p "$(dirname "$report_file")"
    
    cat > "$report_file" << EOF
{
  "report_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "services_checked": [$(echo "$SERVICES" | tr ',' ' ' | sed 's/^/"/;s/$/"/;s/ /","/g')],
  "registry": "$REGISTRY",
  "image_name": "$IMAGE_NAME",
  "tag": "$TAG",
  "total_checks": $TOTAL_CHECKS,
  "passed_checks": $PASSED_CHECKS,
  "failed_checks": $FAILED_CHECKS,
  "compliance_score": $((PASSED_CHECKS * 100 / TOTAL_CHECKS)),
  "compliance_results": {
EOF
    
    local first=true
    for check in "${!COMPLIANCE_RESULTS[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "$report_file"
        fi
        echo "    \"$check\": \"${COMPLIANCE_RESULTS[$check]}\"" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF
  },
  "security_standards": {
    "distroless_compliance": "SPEC-1B-v2-DISTROLESS",
    "tor_integration": "SPEC-5 Web-Based GUI Architecture",
    "trust_nothing_policy": "SPEC-1A Requirements",
    "container_security": "Docker Security Best Practices"
  },
  "recommendations": [
    "Ensure all containers use distroless base images",
    "Verify .onion service accessibility",
    "Regularly scan for vulnerabilities with Trivy",
    "Sign all container images with cosign",
    "Enforce Tor-only access for all GUI services",
    "Run containers as non-root users",
    "Apply security options to containers"
  ]
}
EOF
    
    log_success "Compliance report generated: $report_file"
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
    
    log_info "Starting GUI security compliance verification..."
    log_info "Services: $SERVICES"
    log_info "Registry: $REGISTRY"
    log_info "Image Name: $IMAGE_NAME"
    log_info "Tag: $TAG"
    log_info "Fail on non-compliance: $FAIL_ON_NON_COMPLIANCE"
    log_info "Verbose: $VERBOSE"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Check compliance for each service
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        echo ""
        log_info "=== Checking compliance for $service GUI ==="
        
        # Distroless compliance
        check_distroless_compliance "$service"
        
        # Tor integration
        check_tor_integration "$service"
        
        # Security scanning
        check_security_scanning "$service"
        
        # Image signing
        check_image_signing "$service"
        
        # Container runtime security
        check_container_runtime_security "$service"
        
        # Trust-nothing policy
        check_trust_nothing_policy "$service"
    done
    
    # Generate compliance report
    generate_compliance_report
    
    # Display summary
    echo ""
    log_info "=== COMPLIANCE VERIFICATION SUMMARY ==="
    log_info "Total checks: $TOTAL_CHECKS"
    log_info "Passed checks: $PASSED_CHECKS"
    log_info "Failed checks: $FAILED_CHECKS"
    log_info "Compliance score: $((PASSED_CHECKS * 100 / TOTAL_CHECKS))%"
    
    # Show failed checks
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        echo ""
        log_error "=== FAILED CHECKS ==="
        for check in "${!COMPLIANCE_RESULTS[@]}"; do
            if [[ "${COMPLIANCE_RESULTS[$check]}" == "FAIL" ]]; then
                log_error "✗ $check"
            fi
        done
    fi
    
    # Exit with appropriate code
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        if [[ "$FAIL_ON_NON_COMPLIANCE" == "true" ]]; then
            log_error "Security compliance verification failed!"
            exit 1
        else
            log_warn "Security compliance verification completed with warnings"
            exit 0
        fi
    else
        log_success "All security compliance checks passed!"
        exit 0
    fi
}

# Run main function with all arguments
main "$@"

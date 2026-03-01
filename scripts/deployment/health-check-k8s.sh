#!/bin/bash

# Lucid Kubernetes Health Check Script
# Step 52: Production Kubernetes Deployment
# Version: 1.0.0
# Last Updated: 2025-01-14

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NAMESPACE="${NAMESPACE:-lucid-system}"
TIMEOUT="${TIMEOUT:-30}"
VERBOSE="${VERBOSE:-false}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-text}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
declare -A HEALTH_RESULTS
OVERALL_HEALTH="HEALTHY"

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

# Health check functions
check_namespace() {
    log_info "Checking namespace: ${NAMESPACE}"
    
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        HEALTH_RESULTS["namespace"]="UNHEALTHY"
        log_error "Namespace ${NAMESPACE} does not exist"
        return 1
    fi
    
    HEALTH_RESULTS["namespace"]="HEALTHY"
    log_success "Namespace ${NAMESPACE} exists"
    return 0
}

check_pods() {
    log_info "Checking pod health..."
    
    local unhealthy_pods=0
    local total_pods=0
    
    # Get all pods in namespace
    local pods=$(kubectl get pods -n "${NAMESPACE}" --no-headers 2>/dev/null || echo "")
    
    if [[ -z "${pods}" ]]; then
        HEALTH_RESULTS["pods"]="UNHEALTHY"
        log_error "No pods found in namespace ${NAMESPACE}"
        return 1
    fi
    
    # Count total pods
    total_pods=$(echo "${pods}" | wc -l)
    
    # Check each pod
    while IFS= read -r pod_line; do
        if [[ -n "${pod_line}" ]]; then
            local pod_name=$(echo "${pod_line}" | awk '{print $1}')
            local pod_status=$(echo "${pod_line}" | awk '{print $3}')
            local pod_ready=$(echo "${pod_line}" | awk '{print $2}')
            
            if [[ "${pod_status}" != "Running" ]] || [[ "${pod_ready}" != *"/"* ]] || [[ "${pod_ready}" == *"0/"* ]]; then
                ((unhealthy_pods++))
                if [[ "${VERBOSE}" == "true" ]]; then
                    log_warning "Pod ${pod_name} is not healthy (Status: ${pod_status}, Ready: ${pod_ready})"
                fi
            fi
        fi
    done <<< "${pods}"
    
    if [[ "${unhealthy_pods}" -gt 0 ]]; then
        HEALTH_RESULTS["pods"]="UNHEALTHY"
        log_error "Found ${unhealthy_pods} unhealthy pods out of ${total_pods} total"
        return 1
    fi
    
    HEALTH_RESULTS["pods"]="HEALTHY"
    log_success "All ${total_pods} pods are healthy"
    return 0
}

check_deployments() {
    log_info "Checking deployment health..."
    
    local deployments=(
        "api-gateway"
        "blockchain-engine"
        "session-management"
        "rdp-services"
        "node-management"
        "admin-interface"
        "tron-payment"
        "auth-service"
        "service-mesh-controller"
    )
    
    local unhealthy_deployments=0
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "${deployment}" -n "${NAMESPACE}" &> /dev/null; then
            local available=$(kubectl get deployment "${deployment}" -n "${NAMESPACE}" -o jsonpath='{.status.availableReplicas}')
            local desired=$(kubectl get deployment "${deployment}" -n "${NAMESPACE}" -o jsonpath='{.spec.replicas}')
            
            if [[ "${available}" != "${desired}" ]]; then
                ((unhealthy_deployments++))
                if [[ "${VERBOSE}" == "true" ]]; then
                    log_warning "Deployment ${deployment} has ${available}/${desired} available replicas"
                fi
            fi
        else
            ((unhealthy_deployments++))
            if [[ "${VERBOSE}" == "true" ]]; then
                log_warning "Deployment ${deployment} not found"
            fi
        fi
    done
    
    if [[ "${unhealthy_deployments}" -gt 0 ]]; then
        HEALTH_RESULTS["deployments"]="UNHEALTHY"
        log_error "Found ${unhealthy_deployments} unhealthy deployments"
        return 1
    fi
    
    HEALTH_RESULTS["deployments"]="HEALTHY"
    log_success "All deployments are healthy"
    return 0
}

check_services() {
    log_info "Checking service health..."
    
    local services=$(kubectl get services -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l)
    
    if [[ "${services}" -eq 0 ]]; then
        HEALTH_RESULTS["services"]="UNHEALTHY"
        log_error "No services found in namespace ${NAMESPACE}"
        return 1
    fi
    
    HEALTH_RESULTS["services"]="HEALTHY"
    log_success "Found ${services} services"
    return 0
}

check_ingress() {
    log_info "Checking ingress health..."
    
    local ingress_count=$(kubectl get ingress -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l)
    
    if [[ "${ingress_count}" -eq 0 ]]; then
        HEALTH_RESULTS["ingress"]="WARNING"
        log_warning "No ingress resources found"
        return 0
    fi
    
    # Check ingress status
    local unhealthy_ingress=0
    while IFS= read -r ingress_line; do
        if [[ -n "${ingress_line}" ]]; then
            local ingress_name=$(echo "${ingress_line}" | awk '{print $1}')
            local ingress_class=$(echo "${ingress_line}" | awk '{print $3}')
            
            if [[ -z "${ingress_class}" ]]; then
                ((unhealthy_ingress++))
                if [[ "${VERBOSE}" == "true" ]]; then
                    log_warning "Ingress ${ingress_name} has no ingress class"
                fi
            fi
        fi
    done <<< "$(kubectl get ingress -n "${NAMESPACE}" --no-headers 2>/dev/null || echo "")"
    
    if [[ "${unhealthy_ingress}" -gt 0 ]]; then
        HEALTH_RESULTS["ingress"]="UNHEALTHY"
        log_error "Found ${unhealthy_ingress} unhealthy ingress resources"
        return 1
    fi
    
    HEALTH_RESULTS["ingress"]="HEALTHY"
    log_success "All ingress resources are healthy"
    return 0
}

check_persistent_volumes() {
    log_info "Checking persistent volume health..."
    
    local pvcs=$(kubectl get pvc -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l)
    local bound_pvcs=0
    
    if [[ "${pvcs}" -gt 0 ]]; then
        while IFS= read -r pvc_line; do
            if [[ -n "${pvc_line}" ]]; then
                local pvc_status=$(echo "${pvc_line}" | awk '{print $2}')
                if [[ "${pvc_status}" == "Bound" ]]; then
                    ((bound_pvcs++))
                fi
            fi
        done <<< "$(kubectl get pvc -n "${NAMESPACE}" --no-headers 2>/dev/null || echo "")"
        
        if [[ "${bound_pvcs}" != "${pvcs}" ]]; then
            HEALTH_RESULTS["pvc"]="UNHEALTHY"
            log_error "Found ${pvcs} PVCs, but only ${bound_pvcs} are bound"
            return 1
        fi
    fi
    
    HEALTH_RESULTS["pvc"]="HEALTHY"
    log_success "All persistent volume claims are healthy"
    return 0
}

check_application_health() {
    log_info "Checking application health endpoints..."
    
    # Get API Gateway service
    local api_gateway_service=$(kubectl get service api-gateway -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -z "${api_gateway_service}" ]]; then
        api_gateway_service=$(kubectl get service api-gateway -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    fi
    
    if [[ -n "${api_gateway_service}" ]]; then
        # Test health endpoint
        if curl -f -s --max-time "${TIMEOUT}" "http://${api_gateway_service}:8080/health" &> /dev/null; then
            HEALTH_RESULTS["app_health"]="HEALTHY"
            log_success "Application health endpoint is responding"
        else
            HEALTH_RESULTS["app_health"]="UNHEALTHY"
            log_error "Application health endpoint is not responding"
            return 1
        fi
    else
        HEALTH_RESULTS["app_health"]="WARNING"
        log_warning "API Gateway service not found, cannot test application health"
    fi
    
    return 0
}

check_resource_usage() {
    log_info "Checking resource usage..."
    
    # Check CPU and memory usage
    local high_cpu_pods=$(kubectl top pods -n "${NAMESPACE}" --no-headers 2>/dev/null | awk '$2 > 80' | wc -l)
    local high_memory_pods=$(kubectl top pods -n "${NAMESPACE}" --no-headers 2>/dev/null | awk '$3 > 80' | wc -l)
    
    if [[ "${high_cpu_pods}" -gt 0 ]]; then
        log_warning "Found ${high_cpu_pods} pods with high CPU usage (>80%)"
    fi
    
    if [[ "${high_memory_pods}" -gt 0 ]]; then
        log_warning "Found ${high_memory_pods} pods with high memory usage (>80%)"
    fi
    
    if [[ "${high_cpu_pods}" -gt 0 ]] || [[ "${high_memory_pods}" -gt 0 ]]; then
        HEALTH_RESULTS["resources"]="WARNING"
    else
        HEALTH_RESULTS["resources"]="HEALTHY"
    fi
    
    log_success "Resource usage check completed"
    return 0
}

# Generate health report
generate_report() {
    log_info "Generating health report..."
    
    if [[ "${OUTPUT_FORMAT}" == "json" ]]; then
        generate_json_report
    else
        generate_text_report
    fi
}

generate_text_report() {
    echo "=== Lucid System Health Report ==="
    echo "Namespace: ${NAMESPACE}"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    for component in "${!HEALTH_RESULTS[@]}"; do
        local status="${HEALTH_RESULTS[$component]}"
        case "${status}" in
            "HEALTHY")
                echo -e "✓ ${component}: ${GREEN}${status}${NC}"
                ;;
            "WARNING")
                echo -e "⚠ ${component}: ${YELLOW}${status}${NC}"
                ;;
            "UNHEALTHY")
                echo -e "✗ ${component}: ${RED}${status}${NC}"
                ;;
        esac
    done
    
    echo ""
    echo "=== Overall Status ==="
    if [[ "${OVERALL_HEALTH}" == "HEALTHY" ]]; then
        echo -e "Overall: ${GREEN}${OVERALL_HEALTH}${NC}"
    else
        echo -e "Overall: ${RED}${OVERALL_HEALTH}${NC}"
    fi
}

generate_json_report() {
    echo "{"
    echo "  \"namespace\": \"${NAMESPACE}\","
    echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    echo "  \"overall_health\": \"${OVERALL_HEALTH}\","
    echo "  \"components\": {"
    
    local first=true
    for component in "${!HEALTH_RESULTS[@]}"; do
        if [[ "${first}" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        echo -n "    \"${component}\": \"${HEALTH_RESULTS[$component]}\""
    done
    
    echo ""
    echo "  }"
    echo "}"
}

# Calculate overall health
calculate_overall_health() {
    for status in "${HEALTH_RESULTS[@]}"; do
        if [[ "${status}" == "UNHEALTHY" ]]; then
            OVERALL_HEALTH="UNHEALTHY"
            return
        elif [[ "${status}" == "WARNING" ]] && [[ "${OVERALL_HEALTH}" == "HEALTHY" ]]; then
            OVERALL_HEALTH="WARNING"
        fi
    done
}

# Main function
main() {
    log_info "Starting Kubernetes health check..."
    log_info "Namespace: ${NAMESPACE}"
    log_info "Timeout: ${TIMEOUT}s"
    log_info "Verbose: ${VERBOSE}"
    
    # Run all health checks
    check_namespace
    check_pods
    check_deployments
    check_services
    check_ingress
    check_persistent_volumes
    check_application_health
    check_resource_usage
    
    # Calculate overall health
    calculate_overall_health
    
    # Generate report
    generate_report
    
    # Exit with appropriate code
    if [[ "${OVERALL_HEALTH}" == "HEALTHY" ]]; then
        log_success "Health check completed successfully"
        exit 0
    elif [[ "${OVERALL_HEALTH}" == "WARNING" ]]; then
        log_warning "Health check completed with warnings"
        exit 1
    else
        log_error "Health check failed"
        exit 2
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="true"
            shift
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --namespace NS        Set Kubernetes namespace (default: lucid-system)"
            echo "  --timeout SECONDS    Set timeout for health checks (default: 30)"
            echo "  --verbose            Enable verbose output"
            echo "  --format FORMAT      Set output format (text|json, default: text)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"

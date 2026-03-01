#!/bin/bash

# Lucid Kubernetes Rollback Script
# Step 52: Production Kubernetes Deployment
# Version: 1.0.0
# Last Updated: 2025-01-14

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NAMESPACE="${NAMESPACE:-lucid-system}"
ROLLBACK_REVISION="${ROLLBACK_REVISION:-}"
DRY_RUN="${DRY_RUN:-false}"
FORCE="${FORCE:-false}"

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

# Error handling
handle_error() {
    log_error "Rollback failed at line $1"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_error "Namespace ${NAMESPACE} does not exist"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# Get deployment history
get_deployment_history() {
    local deployment="$1"
    
    log_info "Getting deployment history for: ${deployment}"
    
    if ! kubectl get deployment "${deployment}" -n "${NAMESPACE}" &> /dev/null; then
        log_warning "Deployment ${deployment} not found"
        return 1
    fi
    
    kubectl rollout history deployment "${deployment}" -n "${NAMESPACE}"
}

# Rollback specific deployment
rollback_deployment() {
    local deployment="$1"
    local revision="$2"
    
    log_info "Rolling back deployment: ${deployment}"
    
    if ! kubectl get deployment "${deployment}" -n "${NAMESPACE}" &> /dev/null; then
        log_warning "Deployment ${deployment} not found, skipping..."
        return 0
    fi
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "Dry run mode - would rollback ${deployment} to revision ${revision}"
        return 0
    fi
    
    # Rollback to specific revision or previous
    if [[ -n "${revision}" ]]; then
        log_info "Rolling back ${deployment} to revision ${revision}"
        kubectl rollout undo deployment "${deployment}" -n "${NAMESPACE}" --to-revision="${revision}"
    else
        log_info "Rolling back ${deployment} to previous revision"
        kubectl rollout undo deployment "${deployment}" -n "${NAMESPACE}"
    fi
    
    # Wait for rollback to complete
    log_info "Waiting for rollback to complete..."
    kubectl rollout status deployment "${deployment}" -n "${NAMESPACE}" --timeout=300s
    
    log_success "Rollback completed for ${deployment}"
}

# Rollback all deployments
rollback_all_deployments() {
    log_info "Rolling back all deployments..."
    
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
    
    for deployment in "${deployments[@]}"; do
        rollback_deployment "${deployment}" "${ROLLBACK_REVISION}"
    done
    
    log_success "All deployments rolled back"
}

# Rollback statefulsets
rollback_statefulsets() {
    log_info "Rolling back statefulsets..."
    
    local statefulsets=(
        "mongodb"
        "redis"
        "elasticsearch"
    )
    
    for statefulset in "${statefulsets[@]}"; do
        if kubectl get statefulset "${statefulset}" -n "${NAMESPACE}" &> /dev/null; then
            log_info "Rolling back statefulset: ${statefulset}"
            
            if [[ "${DRY_RUN}" == "true" ]]; then
                log_info "Dry run mode - would rollback ${statefulset}"
            else
                if [[ -n "${ROLLBACK_REVISION}" ]]; then
                    kubectl rollout undo statefulset "${statefulset}" -n "${NAMESPACE}" --to-revision="${ROLLBACK_REVISION}"
                else
                    kubectl rollout undo statefulset "${statefulset}" -n "${NAMESPACE}"
                fi
                
                kubectl rollout status statefulset "${statefulset}" -n "${NAMESPACE}" --timeout=300s
            fi
        else
            log_warning "StatefulSet ${statefulset} not found, skipping..."
        fi
    done
    
    log_success "Statefulsets rolled back"
}

# Verify rollback
verify_rollback() {
    log_info "Verifying rollback..."
    
    # Check pod status
    local failed_pods=$(kubectl get pods -n "${NAMESPACE}" --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers | wc -l)
    if [[ "${failed_pods}" -gt 0 ]]; then
        log_warning "Some pods are not running after rollback:"
        kubectl get pods -n "${NAMESPACE}" --field-selector=status.phase!=Running,status.phase!=Succeeded
    else
        log_success "All pods are running"
    fi
    
    # Check deployment status
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
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "${deployment}" -n "${NAMESPACE}" &> /dev/null; then
            local status=$(kubectl get deployment "${deployment}" -n "${NAMESPACE}" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}')
            if [[ "${status}" == "True" ]]; then
                log_success "Deployment ${deployment} is available"
            else
                log_warning "Deployment ${deployment} is not available"
            fi
        fi
    done
}

# Get rollback status
get_rollback_status() {
    log_info "Getting rollback status..."
    
    echo "=== Deployment Status ==="
    kubectl get deployments -n "${NAMESPACE}"
    
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods -n "${NAMESPACE}" -o wide
    
    echo ""
    echo "=== Service Status ==="
    kubectl get services -n "${NAMESPACE}"
    
    echo ""
    echo "=== Recent Events ==="
    kubectl get events -n "${NAMESPACE}" --sort-by='.lastTimestamp' | tail -20
}

# Emergency rollback (force delete and recreate)
emergency_rollback() {
    log_warning "Performing emergency rollback..."
    
    if [[ "${FORCE}" != "true" ]]; then
        log_error "Emergency rollback requires --force flag"
        exit 1
    fi
    
    # Delete all deployments
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
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "${deployment}" -n "${NAMESPACE}" &> /dev/null; then
            log_info "Force deleting deployment: ${deployment}"
            kubectl delete deployment "${deployment}" -n "${NAMESPACE}" --force --grace-period=0
        fi
    done
    
    # Delete all pods
    kubectl delete pods --all -n "${NAMESPACE}" --force --grace-period=0
    
    log_warning "Emergency rollback completed. Manual intervention required."
}

# Main function
main() {
    log_info "Starting Kubernetes rollback..."
    log_info "Namespace: ${NAMESPACE}"
    log_info "Rollback revision: ${ROLLBACK_REVISION:-previous}"
    log_info "Dry run: ${DRY_RUN}"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Perform rollback
    if [[ "${EMERGENCY:-false}" == "true" ]]; then
        emergency_rollback
    else
        rollback_all_deployments
        rollback_statefulsets
        
        # Verify rollback
        verify_rollback
        
        # Show status
        get_rollback_status
    fi
    
    log_success "Rollback completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --revision)
            ROLLBACK_REVISION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --force)
            FORCE="true"
            shift
            ;;
        --emergency)
            EMERGENCY="true"
            shift
            ;;
        --status)
            get_rollback_status
            exit 0
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --namespace NS        Set Kubernetes namespace (default: lucid-system)"
            echo "  --revision REV        Rollback to specific revision (default: previous)"
            echo "  --dry-run            Show what would be rolled back without applying"
            echo "  --force              Force rollback (required for emergency rollback)"
            echo "  --emergency          Perform emergency rollback (force delete)"
            echo "  --status             Show current rollback status"
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

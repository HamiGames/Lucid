#!/bin/bash

# Lucid Kubernetes Deployment Script
# Step 52: Production Kubernetes Deployment
# Version: 1.0.0
# Last Updated: 2025-01-14

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KUBERNETES_DIR="${PROJECT_ROOT}/infrastructure/kubernetes"
NAMESPACE="${NAMESPACE:-lucid-system}"
ENVIRONMENT="${ENVIRONMENT:-production}"
DRY_RUN="${DRY_RUN:-false}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-300}"

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
    log_error "Kubernetes deployment failed at line $1"
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
        log_warning "Namespace ${NAMESPACE} does not exist. Creating..."
        kubectl create namespace "${NAMESPACE}"
    fi
    
    # Check if kustomize is available
    if ! command -v kustomize &> /dev/null && ! kubectl kustomize --help &> /dev/null; then
        log_warning "kustomize not found. Using kubectl apply instead of kustomize build"
    fi
    
    log_success "Prerequisites validated"
}

# Deploy using kustomize
deploy_with_kustomize() {
    log_info "Deploying with kustomize..."
    
    local kustomize_cmd="kubectl apply -k"
    if command -v kustomize &> /dev/null; then
        kustomize_cmd="kustomize build | kubectl apply -f -"
    fi
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "Dry run mode - showing what would be deployed"
        if command -v kustomize &> /dev/null; then
            kustomize build "${KUBERNETES_DIR}"
        else
            kubectl kustomize "${KUBERNETES_DIR}"
        fi
        return 0
    fi
    
    # Deploy the entire system
    cd "${KUBERNETES_DIR}"
    if command -v kustomize &> /dev/null; then
        kustomize build . | kubectl apply -f -
    else
        kubectl apply -k .
    fi
    
    log_success "Kustomize deployment completed"
}

# Deploy individual components
deploy_components() {
    log_info "Deploying individual components..."
    
    local components=(
        "00-namespace.yaml"
        "01-configmaps"
        "02-secrets"
        "03-databases"
        "04-auth"
        "05-core"
        "06-application"
        "07-support"
        "08-ingress"
    )
    
    for component in "${components[@]}"; do
        local component_path="${KUBERNETES_DIR}/${component}"
        
        if [[ -d "${component_path}" ]]; then
            log_info "Deploying component: ${component}"
            kubectl apply -f "${component_path}" -n "${NAMESPACE}"
        elif [[ -f "${component_path}" ]]; then
            log_info "Deploying component: ${component}"
            kubectl apply -f "${component_path}"
        else
            log_warning "Component ${component} not found, skipping..."
        fi
    done
    
    log_success "Component deployment completed"
}

# Wait for deployments to be ready
wait_for_deployments() {
    log_info "Waiting for deployments to be ready..."
    
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
            log_info "Waiting for deployment: ${deployment}"
            kubectl rollout status deployment "${deployment}" -n "${NAMESPACE}" --timeout="${WAIT_TIMEOUT}s"
        else
            log_warning "Deployment ${deployment} not found, skipping..."
        fi
    done
    
    log_success "All deployments are ready"
}

# Wait for statefulsets to be ready
wait_for_statefulsets() {
    log_info "Waiting for statefulsets to be ready..."
    
    local statefulsets=(
        "mongodb"
        "redis"
        "elasticsearch"
    )
    
    for statefulset in "${statefulsets[@]}"; do
        if kubectl get statefulset "${statefulset}" -n "${NAMESPACE}" &> /dev/null; then
            log_info "Waiting for statefulset: ${statefulset}"
            kubectl rollout status statefulset "${statefulset}" -n "${NAMESPACE}" --timeout="${WAIT_TIMEOUT}s"
        else
            log_warning "StatefulSet ${statefulset} not found, skipping..."
        fi
    done
    
    log_success "All statefulsets are ready"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check all pods are running
    local failed_pods=$(kubectl get pods -n "${NAMESPACE}" --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers | wc -l)
    if [[ "${failed_pods}" -gt 0 ]]; then
        log_warning "Some pods are not running:"
        kubectl get pods -n "${NAMESPACE}" --field-selector=status.phase!=Running,status.phase!=Succeeded
    fi
    
    # Check services
    local services=$(kubectl get services -n "${NAMESPACE}" --no-headers | wc -l)
    log_info "Found ${services} services in namespace ${NAMESPACE}"
    
    # Check ingress
    if kubectl get ingress -n "${NAMESPACE}" &> /dev/null; then
        log_info "Ingress resources found"
        kubectl get ingress -n "${NAMESPACE}"
    else
        log_warning "No ingress resources found"
    fi
    
    log_success "Deployment verification completed"
}

# Get deployment status
get_status() {
    log_info "Getting deployment status..."
    
    echo "=== Namespace: ${NAMESPACE} ==="
    kubectl get all -n "${NAMESPACE}"
    
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods -n "${NAMESPACE}" -o wide
    
    echo ""
    echo "=== Service Status ==="
    kubectl get services -n "${NAMESPACE}"
    
    echo ""
    echo "=== Ingress Status ==="
    kubectl get ingress -n "${NAMESPACE}" 2>/dev/null || echo "No ingress found"
    
    echo ""
    echo "=== Persistent Volumes ==="
    kubectl get pv,pvc -n "${NAMESPACE}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up deployment..."
    
    # Delete all resources in namespace
    kubectl delete all --all -n "${NAMESPACE}"
    kubectl delete pvc --all -n "${NAMESPACE}"
    
    # Delete namespace (optional)
    if [[ "${CLEANUP_NAMESPACE:-false}" == "true" ]]; then
        kubectl delete namespace "${NAMESPACE}"
    fi
    
    log_success "Cleanup completed"
}

# Main function
main() {
    log_info "Starting Kubernetes deployment..."
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Namespace: ${NAMESPACE}"
    log_info "Dry run: ${DRY_RUN}"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Deploy components
    if [[ "${USE_KUSTOMIZE:-true}" == "true" ]]; then
        deploy_with_kustomize
    else
        deploy_components
    fi
    
    # Wait for deployments
    if [[ "${DRY_RUN}" != "true" ]]; then
        wait_for_statefulsets
        wait_for_deployments
        
        # Verify deployment
        verify_deployment
        
        # Show status
        get_status
    fi
    
    log_success "Kubernetes deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --timeout)
            WAIT_TIMEOUT="$2"
            shift 2
            ;;
        --no-kustomize)
            USE_KUSTOMIZE="false"
            shift
            ;;
        --status)
            get_status
            exit 0
            ;;
        --cleanup)
            cleanup
            exit 0
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --namespace NS        Set Kubernetes namespace (default: lucid-system)"
            echo "  --environment ENV     Set deployment environment (default: production)"
            echo "  --dry-run            Show what would be deployed without applying"
            echo "  --timeout SECONDS    Set wait timeout (default: 300)"
            echo "  --no-kustomize       Use individual component deployment instead of kustomize"
            echo "  --status             Show current deployment status"
            echo "  --cleanup            Clean up deployment"
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

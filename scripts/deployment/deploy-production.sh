#!/bin/bash

# Lucid Production Deployment Script
# Step 52: Production Kubernetes Deployment
# Version: 1.0.0
# Last Updated: 2025-01-14

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KUBERNETES_DIR="${PROJECT_ROOT}/infrastructure/kubernetes"
NAMESPACE="lucid-system"
ENVIRONMENT="${ENVIRONMENT:-production}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

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
    log_error "Deployment failed at line $1"
    log_error "Rolling back deployment..."
    rollback_deployment
    exit 1
}

trap 'handle_error $LINENO' ERR

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_warning "Namespace ${NAMESPACE} does not exist. Creating..."
        kubectl create namespace "${NAMESPACE}"
    fi
    
    # Check if required secrets exist
    if ! kubectl get secret lucid-secrets -n "${NAMESPACE}" &> /dev/null; then
        log_error "Required secrets not found. Please run secrets generation first."
        exit 1
    fi
    
    # Check if images are available
    check_required_images
    
    log_success "Pre-deployment checks passed"
}

# Check if required container images are available
check_required_images() {
    log_info "Checking required container images..."
    
    local images=(
        "lucid-api-gateway:latest"
        "lucid-blockchain-engine:latest"
        "lucid-session-management:latest"
        "lucid-rdp-services:latest"
        "lucid-node-management:latest"
        "lucid-admin-interface:latest"
        "lucid-tron-payment:latest"
        "lucid-auth-service:latest"
        "lucid-service-mesh-controller:latest"
    )
    
    for image in "${images[@]}"; do
        if ! docker image inspect "${image}" &> /dev/null; then
            log_warning "Image ${image} not found locally. Will pull from registry."
        fi
    done
}

# Deploy infrastructure components
deploy_infrastructure() {
    log_info "Deploying infrastructure components..."
    
    # Deploy databases first
    log_info "Deploying databases..."
    kubectl apply -f "${KUBERNETES_DIR}/03-databases/" -n "${NAMESPACE}"
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    kubectl wait --for=condition=ready pod -l app=mongodb -n "${NAMESPACE}" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n "${NAMESPACE}" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=elasticsearch -n "${NAMESPACE}" --timeout=300s
    
    log_success "Infrastructure components deployed"
}

# Deploy core services
deploy_core_services() {
    log_info "Deploying core services..."
    
    # Deploy auth service first
    log_info "Deploying authentication service..."
    kubectl apply -f "${KUBERNETES_DIR}/04-auth/" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=auth-service -n "${NAMESPACE}" --timeout=300s
    
    # Deploy API Gateway
    log_info "Deploying API Gateway..."
    kubectl apply -f "${KUBERNETES_DIR}/05-core/api-gateway.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=api-gateway -n "${NAMESPACE}" --timeout=300s
    
    # Deploy blockchain core
    log_info "Deploying blockchain core..."
    kubectl apply -f "${KUBERNETES_DIR}/05-core/blockchain-engine.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=blockchain-engine -n "${NAMESPACE}" --timeout=300s
    
    # Deploy service mesh
    log_info "Deploying service mesh..."
    kubectl apply -f "${KUBERNETES_DIR}/05-core/service-mesh.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=service-mesh-controller -n "${NAMESPACE}" --timeout=300s
    
    log_success "Core services deployed"
}

# Deploy application services
deploy_application_services() {
    log_info "Deploying application services..."
    
    # Deploy session management
    log_info "Deploying session management..."
    kubectl apply -f "${KUBERNETES_DIR}/06-application/session-management.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=session-management -n "${NAMESPACE}" --timeout=300s
    
    # Deploy RDP services
    log_info "Deploying RDP services..."
    kubectl apply -f "${KUBERNETES_DIR}/06-application/rdp-services.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=rdp-services -n "${NAMESPACE}" --timeout=300s
    
    # Deploy node management
    log_info "Deploying node management..."
    kubectl apply -f "${KUBERNETES_DIR}/06-application/node-management.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=node-management -n "${NAMESPACE}" --timeout=300s
    
    log_success "Application services deployed"
}

# Deploy support services
deploy_support_services() {
    log_info "Deploying support services..."
    
    # Deploy admin interface
    log_info "Deploying admin interface..."
    kubectl apply -f "${KUBERNETES_DIR}/07-support/admin-interface.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=admin-interface -n "${NAMESPACE}" --timeout=300s
    
    # Deploy TRON payment (isolated)
    log_info "Deploying TRON payment service..."
    kubectl apply -f "${KUBERNETES_DIR}/07-support/tron-payment.yaml" -n "${NAMESPACE}"
    kubectl wait --for=condition=ready pod -l app=tron-payment -n "${NAMESPACE}" --timeout=300s
    
    log_success "Support services deployed"
}

# Deploy ingress
deploy_ingress() {
    log_info "Deploying ingress..."
    
    kubectl apply -f "${KUBERNETES_DIR}/08-ingress/" -n "${NAMESPACE}"
    
    # Wait for ingress to be ready
    kubectl wait --for=condition=ready pod -l app=ingress-nginx -n "${NAMESPACE}" --timeout=300s
    
    log_success "Ingress deployed"
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    # Check all deployments
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
        if ! kubectl get deployment "${deployment}" -n "${NAMESPACE}" &> /dev/null; then
            log_error "Deployment ${deployment} not found"
            return 1
        fi
        
        if ! kubectl rollout status deployment "${deployment}" -n "${NAMESPACE}" --timeout=300s; then
            log_error "Deployment ${deployment} not ready"
            return 1
        fi
    done
    
    # Check service endpoints
    check_service_endpoints
    
    log_success "All health checks passed"
}

# Check service endpoints
check_service_endpoints() {
    log_info "Checking service endpoints..."
    
    # Get API Gateway service
    local api_gateway_service=$(kubectl get service api-gateway -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [[ -z "${api_gateway_service}" ]]; then
        api_gateway_service=$(kubectl get service api-gateway -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}')
    fi
    
    # Test API Gateway health endpoint
    if ! curl -f "http://${api_gateway_service}:8080/health" &> /dev/null; then
        log_warning "API Gateway health check failed"
    else
        log_success "API Gateway is responding"
    fi
}

# Rollback deployment
rollback_deployment() {
    log_warning "Rolling back deployment..."
    
    # Rollback all deployments
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
            kubectl rollout undo deployment "${deployment}" -n "${NAMESPACE}"
        fi
    done
    
    log_warning "Rollback completed"
}

# Main deployment function
main() {
    log_info "Starting Lucid production deployment..."
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Namespace: ${NAMESPACE}"
    
    # Run pre-deployment checks
    pre_deployment_checks
    
    # Deploy components in order
    deploy_infrastructure
    deploy_core_services
    deploy_application_services
    deploy_support_services
    deploy_ingress
    
    # Run health checks
    health_check
    
    log_success "Production deployment completed successfully!"
    log_info "Access the system at: https://api.lucid.onion"
    log_info "Admin interface: https://admin.lucid.onion"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --environment ENV    Set deployment environment (default: production)"
            echo "  --namespace NS        Set Kubernetes namespace (default: lucid-system)"
            echo "  --log-level LEVEL     Set log level (default: INFO)"
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

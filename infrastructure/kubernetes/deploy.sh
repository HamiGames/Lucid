#!/bin/bash

# Lucid Blockchain System Kubernetes Deployment Script
# This script deploys the complete Lucid blockchain system to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="lucid-system"
CONTEXT="lucid-cluster"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    print_success "kubectl is available"
}

# Function to check if kustomize is available
check_kustomize() {
    if ! command -v kustomize &> /dev/null; then
        print_warning "kustomize is not available, using kubectl apply -k"
    else
        print_success "kustomize is available"
    fi
}

# Function to check cluster connectivity
check_cluster() {
    print_status "Checking cluster connectivity..."
    if kubectl cluster-info &> /dev/null; then
        print_success "Cluster is accessible"
    else
        print_error "Cannot connect to cluster"
        exit 1
    fi
}

# Function to create namespace
create_namespace() {
    print_status "Creating namespace: $NAMESPACE"
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        print_warning "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace $NAMESPACE
        print_success "Namespace $NAMESPACE created"
    fi
}

# Function to apply Kubernetes manifests
apply_manifests() {
    print_status "Applying Kubernetes manifests..."
    
    # Apply namespace first
    kubectl apply -f 00-namespace.yaml
    
    # Apply ConfigMaps
    print_status "Applying ConfigMaps..."
    kubectl apply -f 01-configmaps/
    
    # Apply Secrets
    print_status "Applying Secrets..."
    kubectl apply -f 02-secrets/
    
    # Apply Databases
    print_status "Applying Database StatefulSets..."
    kubectl apply -f 03-databases/
    
    # Apply Auth Service
    print_status "Applying Auth Service..."
    kubectl apply -f 04-auth/
    
    # Apply Core Services
    print_status "Applying Core Services..."
    kubectl apply -f 05-core/
    
    # Apply Application Services
    print_status "Applying Application Services..."
    kubectl apply -f 06-application/
    
    # Apply Support Services
    print_status "Applying Support Services..."
    kubectl apply -f 07-support/
    
    # Apply Ingress
    print_status "Applying Ingress..."
    kubectl apply -f 08-ingress/
    
    print_success "All manifests applied successfully"
}

# Function to wait for deployments
wait_for_deployments() {
    print_status "Waiting for deployments to be ready..."
    
    # Wait for database StatefulSets
    print_status "Waiting for MongoDB..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mongodb -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for Redis..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for Elasticsearch..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=elasticsearch -n $NAMESPACE --timeout=300s
    
    # Wait for auth service
    print_status "Waiting for Auth Service..."
    kubectl wait --for=condition=available deployment/auth-service -n $NAMESPACE --timeout=300s
    
    # Wait for core services
    print_status "Waiting for API Gateway..."
    kubectl wait --for=condition=available deployment/api-gateway -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for Blockchain Engine..."
    kubectl wait --for=condition=available deployment/blockchain-engine -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for Service Mesh Controller..."
    kubectl wait --for=condition=available deployment/service-mesh-controller -n $NAMESPACE --timeout=300s
    
    # Wait for application services
    print_status "Waiting for Session Management..."
    kubectl wait --for=condition=available deployment/session-management -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for RDP Services..."
    kubectl wait --for=condition=available deployment/rdp-services -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for Node Management..."
    kubectl wait --for=condition=available deployment/node-management -n $NAMESPACE --timeout=300s
    
    # Wait for support services
    print_status "Waiting for Admin Interface..."
    kubectl wait --for=condition=available deployment/admin-interface -n $NAMESPACE --timeout=300s
    
    print_status "Waiting for TRON Payment..."
    kubectl wait --for=condition=available deployment/tron-payment -n $NAMESPACE --timeout=300s
    
    print_success "All deployments are ready"
}

# Function to check system health
check_health() {
    print_status "Checking system health..."
    
    # Check pod status
    print_status "Pod status:"
    kubectl get pods -n $NAMESPACE
    
    # Check service status
    print_status "Service status:"
    kubectl get services -n $NAMESPACE
    
    # Check ingress status
    print_status "Ingress status:"
    kubectl get ingress -n $NAMESPACE
    
    print_success "System health check completed"
}

# Function to display access information
display_access_info() {
    print_status "Access Information:"
    echo ""
    echo "API Gateway: http://api.lucid.onion"
    echo "Admin Interface: http://admin.lucid.onion"
    echo "Blockchain Core: http://blockchain.lucid.onion"
    echo "Session Management: http://sessions.lucid.onion"
    echo "Node Management: http://nodes.lucid.onion"
    echo "TRON Payment: http://payments.lucid.onion"
    echo ""
    echo "To access services locally, you can use port-forward:"
    echo "kubectl port-forward -n $NAMESPACE service/api-gateway-service 8080:8080"
    echo "kubectl port-forward -n $NAMESPACE service/admin-interface-service 8083:8083"
    echo ""
}

# Function to cleanup (optional)
cleanup() {
    print_status "Cleaning up Lucid system..."
    kubectl delete namespace $NAMESPACE
    print_success "Lucid system cleaned up"
}

# Main deployment function
deploy() {
    print_status "Starting Lucid Blockchain System deployment..."
    echo ""
    
    # Pre-deployment checks
    check_kubectl
    check_kustomize
    check_cluster
    
    # Create namespace
    create_namespace
    
    # Apply manifests
    apply_manifests
    
    # Wait for deployments
    wait_for_deployments
    
    # Check health
    check_health
    
    # Display access information
    display_access_info
    
    print_success "Lucid Blockchain System deployed successfully!"
    echo ""
    print_status "Next steps:"
    echo "1. Configure your DNS to point to the cluster ingress"
    echo "2. Update SSL certificates if needed"
    echo "3. Configure external services (TRON, etc.)"
    echo "4. Run system tests to verify functionality"
    echo ""
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    cleanup)
        cleanup
        ;;
    status)
        check_health
        ;;
    *)
        echo "Usage: $0 {deploy|cleanup|status}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy the Lucid system (default)"
        echo "  cleanup - Remove the Lucid system"
        echo "  status  - Check system status"
        exit 1
        ;;
esac

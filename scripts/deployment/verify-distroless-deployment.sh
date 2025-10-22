#!/bin/bash
# Path: scripts/deployment/verify-distroless-deployment.sh
# Verify Distroless Deployment
# Comprehensive verification of all deployed services and infrastructure
# MUST RUN ON PI CONSOLE

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Project root
PROJECT_ROOT="${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}"

echo ""
log_info "========================================"
log_info "Distroless Deployment Verification"
log_info "========================================"
echo ""

# Function to check network
check_network() {
    local network_name=$1
    local expected_subnet=$2
    local description=$3
    
    log_info "Checking network: $network_name"
    
    if docker network ls | grep -q "^$network_name "; then
        local actual_subnet=$(docker network inspect "$network_name" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "")
        
        if [ "$actual_subnet" = "$expected_subnet" ]; then
            log_success "$description: $network_name ($expected_subnet)"
            return 0
        else
            log_warning "$description: $network_name has wrong subnet ($actual_subnet vs $expected_subnet)"
            return 1
        fi
    else
        log_error "$description: $network_name not found"
        return 1
    fi
}

# Function to check container health
check_container_health() {
    local container_name=$1
    local description=$2
    
    log_info "Checking container: $container_name"
    
    if docker ps --format '{{.Names}}' | grep -q "^$container_name$"; then
        local status=$(docker inspect --format '{{.State.Status}}' "$container_name")
        local health=$(docker inspect --format '{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck")
        
        if [ "$status" = "running" ]; then
            if [ "$health" = "healthy" ]; then
                log_success "$description: $container_name is healthy"
                return 0
            elif [ "$health" = "no-healthcheck" ]; then
                log_info "$description: $container_name is running (no health check)"
                return 0
            else
                log_warning "$description: $container_name health status: $health"
                return 1
            fi
        else
            log_error "$description: $container_name status: $status"
            return 1
        fi
    else
        log_error "$description: $container_name not found"
        return 1
    fi
}

# Function to test service endpoint
test_service_endpoint() {
    local service_name=$1
    local endpoint=$2
    local description=$3
    
    log_info "Testing endpoint: $service_name"
    
    if curl -f -s "$endpoint" > /dev/null 2>&1; then
        log_success "$description: $service_name endpoint is responding"
        return 0
    else
        log_warning "$description: $service_name endpoint not responding"
        return 1
    fi
}

# Function to test database security
test_database_security() {
    local db_name=$1
    local container_name=$2
    local test_command=$3
    local description=$4
    
    log_info "Testing database security: $db_name"
    
    if eval "$test_command" 2>&1 | grep -q "Authentication failed\|NOAUTH"; then
        log_success "$description: $db_name requires authentication (secure)"
        return 0
    else
        log_warning "$description: $db_name security test inconclusive"
        return 1
    fi
}

# Function to check network isolation
check_network_isolation() {
    local container_name=$1
    local expected_network=$2
    local description=$3
    
    log_info "Checking network isolation: $container_name"
    
    if docker inspect "$container_name" 2>/dev/null | grep -q "$expected_network"; then
        log_success "$description: $container_name is on $expected_network"
        return 0
    else
        log_error "$description: $container_name is not on $expected_network"
        return 1
    fi
}

# Main verification process

# Step 1: Check networks
log_info "Step 1: Verifying Docker Networks"
echo ""

network_checks=0
total_networks=6

check_network "lucid-pi-network" "172.20.0.0/16" "Main Network" && network_checks=$((network_checks + 1))
check_network "lucid-tron-isolated" "172.21.0.0/16" "TRON Isolated Network" && network_checks=$((network_checks + 1))
check_network "lucid-gui-network" "172.22.0.0/16" "GUI Network" && network_checks=$((network_checks + 1))
check_network "lucid-distroless-production" "172.23.0.0/16" "Distroless Production Network" && network_checks=$((network_checks + 1))
check_network "lucid-distroless-dev" "172.24.0.0/16" "Distroless Development Network" && network_checks=$((network_checks + 1))
check_network "lucid-multi-stage-network" "172.25.0.0/16" "Multi-Stage Network" && network_checks=$((network_checks + 1))

echo ""
log_info "Network verification: $network_checks/$total_networks networks correct"
echo ""

# Step 2: Check environment files
log_info "Step 2: Verifying Environment Files"
echo ""

env_checks=0
total_env_files=6

for env_file in "configs/environment/.env.foundation" "configs/environment/.env.core" "configs/environment/.env.application" "configs/environment/.env.support" "configs/environment/.env.gui" "configs/environment/.env.distroless"; do
    if [ -f "$env_file" ]; then
        log_success "Environment file found: $env_file"
        env_checks=$((env_checks + 1))
    else
        log_error "Environment file missing: $env_file"
    fi
done

echo ""
log_info "Environment file verification: $env_checks/$total_env_files files found"
echo ""

# Step 3: Check distroless base infrastructure
log_info "Step 3: Verifying Distroless Base Infrastructure"
echo ""

distroless_checks=0
total_distroless=0

# Check if distroless containers exist
if docker ps --format '{{.Names}}' | grep -q "distroless"; then
    total_distroless=$(docker ps --format '{{.Names}}' | grep "distroless" | wc -l)
    
    docker ps --format '{{.Names}}' | grep "distroless" | while read container; do
        if check_container_health "$container" "Distroless Container"; then
            distroless_checks=$((distroless_checks + 1))
        fi
    done
else
    log_info "No distroless containers found (optional infrastructure)"
fi

echo ""
log_info "Distroless infrastructure verification: $distroless_checks/$total_distroless containers healthy"
echo ""

# Step 4: Check Lucid services
log_info "Step 4: Verifying Lucid Services"
echo ""

lucid_checks=0
total_lucid=0

# Foundation services
foundation_services=("lucid-mongodb" "lucid-redis" "lucid-elasticsearch" "lucid-auth-service")
for service in "${foundation_services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^$service$"; then
        total_lucid=$((total_lucid + 1))
        if check_container_health "$service" "Foundation Service"; then
            lucid_checks=$((lucid_checks + 1))
        fi
    fi
done

# Core services
core_services=("lucid-api-gateway" "lucid-blockchain-core" "lucid-service-mesh-controller")
for service in "${core_services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^$service$"; then
        total_lucid=$((total_lucid + 1))
        if check_container_health "$service" "Core Service"; then
            lucid_checks=$((lucid_checks + 1))
        fi
    fi
done

# Application services
app_services=("lucid-session-pipeline" "lucid-node-management" "lucid-rdp-server-manager")
for service in "${app_services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^$service$"; then
        total_lucid=$((total_lucid + 1))
        if check_container_health "$service" "Application Service"; then
            lucid_checks=$((lucid_checks + 1))
        fi
    fi
done

# Support services
support_services=("lucid-admin-interface" "lucid-tron-client")
for service in "${support_services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^$service$"; then
        total_lucid=$((total_lucid + 1))
        if check_container_health "$service" "Support Service"; then
            lucid_checks=$((lucid_checks + 1))
        fi
    fi
done

echo ""
log_info "Lucid services verification: $lucid_checks/$total_lucid containers healthy"
echo ""

# Step 5: Test service endpoints
log_info "Step 5: Testing Service Endpoints"
echo ""

endpoint_checks=0
total_endpoints=0

# Test foundation endpoints
if docker ps --format '{{.Names}}' | grep -q "lucid-auth-service"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "Auth Service" "http://localhost:8089/health" "Foundation Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

# Test core endpoints
if docker ps --format '{{.Names}}' | grep -q "lucid-api-gateway"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "API Gateway" "http://localhost:8080/health" "Core Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

if docker ps --format '{{.Names}}' | grep -q "lucid-blockchain-core"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "Blockchain Core" "http://localhost:8084/health" "Core Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

# Test application endpoints
if docker ps --format '{{.Names}}' | grep -q "lucid-session-pipeline"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "Session Pipeline" "http://localhost:8083/health" "Application Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

if docker ps --format '{{.Names}}' | grep -q "lucid-node-management"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "Node Management" "http://localhost:8095/health" "Application Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

# Test support endpoints
if docker ps --format '{{.Names}}' | grep -q "lucid-admin-interface"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "Admin Interface" "http://localhost:8120/health" "Support Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

if docker ps --format '{{.Names}}' | grep -q "lucid-tron-client"; then
    total_endpoints=$((total_endpoints + 1))
    if test_service_endpoint "TRON Client" "http://localhost:8091/health" "Support Service"; then
        endpoint_checks=$((endpoint_checks + 1))
    fi
fi

echo ""
log_info "Service endpoint verification: $endpoint_checks/$total_endpoints endpoints responding"
echo ""

# Step 6: Test database security
log_info "Step 6: Testing Database Security"
echo ""

security_checks=0
total_security=0

# Test MongoDB security
if docker ps --format '{{.Names}}' | grep -q "lucid-mongodb"; then
    total_security=$((total_security + 1))
    if test_database_security "MongoDB" "lucid-mongodb" "docker exec lucid-mongodb mongosh -u lucid -p wrongpassword --authenticationDatabase admin --eval \"db.runCommand('ping')\"" "Database Security"; then
        security_checks=$((security_checks + 1))
    fi
fi

# Test Redis security
if docker ps --format '{{.Names}}' | grep -q "lucid-redis"; then
    total_security=$((total_security + 1))
    if test_database_security "Redis" "lucid-redis" "docker exec lucid-redis redis-cli ping" "Database Security"; then
        security_checks=$((security_checks + 1))
    fi
fi

echo ""
log_info "Database security verification: $security_checks/$total_security databases secure"
echo ""

# Step 7: Test network isolation
log_info "Step 7: Testing Network Isolation"
echo ""

isolation_checks=0
total_isolation=0

# Test TRON isolation
if docker ps --format '{{.Names}}' | grep -q "lucid-tron-client"; then
    total_isolation=$((total_isolation + 1))
    if check_network_isolation "lucid-tron-client" "lucid-tron-isolated" "TRON Isolation"; then
        isolation_checks=$((isolation_checks + 1))
    fi
fi

# Test main services network
if docker ps --format '{{.Names}}' | grep -q "lucid-api-gateway"; then
    total_isolation=$((total_isolation + 1))
    if check_network_isolation "lucid-api-gateway" "lucid-pi-network" "Main Services Network"; then
        isolation_checks=$((isolation_checks + 1))
    fi
fi

echo ""
log_info "Network isolation verification: $isolation_checks/$total_isolation networks correct"
echo ""

# Step 8: Check multi-stage build infrastructure
log_info "Step 8: Verifying Multi-Stage Build Infrastructure"
echo ""

multi_stage_checks=0
total_multi_stage=0

# Check if multi-stage containers exist
if docker ps --format '{{.Names}}' | grep -q "multi-stage"; then
    total_multi_stage=$(docker ps --format '{{.Names}}' | grep "multi-stage" | wc -l)
    
    docker ps --format '{{.Names}}' | grep "multi-stage" | while read container; do
        if check_container_health "$container" "Multi-Stage Container"; then
            multi_stage_checks=$((multi_stage_checks + 1))
        fi
    done
else
    log_info "No multi-stage containers found (optional infrastructure)"
fi

echo ""
log_info "Multi-stage build verification: $multi_stage_checks/$total_multi_stage containers healthy"
echo ""

# Step 9: Summary
log_info "Step 9: Deployment Summary"
echo ""

total_checks=$((network_checks + env_checks + distroless_checks + lucid_checks + endpoint_checks + security_checks + isolation_checks + multi_stage_checks))
total_possible=$((total_networks + total_env_files + total_distroless + total_lucid + total_endpoints + total_security + total_isolation + total_multi_stage))

log_info "Overall verification: $total_checks/$total_possible checks passed"
echo ""

if [ $total_checks -eq $total_possible ]; then
    log_success "========================================"
    log_success "All verifications passed!"
    log_success "Distroless deployment is fully operational"
    log_success "========================================"
elif [ $total_checks -gt $((total_possible * 3 / 4)) ]; then
    log_warning "========================================"
    log_warning "Most verifications passed"
    log_warning "Deployment is mostly operational"
    log_warning "========================================"
else
    log_error "========================================"
    log_error "Multiple verifications failed"
    log_error "Deployment has significant issues"
    log_error "========================================"
fi

echo ""
log_info "Detailed breakdown:"
log_info "  • Networks: $network_checks/$total_networks"
log_info "  • Environment files: $env_checks/$total_env_files"
log_info "  • Distroless infrastructure: $distroless_checks/$total_distroless"
log_info "  • Lucid services: $lucid_checks/$total_lucid"
log_info "  • Service endpoints: $endpoint_checks/$total_endpoints"
log_info "  • Database security: $security_checks/$total_security"
log_info "  • Network isolation: $isolation_checks/$total_isolation"
log_info "  • Multi-stage build: $multi_stage_checks/$total_multi_stage"
echo ""

log_info "Next steps:"
log_info "  1. Review any failed verifications above"
log_info "  2. Check container logs for issues: docker logs <container_name>"
log_info "  3. Test service endpoints manually"
log_info "  4. Configure monitoring and alerting"
log_info "  5. Set up backup procedures"
echo ""

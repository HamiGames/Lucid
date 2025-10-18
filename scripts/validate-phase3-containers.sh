#!/bin/bash

# Step 32: Phase 3 Container Builds Validation Script
# Validates all 10 application containers are running

set -e

echo "=========================================="
echo "Step 32: Phase 3 Container Builds Validation"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check container health
check_container_health() {
    local container_name=$1
    local port=$2
    local service_name=$3
    
    echo -n "Checking $service_name ($container_name) on port $port... "
    
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ HEALTHY${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ RUNNING (health check failed)${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ NOT RUNNING${NC}"
        return 1
    fi
}

# Function to check all containers
check_all_containers() {
    local failed_checks=0
    
    echo "Checking Phase 3 Application Containers..."
    echo "=========================================="
    
    # Session Management Services (5 containers)
    echo "Session Management Services:"
    check_container_health "lucid-session-pipeline" "8083" "Session Pipeline Manager" || ((failed_checks++))
    check_container_health "lucid-session-recorder" "8084" "Session Recorder" || ((failed_checks++))
    check_container_health "lucid-session-processor" "8085" "Session Processor" || ((failed_checks++))
    check_container_health "lucid-session-storage" "8086" "Session Storage" || ((failed_checks++))
    check_container_health "lucid-session-api" "8087" "Session API Gateway" || ((failed_checks++))
    
    echo ""
    echo "RDP Services:"
    check_container_health "lucid-rdp-server-manager" "8090" "RDP Server Manager" || ((failed_checks++))
    check_container_health "lucid-xrdp" "8091" "XRDP Integration" || ((failed_checks++))
    check_container_health "lucid-rdp-controller" "8092" "RDP Session Controller" || ((failed_checks++))
    check_container_health "lucid-rdp-monitor" "8093" "RDP Resource Monitor" || ((failed_checks++))
    
    echo ""
    echo "Node Management:"
    check_container_health "lucid-node-management" "8095" "Node Management" || ((failed_checks++))
    
    echo ""
    echo "External Dependencies:"
    check_container_health "lucid-mongodb" "27017" "MongoDB Database" || ((failed_checks++))
    check_container_health "lucid-redis" "6379" "Redis Cache" || ((failed_checks++))
    
    return $failed_checks
}

# Function to show container status summary
show_container_summary() {
    echo ""
    echo "=========================================="
    echo "Container Status Summary"
    echo "=========================================="
    
    echo "Application Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "lucid-"
    
    echo ""
    echo "Total Running Containers:"
    local total_containers=$(docker ps --format "{{.Names}}" | grep "lucid-" | wc -l)
    echo "Expected: 12 containers (10 application + 2 dependencies)"
    echo "Running: $total_containers containers"
}

# Function to show port allocation
show_port_allocation() {
    echo ""
    echo "=========================================="
    echo "Port Allocation Summary"
    echo "=========================================="
    
    echo "Session Management Services:"
    echo "  - Session Pipeline Manager: 8083"
    echo "  - Session Recorder: 8084"
    echo "  - Session Processor: 8085"
    echo "  - Session Storage: 8086"
    echo "  - Session API Gateway: 8087"
    
    echo ""
    echo "RDP Services:"
    echo "  - RDP Server Manager: 8090"
    echo "  - XRDP Integration: 8091"
    echo "  - RDP Session Controller: 8092"
    echo "  - RDP Resource Monitor: 8093"
    
    echo ""
    echo "Node Management:"
    echo "  - Node Management: 8095"
    
    echo ""
    echo "External Dependencies:"
    echo "  - MongoDB Database: 27017"
    echo "  - Redis Cache: 6379"
}

# Main execution
main() {
    echo "Starting Phase 3 Container Validation..."
    echo ""
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running${NC}"
        exit 1
    fi
    
    # Check all containers
    check_all_containers
    local exit_code=$?
    
    # Show summary
    show_container_summary
    show_port_allocation
    
    echo ""
    echo "=========================================="
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ All Phase 3 containers are running and healthy${NC}"
        echo "Step 32: Phase 3 Container Builds - COMPLETED"
    else
        echo -e "${RED}✗ Some containers are not running or unhealthy${NC}"
        echo "Please check the container logs and restart failed services"
        echo "Use: docker-compose -f docker-compose.phase3.yml up -d"
    fi
    echo "=========================================="
    
    exit $exit_code
}

# Run main function
main "$@"

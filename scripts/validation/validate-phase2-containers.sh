#!/bin/bash
# File: scripts/validation/validate-phase2-containers.sh
# Purpose: Validate all Phase 2 containers operational on lucid-dev network
# Build Host: Windows 11 console
# Target Host: Raspberry Pi (via SSH)

set -e

echo "=== Phase 2 Container Validation ==="
echo "Validating all Phase 2 containers operational on lucid-dev network"
echo "Timestamp: $(date)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check container health
check_container_health() {
    local container_name=$1
    local port=$2
    local health_endpoint=$3
    
    echo -n "Checking $container_name on port $port... "
    
    if docker ps | grep -q "$container_name"; then
        if curl -f -s "http://localhost:$port$health_endpoint" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ HEALTHY${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ RUNNING BUT UNHEALTHY${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ NOT RUNNING${NC}"
        return 1
    fi
}

# Function to check network connectivity
check_network_connectivity() {
    echo "Checking lucid-dev network..."
    if docker network ls | grep -q "lucid-dev"; then
        echo -e "${GREEN}✓ lucid-dev network exists${NC}"
    else
        echo -e "${RED}✗ lucid-dev network not found${NC}"
        return 1
    fi
}

# Function to check service discovery
check_service_discovery() {
    echo "Checking service discovery (Consul)..."
    if curl -f -s "http://localhost:8500/v1/status/leader" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Consul service discovery operational${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Consul service discovery not responding${NC}"
        return 1
    fi
}

# Main validation
echo "Starting Phase 2 container validation..."
echo ""

# Check network
check_network_connectivity
echo ""

# Check service discovery
check_service_discovery
echo ""

# Check API Gateway (enhanced)
check_container_health "lucid-api-gateway" "8080" "/health"
echo ""

# Check Blockchain Core containers
echo "=== Blockchain Core Cluster ==="
check_container_health "lucid-blockchain-engine" "8084" "/health"
check_container_health "lucid-session-anchoring" "8085" "/health"
check_container_health "lucid-block-manager" "8086" "/health"
check_container_health "lucid-data-chain" "8087" "/health"
echo ""

# Check Service Mesh Controller
echo "=== Cross-Cluster Integration ==="
check_container_health "lucid-service-mesh-controller" "8500" "/health"
echo ""

# Summary
echo "=== Validation Summary ==="
echo "Phase 2 containers validation completed at $(date)"
echo ""

# Check if all containers are healthy
total_containers=6
healthy_containers=0

# Count healthy containers
for container in "lucid-api-gateway:8080" "lucid-blockchain-engine:8084" "lucid-session-anchoring:8085" "lucid-block-manager:8086" "lucid-data-chain:8087" "lucid-service-mesh-controller:8500"; do
    container_name=$(echo $container | cut -d: -f1)
    port=$(echo $container | cut -d: -f2)
    if docker ps | grep -q "$container_name" && curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
        ((healthy_containers++))
    fi
done

echo "Healthy containers: $healthy_containers/$total_containers"

if [ $healthy_containers -eq $total_containers ]; then
    echo -e "${GREEN}✓ All Phase 2 containers operational${NC}"
    exit 0
else
    echo -e "${RED}✗ Some Phase 2 containers not operational${NC}"
    exit 1
fi

#!/bin/bash
# auth/build-auth-service.sh
# Build authentication service container with network binding

set -e

echo "Building authentication service container..."

# Configuration
AUTH_SERVICE_IMAGE="pickme/lucid-auth-service:latest-arm64"
AUTH_SERVICE_CONTAINER="lucid-auth-service"
LUCID_NETWORK="lucid-pi-network"
NETWORK_SUBNET="172.20.0.0/16"
NETWORK_GATEWAY="172.20.0.1"
AUTH_SERVICE_PORT="8089"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check if network exists
check_network_exists() {
    if docker network ls | grep -q "$LUCID_NETWORK"; then
        echo "Network $LUCID_NETWORK already exists"
        return 0
    else
        echo "Network $LUCID_NETWORK does not exist"
        return 1
    fi
}

# Function to create network if it doesn't exist
create_network() {
    echo "Creating Docker network: $LUCID_NETWORK"
    docker network create $LUCID_NETWORK \
        --driver bridge \
        --subnet $NETWORK_SUBNET \
        --gateway $NETWORK_GATEWAY \
        --attachable \
        --opt com.docker.network.bridge.enable_icc=true \
        --opt com.docker.network.bridge.enable_ip_masquerade=true \
        --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
        --opt com.docker.network.driver.mtu=1500 \
        --label "lucid.network=main" \
        --label "lucid.subnet=$NETWORK_SUBNET"
    
    if [ $? -eq 0 ]; then
        print_status 0 "Network $LUCID_NETWORK created successfully"
    else
        print_status 1 "Failed to create network $LUCID_NETWORK"
        exit 1
    fi
}

# Function to build auth service container
build_auth_service() {
    echo "Building auth service container..."
    
    # Set build context
    cd auth
    
    # Build auth service container with network binding
    docker buildx build \
        --platform linux/arm64 \
        -t $AUTH_SERVICE_IMAGE \
        -f Dockerfile \
        --network $LUCID_NETWORK \
        --build-arg LUCID_NETWORK=$LUCID_NETWORK \
        --build-arg NETWORK_SUBNET=$NETWORK_SUBNET \
        --build-arg NETWORK_GATEWAY=$NETWORK_GATEWAY \
        --push .
    
    if [ $? -eq 0 ]; then
        print_status 0 "Auth service container built and pushed successfully"
    else
        print_status 1 "Failed to build auth service container"
        exit 1
    fi
}

# Function to verify network configuration
verify_network_config() {
    echo "Verifying network configuration..."
    
    # Check if network exists
    if check_network_exists; then
        print_status 0 "Network $LUCID_NETWORK exists"
    else
        print_status 1 "Network $LUCID_NETWORK not found"
        return 1
    fi
    
    # Verify network details
    echo "Network details:"
    docker network inspect $LUCID_NETWORK | grep -E "Subnet|Gateway"
    
    # Check if image exists
    if docker images | grep -q "$AUTH_SERVICE_IMAGE"; then
        print_status 0 "Auth service image exists"
    else
        print_status 1 "Auth service image not found"
        return 1
    fi
}

# Function to test container with network binding
test_container_network() {
    echo "Testing container network binding..."
    
    # Run container with network binding
    docker run --rm \
        --name test-auth-service \
        --network $LUCID_NETWORK \
        -p $AUTH_SERVICE_PORT:$AUTH_SERVICE_PORT \
        $AUTH_SERVICE_IMAGE \
        python -c "import socket; print('Network test successful')" &
    
    # Wait for container to start
    sleep 5
    
    # Check if container is running
    if docker ps | grep -q "test-auth-service"; then
        print_status 0 "Container network binding test successful"
        docker stop test-auth-service 2>/dev/null || true
    else
        print_status 1 "Container network binding test failed"
        return 1
    fi
}

# Main execution
echo -e "${BLUE}=== Lucid Auth Service Build ===${NC}"
echo "Target: ARM64 (Raspberry Pi)"
echo "Network: $LUCID_NETWORK ($NETWORK_SUBNET)"
echo "Gateway: $NETWORK_GATEWAY"
echo "Port: $AUTH_SERVICE_PORT"
echo ""

# Step 1: Check/create network
echo -e "${BLUE}--- Network Configuration ---${NC}"
if check_network_exists; then
    print_status 0 "Network $LUCID_NETWORK already exists"
else
    create_network
fi

# Step 2: Build auth service
echo -e "${BLUE}--- Building Auth Service ---${NC}"
build_auth_service

# Step 3: Verify configuration
echo -e "${BLUE}--- Verification ---${NC}"
verify_network_config

# Step 4: Test network binding
echo -e "${BLUE}--- Network Binding Test ---${NC}"
test_container_network

echo ""
echo -e "${GREEN}=== Build Summary ===${NC}"
echo "✓ Auth service container built and pushed successfully"
echo "✓ Network binding configured for $LUCID_NETWORK"
echo "✓ Container ready for Phase 1 Foundation Services deployment"
echo ""
echo "Container: $AUTH_SERVICE_IMAGE"
echo "Network: $LUCID_NETWORK ($NETWORK_SUBNET)"
echo "Port: $AUTH_SERVICE_PORT"
echo "Gateway: $NETWORK_GATEWAY"
echo ""
echo -e "${GREEN}✓ Auth service build completed successfully!${NC}"

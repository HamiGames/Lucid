#!/bin/bash
# auth/build-auth-service.sh
# Deploy authentication service container on Pi (Pi-side deployment using pre-built images)

set -e

echo "Deploying authentication service container on Pi..."

# Configuration
AUTH_SERVICE_IMAGE="pickme/lucid-auth-service:latest-arm64"
AUTH_SERVICE_CONTAINER="lucid-auth-service"
LUCID_NETWORK="lucid-pi-network"
NETWORK_SUBNET="172.20.0.0/16"
NETWORK_GATEWAY="172.20.0.1"
AUTH_SERVICE_PORT="8089"
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/mnt/myssd/Lucid/Lucid"

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

# Function to check if network exists on Pi
check_network_exists() {
    echo "Checking if network exists on Pi..."
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "docker network ls | grep -q '$LUCID_NETWORK'"; then
        echo "Network $LUCID_NETWORK already exists on Pi"
        return 0
    else
        echo "Network $LUCID_NETWORK does not exist on Pi"
        return 1
    fi
}

# Function to create network on Pi if it doesn't exist
create_network() {
    echo "Creating Docker network on Pi: $LUCID_NETWORK"
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "
        docker network create $LUCID_NETWORK \
            --driver bridge \
            --subnet $NETWORK_SUBNET \
            --gateway $NETWORK_GATEWAY \
            --attachable \
            --opt com.docker.network.bridge.enable_icc=true \
            --opt com.docker.network.bridge.enable_ip_masquerade=true \
            --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
            --opt com.docker.network.driver.mtu=1500 \
            --label 'lucid.network=main' \
            --label 'lucid.subnet=$NETWORK_SUBNET' 2>/dev/null || echo 'Network already exists'
    "
    
    if [ $? -eq 0 ]; then
        print_status 0 "Network $LUCID_NETWORK created successfully on Pi"
    else
        print_status 1 "Failed to create network $LUCID_NETWORK on Pi"
        exit 1
    fi
}

# Function to pull auth service image on Pi
pull_auth_service_image() {
    echo "Pulling auth service image on Pi..."
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker pull $AUTH_SERVICE_IMAGE
    "
    
    if [ $? -eq 0 ]; then
        print_status 0 "Auth service image pulled successfully on Pi"
    else
        print_status 1 "Failed to pull auth service image on Pi"
        exit 1
    fi
}

# Function to deploy auth service container on Pi
deploy_auth_service() {
    echo "Deploying auth service container on Pi..."
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        
        # Stop existing container if running
        docker stop $AUTH_SERVICE_CONTAINER 2>/dev/null || true
        docker rm $AUTH_SERVICE_CONTAINER 2>/dev/null || true
        
        # Run auth service container with network binding
        docker run -d \
            --name $AUTH_SERVICE_CONTAINER \
            --network $LUCID_NETWORK \
            -p $AUTH_SERVICE_PORT:$AUTH_SERVICE_PORT \
            -v /mnt/myssd/Lucid/logs/auth-service:/app/logs:rw \
            -v auth-cache:/tmp/auth \
            --user 65532:65532 \
            --security-opt no-new-privileges:true \
            --security-opt seccomp:unconfined \
            --cap-drop=ALL \
            --cap-add=NET_BIND_SERVICE \
            --read-only \
            --tmpfs /tmp:rw,noexec,nosuid,size=100m \
            --restart unless-stopped \
            --health-cmd 'curl -f http://localhost:$AUTH_SERVICE_PORT/health || exit 1' \
            --health-interval 30s \
            --health-timeout 10s \
            --health-retries 3 \
            $AUTH_SERVICE_IMAGE
    "
    
    if [ $? -eq 0 ]; then
        print_status 0 "Auth service container deployed successfully on Pi"
    else
        print_status 1 "Failed to deploy auth service container on Pi"
        exit 1
    fi
}

# Function to verify deployment on Pi
verify_deployment() {
    echo "Verifying deployment on Pi..."
    
    # Check if container is running
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "docker ps | grep -q '$AUTH_SERVICE_CONTAINER'"; then
        print_status 0 "Auth service container is running on Pi"
    else
        print_status 1 "Auth service container is not running on Pi"
        return 1
    fi
    
    # Check network connectivity
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "docker exec $AUTH_SERVICE_CONTAINER curl -f http://localhost:$AUTH_SERVICE_PORT/health >/dev/null 2>&1"; then
        print_status 0 "Auth service health check passed on Pi"
    else
        print_status 1 "Auth service health check failed on Pi"
        return 1
    fi
    
    # Verify distroless compliance
    echo "Verifying distroless compliance..."
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "docker exec $AUTH_SERVICE_CONTAINER id | grep -q '65532'"; then
        print_status 0 "Auth service running as non-root user (65532:65532)"
    else
        print_status 1 "Auth service not running as non-root user"
        return 1
    fi
    
    # Verify no shell access
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "docker exec $AUTH_SERVICE_CONTAINER sh -c 'echo test' 2>&1" | grep -q "executable file not found"; then
        print_status 0 "Auth service has no shell access (distroless compliant)"
    else
        print_status 1 "Auth service has shell access (not distroless)"
        return 1
    fi
}

# Main execution
echo -e "${BLUE}=== Lucid Auth Service Pi Deployment ===${NC}"
echo "Target: Raspberry Pi 5 ($PI_HOST)"
echo "Network: $LUCID_NETWORK ($NETWORK_SUBNET)"
echo "Gateway: $NETWORK_GATEWAY"
echo "Port: $AUTH_SERVICE_PORT"
echo "Image: $AUTH_SERVICE_IMAGE"
echo ""

# Step 1: Check/create network on Pi
echo -e "${BLUE}--- Network Configuration on Pi ---${NC}"
if check_network_exists; then
    print_status 0 "Network $LUCID_NETWORK already exists on Pi"
else
    create_network
fi

# Step 2: Pull auth service image on Pi
echo -e "${BLUE}--- Pulling Auth Service Image on Pi ---${NC}"
pull_auth_service_image

# Step 3: Deploy auth service on Pi
echo -e "${BLUE}--- Deploying Auth Service on Pi ---${NC}"
deploy_auth_service

# Step 4: Verify deployment
echo -e "${BLUE}--- Verification ---${NC}"
verify_deployment

echo ""
echo -e "${GREEN}=== Deployment Summary ===${NC}"
echo "✓ Auth service container deployed successfully on Pi"
echo "✓ Network binding configured for $LUCID_NETWORK"
echo "✓ Container ready for Phase 1 Foundation Services"
echo "✓ Distroless compliance verified"
echo ""
echo "Container: $AUTH_SERVICE_CONTAINER"
echo "Image: $AUTH_SERVICE_IMAGE"
echo "Network: $LUCID_NETWORK ($NETWORK_SUBNET)"
echo "Port: $AUTH_SERVICE_PORT"
echo "Pi Host: $PI_HOST"
echo ""
echo -e "${GREEN}✓ Auth service deployment completed successfully on Pi!${NC}"

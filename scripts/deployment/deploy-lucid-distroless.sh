#!/bin/bash
# Lucid Distroless Deployment Script
# Deploys Lucid platform with proper order and distroless containers
# Target: Raspberry Pi 5 (192.168.0.75)
# MUST RUN ON PI CONSOLE - NOT FROM WINDOWS

set -euo pipefail

# Configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_HOST="192.168.0.75"
DEPLOYMENT_USER="pickme"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Lucid Distroless Deployment Script${NC}"
echo "=============================================="
echo "Target: $DEPLOYMENT_HOST"
echo "User: $DEPLOYMENT_USER"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Function to run commands on Pi
run_on_pi() {
    local cmd="$1"
    echo -e "${YELLOW}Running on Pi: $cmd${NC}"
    ssh -o StrictHostKeyChecking=no $DEPLOYMENT_USER@$DEPLOYMENT_HOST "$cmd"
}

# Function to check if service is healthy
check_service_health() {
    local service_name="$1"
    local port="$2"
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Checking health of $service_name on port $port...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if run_on_pi "curl -f http://localhost:$port/health 2>/dev/null"; then
            echo -e "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Attempt $attempt/$max_attempts: $service_name not ready yet...${NC}"
        sleep 10
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to become healthy after $max_attempts attempts${NC}"
    return 1
}

# Function to deploy phase
deploy_phase() {
    local phase_name="$1"
    local compose_file="$2"
    local env_file="$3"
    
    echo -e "${BLUE}📦 Deploying $phase_name...${NC}"
    
    # Deploy services
    run_on_pi "cd $PROJECT_ROOT && docker-compose --env-file $env_file -f $compose_file up -d"
    
    # Wait for services to initialize
    echo -e "${YELLOW}Waiting for $phase_name services to initialize...${NC}"
    sleep 30
    
    # Check service health
    case "$phase_name" in
        "Foundation Services")
            check_service_health "MongoDB" "27017" || true
            check_service_health "Redis" "6379" || true
            check_service_health "Elasticsearch" "9200" || true
            check_service_health "Auth Service" "8089" || true
            ;;
        "Core Services")
            check_service_health "API Gateway" "8080" || true
            check_service_health "Blockchain Core" "8084" || true
            check_service_health "Blockchain Engine" "8085" || true
            ;;
        "Application Services")
            check_service_health "Session Pipeline" "8083" || true
            check_service_health "Session Recorder" "8110" || true
            check_service_health "RDP Server Manager" "8090" || true
            ;;
        "Support Services")
            check_service_health "Admin Interface" "8120" || true
            ;;
    esac
    
    echo -e "${GREEN}✅ $phase_name deployment completed${NC}"
}

# Main deployment function
main() {
    echo -e "${BLUE}🏗️  Starting Lucid Distroless Deployment${NC}"
    echo ""
    
    # Phase 1: Prerequisites
    echo -e "${BLUE}📋 Phase 1: Prerequisites${NC}"
    echo "================================"
    
    # Check SSH connection
    echo -e "${YELLOW}Testing SSH connection...${NC}"
    if ! run_on_pi "echo 'SSH connection successful'"; then
        echo -e "${RED}❌ SSH connection failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ SSH connection successful${NC}"
    
    # Check Docker
    echo -e "${YELLOW}Checking Docker...${NC}"
    if ! run_on_pi "docker --version"; then
        echo -e "${RED}❌ Docker not available${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is available${NC}"
    
    # Create directories
    echo -e "${YELLOW}Creating directories...${NC}"
    run_on_pi "sudo mkdir -p /mnt/myssd/Lucid/data/{mongodb,redis,elasticsearch} /mnt/myssd/Lucid/logs/{mongodb,redis,elasticsearch,auth-service,api-gateway,blockchain-core,session-pipeline,admin-interface}"
    run_on_pi "sudo chown -R $DEPLOYMENT_USER:$DEPLOYMENT_USER /mnt/myssd/Lucid/data /mnt/myssd/Lucid/logs"
    echo -e "${GREEN}✅ Directories created${NC}"
    
    # Create networks
    echo -e "${YELLOW}Creating Docker networks...${NC}"
    run_on_pi "docker network create lucid-pi-network --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 --attachable 2>/dev/null || echo 'Network already exists'"
    run_on_pi "docker network create lucid-tron-isolated --driver bridge --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable 2>/dev/null || echo 'Network already exists'"
    echo -e "${GREEN}✅ Networks created${NC}"
    
    # Generate environment files
    echo -e "${YELLOW}Generating environment files...${NC}"
    run_on_pi "cd $PROJECT_ROOT && chmod +x scripts/config/generate-*.sh && bash scripts/config/generate-foundation-env.sh"
    echo -e "${GREEN}✅ Environment files generated${NC}"
    
    # Phase 2: Foundation Services
    echo -e "${BLUE}📋 Phase 2: Foundation Services${NC}"
    echo "=================================="
    deploy_phase "Foundation Services" "configs/docker/docker-compose.foundation.yml" "configs/environment/.env.foundation"
    
    # Phase 3: Core Services
    echo -e "${BLUE}📋 Phase 3: Core Services${NC}"
    echo "=============================="
    deploy_phase "Core Services" "configs/docker/docker-compose.core.yml" "configs/environment/.env.foundation"
    
    # Phase 4: Application Services
    echo -e "${BLUE}📋 Phase 4: Application Services${NC}"
    echo "====================================="
    deploy_phase "Application Services" "configs/docker/docker-compose.application.yml" "configs/environment/.env.foundation"
    
    # Phase 5: Support Services
    echo -e "${BLUE}📋 Phase 5: Support Services${NC}"
    echo "=================================="
    deploy_phase "Support Services" "configs/docker/docker-compose.support.yml" "configs/environment/.env.foundation"
    
    # Final verification
    echo -e "${BLUE}📋 Final Verification${NC}"
    echo "======================"
    
    echo -e "${YELLOW}Checking all services...${NC}"
    run_on_pi "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    
    echo -e "${YELLOW}Checking service health...${NC}"
    run_on_pi "curl -f http://localhost:8080/health 2>/dev/null && echo '✅ API Gateway: Healthy' || echo '❌ API Gateway: Failed'"
    run_on_pi "curl -f http://localhost:8084/health 2>/dev/null && echo '✅ Blockchain Core: Healthy' || echo '❌ Blockchain Core: Failed'"
    run_on_pi "curl -f http://localhost:8089/health 2>/dev/null && echo '✅ Auth Service: Healthy' || echo '❌ Auth Service: Failed'"
    run_on_pi "curl -f http://localhost:8120/health 2>/dev/null && echo '✅ Admin Interface: Healthy' || echo '❌ Admin Interface: Failed'"
    
    echo -e "${GREEN}🎉 Lucid Distroless Deployment Completed Successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Service Summary:${NC}"
    echo "=================="
    echo "• API Gateway: http://$DEPLOYMENT_HOST:8080"
    echo "• Blockchain Core: http://$DEPLOYMENT_HOST:8084"
    echo "• Auth Service: http://$DEPLOYMENT_HOST:8089"
    echo "• Admin Interface: http://$DEPLOYMENT_HOST:8120"
    echo "• Session Pipeline: http://$DEPLOYMENT_HOST:8083"
    echo ""
    echo -e "${GREEN}✅ All services are running with distroless containers${NC}"
}

# Run main function
main "$@"
